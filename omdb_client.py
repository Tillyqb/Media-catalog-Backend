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

    def get_by_imdb_id(self, imdb_id: str) -> dict[str, Any]:
        """Fetch full details for one IMDb id."""
        return self._request({"i": imdb_id, "plot": "short"})

    def search(self, query: str, page: int = 1) -> dict[str, Any]:
        """Search movies by text query."""
        return self._request({"s": query, "page": page})

    def search_with_details(self, query: str, page: int = 1) -> list[dict[str, Any]]:
        """Search movies and hydrate each result with detailed OMDb fields."""
        search_payload = self.search(query=query, page=page)
        search_results = search_payload.get("Search", [])

        detailed_results: list[dict[str, Any]] = []
        for item in search_results:
            imdb_id = item.get("imdbID")
            if not imdb_id:
                continue
            detailed_results.append(self.get_by_imdb_id(imdb_id))

        return detailed_results
