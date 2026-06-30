import sqlite3

from app.config.settings import settings, PROJECT_ROOT
from app.models.flight import Flight

DATABASE = PROJECT_ROOT / settings.database_path


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS flights(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT NOT NULL,
            max_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def add_flight(flight: Flight):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO flights
        (origin, destination, departure_date, return_date, max_price)
        VALUES (?, ?, ?, ?, ?)
    """, (
        flight.origin,
        flight.destination,
        flight.departure_date,
        flight.return_date,
        flight.max_price
    ))

    conn.commit()
    conn.close()


def get_all_flights():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM flights")

    flights = cursor.fetchall()

    conn.close()

    return flights