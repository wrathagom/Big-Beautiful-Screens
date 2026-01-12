"""Clerk Frontend API Proxy.

Proxies requests from your app domain to Clerk's Frontend API.
This allows cookies to be set on your domain instead of Clerk's subdomain.

See: https://clerk.com/docs/advanced-usage/using-proxies
"""

import httpx
from fastapi import APIRouter, Request, Response

router = APIRouter(include_in_schema=False)

# Clerk Frontend API base URL
CLERK_FAPI_URL = "https://clerk.bigbeautifulscreens.com"


@router.api_route(
    "/__clerk/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def clerk_proxy(request: Request, path: str):
    """Proxy requests to Clerk Frontend API.

    All requests to /__clerk/* are forwarded to clerk.bigbeautifulscreens.com/*
    with headers and body intact.
    """
    # Build the target URL
    target_url = f"{CLERK_FAPI_URL}/{path}"

    # Include query params
    if request.query_params:
        target_url += f"?{request.query_params}"

    # Get request body
    body = await request.body()

    # Forward headers (excluding host)
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ("host", "content-length"):
            headers[key] = value

    # Make the proxied request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                follow_redirects=False,
            )

            # Build response with all headers from Clerk
            proxy_response = Response(
                content=response.content,
                status_code=response.status_code,
            )

            # Forward response headers
            for key, value in response.headers.items():
                # Skip hop-by-hop headers
                if key.lower() not in (
                    "content-encoding",
                    "content-length",
                    "transfer-encoding",
                    "connection",
                ):
                    proxy_response.headers[key] = value

            return proxy_response

        except httpx.RequestError as e:
            print(f"Clerk proxy error: {e}")
            return Response(
                content=f"Proxy error: {e}",
                status_code=502,
            )
