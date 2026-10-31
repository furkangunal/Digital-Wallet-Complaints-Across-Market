"""Streamlit dashboard: complaint themes and sentiment across digital wallet apps.

Available in English and Turkish (language switch at the top, or ?lang=tr).

Run from the project root:
    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
warnings.filterwarnings("ignore")

from src import analysis as A, charts as C  # noqa: E402
from src.i18n import (COLUMN_TR, LANGS, category_label, fmt_int, fmt_num,  # noqa: E402
                      fmt_pct, localize_columns, phase_name, t, translate_label)
from src.taxonomy import CATEGORIES  # noqa: E402

st.set_page_config(page_title="Digital Wallet Complaints", page_icon="💳", layout="wide")


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner="Loading reviews…")
def load():
    reviews, complaints = A.load_reviews(), A.load_complaints()
    weekly = A.papara_weekly(reviews, complaints)
    _, phases = A.detect_papara_events(weekly)
    reviews = A.add_comparison_scope(reviews, phases)
    complaints = A.add_comparison_scope(complaints, phases)
    return reviews, complaints, weekly, phases


@st.cache_data(show_spinner=False)
def strengths():
    reviews, complaints, _, _ = load()
    return A.strengths_weaknesses(reviews, complaints)


def chart(c, height: int) -> None:
    """Render with the shared theme (not Streamlit's) at an explicit height.

    Streamlit rescales charts whose size it has to guess, so every chart is
    fitted to its container width and given its full pixel height (plot plus
    title, legend and axes, ~110px).
    """
    if isinstance(c, alt.VConcatChart):
        c.vconcat = [sub.properties(width="container") for sub in c.vconcat]
    else:
        c = c.properties(width="container", height=height - 110)
    st.altair_chart(c, theme=None, width="stretch", height=height)


def table_view(df: pd.DataFrame, label: str) -> None:
    with st.expander(label):
        st.dataframe(localize_columns(df, lang), hide_index=True)


# --------------------------------------------------------------------------- #
# Language (kept in the URL so a Turkish link can be shared)
# --------------------------------------------------------------------------- #
head, switch = st.columns([6, 1])
lang = switch.segmented_control(
    "Language", list(LANGS), format_func=LANGS.get, label_visibility="collapsed",
    default=st.query_params.get("lang", "en") if st.query_params.get("lang") in LANGS else "en",
) or "en"
st.query_params["lang"] = lang

try:
    reviews, complaints, weekly, phases = load()
except FileNotFoundError:
    st.error(t("no_data", lang))
    st.stop()

# --------------------------------------------------------------------------- #
# Header and filters (one row, scoping everything below)
# --------------------------------------------------------------------------- #
head.title(t("page_title", lang))
st.caption(t("caption", lang))

f1, f2, f3 = st.columns([3, 2, 2])
apps = f1.pills(t("apps", lang), A.APP_ORDER, selection_mode="multi", default=A.APP_ORDER,
                format_func=A.APP_NAMES.get) or A.APP_ORDER
exclude_event = f2.toggle(t("exclude_event", lang), value=True,
                          help=t("exclude_event_help", lang))
exclude_shutdown = f3.toggle(t("hide_shutdown", lang), value=True,
                             help=t("hide_shutdown_help", lang))

r = reviews[reviews["app"].isin(apps)].copy()
c = complaints[complaints["app"].isin(apps)].copy()
if not exclude_event:
    r["in_comparison"], c["in_comparison"] = r["in_main_window"], c["in_main_window"]

(tab_overview, tab_strengths, tab_complaints, tab_trend, tab_versions, tab_papara,
 tab_reviews) = st.tabs(
    [t(k, lang) for k in ("tab_overview", "tab_strengths", "tab_complaints", "tab_trend",
                          "tab_versions", "tab_papara", "tab_reviews")])

# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
with tab_overview:
    ov = A.overview(r, c).dropna(subset=["reviews"])
    cols = st.columns(len(ov))
    for col, (_, row) in zip(cols, ov.iterrows(), strict=True):
        with col.container(border=True):
            st.markdown(f"**{row['app_name']}**")
            st.metric(t("average_rating", lang), f"{fmt_num(row['avg_stars'], 2, lang)} ★")
            st.metric(t("complaint_rate", lang), fmt_pct(row["complaint_rate"], lang),
                      help=t("complaint_rate_help", lang))
            st.metric(t("text_sentiment", lang),
                      fmt_num(row["avg_polarity"], 2, lang, signed=True),
                      help=t("text_sentiment_help", lang))
            st.caption(t("n_reviews", lang, n=fmt_int(int(row["reviews"]), lang)))

    left, right = st.columns([3, 2])
    with left:
        chart(C.complaint_rate_bars(ov, lang=lang), 250)
    with right:
        st.subheader(t("key_findings", lang))
        st.markdown(t("findings", lang))
    table_view(ov.reset_index(drop=True).round(3), t("table_view", lang))

# --------------------------------------------------------------------------- #
# Strengths and weaknesses
# --------------------------------------------------------------------------- #
def sw_value(row: pd.Series, col: str) -> str:
    """Human-readable value of one strengths/weaknesses metric."""
    v = row[col]
    if row["unit"] == "stars":
        return f"{fmt_num(v, 2, lang)} ★"
    if row["unit"] == "share":
        return fmt_pct(v, lang)
    if row["unit"] == "hours":
        return (t("sw_minutes", lang, m=f"{v * 60:.0f}") if v < 1
                else t("sw_hours", lang, h=fmt_num(v, 1, lang)))
    return t("sw_per100", lang, v=fmt_num(v, 1, lang))


def sw_line(row: pd.Series) -> str:
    name = (category_label(row["key"], lang) if row["kind"] == "category"
            else t(f"sw_m_{row['key']}", lang))
    return (f"**{name}**: {sw_value(row, 'value')} "
            f"({t('sw_vs', lang, others=sw_value(row, 'others'))})")


with tab_strengths:
    st.markdown(t("sw_intro", lang))
    sw = strengths()
    sw = sw[sw["app"].isin(apps)]
    mx, _ = st.columns([2, 1])
    with mx:
        chart(C.strengths_matrix(sw, lang=lang), 520)

    sw_app = st.segmented_control(t("app", lang), apps, default=apps[0],
                                  format_func=A.APP_NAMES.get, key="sw_app") or apps[0]
    mine = sw[(sw["app"] == sw_app) & sw["notable"]].copy()
    # Strongest effects first: compare on a log-ratio scale so 3× and 0.33× rank equally.
    mine["strength"] = np.abs(np.log(mine["ratio"].clip(lower=1e-6)))
    mine = mine.sort_values("strength", ascending=False)
    lead_col, lag_col = st.columns(2)
    with lead_col.container(border=True):
        st.markdown(f"#### ✅ {t('sw_leads', lang)}")
        leads = mine[mine["better"]]
        st.markdown("\n".join(f"- {sw_line(r)}" for _, r in leads.iterrows())
                    if len(leads) else t("sw_none_leads", lang))
    with lag_col.container(border=True):
        st.markdown(f"#### ⚠️ {t('sw_lags', lang)}")
        lags = mine[~mine["better"]]
        st.markdown("\n".join(f"- {sw_line(r)}" for _, r in lags.iterrows())
                    if len(lags) else t("sw_none_lags", lang))

    db, _ = st.columns([2, 1])
    with db:
        n_cats = int(((sw["app"] == sw_app) & (sw["kind"] == "category")).sum())
        chart(C.strengths_dumbbell(sw, sw_app, lang=lang), 30 * n_cats + 170)
    if sw_app == "papara":
        st.caption(t("sw_papara_note", lang))
    st.caption(t("sw_reply_note", lang))
    table_view(sw[sw["app"] == sw_app].assign(
                   key=lambda d: [category_label(k, lang) if kd == "category"
                                  else t(f"sw_m_{k}", lang)
                                  for k, kd in zip(d["key"], d["kind"], strict=True)])
                 .drop(columns=["app", "app_name", "kind"]).round(3), t("table_view", lang))

# --------------------------------------------------------------------------- #
# Complaint themes
# --------------------------------------------------------------------------- #
with tab_complaints:
    excl = ("service_disruption",) if exclude_shutdown else ()
    shares = A.category_shares(c, exclude=excl)
    st.markdown(t("complaints_note", lang))
    hm, _ = st.columns([2, 1])
    with hm:
        chart(C.category_heatmap(shares, t("heatmap_title", lang), t("heatmap_subtitle", lang),
                                 lang=lang), 560)
    table_view(shares.assign(category_label=shares["category"].map(
                                 lambda k: category_label(k, lang)))
                     .drop(columns=["app", "category"]).round(3), t("table_view", lang))

# --------------------------------------------------------------------------- #
# Sentiment trend
# --------------------------------------------------------------------------- #
with tab_trend:
    freq = st.segmented_control(t("granularity", lang), ["month", "week"], default="month",
                                format_func=lambda f: t(f"freq_{f}", lang)) or "month"
    trend = A.trend(r, freq=freq, smooth=1 if freq == "month" else 4)
    note = "" if freq == "month" else t("rolling_note", lang)
    chart(C.trend_lines(trend, "avg_stars", t("stars_title", lang), t("avg_rating_axis", lang),
                        (1, 5), ".1f", t("all_reviews", lang) + note, freq=freq, lang=lang), 410)
    chart(C.trend_lines(trend, "avg_polarity", t("sentiment_title", lang),
                        t("sentiment_axis", lang), (-1, 1), ".2f",
                        t("reviews_3words", lang) + note, freq=freq, lang=lang), 410)
    if "papara" in apps:
        st.caption(t("papara_noise", lang))
    table_view(trend[["period", "app_name", "reviews", "avg_stars", "avg_polarity",
                      "neg_share"]].round(3), t("table_view", lang))

# --------------------------------------------------------------------------- #
# Version impact
# --------------------------------------------------------------------------- #
with tab_versions:
    ver_apps = [a for a in apps if a != "papara"] or ["paypal"]
    app = st.segmented_control(t("app", lang), ver_apps, default=ver_apps[0],
                               format_func=A.APP_NAMES.get) or ver_apps[0]
    vs = A.version_stats(reviews, complaints, app)
    chart(C.version_chart(vs, lang=lang), 410)
    st.caption(t("versions_note", lang))
    drops = vs[vs["significant_drop"]][["version", "first_seen", "reviews", "avg_stars", "delta",
                                        "biggest_rise", "rise_pp"]]
    if len(drops):
        drops = drops.assign(biggest_rise=drops["biggest_rise"].map(
            lambda s: translate_label(s, lang)))
        st.dataframe(localize_columns(drops.round(2), lang), hide_index=True)
    table_view(vs[["version", "first_seen", "reviews", "avg_stars", "ci", "delta", "p_value"]]
               .round(3), t("all_versions", lang))

    if app == "paypal":
        st.subheader(t("paypal_compare", lang))
        mv = A.major_version_comparison(reviews, complaints, "paypal", "8", "10")
        m1, m2, m3 = st.columns(3)
        m1.metric(t("v8_rating", lang), f"{fmt_num(mv['stars']['8'], 2, lang)} ★",
                  help=f"n = {fmt_int(mv['n']['8'], lang)}")
        m2.metric(t("v10_rating", lang), f"{fmt_num(mv['stars']['10'], 2, lang)} ★",
                  delta=f"{fmt_num(mv['stars']['10'] - mv['stars']['8'], 2, lang, True)} ★",
                  delta_color="normal", help=f"n = {fmt_int(mv['n']['10'], lang)}")
        m3.metric(t("welch", lang), f"p = {mv['p_value']:.0e}")
        date = mv["since"].strftime("%d.%m.%Y" if lang == "tr" else "%d %b %Y")
        pb, _ = st.columns([2, 1])
        with pb:
            chart(C.paired_bars(mv["category_shares"], "8", "10", "paypal",
                                t("paired_title", lang), t("paired_subtitle", lang, date=date),
                                lang=lang), 520)

# --------------------------------------------------------------------------- #
# Papara event
# --------------------------------------------------------------------------- #
with tab_papara:
    st.markdown(t("papara_note", lang))
    chart(C.papara_timeline(weekly, phases, lang=lang), 470)
    summary = A.phase_summary(reviews, complaints, phases)
    summary["phase"] = summary["phase"].map(lambda p: phase_name(p, lang))
    pct_cols = ["complaint_rate", "shutdown_share", "five_star_complaints"]
    summary = localize_columns(summary.round(2), lang)
    st.dataframe(summary, hide_index=True, column_config={
        (COLUMN_TR[col] if lang == "tr" else col): st.column_config.NumberColumn(format="percent")
        for col in pct_cols})
    ph, _ = st.columns([3, 1])
    with ph:
        chart(C.phase_heatmap(A.phase_category_shares(complaints, phases), lang=lang), 470)
    st.caption(t("baseline_note", lang))

# --------------------------------------------------------------------------- #
# Review explorer
# --------------------------------------------------------------------------- #
with tab_reviews:
    st.markdown(t("explorer_note", lang))
    e1, e2, e3, e4 = st.columns([2, 3, 2, 3])
    ex_app = e1.selectbox(t("app", lang), apps, format_func=A.APP_NAMES.get)
    cats = ["all"] + sorted(CATEGORIES, key=lambda k: category_label(k, lang))
    ex_cat = e2.selectbox(t("category", lang), cats,
                          format_func=lambda k: t("all", lang) if k == "all"
                          else category_label(k, lang))
    ex_stars = e3.multiselect(t("rating", lang), [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])
    query = e4.text_input(t("contains", lang), placeholder=t("contains_placeholder", lang))

    pool = c[(c["app"] == ex_app) & c["score"].isin(ex_stars)
             & (c["in_comparison"] | (ex_app == "papara"))]
    if ex_cat != "all":
        pool = pool[pool["category"] == ex_cat]
    if query:
        pool = pool[pool["text"].str.contains(query, case=False, regex=False)]
    if "seed" not in st.session_state:
        st.session_state.seed = 0
    if st.button(t("shuffle", lang)):
        st.session_state.seed += 1
    st.caption(t("matching", lang, n=fmt_int(len(pool), lang)))
    sample = pool.sample(min(25, len(pool)), random_state=st.session_state.seed)
    sample = (sample[["at", "score", "category", "review_version", "text"]]
              .assign(category=lambda d: d["category"].map(lambda k: category_label(k, lang)))
              .rename(columns={"at": "date", "score": "rating", "review_version": "version"}))
    sample = localize_columns(sample, lang)
    date_col, text_col = sample.columns[0], sample.columns[-1]
    st.dataframe(sample, hide_index=True, column_config={
        date_col: st.column_config.DatetimeColumn(format="D MMM YYYY"),
        text_col: st.column_config.TextColumn(width="large")})
