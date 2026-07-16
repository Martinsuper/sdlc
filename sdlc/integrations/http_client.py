"""HTTP client wrapper around httpx with SSRF protection."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

import httpx


class SSRFError(Exception):
    """Raised when a request targets a private/reserved IP address."""


def _is_private_url(url: str) -> bool:
    """Return True if *url* resolves to a private or reserved IP range.

    Blocks:
      - Loopback: 127.x.x.x
      - Link-local: 169.254.x.x (AWS metadata), fe80::/10
      - Private: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
      - Unspecified: 0.0.0.0, ::
      - localhost hostname
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return False

    # Block literal 'localhost'
    if hostname.lower() == "localhost":
        return True

    # Try to parse as an IP address directly
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved
    except ValueError:
        pass

    # Not a literal IP -- hostname resolution is not performed here
    # to avoid DNS rebinding attacks.  Hostnames that look like they
    # embed private IPs (e.g. 127.0.0.1.nip.io) are best handled at
    # the network level.  We block obvious patterns:
    return bool(hostname.endswith(".internal") or hostname.endswith(".local"))


class HTTPClient:
    """Synchronous HTTP client with SSRF protection."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

    def _check_ssrf(self, url: str) -> None:
        """Raise SSRFError if *url* targets a private/reserved address."""
        if _is_private_url(url):
            raise SSRFError(
                f"Request to {url} blocked: target is a private/reserved address"
            )

    def get(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a GET request."""
        self._check_ssrf(url)
        return self._client.get(url, **kwargs)  # type: ignore[arg-type]

    def post(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a POST request."""
        self._check_ssrf(url)
        return self._client.post(url, **kwargs)  # type: ignore[arg-type]

    def put(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a PUT request."""
        self._check_ssrf(url)
        return self._client.put(url, **kwargs)  # type: ignore[arg-type]

    def delete(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a DELETE request."""
        self._check_ssrf(url)
        return self._client.delete(url, **kwargs)  # type: ignore[arg-type]

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
