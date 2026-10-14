"""Wait for the separately migrated queue before API/worker startup."""
import os
import time
import psycopg
from .run_store import SCHEMA_VERSION


def main():
    database_url = os.getenv("RELAY_DATABASE_URL")
    if not database_url:
        raise SystemExit("RELAY_DATABASE_URL is required")
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(database_url, connect_timeout=3) as connection:
                row = connection.execute("SELECT MAX(version) FROM relay_schema_migrations").fetchone()
                if row[0] == SCHEMA_VERSION:
                    return
        except psycopg.Error:
            pass
        time.sleep(1)
    raise SystemExit("The migrated investigation queue did not become ready")


if __name__ == "__main__":
    main()
