"""Initialize the durable investigation queue; deployment runs this separately."""
import os
from relayops.persistence.run_store import migrate_postgres


def main():
    database_url = os.getenv("RELAY_DATABASE_URL")
    if not database_url:
        raise SystemExit("RELAY_DATABASE_URL is required")
    migrate_postgres(database_url)


if __name__ == "__main__":
    main()
