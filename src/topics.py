"""Topic modelling of complaints with BERTopic, and mapping to shared categories.

One model is fitted per language: English (Cash App, PayPal, Revolut share a
model, so their topics are directly comparable) and Turkish (Papara).

    python -m src.topics fit      # fit models, write topic reports and proposed mappings
    python -m src.topics apply    # apply config/topic_mapping_<lang>.csv to every complaint

Complaints are reviews whose text sentiment is negative, plus 1-2 star reviews
whose text is not positive. Scope: the shared 12-month window for all apps,
plus Papara's extended period (needed for the event-impact analysis).

Embeddings are computed from the lightly cleaned ``text`` (the transformer
sees natural language); topic keywords are computed from ``text_norm``.
"""

from __future__ import annotations

import argparse
import logging
import re

import numpy as np
import pandas as pd
from bertopic import BERTopic
from bertopic.representation import MaximalMarginalRelevance
from bertopic.vectorizers import ClassTfidfTransformer
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, CountVectorizer
from umap import UMAP

from src.config import CONFIG_DIR, INTERIM_DIR, PROCESSED_DIR, PROJECT_ROOT
from src.taxonomy import CATEGORIES

log = logging.getLogger("topics")

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBEDDING_VERSION = "brandmask-v1"   # bump to invalidate cached embeddings

# Brand names are masked before embedding. Otherwise reviews cluster by
# *which app* they mention ("negative things about PayPal") rather than by
# the complaint itself, which would defeat the cross-market comparison.
BRAND_RE = re.compile(r"\b(cash\s?app|pay\s?pal|revolut|papara)\w*", re.I)
BRAND_MASK = {"en": "the app", "tr": "uygulama"}
SEED = 42
MIN_CLUSTER_SIZE = {"en": 60, "tr": 15}
OUTLIER_THRESHOLD = 0.5      # min cosine similarity to re-assign an outlier to a topic
MODEL_DIR = PROJECT_ROOT / "models"
REPORT_DIR = PROJECT_ROOT / "reports"

# Brand and generic review words carry no information about the complaint.
DOMAIN_STOPWORDS = {
    "en": {"app", "apps", "cash", "cashapp", "paypal", "revolut", "use", "using", "used",
           "just", "like", "get", "got", "im", "dont", "doesnt", "didnt", "cant", "ive",
           "really", "even", "ever", "would", "could", "also", "one", "still", "please",
           "thing", "things", "way", "know", "want", "make", "say", "said"},
    "tr": {"papara", "paparayı", "paparaya", "paparada", "paparanın", "uygulama",
           "uygulamayı", "uygulamada", "uygulamanın", "uygulamaya"},
}
TR_STOPWORDS = {
    "acaba", "ama", "ancak", "artık", "aslında", "az", "bana", "bazı", "belki", "ben",
    "beni", "benim", "bile", "bir", "biraz", "birçok", "biri", "birkaç", "biz", "bize",
    "bizi", "bizim", "bu", "buna", "bunda", "bundan", "bunu", "bunun", "burada", "da",
    "daha", "dahi", "de", "defa", "değil", "diğer", "diye", "dolayı", "en", "gibi", "göre",
    "hala", "halde", "hem", "hep", "hepsi", "her", "hiç", "için", "ile", "ise", "işte",
    "kadar", "ki", "kim", "mi", "mı", "mu", "mü", "nasıl", "ne", "neden", "nerede", "o",
    "olan", "olarak", "oldu", "olduğu", "olsun", "on", "ona", "onu", "onun", "orada",
    "öyle", "sadece", "sanki", "sen", "seni", "siz", "size", "sizi", "sizin", "şey",
    "şimdi", "şu", "şuan", "tabi", "tüm", "ve", "veya", "ya", "yani", "zaten", "çok",
    "bi", "olur", "olmuyor", "var", "yok", "lütfen", "niye", "artik", "gerçekten",
    "falan", "hatta", "ayrıca", "böyle", "şöyle", "yine", "tekrar", "sonra",
    "önce", "bende", "sizde", "bunlar", "onlar", "kendi", "ediyorum", "yapıyorum",
}
STOPWORDS = {
    "en": sorted(ENGLISH_STOP_WORDS | DOMAIN_STOPWORDS["en"]),
    "tr": sorted(TR_STOPWORDS | DOMAIN_STOPWORDS["tr"]),
}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load_complaints() -> pd.DataFrame:
    clean = pd.read_parquet(PROCESSED_DIR / "reviews_clean.parquet")
    sent = pd.read_parquet(INTERIM_DIR / "sentiment.parquet",
                           columns=["review_id", "sentiment", "polarity"])
    df = clean.merge(sent, on="review_id")
    complaint = (df["sentiment"] == "negative") | ((df["score"] <= 2) & (df["sentiment"] != "positive"))
    scope = df["in_main_window"] | (df["app"] == "papara")
    return df[complaint & scope].reset_index(drop=True)


def embed(df: pd.DataFrame, lang: str, encoder: SentenceTransformer) -> np.ndarray:
    """Sentence embeddings, cached per review_id so refits are fast."""
    path = INTERIM_DIR / f"embeddings_{lang}_{EMBEDDING_VERSION}.parquet"
    cache = pd.read_parquet(path) if path.exists() else pd.DataFrame(columns=["review_id", "emb"])
    known = dict(zip(cache["review_id"], cache["emb"], strict=True))
    todo = df.loc[~df["review_id"].isin(known), ["review_id", "text"]]
    if len(todo):
        log.info("%s: embedding %d reviews", lang, len(todo))
        texts = [BRAND_RE.sub(BRAND_MASK[lang], t) for t in todo["text"]]
        vecs = encoder.encode(texts, batch_size=64, show_progress_bar=True,
                              normalize_embeddings=True)
        known.update(zip(todo["review_id"], list(vecs), strict=True))
        pd.DataFrame({"review_id": list(known), "emb": list(known.values())}).to_parquet(path)
    return np.vstack([known[r] for r in df["review_id"]]).astype(np.float32)


# --------------------------------------------------------------------------- #
# Fit
# --------------------------------------------------------------------------- #
def build_model(lang: str, encoder: SentenceTransformer) -> BERTopic:
    return BERTopic(
        embedding_model=encoder,
        umap_model=UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine",
                        random_state=SEED),
        hdbscan_model=HDBSCAN(min_cluster_size=MIN_CLUSTER_SIZE[lang], metric="euclidean",
                              cluster_selection_method="eom", prediction_data=True),
        vectorizer_model=CountVectorizer(stop_words=STOPWORDS[lang], ngram_range=(1, 2),
                                         min_df=5),
        ctfidf_model=ClassTfidfTransformer(reduce_frequent_words=True),
        representation_model=MaximalMarginalRelevance(diversity=0.3),
        top_n_words=10,
    )


def propose_categories(emb: np.ndarray, topics: np.ndarray,
                       encoder: SentenceTransformer) -> pd.DataFrame:
    """Suggest a category per topic by comparing topic centroids to category descriptions."""
    keys = [k for k in CATEGORIES if k != "other"]
    cat_emb = encoder.encode([CATEGORIES[k]["description"] for k in keys],
                             normalize_embeddings=True)
    rows = []
    for t in sorted(set(topics)):
        if t == -1:
            continue
        centroid = emb[topics == t].mean(axis=0)
        centroid /= np.linalg.norm(centroid)
        sims = cat_emb @ centroid
        best, second = np.argsort(sims)[::-1][:2]
        rows.append({"topic": t, "proposed": keys[best], "sim": round(float(sims[best]), 3),
                     "runner_up": keys[second], "sim_2": round(float(sims[second]), 3)})
    return pd.DataFrame(rows)


def fit(lang: str, df: pd.DataFrame, encoder: SentenceTransformer) -> None:
    docs = df["text_norm"].tolist()
    emb = embed(df, lang, encoder)
    model = build_model(lang, encoder)
    topics, _ = model.fit_transform(docs, emb)
    n_out = sum(t == -1 for t in topics)
    topics = model.reduce_outliers(docs, topics, strategy="embeddings", embeddings=emb,
                                   threshold=OUTLIER_THRESHOLD)
    model.update_topics(docs, topics=topics, vectorizer_model=model.vectorizer_model,
                        ctfidf_model=model.ctfidf_model,
                        representation_model=model.representation_model)
    topics = np.array(topics)
    log.info("%s: %d topics; outliers %d -> %d of %d", lang, len(set(topics)) - 1,
             n_out, (topics == -1).sum(), len(topics))

    MODEL_DIR.mkdir(exist_ok=True)
    model.save(MODEL_DIR / f"bertopic_{lang}", serialization="safetensors",
               save_ctfidf=True, save_embedding_model=EMBEDDING_MODEL)
    df[["review_id"]].assign(topic=topics).to_parquet(INTERIM_DIR / f"topics_{lang}.parquet")

    # Review sheet: keywords, size per app, examples and the proposed category.
    info = pd.DataFrame({"topic": sorted(set(topics))})
    info["keywords"] = info["topic"].map(
        lambda t: ", ".join(w for w, _ in model.get_topic(t)) if t != -1 else "(outliers)")
    info["count"] = info["topic"].map(pd.Series(topics).value_counts())
    shares = pd.crosstab(topics, df["app"], normalize="columns").round(3)
    info = info.join(shares.add_prefix("share_"), on="topic")
    rng = np.random.default_rng(SEED)
    info["examples"] = info["topic"].map(lambda t: " || ".join(
        df["text"].to_numpy()[rng.choice(np.flatnonzero(topics == t),
                                         size=min(4, (topics == t).sum()), replace=False)]
        .astype(str)).replace("\n", " "))
    info = info.merge(propose_categories(emb, topics, encoder), on="topic", how="left")
    REPORT_DIR.mkdir(exist_ok=True)
    info.to_csv(REPORT_DIR / f"topics_{lang}.csv", index=False)
    log.info("%s: review sheet written to reports/topics_%s.csv", lang, lang)


# --------------------------------------------------------------------------- #
# Apply mapping
# --------------------------------------------------------------------------- #
def apply(df: pd.DataFrame) -> None:
    parts = []
    for lang in ("en", "tr"):
        assigned = pd.read_parquet(INTERIM_DIR / f"topics_{lang}.parquet")
        mapping = pd.read_csv(CONFIG_DIR / f"topic_mapping_{lang}.csv")
        unknown = set(mapping["category"]) - set(CATEGORIES)
        if unknown:
            raise ValueError(f"{lang}: unknown categories in mapping: {unknown}")
        missing = set(assigned["topic"]) - set(mapping["topic"]) - {-1}
        if missing:
            raise ValueError(f"{lang}: topics without a mapping: {sorted(missing)}. "
                             "Re-check config after refitting.")
        m = assigned.merge(mapping[["topic", "category"]], on="topic", how="left")
        m["category"] = m["category"].fillna("other")
        parts.append(m)
    out = df[["review_id", "app", "market", "lang", "at", "score", "sentiment", "polarity",
              "in_main_window", "review_version", "text"]].merge(
        pd.concat(parts), on="review_id")
    out["category_label"] = out["category"].map(lambda c: CATEGORIES[c]["label"])
    out.to_parquet(PROCESSED_DIR / "complaints.parquet", index=False)
    log.info("Wrote %d categorised complaints", len(out))
    main = out[out["in_main_window"]]
    print(pd.crosstab(main["category_label"], main["app"], normalize="columns")
            .round(3).sort_values("cashapp", ascending=False).to_string())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    p = argparse.ArgumentParser()
    p.add_argument("step", choices=["fit", "apply"])
    p.add_argument("--langs", nargs="+", default=["en", "tr"])
    args = p.parse_args()

    df = load_complaints()
    log.info("Complaints per app:\n%s", df["app"].value_counts().to_string())
    if args.step == "fit":
        encoder = SentenceTransformer(EMBEDDING_MODEL)
        for lang in args.langs:
            fit(lang, df[df["lang"] == lang].reset_index(drop=True), encoder)
    else:
        apply(df)


if __name__ == "__main__":
    main()
