import argparse

from sqlalchemy import inspect, text

from app.db.base import Base
from app.db.session import engine

# Import models so SQLAlchemy metadata includes all mapped tables.
from app.db.models import anime, user, user_anime_entry, user_stats  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Drop all database tables defined by SQLAlchemy models."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate empty tables after dropping them.",
    )
    args = parser.parse_args()

    if not args.yes:
        confirm = input(
            "This will DROP ALL tables for the current DATABASE_URL. Type 'drop' to continue: "
        ).strip()
        if confirm.lower() != "drop":
            print("Aborted. No changes made.")
            return

    with engine.begin() as conn:
        schema = conn.dialect.default_schema_name or "public"
        table_names = inspect(conn).get_table_names(schema=schema)

        if not table_names:
            print("No tables found.")
        else:
            for table_name in table_names:
                conn.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{table_name}" CASCADE'))
            print(f"Dropped {len(table_names)} table(s) from schema '{schema}'.")

    if args.recreate:
        Base.metadata.create_all(bind=engine)
        print("Recreated ORM tables.")


if __name__ == "__main__":
    main()
