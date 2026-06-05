"""HTTP client wrapper around httpx."""

from __future__ import annotations

import httpx


class HTTPClient:
    """Synchronous HTTP client with sensible defaults."""

    def __init__(self, timeout: int = 30) -> None:
        self._client = httpx.Client(timeout=timeout)

    def get(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a GET request."""
        return self._client.get(url, **kwargs)  # type: ignore[arg-type]

    def post(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a POST request."""
        return self._client.post(url, **kwargs)  # type: ignore[arg-type]

    def put(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a PUT request."""
        return self._client.put(url, **kwargs)  # type: ignore[arg-type]

    def delete(self, url: str, **kwargs: object) -> httpx.Response:
        """Send a DELETE request."""
        return self._client.delete(url, **kwargs)  # type: ignore[arg-type]

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> HTTPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
