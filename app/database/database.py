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

    conn.commit()
    conn.close()


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
            max_price
        )
        VALUES
        (
            ?, ?, ?, ?, ?
        )
        """,
        (
            flight.origin,
            flight.destination,
            flight.departure_date,
            flight.return_date,
            flight.max_price,
        ),
    )

    conn.commit()
    conn.close()


def get_all_flights():

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            origin,
            destination,
            departure_date,
            return_date,
            max_price
        FROM flights
        """
    ).fetchall()

    conn.close()

    flights = []

    for row in rows:

        flights.append(
            Flight(
                origin=row[0],
                destination=row[1],
                departure_date=row[2],
                return_date=row[3],
                max_price=row[4],
            )
        )

    return flights


def delete_flight(index: int):

    conn = get_connection()

    conn.execute(
        """
        DELETE FROM flights
        WHERE id = ?
        """,
        (index,),
    )

    conn.commit()
    conn.close()