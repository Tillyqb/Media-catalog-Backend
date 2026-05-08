"""Main entry point for the media catalog backend."""

import os
import sys

from dotenv import load_dotenv
from mysql.connector import Error

from access_layer import DatabaseConfig, MySQLMediaAccessLayer
from omdb_client import OMDBClient

def main() -> int:
    """Run startup checks and initialize storage layer."""
    load_dotenv()

    config = DatabaseConfig.from_env()
    access_layer = MySQLMediaAccessLayer(config)
    omdb_api_key = os.getenv("OMDB_API_KEY", "")

    print("Media Catalog Backend starting...")
    print(
        f"Using MySQL at {config.host}:{config.port}, "
        f"database '{config.database}'."
    )

    try:
        access_layer.initialize_schema()

        # Lightweight sanity check: this confirms read-access works after init.
        items = access_layer.list_media_items(limit=1)
        print(f"MySQL database ready. Existing item count sample: {len(items)}")

        omdb_client = OMDBClient(omdb_api_key)
        print(f"OMDb client ready ({omdb_client.BASE_URL}).")
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Error as exc:
        print(f"MySQL initialization failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
