"""Authentication module for Big Beautiful Screens.

Handles Clerk authentication in SaaS mode using the official Clerk SDK.
In self-hosted mode, authentication is bypassed.
"""

from dataclasses import dataclass
from typing import Annotated
from urllib.parse import quote

from clerk_backend_api import AuthenticateRequestOptions, Clerk
from fastapi import Depends, Header, HTTPException, Request

from .config import AppMode, get_settings

# Clerk SDK instance (lazy initialized)
_clerk_client: Clerk | None = None


def _get_clerk() -> Clerk:
    """Get or create the Clerk client instance."""
    global _clerk_client
    if _clerk_client is None:
        settings = get_settings()
        _clerk_client = Clerk(bearer_auth=settings.CLERK_SECRET_KEY)
    return _clerk_client


def _auth_debug_log(settings, message: str) -> None:
    if settings.AUTH_DEBUG:
        print(message)


def _get_request_origin(request: Request) -> str | None:
    """Build request origin, honoring proxy headers if present."""
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host = forwarded_host or request.headers.get("host")
    scheme = forwarded_proto or request.url.scheme
    if not host:
        return None
    return f"{scheme}://{host}".rstrip("/")


def get_clerk_sign_in_url(redirect_url: str, request: Request | None = None) -> str:
    """Get the Clerk sign-in URL with redirect.

    The redirect goes through /auth/callback first to set session cookies,
    then to the final destination.
    """
    settings = get_settings()

    if not settings.CLERK_SIGN_IN_URL:
        return f"/sign-in?redirect_url={redirect_url}"

    request_origin = _get_request_origin(request) if request else None
    app_url = (request_origin or settings.APP_URL).rstrip("/")
    # Redirect to auth/callback first, which will then redirect to the final URL
    callback_url = f"{app_url}/auth/callback?redirect_url={quote(redirect_url)}"
    sign_in_base = settings.CLERK_SIGN_IN_URL.rstrip("/")

    return f"{sign_in_base}?redirect_url={quote(callback_url)}"


@dataclass
class AuthUser:
    """Authenticated user information."""

    user_id: str
    email: str | None = None
    name: str | None = None
    org_id: str | None = None
    org_role: str | None = None


def _get_session_cookie(request: Request) -> tuple[str | None, str | None]:
    """Return the session cookie name/value, supporting Clerk instance suffixes."""
    if "__session" in request.cookies:
        return "__session", request.cookies.get("__session")
    for name, value in request.cookies.items():
        if name.startswith("__session"):
            return name, value
    return None, None


def has_session_cookie(request: Request) -> bool:
    """Check if the request has a session cookie (even if expired)."""
    name, value = _get_session_cookie(request)
    return bool(name and value)


def _get_clerk_db_jwt(request: Request) -> str | None:
    """Return Clerk dev browser token from query or cookies."""
    db_jwt = request.query_params.get("__clerk_db_jwt")
    if db_jwt:
        return db_jwt
    if "__clerk_db_jwt" in request.cookies:
        return request.cookies.get("__clerk_db_jwt")
    for name, value in request.cookies.items():
        if name.startswith("__clerk_db_jwt"):
            return value
    return None


def _has_clerk_token(request: Request) -> bool:
    """Check if request has any Clerk token (cookie, header, or query param)."""
    if has_session_cookie(request):
        return True
    if _get_clerk_db_jwt(request):
        return True
    auth_header = request.headers.get("Authorization", "")
    return bool(auth_header.startswith("Bearer "))


async def get_current_user(request: Request) -> AuthUser | None:
    """Get the current authenticated user, or None if not authenticated.

    Uses the Clerk SDK to verify tokens, handling both development mode
    (__clerk_db_jwt) and production mode (__session cookie).
    """
    settings = get_settings()

    # In self-hosted mode, return None (no authentication)
    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return None

    _auth_debug_log(settings, "=== GET_CURRENT_USER DEBUG ===")
    _auth_debug_log(settings, f"Cookies: {list(request.cookies.keys())}")
    session_name, session_value = _get_session_cookie(request)
    _auth_debug_log(settings, f"Has __session: {session_value is not None}")
    if session_name and session_name != "__session":
        _auth_debug_log(settings, f"Session cookie name: {session_name}")
    db_jwt = _get_clerk_db_jwt(request)
    _auth_debug_log(settings, f"Has __clerk_db_jwt param: {db_jwt is not None}")

    # Check if there's any token to verify
    if not _has_clerk_token(request):
        _auth_debug_log(settings, "No Clerk token found, returning None")
        return None

    try:
        clerk = _get_clerk()

        # In dev mode, Clerk uses __clerk_db_jwt query param instead of cookies
        # We need to verify this token via the Clerk API
        db_jwt = _get_clerk_db_jwt(request)
        if db_jwt:
            # Verify the dev browser token via Clerk API
            try:
                client = clerk.clients.verify(request={"token": db_jwt})
                if client and client.sessions:
                    # Get the most recent active session
                    for session in client.sessions:
                        if session.status == "active" and session.user_id:
                            # Fetch user details
                            user = clerk.users.get(user_id=session.user_id)
                            if user:
                                email = None
                                if user.email_addresses:
                                    primary = next(
                                        (
                                            e
                                            for e in user.email_addresses
                                            if e.id == user.primary_email_address_id
                                        ),
                                        user.email_addresses[0] if user.email_addresses else None,
                                    )
                                    if primary:
                                        email = primary.email_address

                                return AuthUser(
                                    user_id=user.id,
                                    email=email,
                                    name=f"{user.first_name or ''} {user.last_name or ''}".strip()
                                    or None,
                                    org_id=None,
                                    org_role=None,
                                )
            except Exception as e:
                print(f"Clerk dev token verification failed: {e}")

        # Standard flow: use authenticate_request for cookies/headers
        authorized_parties = [settings.APP_URL.rstrip("/")]
        request_origin = _get_request_origin(request)
        if request_origin and request_origin not in authorized_parties:
            authorized_parties.append(request_origin)

        _auth_debug_log(
            settings,
            f"Calling authenticate_request with authorized_parties: {authorized_parties}",
        )
        request_state = clerk.authenticate_request(
            request,
            AuthenticateRequestOptions(
                authorized_parties=authorized_parties,
            ),
        )

        _auth_debug_log(
            settings,
            "authenticate_request result: "
            f"is_signed_in={request_state.is_signed_in}, reason={request_state.reason}",
        )

        if not request_state.is_signed_in:
            if request_state.reason:
                _auth_debug_log(settings, f"Clerk auth failed: {request_state.reason}")
            return None

        # Extract user info from the verified token payload
        payload = request_state.payload or {}
        user_id = payload.get("sub")
        if not user_id:
            return None

        return AuthUser(
            user_id=user_id,
            email=payload.get("email"),
            name=payload.get("name"),
            org_id=payload.get("org_id"),
            org_role=payload.get("org_role"),
        )

    except Exception as e:
        print(f"Clerk authentication error: {e}")
        return None


async def require_auth(request: Request) -> AuthUser:
    """Require authentication - raises 401 if not authenticated."""
    settings = get_settings()

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return AuthUser(user_id="self-hosted", email=None, name="Self-Hosted User")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_auth_or_api_key(
    request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")
) -> AuthUser | str:
    """Require either Clerk authentication or API key."""
    settings = get_settings()

    if x_api_key:
        return x_api_key

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        raise HTTPException(
            status_code=401, detail="API key required", headers={"X-API-Key": "Required"}
        )

    user = await get_current_user(request)
    if user:
        return user

    raise HTTPException(
        status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"}
    )


# FastAPI dependency types
OptionalUser = Annotated[AuthUser | None, Depends(get_current_user)]
RequiredUser = Annotated[AuthUser, Depends(require_auth)]
AuthOrApiKey = Annotated[AuthUser | str, Depends(require_auth_or_api_key)]


# ============== Access Control Helpers ==============


def can_access_screen(user: AuthUser | None, screen: dict) -> bool:
    """Check if a user can access (view) a screen."""
    settings = get_settings()

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    if not screen.get("owner_id") and not screen.get("org_id"):
        return True

    if not user:
        return False

    if screen.get("owner_id") == user.user_id:
        return True

    return bool(screen.get("org_id") and screen.get("org_id") == user.org_id)


def can_modify_screen(user: AuthUser | None, screen: dict, api_key: str | None = None) -> bool:
    """Check if a user can modify a screen."""
    settings = get_settings()

    if api_key and screen.get("api_key") == api_key:
        return True

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return False

    if not user:
        return False

    if screen.get("owner_id") == user.user_id:
        return True

    return bool(
        screen.get("org_id")
        and screen.get("org_id") == user.org_id
        and user.org_role in ("admin", "owner")
    )


def can_access_theme(user: AuthUser | None, theme: dict) -> bool:
    """Check if a user can access (view) a theme."""
    settings = get_settings()

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    if theme.get("is_builtin") or not theme.get("owner_id"):
        return True

    if not user:
        return False

    return theme.get("owner_id") == user.user_id


def can_modify_theme(user: AuthUser | None, theme: dict) -> bool:
    """Check if a user can modify a theme."""
    settings = get_settings()

    if settings.APP_MODE == AppMode.SELF_HOSTED:
        return True

    if not user:
        return False

    if theme.get("is_builtin"):
        return False

    return theme.get("owner_id") == user.user_id
