import argparse

from app.db.base import Base
from app.db.session import engine

# Import models so SQLAlchemy metadata includes all mapped tables.
from app.db.models import anime, user, user_anime_entry  # noqa: F401


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

    Base.metadata.drop_all(bind=engine)
    print("Dropped all tables.")

    if args.recreate:
        Base.metadata.create_all(bind=engine)
        print("Recreated all tables.")


if __name__ == "__main__":
    main()
