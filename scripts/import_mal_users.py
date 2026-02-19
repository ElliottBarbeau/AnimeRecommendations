import argparse
import time

from fastapi import HTTPException

from app.api.v1.routes.user import import_mal_list
from app.db.session import SessionLocal
from app.schemas.user import UserImportMALRequest


def parse_usernames(args: argparse.Namespace) -> list[str]:
    usernames: list[str] = []

    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            for raw in handle:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                usernames.append(line)

    seen: set[str] = set()
    deduped: list[str] = []
    for username in usernames:
        if username not in seen:
            seen.add(username)
            deduped.append(username)

    return deduped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk import MAL users using the existing /users/import/mal route logic."
    )
    parser.add_argument(
        "--file",
        type=str,
        default="",
        help="Path to a text file with one MAL username per line.",
    )
    parser.add_argument(
        "--max-users",
        type=int,
        default=0,
        help="Optional limit for how many usernames to import (0 = no limit).",
    )
    args = parser.parse_args()

    usernames = parse_usernames(args)
    if not usernames:
        raise SystemExit("No usernames provided. Use --usernames and/or --file.")

    if args.max_users > 0:
        usernames = usernames[: args.max_users]

    total = len(usernames)
    ok = 0
    failed = 0

    print(f"Starting import for {total} MAL users.")
    for index, username in enumerate(usernames, start=1):
        db = SessionLocal()
        try:
            payload = UserImportMALRequest(
                mal_list_url=f"https://myanimelist.net/animelist/{username}"
            )
            result = import_mal_list(payload=payload, db=db)
            ok += 1
            print(
                f"[{index}/{total}] OK {username} "
                f"(items={result.items_seen}, anime+={result.anime_created}, entries+={result.entries_created})"
            )
        except HTTPException as exc:
            failed += 1
            print(f"[{index}/{total}] FAIL {username} (status={exc.status_code} detail={exc.detail})")
            if args.stop_on_error:
                db.close()
                break
        except Exception as exc:
            failed += 1
            print(f"[{index}/{total}] FAIL {username} (error={exc})")
            if args.stop_on_error:
                db.close()
                break
        finally:
            db.close()

        if index < total and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    print(f"Done. total={total} ok={ok} failed={failed}")


if __name__ == "__main__":
    main()
