"""Clean raw reviews and write analysis-ready tables to ``data/processed/``.

Reviews are never silently discarded: every row is kept in
``reviews_all.parquet`` with a ``drop_reason`` column (null = kept), and the
subset used for text analysis is written to ``reviews_clean.parquet``.
Star-rating trends can therefore still use short reviews such as "good",
which carry a rating but no analysable text.

Drop reasons, applied in this order (a review gets the first that matches):
    empty           no text, or only emojis/punctuation/numbers
    duplicate_id    same reviewId seen before (scraper overlap)
    too_short       fewer than MIN_WORDS words
    spam_url        contains a link
    spam_contact    contains an e-mail address or phone number (often fake "support" scams)
    spam_referral   referral/promo code or cashtag begging
    spam_gibberish  mostly non-letters, or one token repeated over and over
    wrong_language  confidently detected as a language other than the app's
    duplicate_text  identical long text posted repeatedly (copy-paste campaign)

Usage:
    python -m src.clean_reviews
"""

from __future__ import annotations

import json
import logging
import re

import pandas as pd
from lingua import Language, LanguageDetectorBuilder

from src.config import APPS, MAIN_WINDOW, PROCESSED_DIR, RAW_DIR
from src.preprocess import (EMAIL_RE, PHONE_RE, URL_RE, WORD_RE, CorpusDeasciifier,
                            base_clean, count_words, extract_emojis, normalize,
                            strip_noise, tr_lower)

log = logging.getLogger("clean")

MIN_WORDS = 3
LANG_CHECK_MIN_WORDS = 4      # language detection is unreliable on shorter texts
LANG_MIN_CONFIDENCE = 0.5     # detected language must be at least this confident...
LANG_MAX_EXPECTED = 0.1       # ...and the expected language at most this likely
DUP_MIN_WORDS = 12            # shorter repeats ("i love cash app") are natural, not spam
DUP_MIN_COUNT = 3

# Only code *sharing* and money begging count as spam. Complaints about
# referral programmes ("my referral bonus was never paid") are kept, since
# they are a genuine complaint topic.
REFERRAL_RE = re.compile(
    r"\b(use my (?:referral |invite |promo )?code|my (?:referral |invite |promo )?code is"
    r"|sign ?up (?:with|using) my (?:code|link)"
    r"|referans kodum|davet kodum|kodumu kullan|kodum ile)", re.I)
CASHTAG_RE = re.compile(r"\$(?!cash ?app\b|cash\b)[A-Za-z][A-Za-z0-9_]{2,}", re.I)
BEGGING_RE = re.compile(r"\b(bless me|hook me up|anything helps|send (?:me|it) to)\b", re.I)

# Common function words; a text containing several of them is in that
# language even if the detector is thrown off by typos or slang.
FUNCTION_WORDS = {
    "en": {"the", "and", "i", "it", "to", "my", "is", "a", "you", "of", "for", "not",
           "this", "that", "in", "me", "have", "but", "with", "was", "on", "can"},
    "tr": {"ve", "bir", "bu", "çok", "ama", "için", "ben", "da", "de", "ne", "mi",
           "var", "yok", "gibi", "daha", "her", "hiç", "olarak", "neden", "artık"},
}
# A phone number alone is not spam (Papara account numbers are 10 digits);
# combined with a contact prompt it is the typical fake-support scam pattern.
CONTACT_PROMPT_RE = re.compile(
    r"\b(call|contact|whatsapp|telegram|text me|reach (?:me|us|them)|helpline|hotline"
    r"|ara(?:yın|yin)|ulaş)", re.I)

# Candidate languages for detection: those actually seen in the data plus close
# neighbours. A restricted set is far more accurate than all 75 languages.
CANDIDATE_LANGUAGES = [
    Language.ENGLISH, Language.TURKISH, Language.AZERBAIJANI, Language.SPANISH,
    Language.PORTUGUESE, Language.FRENCH, Language.GERMAN, Language.ITALIAN,
    Language.DUTCH, Language.ROMANIAN, Language.POLISH, Language.HUNGARIAN,
    Language.CZECH, Language.LITHUANIAN, Language.BULGARIAN, Language.RUSSIAN,
    Language.UKRAINIAN, Language.SERBIAN, Language.CROATIAN, Language.GREEK,
    Language.ARABIC, Language.SWEDISH,
]
EXPECTED_LANGUAGE = {"en": Language.ENGLISH, "tr": Language.TURKISH}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_raw() -> pd.DataFrame:
    frames = []
    for app in APPS.values():
        path = RAW_DIR / app.key / "reviews.jsonl"
        if not path.exists():
            log.warning("%s: no raw data found at %s", app.key, path)
            continue
        # Parse line by line so a half-written last line (collector still
        # running or interrupted) is skipped instead of failing the whole file.
        records = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    log.warning("%s: skipping malformed line", app.key)
        frames.append(pd.DataFrame.from_records(records))
    if not frames:
        raise SystemExit("No raw data found. Run `python -m src.collect_reviews` first.")
    df = pd.concat(frames, ignore_index=True)
    log.info("Loaded %d raw reviews", len(df))
    return df


# --------------------------------------------------------------------------- #
# Spam / quality rules
# --------------------------------------------------------------------------- #
def is_gibberish(text: str) -> bool:
    chars = re.sub(r"\s", "", strip_noise(text))
    if not chars:
        return False
    letter_ratio = sum(c.isalpha() for c in chars) / len(chars)
    if letter_ratio < 0.5:
        return True
    tokens = [t.lower() for t in WORD_RE.findall(text)]
    if len(tokens) >= 6:
        top_share = pd.Series(tokens).value_counts(normalize=True).iloc[0]
        if top_share > 0.5:
            return True
    return False


def is_referral_spam(text: str) -> bool:
    if REFERRAL_RE.search(text):
        return True
    return bool(CASHTAG_RE.search(text) and BEGGING_RE.search(text))


def is_contact_spam(text: str) -> bool:
    if EMAIL_RE.search(text):
        return True
    return bool(PHONE_RE.search(text) and CONTACT_PROMPT_RE.search(text))


def detect_wrong_language(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Flag reviews confidently written in a language other than the app's.

    Returns (wrong-language flags, detected ISO code) aligned to ``df``.
    """
    flags = pd.Series(False, index=df.index)
    detected = pd.Series(pd.NA, index=df.index, dtype="string")
    candidates = df.index[df["n_words"] >= LANG_CHECK_MIN_WORDS]
    if len(candidates) == 0:
        return flags, detected

    detector = LanguageDetectorBuilder.from_languages(*CANDIDATE_LANGUAGES).build()
    texts = [strip_noise(t) for t in df.loc[candidates, "text"]]
    log.info("Running language detection on %d reviews", len(texts))
    results = detector.compute_language_confidence_values_in_parallel(texts)

    codes, wrong = [], []
    for idx, text, values in zip(candidates, texts, results, strict=True):
        lang = df.at[idx, "lang"]
        expected = EXPECTED_LANGUAGE[lang]
        top = values[0]
        expected_conf = next((v.value for v in values if v.language == expected), 0.0)
        tokens = {t.lower() for t in WORD_RE.findall(text)}
        codes.append(top.language.iso_code_639_1.name.lower())
        wrong.append(top.language != expected
                     and top.value >= LANG_MIN_CONFIDENCE
                     and expected_conf <= LANG_MAX_EXPECTED
                     and len(tokens & FUNCTION_WORDS[lang]) < 2)
    detected.loc[candidates] = codes
    flags.loc[candidates] = wrong
    return flags, detected


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def build_table(raw: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame({
        "review_id": raw["reviewId"],
        "app": raw["app"],
        "market": raw["market"],
        "lang": raw["lang"],
        "at": pd.to_datetime(raw["at"]),
        "score": raw["score"].astype("int8"),
        "thumbs_up": raw["thumbsUpCount"].fillna(0).astype("int32"),
        "review_version": raw["reviewCreatedVersion"],
        "app_version": raw["appVersion"],
        "raw_text": raw["content"].fillna(""),
    })
    replied_at = pd.to_datetime(raw["repliedAt"])
    df["has_reply"] = replied_at.notna()
    df["reply_hours"] = (replied_at - df["at"]).dt.total_seconds() / 3600
    df["date"] = df["at"].dt.normalize()

    start, end = (pd.Timestamp(x) for x in MAIN_WINDOW)
    df["in_main_window"] = (df["at"] >= start) & (df["at"] < end)

    df["text"] = df["raw_text"].map(base_clean)
    df["emojis"] = df["text"].map(extract_emojis)
    df["n_words"] = df["text"].map(count_words)
    return df


def assign_drop_reasons(df: pd.DataFrame) -> pd.Series:
    reason = pd.Series(pd.NA, index=df.index, dtype="string")

    def mark(mask: pd.Series, label: str) -> None:
        reason.loc[mask & reason.isna()] = label

    mark(df["n_words"] == 0, "empty")
    mark(df["review_id"].duplicated(), "duplicate_id")
    mark(df["n_words"] < MIN_WORDS, "too_short")
    mark(df["text"].str.contains(URL_RE), "spam_url")
    mark(df["text"].map(is_contact_spam), "spam_contact")
    mark(df["text"].map(is_referral_spam), "spam_referral")
    mark(df["text"].map(is_gibberish), "spam_gibberish")

    # Language detection is the slowest rule, so run it only on survivors.
    wrong, detected = detect_wrong_language(df[reason.isna()])
    mark(wrong.reindex(df.index, fill_value=False), "wrong_language")
    df["detected_lang"] = detected.reindex(df.index)

    # Copy-paste campaigns: identical long texts repeated within one app.
    # The first occurrence is kept, later copies are dropped.
    key = (df["app"] + "|" + df["text_norm"])[reason.isna() & (df["n_words"] >= DUP_MIN_WORDS)]
    copies = key.duplicated() & (key.map(key.value_counts()) >= DUP_MIN_COUNT)
    mark(copies.reindex(df.index, fill_value=False), "duplicate_text")
    return reason


def add_normalized_text(df: pd.DataFrame) -> pd.DataFrame:
    df["text_norm"] = ""
    for lang, group in df.groupby("lang"):
        deasciify = None
        if lang == "tr":
            deasciify = CorpusDeasciifier(group["text"].map(tr_lower))
            log.info("Deasciifier learned %d word mappings", len(deasciify.mapping))
        df.loc[group.index, "text_norm"] = [normalize(t, lang, deasciify) for t in group["text"]]
    return df


def report(df: pd.DataFrame) -> pd.DataFrame:
    table = (df.assign(drop_reason=df["drop_reason"].fillna("kept"))
               .pivot_table(index="drop_reason", columns="app", values="review_id",
                            aggfunc="count", fill_value=0))
    table.loc["total"] = table.sum()
    order = ["kept"] + [r for r in table.index if r not in ("kept", "total")] + ["total"]
    return table.loc[order]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%H:%M:%S")
    df = build_table(load_raw())
    df = add_normalized_text(df)
    df["drop_reason"] = assign_drop_reasons(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = df.drop(columns="raw_text").sort_values(["app", "at"]).reset_index(drop=True)
    df.to_parquet(PROCESSED_DIR / "reviews_all.parquet", index=False)
    clean = df[df["drop_reason"].isna()].drop(columns="drop_reason")
    clean.to_parquet(PROCESSED_DIR / "reviews_clean.parquet", index=False)

    summary = report(df)
    summary.to_csv(PROCESSED_DIR / "cleaning_report.csv")
    log.info("Wrote %d clean reviews (of %d)", len(clean), len(df))
    print("\n" + summary.to_string())
    print("\nClean reviews per app inside the main window:")
    print(clean[clean["in_main_window"]].groupby("app").size().to_string())


if __name__ == "__main__":
    main()
