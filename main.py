"""Main entry point for the media catalog backend."""

import sys

from mysql.connector import Error

from access_layer import DatabaseConfig, MySQLMediaAccessLayer

def main() -> int:
    """Run startup checks and initialize storage layer."""
    config = DatabaseConfig.from_env()
    access_layer = MySQLMediaAccessLayer(config)

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
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Error as exc:
        print(f"MySQL initialization failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
