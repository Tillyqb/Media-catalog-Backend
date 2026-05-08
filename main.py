"""API entry point for the media catalog backend."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from mysql.connector import Error

from access_layer import DatabaseConfig, MySQLMediaAccessLayer
from omdb_client import OMDBClient

load_dotenv()

app = FastAPI(title="Media Catalog Backend", version="0.1.0")


def _build_services() -> tuple[MySQLMediaAccessLayer, OMDBClient]:
    """Initialize dependencies from environment variables."""
    config = DatabaseConfig.from_env()
    access_layer = MySQLMediaAccessLayer(config)

    omdb_api_key = os.getenv("OMDB_API_KEY", "")
    omdb_client = OMDBClient(omdb_api_key)
    return access_layer, omdb_client


@app.on_event("startup")
def startup_checks() -> None:
    """Validate DB and OMDb connectivity on boot."""
    try:
        access_layer, omdb_client = _build_services()
        access_layer.initialize_schema()
        access_layer.list_media_items(limit=1)
        if not omdb_client.api_key:
            raise ValueError("OMDB_API_KEY is required")
    except ValueError as exc:
        raise RuntimeError(f"Configuration error: {exc}") from exc
    except Error as exc:
        raise RuntimeError(f"MySQL initialization failed: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    """Simple health endpoint for service checks."""
    return {"status": "ok"}


@app.get("/movies/search")
def search_movies(
    title: str = Query(..., min_length=1, description="Movie title search query"),
    page: int = Query(1, ge=1, le=100),
) -> JSONResponse:
    """Search OMDb by title and return detailed records for frontend display."""
    try:
        _, omdb_client = _build_services()
        movies = omdb_client.search_with_details(query=title, page=page)
    except ValueError as exc:
        message = str(exc)
        if "Movie not found" in message:
            return JSONResponse(
                status_code=200,
                content={"query": title, "count": 0, "results": []},
            )
        raise HTTPException(status_code=400, detail=message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"OMDb request failed: {exc}") from exc

    return JSONResponse(
        status_code=200,
        content={
            "query": title,
            "count": len(movies),
            "results": movies,
        },
    )
