import sqlite3
from pathlib import Path

from app.models.flight import Flight

DB_PATH = Path("data/flights.db")


def get_connection():

    DB_PATH.parent.mkdir(exist_ok=True)

    return sqlite3.connect(DB_PATH)


def initialize_database():

    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flights (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            origin TEXT NOT NULL,
            destination TEXT NOT NULL,

            departure_date TEXT NOT NULL,
            return_date TEXT NOT NULL,

            max_price REAL NOT NULL
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            origin TEXT NOT NULL,
            destination TEXT NOT NULL,

            departure_date TEXT NOT NULL,
            return_date TEXT NOT NULL,

            airline TEXT NOT NULL,

            price REAL NOT NULL,

            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_column(conn, "flights", "date_flex_days", "INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()


def _ensure_column(conn, table: str, column: str, definition: str):
    """Add a column to an existing table if it isn't there yet.

    Lets older databases (created before a given feature existed) pick
    up new columns without a separate migration step.
    """

    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }

    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def add_flight(flight: Flight):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO flights
        (
            origin,
            destination,
            departure_date,
            return_date,
            max_price,
            date_flex_days
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?
        )
        """,
        (
            flight.origin,
            flight.destination,
            flight.departure_date,
            flight.return_date,
            flight.max_price,
            flight.date_flex_days,
        ),
    )

    conn.commit()
    conn.close()


def get_all_flights():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            id,
            origin,
            destination,
            departure_date,
            return_date,
            max_price,
            date_flex_days
        FROM flights
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    flights = []

    for row in rows:

        flights.append(
            Flight(
                id=row[0],
                origin=row[1],
                destination=row[2],
                departure_date=row[3],
                return_date=row[4],
                max_price=row[5],
                date_flex_days=row[6],
            )
        )

    return flights


def save_price(result):

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO price_history
        (
            origin,
            destination,
            departure_date,
            return_date,
            airline,
            price
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?
        )
        """,
        (
            result.origin,
            result.destination,
            result.departure_date,
            result.return_date,
            result.airline,
            result.price,
        ),
    )

    conn.commit()
    conn.close()


def get_last_price(flight):

    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            price
        FROM price_history
        WHERE origin=?
          AND destination=?
          AND departure_date=?
          AND return_date=?
        ORDER BY checked_at DESC
        LIMIT 1
        """,
        (
            flight.origin,
            flight.destination,
            flight.departure_date,
            flight.return_date,
        ),
    ).fetchone()

    conn.close()

    if row:
        return row[0]

    return None


def get_price_history(limit: int = 20):

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            airline,
            price,
            checked_at
        FROM price_history
        ORDER BY checked_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    conn.close()

    return rows


def delete_flight(flight_id: int):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM flights
        WHERE id = ?
        """,
        (flight_id,),
    )

    conn.commit()
    conn.close()