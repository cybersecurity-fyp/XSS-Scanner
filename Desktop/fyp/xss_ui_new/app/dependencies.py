"""
app/dependencies.py — Shared FastAPI dependency functions.
Use these in route handlers via Depends() or direct calls.
"""

import ipaddress
from urllib.parse import urlparse
from fastapi import Request, HTTPException


def get_session_user(request: Request) -> dict | None:
    """Return the current session user or None."""
    return request.session.get('user')


def require_auth(request: Request) -> dict:
    """Raise 401 if not authenticated. Returns the user dict."""
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user


def require_admin(request: Request) -> dict:
    """Raise 403 if user is not an admin."""
    user = require_auth(request)
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin access required')
    return user


def validate_safe_url(url: str) -> str:
    """
    Validate a scan target URL for SSRF safety.
    Raises HTTPException(400) on invalid/private URLs.
    Returns the URL if safe.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise HTTPException(400, 'URL must start with http:// or https://')

        host = parsed.hostname
        if not host:
            raise HTTPException(400, 'Invalid URL: no hostname')

        # Block cloud metadata endpoints (by IP or hostname)
        if host in ('169.254.169.254', 'metadata.google.internal', '168.63.129.16'):
            raise HTTPException(400, 'Scanning cloud metadata endpoints is not permitted')

        # Block loopback hostnames explicitly (ipaddress won't resolve 'localhost')
        _LOOPBACK_HOSTS = frozenset({'localhost', 'localhost.localdomain',
                                     'ip6-localhost', 'ip6-loopback'})
        if host.lower() in _LOOPBACK_HOSTS:
            raise HTTPException(400, 'Scanning private/internal addresses is not permitted')

        # Block private/loopback IPs
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise HTTPException(400, 'Scanning private/internal addresses is not permitted')
        except ValueError:
            pass  # It's a public hostname — OK

        return url

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, 'Invalid URL')
