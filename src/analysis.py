"""Analysis functions shared by the notebook and the Streamlit dashboard.

All cross-market comparisons use the *comparison scope*: the shared 12-month
window, minus Papara's event weeks (see ``detect_papara_events``), so that
the 2025 legal process does not distort the general results.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from src.config import APPS, CONFIG_DIR, INTERIM_DIR, PROCESSED_DIR
from src.taxonomy import CATEGORIES

APP_ORDER = ["cashapp", "paypal", "revolut", "papara"]
APP_NAMES = {k: APPS[k].name for k in APP_ORDER}

# Event detection rule (weekly Papara data): a week is a *shock* when review
# volume is at least VOLUME_X times the median of the previous BASELINE_WEEKS
# weeks AND either the complaint share or the share of "Service shutdown /
# regulatory" complaints rises by at least SHARE_JUMP over the same baseline.
# Weeks with fewer than MIN_WEEKLY_REVIEWS are never shocks (small-number noise).
# Each shock opens a SHOCK_WEEKS-long crisis window; a shock inside an open
# window belongs to the same episode and extends it.
BASELINE_WEEKS = 8
VOLUME_X = 1.75
SHARE_JUMP = 0.2
MIN_WEEKLY_REVIEWS = 50
SHOCK_WEEKS = 8
# Recovery rule: after the last crisis, the first week whose volume is at least
# RECOVERY_VOLUME_X times the previous median AND whose rating is at least
# RECOVERY_STARS above the previous mean marks the relaunch.
RECOVERY_VOLUME_X = 2.5
RECOVERY_STARS = 0.75


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_reviews() -> pd.DataFrame:
    """Every review (including short ones), with sentiment where available."""
    reviews = pd.read_parquet(PROCESSED_DIR / "reviews_all.parquet")
    sent = pd.read_parquet(INTERIM_DIR / "sentiment.parquet",
                           columns=["review_id", "sentiment", "polarity"])
    df = reviews.merge(sent, on="review_id", how="left")
    df["is_clean"] = df["drop_reason"].isna()
    df["app_name"] = df["app"].map(APP_NAMES)
    return df


def load_complaints() -> pd.DataFrame:
    df = pd.read_parquet(PROCESSED_DIR / "complaints.parquet")
    df["app_name"] = df["app"].map(APP_NAMES)
    return df


# --------------------------------------------------------------------------- #
# Papara event windows
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Phase:
    name: str
    start: pd.Timestamp
    end: pd.Timestamp        # exclusive
    is_event: bool


def papara_weekly(reviews: pd.DataFrame, complaints: pd.DataFrame) -> pd.DataFrame:
    p = reviews[reviews["app"] == "papara"].set_index("at")
    weekly = p.resample("W-SUN", label="left", closed="left").agg(
        reviews=("score", "size"), stars=("score", "mean"))
    c = complaints[complaints["app"] == "papara"].set_index("at")
    cw = c.resample("W-SUN", label="left", closed="left").agg(
        complaints=("category", "size"),
        shutdown=("category", lambda s: (s == "service_disruption").sum()))
    weekly = weekly.join(cw).fillna({"complaints": 0, "shutdown": 0})
    # Complaint share is relative to clean reviews (complaints are drawn from them).
    clean = p[p["is_clean"]].resample("W-SUN", label="left", closed="left").size()
    weekly["clean_reviews"] = clean.reindex(weekly.index).fillna(0)
    weekly["complaint_share"] = weekly["complaints"] / weekly["clean_reviews"].replace(0, np.nan)
    weekly["shutdown_share"] = weekly["shutdown"] / weekly["complaints"].replace(0, np.nan)
    return weekly


def detect_papara_events(weekly: pd.DataFrame) -> tuple[list[pd.Timestamp], list[Phase]]:
    base = weekly.shift(1).rolling(BASELINE_WEEKS, min_periods=BASELINE_WEEKS)
    is_shock = (
        (weekly["reviews"] >= MIN_WEEKLY_REVIEWS)
        & (weekly["reviews"] >= VOLUME_X * base["reviews"].median())
        & ((weekly["complaint_share"] >= base["complaint_share"].mean() + SHARE_JUMP)
           | (weekly["shutdown_share"] >= base["shutdown_share"].mean() + SHARE_JUMP))
    )
    shocks = list(weekly.index[is_shock])

    # Group shocks into episodes: [first shock, last shock + window).
    window = pd.Timedelta(weeks=SHOCK_WEEKS)
    episodes: list[list[pd.Timestamp]] = []
    for s in shocks:
        if episodes and s < episodes[-1][1]:
            episodes[-1][1] = s + window
        else:
            episodes.append([s, s + window])

    start, end = weekly.index.min(), weekly.index.max() + pd.Timedelta(weeks=1)
    phases, cursor = [], start
    for i, (s, e) in enumerate(episodes, 1):
        if s > cursor:
            name = "Before the event" if i == 1 else f"Between shocks {i - 1} and {i}"
            phases.append(Phase(name, cursor, s, is_event=i > 1))
        phases.append(Phase(f"Shock {i}", s, e, is_event=True))
        cursor = e

    is_recovery = (
        (weekly.index >= cursor)
        & (weekly["reviews"] >= RECOVERY_VOLUME_X * base["reviews"].median())
        & (weekly["stars"] >= base["stars"].mean() + RECOVERY_STARS)
    )
    if episodes and is_recovery.any():
        relaunch = weekly.index[is_recovery][0]
        phases.append(Phase("After the event", cursor, relaunch, is_event=False))
        phases.append(Phase("Relaunch", relaunch, end, is_event=False))
    else:
        phases.append(Phase("After the event", cursor, end, is_event=False))
    return shocks, phases


def phase_of(ts: pd.Series, phases: list[Phase]) -> pd.Series:
    out = pd.Series(pd.NA, index=ts.index, dtype="string")
    for ph in phases:
        out[(ts >= ph.start) & (ts < ph.end)] = ph.name
    return out


def add_comparison_scope(df: pd.DataFrame, phases: list[Phase]) -> pd.DataFrame:
    """Mark rows used in cross-market comparisons.

    Shared 12-month window for every app; for Papara, weeks that fall inside an
    event phase (shocks and the restricted period between them) are excluded.
    """
    df = df.copy()
    in_event = pd.Series(False, index=df.index)
    for ph in phases:
        if ph.is_event:
            in_event |= (df["at"] >= ph.start) & (df["at"] < ph.end)
    df["in_comparison"] = df["in_main_window"] & ~((df["app"] == "papara") & in_event)
    return df


# --------------------------------------------------------------------------- #
# Cross-market comparison
# --------------------------------------------------------------------------- #
def overview(reviews: pd.DataFrame, complaints: pd.DataFrame) -> pd.DataFrame:
    r = reviews[reviews["in_comparison"]]
    c = complaints[complaints["in_comparison"]]
    out = pd.DataFrame({
        "reviews": r.groupby("app").size(),
        "avg_stars": r.groupby("app")["score"].mean(),
        "clean_reviews": r[r["is_clean"]].groupby("app").size(),
        "avg_polarity": r.groupby("app")["polarity"].mean(),
        "complaints": c.groupby("app").size(),
    }).reindex(APP_ORDER)
    out["complaint_rate"] = out["complaints"] / out["clean_reviews"]
    out.insert(0, "app_name", out.index.map(APP_NAMES))
    return out


def category_shares(complaints: pd.DataFrame, exclude: tuple[str, ...] = ()) -> pd.DataFrame:
    """Share of complaints per category and app (long format, with 95% CI)."""
    c = complaints[complaints["in_comparison"] & ~complaints["category"].isin(exclude)]
    counts = c.groupby(["app", "category"]).size().unstack(fill_value=0)
    totals = counts.sum(axis=1)
    rows = []
    for app in counts.index:
        for cat in counts.columns:
            k, n = counts.at[app, cat], totals[app]
            lo, hi = wilson(k, n)
            rows.append({"app": app, "app_name": APP_NAMES[app], "category": cat,
                         "category_label": CATEGORIES[cat]["label"], "complaints": k,
                         "total": n, "share": k / n, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(rows)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return np.nan, np.nan
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return centre - half, centre + half


# --------------------------------------------------------------------------- #
# Trends
# --------------------------------------------------------------------------- #
PERIODS = {"month": ("MS", 20), "week": ("W-MON", 5)}   # rule, min days covered


def trend(reviews: pd.DataFrame, freq: str = "month", apps: list[str] | None = None,
          smooth: int = 1) -> pd.DataFrame:
    """Average stars (all reviews) and text sentiment (clean reviews) per period.

    Stars use every review, including short ones, so the rating trend is not
    biased by the cleaning step; polarity needs text and uses clean reviews.
    Monthly is the default: Papara has only ~10 reviews a week after the
    event, which makes weekly values mostly noise.
    """
    rule, min_days = PERIODS[freq]
    r = reviews[reviews["in_main_window"]]
    if apps:
        r = r[r["app"].isin(apps)]
    frames = []
    for app, g in r.groupby("app"):
        g = g.set_index("at")
        res = g.resample(rule, label="left", closed="left")
        w = res.agg(reviews=("score", "size"), avg_stars=("score", "mean"))
        w["days"] = res["date"].nunique()
        clean = g[g["is_clean"]].resample(rule, label="left", closed="left")
        w["avg_polarity"] = clean["polarity"].mean()
        w["neg_share"] = clean["sentiment"].apply(
            lambda s: (s == "negative").mean() if len(s) else np.nan)
        for col in ("avg_stars", "avg_polarity", "neg_share"):
            w[f"{col}_smooth"] = w[col].rolling(smooth, min_periods=1).mean()
        w["app"], w["app_name"] = app, APP_NAMES[app]
        frames.append(w.reset_index().rename(columns={"at": "period"}))
    out = pd.concat(frames, ignore_index=True)
    # Drop partial periods at the edges of the window.
    return out[out["days"] >= min_days].reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Version impact
# --------------------------------------------------------------------------- #
def version_stats(reviews: pd.DataFrame, complaints: pd.DataFrame, app: str,
                  min_reviews: int = 200) -> pd.DataFrame:
    """Per-version rating, compared with the previous version (Welch t-test)."""
    r = reviews[(reviews["app"] == app) & reviews["in_main_window"]
                & reviews["review_version"].notna()]
    v = r.groupby("review_version").agg(reviews=("score", "size"), avg_stars=("score", "mean"),
                                        sd=("score", "std"), first_seen=("at", "min"))
    # Versions already live when the window opens are first "seen" on day one
    # through users who never updated, which biases their rating; skip them.
    window_start = pd.Timestamp(reviews.loc[reviews["in_main_window"], "at"].min())
    v = v[(v["reviews"] >= min_reviews)
          & (v["first_seen"] >= window_start + pd.Timedelta(days=14))].sort_values("first_seen")
    v["ci"] = 1.96 * v["sd"] / np.sqrt(v["reviews"])

    c = complaints[(complaints["app"] == app) & complaints["in_main_window"]]
    top = (c.groupby(["review_version", "category"]).size()
            .groupby(level=0, group_keys=False).apply(lambda s: s / s.sum()))

    rows, prev = [], None
    for ver, row in v.iterrows():
        rec = {"version": ver, **row.to_dict(), "delta": np.nan, "p_value": np.nan,
               "biggest_rise": None, "rise_pp": np.nan}
        if prev is not None:
            a = r.loc[r["review_version"] == prev, "score"]
            b = r.loc[r["review_version"] == ver, "score"]
            rec["delta"] = b.mean() - a.mean()
            rec["p_value"] = stats.ttest_ind(b, a, equal_var=False).pvalue
            if ver in top.index.get_level_values(0) and prev in top.index.get_level_values(0):
                diff = top.loc[ver].sub(top.loc[prev], fill_value=0)
                diff = diff.drop("other", errors="ignore")
                rec["biggest_rise"] = CATEGORIES[diff.idxmax()]["label"]
                rec["rise_pp"] = diff.max() * 100
        rows.append(rec)
        prev = ver
    out = pd.DataFrame(rows)
    out["significant_drop"] = (out["delta"] <= -0.3) & (out["p_value"] < 0.01)
    out["app"], out["app_name"] = app, APP_NAMES[app]
    return out


def major_version_comparison(reviews: pd.DataFrame, complaints: pd.DataFrame, app: str,
                             old: str, new: str) -> dict:
    """Compare two major versions *over the same dates* (staged rollout).

    Restricting both groups to the period in which both versions were being
    reviewed controls for anything else that changed over time.
    """
    def major(s: pd.Series) -> pd.Series:
        return s.str.split(".").str[0]

    r = reviews[(reviews["app"] == app) & reviews["review_version"].notna()].copy()
    r["major"] = major(r["review_version"])
    start = r.loc[r["major"] == new, "at"].min()
    r = r[(r["at"] >= start) & r["major"].isin([old, new])]
    c = complaints[(complaints["app"] == app) & complaints["review_version"].notna()].copy()
    c["major"] = major(c["review_version"])
    c = c[(c["at"] >= start) & c["major"].isin([old, new])]

    shares = pd.crosstab(c["category"], c["major"], normalize="columns")
    shares.index = shares.index.map(lambda k: CATEGORIES[k]["label"])
    a, b = r.loc[r["major"] == old, "score"], r.loc[r["major"] == new, "score"]
    return {
        "since": start,
        "stars": {old: a.mean(), new: b.mean()},
        "n": {old: len(a), new: len(b)},
        "p_value": stats.ttest_ind(b, a, equal_var=False).pvalue,
        "category_shares": shares[[old, new]].sort_values(new, ascending=False),
    }


# --------------------------------------------------------------------------- #
# Strengths and weaknesses: where each app leads or lags the others
# --------------------------------------------------------------------------- #
# A difference is "notable" when it is statistically clear (p < 0.01) AND large
# enough to matter in practice (thresholds below).
NOTABLE_P = 0.01
MIN_STARS_DIFF = 0.3          # average rating, stars
MIN_RATE_DIFF = 0.05          # complaint rate, share of reviews
MIN_REPLY_DIFF = 0.15         # reply rate to complaints
MIN_TIME_RATIO = 2.0          # median reply time
MIN_CAT_RATIO = 1.5           # category incidence, app vs others
MIN_CAT_DIFF = 1.0            # category incidence, complaints per 100 reviews
MIN_COVERAGE = 0.02           # a category must cover ≥2% of a language's complaints


def measurable_categories() -> dict[str, set[str]]:
    """Categories each language's topic model can measure.

    The smaller Turkish model has no topics (or a token topic) for some
    categories; comparing Papara on them would show a false "lead".
    """
    out = {}
    for lang in ("en", "tr"):
        m = pd.read_csv(CONFIG_DIR / f"topic_mapping_{lang}.csv")
        cover = m.groupby("category")["count"].sum() / m["count"].sum()
        out[lang] = set(cover[cover >= MIN_COVERAGE].index) - {"other", "service_disruption"}
    return out


def _two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    if min(n1, n2) == 0:
        return np.nan
    p = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return float(2 * stats.norm.sf(abs(k1 / n1 - k2 / n2) / se)) if se > 0 else np.nan


def _row(app, kind, key, value, others, p, higher_is_better, notable_size, unit):
    better = value > others if higher_is_better else value < others
    return {"app": app, "app_name": APP_NAMES[app], "kind": kind, "key": key,
            "value": value, "others": others, "diff": value - others,
            "ratio": value / others if others else np.nan, "p_value": p,
            "better": bool(better), "notable": bool(notable_size and p < NOTABLE_P),
            "unit": unit}


def strengths_weaknesses(reviews: pd.DataFrame, complaints: pd.DataFrame) -> pd.DataFrame:
    """Compare every app with the pooled other apps on overall metrics and on
    complaint incidence per category (complaints per 100 reviews with text).

    Incidence, not share of complaints, is used: it measures how often users
    actually hit a problem, so an app with few complaints overall is not
    penalised for having a high *share* in one category.
    """
    r = reviews[reviews["in_comparison"]]
    clean = r[r["is_clean"]]
    c = complaints[complaints["in_comparison"]].merge(
        reviews[["review_id", "has_reply", "reply_hours"]], on="review_id", how="left")
    replies = c[c["has_reply"].fillna(False).astype(bool)]
    valid_time = replies[replies["reply_hours"] >= 0]   # negative = review edited later
    lang_of = {a: APPS[a].lang for a in APP_ORDER}
    measurable = measurable_categories()
    rows = []

    for app in APP_ORDER:
        mine, rest = r["app"] == app, r["app"] != app
        # Average rating (all reviews).
        a, b = r.loc[mine, "score"], r.loc[rest, "score"]
        p = stats.ttest_ind(a, b, equal_var=False).pvalue
        rows.append(_row(app, "overall", "avg_stars", a.mean(), b.mean(), p, True,
                         abs(a.mean() - b.mean()) >= MIN_STARS_DIFF, "stars"))
        # Complaint rate (complaints / reviews with text).
        k1, n1 = (c["app"] == app).sum(), (clean["app"] == app).sum()
        k2, n2 = (c["app"] != app).sum(), (clean["app"] != app).sum()
        rows.append(_row(app, "overall", "complaint_rate", k1 / n1, k2 / n2,
                         _two_prop_p(k1, n1, k2, n2), False,
                         abs(k1 / n1 - k2 / n2) >= MIN_RATE_DIFF, "share"))
        # Reply rate to complaints.
        k1, n1 = replies["app"].eq(app).sum(), c["app"].eq(app).sum()
        k2, n2 = replies["app"].ne(app).sum(), c["app"].ne(app).sum()
        rows.append(_row(app, "overall", "reply_rate", k1 / n1, k2 / n2,
                         _two_prop_p(k1, n1, k2, n2), True,
                         abs(k1 / n1 - k2 / n2) >= MIN_REPLY_DIFF, "share"))
        # Median reply time (hours), only where the app replies at all.
        a = valid_time.loc[valid_time["app"] == app, "reply_hours"]
        b = valid_time.loc[valid_time["app"] != app, "reply_hours"]
        if len(a) >= 30 and len(b) >= 30:
            p = stats.mannwhitneyu(a, b).pvalue
            ratio = max(a.median(), b.median()) / max(min(a.median(), b.median()), 1e-9)
            rows.append(_row(app, "overall", "reply_hours", a.median(), b.median(), p, False,
                             ratio >= MIN_TIME_RATIO, "hours"))

        # Category incidence, compared only with apps whose model measures it.
        for cat in sorted(measurable[lang_of[app]]):
            peers = [x for x in APP_ORDER if x != app and cat in measurable[lang_of[x]]]
            if not peers:
                continue
            k1 = ((c["app"] == app) & (c["category"] == cat)).sum()
            n1 = (clean["app"] == app).sum()
            k2 = (c["app"].isin(peers) & (c["category"] == cat)).sum()
            n2 = clean["app"].isin(peers).sum()
            v, o = 100 * k1 / n1, 100 * k2 / n2
            big = (abs(v - o) >= MIN_CAT_DIFF
                   and (max(v, o) / max(min(v, o), 1e-9)) >= MIN_CAT_RATIO)
            rows.append(_row(app, "category", cat, v, o, _two_prop_p(k1, n1, k2, n2),
                             False, big, "per100"))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Papara event impact
# --------------------------------------------------------------------------- #
def phase_summary(reviews: pd.DataFrame, complaints: pd.DataFrame,
                  phases: list[Phase]) -> pd.DataFrame:
    r = reviews[reviews["app"] == "papara"].copy()
    c = complaints[complaints["app"] == "papara"].copy()
    r["phase"], c["phase"] = phase_of(r["at"], phases), phase_of(c["at"], phases)
    rows = []
    for ph in phases:
        rp, cp = r[r["phase"] == ph.name], c[c["phase"] == ph.name]
        weeks = max((ph.end - ph.start).days / 7, 1)
        clean = rp["is_clean"].sum()
        rows.append({
            "phase": ph.name, "start": ph.start.date(), "end": ph.end.date(),
            "reviews_per_week": len(rp) / weeks, "avg_stars": rp["score"].mean(),
            "avg_polarity": rp["polarity"].mean(),
            "complaint_rate": len(cp) / clean if clean else np.nan,
            "shutdown_share": (cp["category"] == "service_disruption").mean() if len(cp) else np.nan,
            "five_star_complaints": ((cp["score"] == 5).mean() if len(cp) else np.nan),
        })
    return pd.DataFrame(rows)


def phase_category_shares(complaints: pd.DataFrame, phases: list[Phase]) -> pd.DataFrame:
    c = complaints[complaints["app"] == "papara"].copy()
    c["phase"] = phase_of(c["at"], phases)
    shares = pd.crosstab(c["category"], c["phase"], normalize="columns")
    shares = shares[[p.name for p in phases if p.name in shares.columns]]
    shares.index = shares.index.map(lambda k: CATEGORIES[k]["label"])
    return shares
