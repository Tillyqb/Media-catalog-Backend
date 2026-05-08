"""MySQL data access layer for media catalog records."""

from dataclasses import dataclass
import os
import re
from typing import Any, Optional

import mysql.connector


@dataclass(frozen=True)
class DatabaseConfig:
    """Database configuration loaded from environment variables."""

    host: str
    port: int
    user: str
    password: str
    database: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Build config from environment variables."""
        port = int(os.getenv("DB_PORT", "3306"))
        return cls(
            host=os.getenv("DB_HOST", "127.0.0.1"),
            port=port,
            user=os.getenv("DB_USER", "media_user"),
            password=os.getenv("DB_PASSWORD", "media_password"),
            database=os.getenv("DB_NAME", "media_catalog"),
        )


def _validate_identifier(identifier: str, variable_name: str) -> None:
    """Allow only safe SQL identifiers for schema/table names."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Invalid value for {variable_name}: {identifier}")


class MySQLMediaAccessLayer:
    """Repository-style access layer for media_items."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        _validate_identifier(self.config.database, "DB_NAME")

    def _connect_server(self):
        """Connect to MySQL without selecting a specific database."""
        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
        )

    def _connect_database(self):
        """Connect directly to the configured database."""
        return mysql.connector.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
        )

    def initialize_schema(self) -> None:
        """Create the database and media_items table if needed."""
        connection = self._connect_server()
        cursor = connection.cursor()

        try:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config.database}")
            cursor.execute(f"USE {self.config.database}")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS media_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    file_path TEXT NOT NULL,
                    media_type VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_media_type (media_type)
                )
                """
            )
            connection.commit()
        finally:
            cursor.close()
            connection.close()

    def create_media_item(self, title: str, file_path: str, media_type: Optional[str] = None) -> int:
        """Insert a media item and return its new id."""
        connection = self._connect_database()
        cursor = connection.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO media_items (title, file_path, media_type)
                VALUES (%s, %s, %s)
                """,
                (title, file_path, media_type),
            )
            connection.commit()
            return int(cursor.lastrowid)
        finally:
            cursor.close()
            connection.close()

    def get_media_item(self, item_id: int) -> Optional[dict[str, Any]]:
        """Fetch a single media item by id."""
        connection = self._connect_database()
        cursor = connection.cursor(dictionary=True)

        try:
            cursor.execute(
                """
                SELECT id, title, file_path, media_type, created_at, updated_at
                FROM media_items
                WHERE id = %s
                """,
                (item_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

    def list_media_items(
        self,
        limit: int = 100,
        offset: int = 0,
        media_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """List media items with optional filter and pagination."""
        if limit <= 0:
            raise ValueError("limit must be > 0")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        connection = self._connect_database()
        cursor = connection.cursor(dictionary=True)

        try:
            if media_type:
                cursor.execute(
                    """
                    SELECT id, title, file_path, media_type, created_at, updated_at
                    FROM media_items
                    WHERE media_type = %s
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (media_type, limit, offset),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, title, file_path, media_type, created_at, updated_at
                    FROM media_items
                    ORDER BY id DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
            return list(cursor.fetchall())
        finally:
            cursor.close()
            connection.close()

    def update_media_item(
        self,
        item_id: int,
        title: Optional[str] = None,
        file_path: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> bool:
        """Update provided fields for one media item."""
        fields = []
        params: list[Any] = []

        if title is not None:
            fields.append("title = %s")
            params.append(title)
        if file_path is not None:
            fields.append("file_path = %s")
            params.append(file_path)
        if media_type is not None:
            fields.append("media_type = %s")
            params.append(media_type)

        if not fields:
            return False

        params.append(item_id)

        connection = self._connect_database()
        cursor = connection.cursor()

        try:
            cursor.execute(
                f"UPDATE media_items SET {', '.join(fields)} WHERE id = %s",
                tuple(params),
            )
            connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            connection.close()

    def delete_media_item(self, item_id: int) -> bool:
        """Delete one media item by id."""
        connection = self._connect_database()
        cursor = connection.cursor()

        try:
            cursor.execute("DELETE FROM media_items WHERE id = %s", (item_id,))
            connection.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            connection.close()
