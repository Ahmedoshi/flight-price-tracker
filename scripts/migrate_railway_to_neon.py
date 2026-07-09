"""One-off data migration: copies every row from an existing Postgres
database (Railway's managed Postgres) into a new Postgres database
(Neon), as part of moving hosting off Railway.

Unlike scripts/migrate_sqlite_to_postgres.py, both sides here are
already Postgres, so there's no "?" -> "%s" placeholder translation to
worry about - this talks to both with plain psycopg2 connections
directly rather than going through app.database.database's
dual-backend wrapper (which only exists to also support SQLite).

The destination schema is created here directly (mirrors the DDL in
app.database.database.initialize_database()'s USE_POSTGRES branch) so
this script has no import-time dependency on DATABASE_URL being set in
the environment it runs in.

Usage:
    python3 scripts/migrate_railway_to_neon.py "<railway_database_url>" "<neon_database_url>"

Get the Railway URL from Railway's Postgres service -> Variables ->
DATABASE_URL (or DATABASE_PUBLIC_URL if running this from outside
Railway's network). Get the Neon URL from the Neon project dashboard
-> Connection Details.

Safe to re-run against a FRESH Neon database. Re-running against a
Neon database that already has migrated flights/price_history rows
will duplicate them (provider_health is idempotent via
ON CONFLICT DO NOTHING) - truncate the destination tables first if you
need to redo the flights/price_history migration.
"""

import sys

import psycopg2


def main():

    if len(sys.argv) != 3:
        print("Usage: python3 scripts/migrate_railway_to_neon.py <railway_database_url> <neon_database_url>")
        sys.exit(1)

    source_url, dest_url = sys.argv[1], sys.argv[2]

    print("Connecting to source (Railway) and destination (Neon)...")
    source_conn = psycopg2.connect(source_url)
    dest_conn = psycopg2.connect(dest_url)

    try:
        print("Ensuring destination schema exists...")
        _initialize_schema(dest_conn)

        migrate_flights(source_conn, dest_conn)
        migrate_price_history(source_conn, dest_conn)
        migrate_provider_health(source_conn, dest_conn)

        dest_conn.commit()
    finally:
        dest_conn.close()
        source_conn.close()

    print("Migration complete.")


def _initialize_schema(dest_conn):

    cur = dest_conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS flights (
            id SERIAL PRIMARY KEY,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            departure_date TEXT NOT NULL,
            return_date TEXT NOT NULL,
            max_price REAL NOT NULL,
            date_flex_days INTEGER NOT NULL DEFAULT 0,
            trip_type TEXT NOT NULL DEFAULT 'round-trip',
            cabin_class TEXT NOT NULL DEFAULT 'economy',
            max_stops INTEGER,
            last_price REAL,
            last_airline TEXT NOT NULL DEFAULT '',
            lowest_price_seen REAL,
            last_notified_price REAL,
            last_checked_at TEXT,
            legs TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id SERIAL PRIMARY KEY,
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

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS provider_health (
            provider TEXT PRIMARY KEY,
            total_checks INTEGER NOT NULL DEFAULT 0,
            success_count INTEGER NOT NULL DEFAULT 0,
            success_response_ms REAL NOT NULL DEFAULT 0,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            disabled_until TEXT,
            last_error TEXT,
            last_checked_at TEXT
        )
        """
    )

    dest_conn.commit()


def migrate_flights(source_conn, dest_conn):

    source_cur = source_conn.cursor()
    source_cur.execute(
        """
        SELECT
            origin, destination, departure_date, return_date, max_price,
            date_flex_days, trip_type, cabin_class, max_stops,
            last_price, last_airline, lowest_price_seen,
            last_notified_price, last_checked_at, legs
        FROM flights
        ORDER BY id
        """
    )
    rows = source_cur.fetchall()

    dest_cur = dest_conn.cursor()

    for row in rows:
        dest_cur.execute(
            """
            INSERT INTO flights
            (origin, destination, departure_date, return_date, max_price,
             date_flex_days, trip_type, cabin_class, max_stops,
             last_price, last_airline, lowest_price_seen,
             last_notified_price, last_checked_at, legs)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            row,
        )

    print(f"Migrated {len(rows)} flight(s).")


def migrate_price_history(source_conn, dest_conn):

    source_cur = source_conn.cursor()
    source_cur.execute(
        """
        SELECT origin, destination, departure_date, return_date,
               airline, price, checked_at
        FROM price_history
        ORDER BY id
        """
    )
    rows = source_cur.fetchall()

    dest_cur = dest_conn.cursor()

    for row in rows:
        dest_cur.execute(
            """
            INSERT INTO price_history
            (origin, destination, departure_date, return_date, airline, price, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            row,
        )

    print(f"Migrated {len(rows)} price history row(s).")


def migrate_provider_health(source_conn, dest_conn):

    source_cur = source_conn.cursor()
    source_cur.execute(
        """
        SELECT provider, total_checks, success_count, success_response_ms,
               consecutive_failures, disabled_until, last_error, last_checked_at
        FROM provider_health
        """
    )
    rows = source_cur.fetchall()

    dest_cur = dest_conn.cursor()

    for row in rows:
        dest_cur.execute(
            """
            INSERT INTO provider_health
            (provider, total_checks, success_count, success_response_ms,
             consecutive_failures, disabled_until, last_error, last_checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider) DO NOTHING
            """,
            row,
        )

    print(f"Migrated {len(rows)} provider health row(s).")


if __name__ == "__main__":
    main()
