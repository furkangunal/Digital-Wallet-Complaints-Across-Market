"""Score every clean review with the selected sentiment model.

The model was chosen with ``src/sentiment_benchmark.py`` (see README). One
multilingual model is used for all markets so that sentiment is measured on
the same scale in English and Turkish.

Output: ``data/interim/sentiment.parquet`` with one row per review:
    review_id, p_neg, p_neu, p_pos, polarity (p_pos - p_neg), sentiment
Already-scored reviews are skipped, so re-running after new data arrives only
scores the new reviews.

Usage:
    python -m src.sentiment
"""

from __future__ import annotations

import logging

import pandas as pd

from src.config import INTERIM_DIR, PROCESSED_DIR
from src.sentiment_models import MODELS, SentimentScorer

log = logging.getLogger("sentiment")

SENTIMENT_MODEL = "xlmr"
OUT_PATH = INTERIM_DIR / "sentiment.parquet"
LABELS = ["negative", "neutral", "positive"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    clean = pd.read_parquet(PROCESSED_DIR / "reviews_clean.parquet",
                            columns=["review_id", "text"])

    done = pd.read_parquet(OUT_PATH) if OUT_PATH.exists() else pd.DataFrame()
    if not done.empty:
        done = done[done["model"] == SENTIMENT_MODEL]
        todo = clean[~clean["review_id"].isin(done["review_id"])]
    else:
        todo = clean
    log.info("%d reviews to score (%d already scored)", len(todo), len(done))
    if todo.empty:
        return

    probs = SentimentScorer(MODELS[SENTIMENT_MODEL]).score(todo["text"].tolist())
    scored = pd.DataFrame({
        "review_id": todo["review_id"].to_numpy(),
        "p_neg": probs[:, 0], "p_neu": probs[:, 1], "p_pos": probs[:, 2],
    })
    scored["polarity"] = scored["p_pos"] - scored["p_neg"]
    scored["sentiment"] = pd.Categorical.from_codes(probs.argmax(axis=1), LABELS)
    scored["model"] = SENTIMENT_MODEL

    result = pd.concat([done, scored], ignore_index=True)
    # Drop reviews that are no longer in the clean set (e.g. cleaning rules changed).
    result = result[result["review_id"].isin(clean["review_id"])]
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    result.to_parquet(OUT_PATH, index=False)
    log.info("Wrote %d sentiment scores to %s", len(result), OUT_PATH)


if __name__ == "__main__":
    main()
