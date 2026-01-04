"""RSS Proxy endpoint for fetching external RSS feeds."""

import ipaddress
import re
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from ..rate_limit import limiter

router = APIRouter(tags=["Proxy"])

# Namespaces commonly used in RSS feeds
NAMESPACES = {
    "media": "http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "atom": "http://www.w3.org/2005/Atom",
}

# Regex to extract first image from HTML content
IMG_TAG_REGEX = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

# Allowed URL schemes for security
ALLOWED_SCHEMES = ("http://", "https://")

# Maximum response size (5MB)
MAX_RESPONSE_SIZE = 5 * 1024 * 1024

# Request timeout (seconds)
REQUEST_TIMEOUT = 10.0

# Blocked hostnames (case-insensitive)
BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",  # GCP metadata
}

# Rate limit for proxy requests
RATE_LIMIT_PROXY = "30/minute"


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private, loopback, or link-local."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            # AWS/cloud metadata endpoint
            or ip_str == "169.254.169.254"
        )
    except ValueError:
        return False


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validate URL is safe to fetch (SSRF protection).
    Returns (is_safe, error_message).
    """
    # Check scheme
    if not url.startswith(ALLOWED_SCHEMES):
        return False, "URL must use http or https scheme"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a hostname"

    # Block known dangerous hostnames
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return False, "This hostname is not allowed"

    # Resolve hostname and check for private IPs
    try:
        # Get all IPs for the hostname
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC)
        for info in addr_info:
            ip = info[4][0]
            if is_private_ip(ip):
                return False, "URLs pointing to private/internal networks are not allowed"
    except socket.gaierror:
        return False, "Could not resolve hostname"

    return True, ""


@router.get("/api/v1/proxy/rss")
@limiter.limit(RATE_LIMIT_PROXY)
async def proxy_rss_feed(
    request: Request, url: str = Query(..., description="RSS feed URL to fetch")
):
    """
    Fetch and parse an RSS feed, returning JSON.

    This proxy endpoint fetches RSS/Atom feeds from external URLs and converts
    them to a normalized JSON format, bypassing browser CORS restrictions.

    Security: Blocks requests to private/internal networks (SSRF protection).
    Rate limited to 30 requests per minute per IP.

    Returns:
        JSON object with feed title, description, and items array
    """
    # Validate URL is safe (SSRF protection)
    is_safe, error = is_safe_url(url)
    if not is_safe:
        raise HTTPException(status_code=400, detail=error)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "BigBeautifulScreens/1.0 (RSS Widget)",
                    "Accept": "application/rss+xml, application/xml, text/xml, */*",
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"Feed returned status {response.status_code}",
                )

            # Check content size
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_RESPONSE_SIZE:
                raise HTTPException(status_code=502, detail="Feed response too large")

            content = response.text

    except httpx.TimeoutException as e:
        raise HTTPException(status_code=504, detail="Feed request timed out") from e
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch feed: {str(e)}") from e

    # Parse the feed
    try:
        feed_data = parse_feed(content)
        return feed_data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse feed: {str(e)}") from e


def parse_feed(xml_content: str) -> dict:
    """Parse RSS or Atom feed XML into a normalized dict."""
    root = ET.fromstring(xml_content)

    # Detect feed type
    if root.tag == "rss" or root.find("channel") is not None:
        return parse_rss(root)
    elif root.tag.endswith("feed") or "{http://www.w3.org/2005/Atom}" in root.tag:
        return parse_atom(root)
    else:
        raise ValueError("Unknown feed format")


def parse_rss(root: ET.Element) -> dict:
    """Parse RSS 2.0 feed."""
    channel = root.find("channel")
    if channel is None:
        raise ValueError("No channel element in RSS feed")

    feed = {
        "title": get_text(channel, "title"),
        "description": get_text(channel, "description"),
        "link": get_text(channel, "link"),
        "items": [],
    }

    for item in channel.findall("item"):
        description = get_text(item, "description")
        image = extract_image_rss(item, description)

        feed["items"].append(
            {
                "title": get_text(item, "title"),
                "description": description,
                "link": get_text(item, "link"),
                "pubDate": get_text(item, "pubDate"),
                "guid": get_text(item, "guid"),
                "image": image,
            }
        )

    return feed


def extract_image_rss(item: ET.Element, description: str | None) -> str | None:
    """Extract image URL from RSS item using multiple strategies."""
    # 1. Check <enclosure> with image type
    enclosure = item.find("enclosure")
    if enclosure is not None:
        enc_type = enclosure.get("type", "")
        enc_url = enclosure.get("url")
        if enc_url and enc_type.startswith("image/"):
            return enc_url

    # 2. Check <media:content> (Media RSS)
    media_content = item.find("media:content", NAMESPACES)
    if media_content is not None:
        media_url = media_content.get("url")
        media_type = media_content.get("type", "")
        medium = media_content.get("medium", "")
        if media_url and (media_type.startswith("image/") or medium == "image"):
            return media_url

    # 3. Check <media:thumbnail>
    media_thumb = item.find("media:thumbnail", NAMESPACES)
    if media_thumb is not None:
        thumb_url = media_thumb.get("url")
        if thumb_url:
            return thumb_url

    # 4. Extract from description HTML
    if description:
        match = IMG_TAG_REGEX.search(description)
        if match:
            return match.group(1)

    # 5. Check <content:encoded> for images
    content_encoded = item.find("content:encoded", NAMESPACES)
    if content_encoded is not None and content_encoded.text:
        match = IMG_TAG_REGEX.search(content_encoded.text)
        if match:
            return match.group(1)

    return None


def parse_atom(root: ET.Element) -> dict:
    """Parse Atom feed."""
    # Handle namespace
    ns = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}

    # Try with namespace first, then without
    def find(elem, tag, namespace="atom"):
        result = elem.find(f"{namespace}:{tag}", ns)
        if result is None:
            result = elem.find(tag)
        return result

    def findall(elem, tag, namespace="atom"):
        result = elem.findall(f"{namespace}:{tag}", ns)
        if not result:
            result = elem.findall(tag)
        return result

    title_elem = find(root, "title")
    subtitle_elem = find(root, "subtitle")

    feed = {
        "title": title_elem.text if title_elem is not None else None,
        "description": subtitle_elem.text if subtitle_elem is not None else None,
        "link": None,
        "items": [],
    }

    # Get feed link
    for link in findall(root, "link"):
        if link.get("rel", "alternate") == "alternate":
            feed["link"] = link.get("href")
            break

    for entry in findall(root, "entry"):
        title_elem = find(entry, "title")
        summary_elem = find(entry, "summary")
        content_elem = find(entry, "content")
        updated_elem = find(entry, "updated")
        published_elem = find(entry, "published")
        id_elem = find(entry, "id")

        # Get entry link
        entry_link = None
        for link in findall(entry, "link"):
            if link.get("rel", "alternate") == "alternate":
                entry_link = link.get("href")
                break

        # Get description text
        description = (
            summary_elem.text
            if summary_elem is not None
            else content_elem.text
            if content_elem is not None
            else None
        )

        # Extract image
        image = extract_image_atom(entry, description, ns)

        feed["items"].append(
            {
                "title": title_elem.text if title_elem is not None else None,
                "description": description,
                "link": entry_link,
                "pubDate": (
                    published_elem.text
                    if published_elem is not None
                    else updated_elem.text
                    if updated_elem is not None
                    else None
                ),
                "guid": id_elem.text if id_elem is not None else None,
                "image": image,
            }
        )

    return feed


def extract_image_atom(entry: ET.Element, description: str | None, ns: dict) -> str | None:
    """Extract image URL from Atom entry."""
    # 1. Check for link with rel="enclosure" and image type
    for link in entry.findall("atom:link", ns) + entry.findall("link"):
        if link.get("rel") == "enclosure":
            link_type = link.get("type", "")
            if link_type.startswith("image/"):
                return link.get("href")

    # 2. Check <media:content>
    media_content = entry.find("media:content", ns)
    if media_content is not None:
        media_url = media_content.get("url")
        media_type = media_content.get("type", "")
        medium = media_content.get("medium", "")
        if media_url and (media_type.startswith("image/") or medium == "image"):
            return media_url

    # 3. Check <media:thumbnail>
    media_thumb = entry.find("media:thumbnail", ns)
    if media_thumb is not None:
        thumb_url = media_thumb.get("url")
        if thumb_url:
            return thumb_url

    # 4. Extract from description/content HTML
    if description:
        match = IMG_TAG_REGEX.search(description)
        if match:
            return match.group(1)

    return None


def get_text(elem: ET.Element, tag: str) -> str | None:
    """Get text content of a child element."""
    child = elem.find(tag)
    return child.text if child is not None else None
