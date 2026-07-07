"""One-off data migration for Roadmap Phase 5: copies every row from
the existing local SQLite database (data/flights.db) into Postgres.

Run this ONCE, on the live Railway deployment, after DATABASE_URL has
been set in the environment (so app.database.database already points
at Postgres) but before relying on Postgres for anything. It never
touches the SQLite file - only reads from it - so it's always safe to
re-run against a fresh Postgres database if something goes wrong.
Re-running against a database that already has migrated flights/price
history will duplicate those rows (provider_health is idempotent via
ON CONFLICT DO NOTHING) - drop and recreate the Postgres tables first
if you need to redo the flights/price_history migration.

Usage (from the Railway console, once DATABASE_URL is set):
    python3 scripts/migrate_sqlite_to_postgres.py
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import database as db  # noqa: E402

SQLITE_PATH = Path("data/flights.db")


def main():

    if not db.USE_POSTGRES:
        print("DATABASE_URL is not set - nothing to migrate to. Aborting.")
        return

    if not SQLITE_PATH.exists():
        print(f"No SQLite database found at {SQLITE_PATH} - nothing to migrate.")
        return

    print("Initializing Postgres schema...")
    db.initialize_database()

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    pg_conn = db.get_connection()

    try:
        migrate_flights(sqlite_conn, pg_conn)
        migrate_price_history(sqlite_conn, pg_conn)
        migrate_provider_health(sqlite_conn, pg_conn)
        pg_conn.commit()
    finally:
        pg_conn.close()
        sqlite_conn.close()

    print("Migration complete.")


def migrate_flights(sqlite_conn, pg_conn):

    rows = sqlite_conn.execute(
        """
        SELECT
            origin, destination, departure_date, return_date, max_price,
            date_flex_days, trip_type, cabin_class, max_stops,
            last_price, last_airline, lowest_price_seen,
            last_notified_price, last_checked_at, legs
        FROM flights
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        pg_conn.execute(
            """
            INSERT INTO flights
            (origin, destination, departure_date, return_date, max_price,
             date_flex_days, trip_type, cabin_class, max_stops,
             last_price, last_airline, lowest_price_seen,
             last_notified_price, last_checked_at, legs)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )

    print(f"Migrated {len(rows)} flight(s).")


def migrate_price_history(sqlite_conn, pg_conn):

    rows = sqlite_conn.execute(
        """
        SELECT origin, destination, departure_date, return_date,
               airline, price, checked_at
        FROM price_history
        ORDER BY id
        """
    ).fetchall()

    for row in rows:
        pg_conn.execute(
            """
            INSERT INTO price_history
            (origin, destination, departure_date, return_date, airline, price, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            row,
        )

    print(f"Migrated {len(rows)} price history row(s).")


def migrate_provider_health(sqlite_conn, pg_conn):

    rows = sqlite_conn.execute(
        """
        SELECT provider, total_checks, success_count, success_response_ms,
               consecutive_failures, disabled_until, last_error, last_checked_at
        FROM provider_health
        """
    ).fetchall()

    for row in rows:
        pg_conn.execute(
            """
            INSERT INTO provider_health
            (provider, total_checks, success_count, success_response_ms,
             consecutive_failures, disabled_until, last_error, last_checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (provider) DO NOTHING
            """,
            row,
        )

    print(f"Migrated {len(rows)} provider health row(s).")


if __name__ == "__main__":
    main()
