"""Flask API entry point for the media catalog backend."""

import os
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from mysql.connector import Error

from access_layer import DatabaseConfig, MySQLMediaAccessLayer
from omdb_client import OMDBClient

load_dotenv()


def _build_services() -> tuple[MySQLMediaAccessLayer, OMDBClient]:
    """Initialize dependencies from environment variables."""
    config = DatabaseConfig.from_env()
    access_layer = MySQLMediaAccessLayer(config)

    omdb_api_key = os.getenv("OMDB_API_KEY", "")
    omdb_client = OMDBClient(omdb_api_key)
    return access_layer, omdb_client


def _serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    """Convert DB row values into JSON-safe values."""
    serialized: dict[str, Any] = {}
    for key, value in record.items():
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _startup_checks(access_layer: MySQLMediaAccessLayer, omdb_client: OMDBClient) -> None:
    """Validate DB and OMDb connectivity on boot."""
    try:
        access_layer.initialize_schema()
        access_layer.list_media_items(limit=1)
        if not omdb_client.api_key:
            raise ValueError("OMDB_API_KEY is required")
    except ValueError as exc:
        raise RuntimeError(f"Configuration error: {exc}") from exc
    except Error as exc:
        raise RuntimeError(f"MySQL initialization failed: {exc}") from exc


app = Flask(__name__)
ACCESS_LAYER, OMDB_CLIENT = _build_services()
_startup_checks(ACCESS_LAYER, OMDB_CLIENT)


@app.get("/health")
def health() -> Any:
    """Simple health endpoint for service checks."""
    return jsonify({"status": "ok"})


@app.get("/movies/search")
def search_movies() -> Any:
    """Search OMDb by title and return detailed records for frontend display."""
    title = request.args.get("title", "").strip()
    page = request.args.get("page", default=1, type=int)

    if not title:
        return jsonify({"detail": "title query parameter is required"}), 400
    if page is None or page < 1 or page > 100:
        return jsonify({"detail": "page must be between 1 and 100"}), 400

    try:
        movies = OMDB_CLIENT.search_with_details(query=title, page=page)
    except ValueError as exc:
        message = str(exc)
        if "Movie not found" in message:
            return jsonify({"query": title, "count": 0, "results": []}), 200
        return jsonify({"detail": message}), 400
    except Exception as exc:
        return jsonify({"detail": f"OMDb request failed: {exc}"}), 502

    return jsonify(
        {
            "query": title,
            "count": len(movies),
            "results": movies,
        }
    )


@app.get("/media-items")
def list_media_items() -> Any:
    """List stored media items with pagination and optional media_type filter."""
    limit = request.args.get("limit", default=100, type=int)
    offset = request.args.get("offset", default=0, type=int)
    media_type = request.args.get("media_type")

    try:
        rows = ACCESS_LAYER.list_media_items(limit=limit, offset=offset, media_type=media_type)
    except ValueError as exc:
        return jsonify({"detail": str(exc)}), 400

    return jsonify({"count": len(rows), "results": [_serialize_record(row) for row in rows]})


@app.get("/media-items/<int:item_id>")
def get_media_item(item_id: int) -> Any:
    """Fetch one stored media item by id."""
    row = ACCESS_LAYER.get_media_item(item_id)
    if not row:
        return jsonify({"detail": "Media item not found"}), 404
    return jsonify(_serialize_record(row))


@app.post("/media-items")
def create_media_item() -> Any:
    """Create one stored media item."""
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    file_path = payload.get("file_path")
    media_type = payload.get("media_type")

    if not title or not file_path:
        return jsonify({"detail": "title and file_path are required"}), 400

    item_id = ACCESS_LAYER.create_media_item(
        title=str(title),
        file_path=str(file_path),
        media_type=str(media_type) if media_type is not None else None,
    )
    row = ACCESS_LAYER.get_media_item(item_id)
    return jsonify(_serialize_record(row or {"id": item_id})), 201


@app.put("/media-items/<int:item_id>")
@app.patch("/media-items/<int:item_id>")
def update_media_item(item_id: int) -> Any:
    """Update fields for one stored media item."""
    payload = request.get_json(silent=True) or {}

    title = payload.get("title") if "title" in payload else None
    file_path = payload.get("file_path") if "file_path" in payload else None
    media_type = payload.get("media_type") if "media_type" in payload else None

    if title is None and file_path is None and media_type is None:
        return jsonify({"detail": "Provide at least one field to update"}), 400

    updated = ACCESS_LAYER.update_media_item(
        item_id,
        title=str(title) if title is not None else None,
        file_path=str(file_path) if file_path is not None else None,
        media_type=str(media_type) if media_type is not None else None,
    )
    if not updated:
        return jsonify({"detail": "Media item not found"}), 404

    row = ACCESS_LAYER.get_media_item(item_id)
    return jsonify(_serialize_record(row or {"id": item_id}))


@app.delete("/media-items/<int:item_id>")
def delete_media_item(item_id: int) -> Any:
    """Delete one stored media item by id."""
    deleted = ACCESS_LAYER.delete_media_item(item_id)
    if not deleted:
        return jsonify({"detail": "Media item not found"}), 404
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
