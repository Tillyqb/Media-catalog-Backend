"""Simple OMDb API client utilities."""

from typing import Any, Optional

import requests


class OMDBClient:
    """Client for the OMDb API."""

    BASE_URL = "https://www.omdbapi.com/"

    def __init__(self, api_key: str, timeout_seconds: int = 10):
        if not api_key:
            raise ValueError("OMDB_API_KEY is required")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        query = {"apikey": self.api_key, **params}
        response = requests.get(self.BASE_URL, params=query, timeout=self.timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        if payload.get("Response") == "False":
            error_message = payload.get("Error", "Unknown OMDb error")
            raise ValueError(f"OMDb API error: {error_message}")

        return payload

    def get_by_title(self, title: str, year: Optional[int] = None) -> dict[str, Any]:
        """Fetch a single movie by title, optionally narrowed by year."""
        params: dict[str, Any] = {"t": title}
        if year is not None:
            params["y"] = year
        return self._request(params)

    def search(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search movies by text query."""
        return self._request({"s": query, "page": page})
