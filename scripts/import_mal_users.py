import argparse
import os
import time

from fastapi import HTTPException

from app.api.v1.routes.user import import_mal_list
from app.db.session import SessionLocal
from app.schemas.user import UserImportMALRequest


def log(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


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
    parser.add_argument(
        "--enrichment-mode",
        type=str,
        default="",
        choices=["", "full", "relations", "none"],
        help="Override MAL_IMPORT_ENRICHMENT_MODE for this run (default: use environment/current behavior).",
    )
    parser.add_argument(
        "--enrichment-min-rating",
        type=float,
        default=None,
        help="Skip per-anime enrichment when MAL provider rating is <= this value (e.g. 7.5).",
    )
    args = parser.parse_args()

    usernames = parse_usernames(args)
    if not usernames:
        raise SystemExit("No usernames provided. Use --file.")

    if args.max_users > 0:
        usernames = usernames[: args.max_users]

    previous_enrichment_mode = os.environ.get("MAL_IMPORT_ENRICHMENT_MODE")
    previous_enrichment_min_rating = os.environ.get("MAL_IMPORT_ENRICHMENT_MIN_RATING")
    if args.enrichment_mode:
        os.environ["MAL_IMPORT_ENRICHMENT_MODE"] = args.enrichment_mode
        log(f"Set MAL_IMPORT_ENRICHMENT_MODE={args.enrichment_mode} for this run")
    if args.enrichment_min_rating is not None:
        os.environ["MAL_IMPORT_ENRICHMENT_MIN_RATING"] = str(args.enrichment_min_rating)
        log(f"Set MAL_IMPORT_ENRICHMENT_MIN_RATING={args.enrichment_min_rating} for this run")

    total = len(usernames)
    ok = 0
    failed = 0
    batch_started = time.perf_counter()

    log(f"Starting import for {total} MAL users.")
    for index, username in enumerate(usernames, start=1):
        user_started = time.perf_counter()
        log(f"[{index}/{total}] START {username}")
        db = SessionLocal()
        try:
            log(f"[{index}/{total}] Building request payload for {username}")
            payload = UserImportMALRequest(
                mal_list_url=f"https://myanimelist.net/animelist/{username}"
            )
            log(f"[{index}/{total}] Calling import_mal_list for {username}")
            result = import_mal_list(payload=payload, db=db)
            ok += 1
            elapsed = time.perf_counter() - user_started
            log(
                f"[{index}/{total}] OK {username} "
                f"(items={result.items_seen}, anime+={result.anime_created}, "
                f"entries+={result.entries_created}, mean={result.mean_score:.2f}, "
                f"stddev={result.stddev_score:.2f}, count={result.rating_count}, "
                f"elapsed={elapsed:.2f}s)"
            )
        except HTTPException as exc:
            failed += 1
            elapsed = time.perf_counter() - user_started
            log(
                f"[{index}/{total}] FAIL {username} "
                f"(status={exc.status_code} detail={exc.detail}, elapsed={elapsed:.2f}s)"
            )
        except Exception as exc:
            failed += 1
            elapsed = time.perf_counter() - user_started
            log(f"[{index}/{total}] FAIL {username} (error={exc}, elapsed={elapsed:.2f}s)")
        finally:
            log(f"[{index}/{total}] Closing DB session for {username}")
            db.close()

    total_elapsed = time.perf_counter() - batch_started
    log(f"Done. total={total} ok={ok} failed={failed} elapsed={total_elapsed:.2f}s")

    if args.enrichment_mode:
        if previous_enrichment_mode is None:
            os.environ.pop("MAL_IMPORT_ENRICHMENT_MODE", None)
        else:
            os.environ["MAL_IMPORT_ENRICHMENT_MODE"] = previous_enrichment_mode
    if args.enrichment_min_rating is not None:
        if previous_enrichment_min_rating is None:
            os.environ.pop("MAL_IMPORT_ENRICHMENT_MIN_RATING", None)
        else:
            os.environ["MAL_IMPORT_ENRICHMENT_MIN_RATING"] = previous_enrichment_min_rating


if __name__ == "__main__":
    main()
