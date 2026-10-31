"""Collect Google Play reviews for the apps defined in ``src/config.py``.

Reviews are fetched newest-first in pages and appended to
``data/raw/<app>/reviews.jsonl``. After every page the pagination token is
saved to ``data/raw/<app>/state.json``, so an interrupted run resumes where it
stopped instead of starting over. Re-running after a run has completed only
continues if a larger ``--max-reviews`` or an older ``--since`` is given.

Personal fields (user name, avatar URL) are dropped at collection time.

Usage:
    python -m src.collect_reviews                       # all apps, defaults
    python -m src.collect_reviews --apps papara revolut
    python -m src.collect_reviews --max-reviews 20000 --since 2024-01-01
    python -m src.collect_reviews --apps cashapp --reset  # discard and refetch
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from google_play_scraper import Sort, reviews
from google_play_scraper.features.reviews import _ContinuationToken

from src.config import APPS, RAW_DIR, AppConfig

log = logging.getLogger("collect")

PAGE_SIZE = 200  # Google Play returns at most ~200 reviews per request
MAX_RETRIES = 5

# Fields kept from the scraper output; user name and avatar are left out.
KEEP_FIELDS = (
    "reviewId",
    "content",
    "score",
    "thumbsUpCount",
    "reviewCreatedVersion",
    "appVersion",
    "at",
    "replyContent",
    "repliedAt",
)


# --------------------------------------------------------------------------- #
# State handling
# --------------------------------------------------------------------------- #
def app_dir(app: AppConfig) -> Path:
    return RAW_DIR / app.key


def load_state(app: AppConfig) -> dict:
    path = app_dir(app) / "state.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"token": None, "exhausted": False, "oldest_at": None}


def save_state(app: AppConfig, state: dict) -> None:
    """Write state atomically so a crash never leaves a half-written file."""
    path = app_dir(app) / "state.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    # On Windows, antivirus or file indexers can briefly lock the target file.
    for attempt in range(10):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            time.sleep(0.5 * (attempt + 1))
    tmp.replace(path)


def load_seen_ids(app: AppConfig) -> set[str]:
    """Review IDs already on disk; used to skip duplicates after a crash."""
    path = app_dir(app) / "reviews.jsonl"
    if not path.exists():
        return set()
    seen = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seen.add(json.loads(line)["reviewId"])
            except (json.JSONDecodeError, KeyError):
                # A partially written last line from an interrupted run.
                log.warning("%s: skipping malformed line in reviews.jsonl", app.key)
    return seen


def make_token(app: AppConfig, token: str | None) -> _ContinuationToken | None:
    if token is None:
        return None
    return _ContinuationToken(
        token, app.lang, app.country, Sort.NEWEST.value, PAGE_SIZE, None, None
    )


# --------------------------------------------------------------------------- #
# Fetching
# --------------------------------------------------------------------------- #
def fetch_page(app: AppConfig, token: _ContinuationToken | None):
    """Fetch one page, retrying with exponential backoff on network errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return reviews(
                app.app_id,
                lang=app.lang,
                country=app.country,
                sort=Sort.NEWEST,
                count=PAGE_SIZE,
                continuation_token=token,
            )
        except Exception as exc:  # the library raises a variety of errors
            wait = min(300, 10 * 2 ** (attempt - 1)) + random.uniform(0, 5)
            log.warning(
                "%s: request failed (%s), attempt %d/%d, retrying in %.0fs",
                app.key, exc, attempt, MAX_RETRIES, wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"{app.key}: giving up after {MAX_RETRIES} failed attempts")


def to_record(raw: dict, app: AppConfig, scraped_at: str) -> dict:
    rec = {k: raw.get(k) for k in KEEP_FIELDS}
    for k in ("at", "repliedAt"):
        if isinstance(rec[k], datetime):
            rec[k] = rec[k].isoformat()
    rec.update(app=app.key, market=app.market, lang=app.lang,
               country=app.country, scraped_at=scraped_at)
    return rec


def collect_app(
    app: AppConfig,
    max_reviews: int,
    since: datetime | None,
    sleep_range: tuple[float, float],
) -> int:
    out_dir = app_dir(app)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "reviews.jsonl"

    state = load_state(app)
    seen = load_seen_ids(app)
    log.info("%s: %d reviews on disk, resuming=%s",
             app.key, len(seen), state["token"] is not None)

    if state["exhausted"]:
        log.info("%s: no more reviews available from Google Play, skipping", app.key)
        return 0

    def reached_since() -> bool:
        return (since is not None and state["oldest_at"] is not None
                and datetime.fromisoformat(state["oldest_at"]) < since)

    # A completed run has no stored token but does have data; continuing it
    # would refetch from the newest review, so only page onward from a token.
    if state["token"] is None and seen:
        log.info("%s: previous run completed; use --reset to refetch", app.key)
        return 0

    added = 0
    with out_path.open("a", encoding="utf-8") as f:
        while len(seen) < max_reviews and not reached_since():
            scraped_at = datetime.now(UTC).isoformat(timespec="seconds")
            batch, next_token = fetch_page(app, make_token(app, state["token"]))

            new = [r for r in batch if r["reviewId"] not in seen]
            for raw in new:
                f.write(json.dumps(to_record(raw, app, scraped_at), ensure_ascii=False) + "\n")
                seen.add(raw["reviewId"])
            f.flush()
            added += len(new)

            if batch:
                oldest = min(r["at"] for r in batch)
                if state["oldest_at"] is None or oldest.isoformat() < state["oldest_at"]:
                    state["oldest_at"] = oldest.isoformat()

            # The token is persisted only after the page is safely on disk.
            state["token"] = next_token.token if next_token else None
            state["exhausted"] = not batch or state["token"] is None
            save_state(app, state)

            log.info("%s: +%d (total %d), oldest so far %s",
                     app.key, len(new), len(seen), (state["oldest_at"] or "-")[:10])

            if state["exhausted"]:
                log.info("%s: reached the end of available reviews", app.key)
                break
            time.sleep(random.uniform(*sleep_range))

    return added


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apps", nargs="+", choices=sorted(APPS), default=sorted(APPS),
                   help="apps to collect (default: all)")
    p.add_argument("--max-reviews", type=int, default=10_000,
                   help="stop once this many reviews per app are on disk (default: 10000)")
    p.add_argument("--since", type=lambda s: datetime.fromisoformat(s),
                   help="stop once reviews older than this date (YYYY-MM-DD) are reached")
    p.add_argument("--min-sleep", type=float, default=2.0,
                   help="minimum pause between requests in seconds (default: 2)")
    p.add_argument("--max-sleep", type=float, default=5.0,
                   help="maximum pause between requests in seconds (default: 5)")
    p.add_argument("--reset", action="store_true",
                   help="delete existing raw data for the selected apps and start over")
    return p.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    args = parse_args()

    for key in args.apps:
        app = APPS[key]
        if args.reset and app_dir(app).exists():
            log.info("%s: --reset given, removing existing raw data", key)
            shutil.rmtree(app_dir(app))
        try:
            added = collect_app(app, args.max_reviews, args.since,
                                (args.min_sleep, args.max_sleep))
            log.info("%s: done, %d new reviews this run", key, added)
        except KeyboardInterrupt:
            log.info("Interrupted; progress is saved, re-run to resume.")
            return
        except RuntimeError as exc:
            log.error("%s", exc)  # move on to the next app


if __name__ == "__main__":
    main()
