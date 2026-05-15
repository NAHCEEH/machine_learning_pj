"""SQLite helper functions for the course recommendation project."""

import sqlite3
from pathlib import Path
from typing import Any

from config import DB_PATH


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Create a SQLite connection with row access by column name."""
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def fetch_all(query: str, params: tuple[Any, ...] = (), db_path: Path = DB_PATH) -> list[sqlite3.Row]:
    """Run a SELECT query and return all rows."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchall()


def fetch_one(query: str, params: tuple[Any, ...] = (), db_path: Path = DB_PATH) -> sqlite3.Row | None:
    """Run a SELECT query and return one row, or None when no row exists."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(query, params)
        return cursor.fetchone()


def is_course_open(course_id: str, semester: str, db_path: Path = DB_PATH) -> bool:
    """Return True when a course is open in the given semester."""
    row = fetch_one(
        """
        SELECT is_open
        FROM semester_open
        WHERE course_id = ? AND semester = ?
        """,
        (course_id, semester),
        db_path,
    )
    return bool(row and row["is_open"])
