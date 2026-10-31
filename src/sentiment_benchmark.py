"""Compare candidate sentiment models using star ratings as weak labels.

For each language a sample stratified by star rating is drawn from the clean
reviews. Star ratings are mapped to labels (1-2 negative, 3 neutral,
4-5 positive) and each model is scored on:

    spearman    rank correlation between polarity and stars; works for any
                label scheme, so it is the main cross-model metric
    binary_f1   macro-F1 on negative vs positive (3-star reviews excluded),
                fair to binary models that cannot predict neutral
    three_f1    macro-F1 on all three classes (binary models are penalised
                here by design, since they never predict neutral)

Star ratings are a noisy proxy (e.g. "great app but fees are a rip-off" with
4 stars), so absolute scores are a lower bound; what matters is the ranking.

Usage:
    python -m src.sentiment_benchmark
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import f1_score

from src.config import PROCESSED_DIR, PROJECT_ROOT
from src.sentiment_models import MODELS, SentimentScorer

log = logging.getLogger("benchmark")

PER_STAR = {"en": 100, "tr": 300}   # English: per star *per app* (3 apps)
SEED = 42
REPORT_DIR = PROJECT_ROOT / "reports"
CLASSES = np.array(["negative", "neutral", "positive"])


def star_label(score: pd.Series) -> pd.Series:
    return pd.cut(score, bins=[0, 2, 3, 5], labels=CLASSES).astype(str)


def draw_sample(clean: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for (lang, _app), g in clean.groupby(["lang", "app"]):
        if lang == "en":
            g = g[g["in_main_window"]]
        n = PER_STAR[lang]
        for _, s in g.groupby("score"):
            parts.append(s.sample(min(n, len(s)), random_state=SEED))
    sample = pd.concat(parts, ignore_index=True)
    sample["gold"] = star_label(sample["score"])
    return sample


def evaluate(sample: pd.DataFrame, probs: np.ndarray) -> dict:
    polarity = probs[:, 2] - probs[:, 0]
    pred3 = CLASSES[probs.argmax(axis=1)]
    pred2 = np.where(probs[:, 2] >= probs[:, 0], "positive", "negative")
    polar = (sample["gold"] != "neutral").to_numpy()
    return {
        "n": len(sample),
        "spearman": spearmanr(polarity, sample["score"]).statistic,
        "binary_f1": f1_score(sample["gold"][polar], pred2[polar], average="macro"),
        "three_f1": f1_score(sample["gold"], pred3, average="macro"),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    clean = pd.read_parquet(PROCESSED_DIR / "reviews_clean.parquet")
    sample = draw_sample(clean)
    log.info("Benchmark sample:\n%s", sample.groupby(["app", "score"]).size().unstack())

    rows, preds = [], {}
    for spec in MODELS.values():
        scorer = SentimentScorer(spec)
        for lang in spec.langs:
            sub = sample[sample["lang"] == lang]
            probs = scorer.score(sub["text"].tolist())
            preds[(spec.key, lang)] = probs
            metrics = evaluate(sub, probs)
            rows.append({"model": spec.key, "lang": lang, **metrics})
            # Per-app breakdown for English, to check the model is not app-biased.
            if lang == "en":
                for app, g in sub.groupby("app"):
                    rows.append({"model": spec.key, "lang": f"en:{app}",
                                 **evaluate(g, probs[sub.index.get_indexer(g.index)])})
        scorer.unload()

    results = pd.DataFrame(rows).round(3)
    REPORT_DIR.mkdir(exist_ok=True)
    results.to_csv(REPORT_DIR / "sentiment_benchmark.csv", index=False)
    print("\n" + results.to_string(index=False))


if __name__ == "__main__":
    main()
