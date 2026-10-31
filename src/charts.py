"""Altair chart builders shared by the notebook (PNG export) and the dashboard.

Colour roles follow one rule each:
* app identity  -> fixed categorical slots (validated for colour-vision deficiency);
                   an app keeps its colour in every chart and under every filter
* magnitude     -> one blue ramp, light to dark
* emphasis      -> app colour for the item in focus, neutral grey for context
* status        -> red is reserved for "significant drop" and always carries a label

Every builder takes ``lang`` ("en" or "tr"); data stays in English and only
labels, titles and number/date formats are translated.
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

from src.analysis import APP_NAMES, APP_ORDER, Phase
from src.i18n import TR_LOCALE, category_label, phase_name, t, translate_label

APP_COLORS = {"cashapp": "#2a78d6", "paypal": "#eb6834", "revolut": "#1baf7a",
              "papara": "#eda100"}
NAME_ORDER = [APP_NAMES[a] for a in APP_ORDER]
APP_SCALE = alt.Scale(domain=NAME_ORDER, range=[APP_COLORS[a] for a in APP_ORDER])
SEQ_RAMP = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95"]
CRITICAL = "#d03b3b"
NEUTRAL = "#b5b3ab"

INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def theme() -> dict:
    return {"config": {
        "background": SURFACE,
        "font": FONT,
        "view": {"stroke": None},
        "title": {"color": INK, "fontSize": 15, "fontWeight": 600, "anchor": "start",
                  "subtitleColor": INK_2, "subtitleFontSize": 12, "offset": 12},
        "axis": {"labelColor": MUTED, "titleColor": INK_2, "gridColor": GRID,
                 "domainColor": BASELINE, "tickColor": BASELINE, "labelFontSize": 11,
                 "titleFontSize": 11, "titleFontWeight": 500, "gridWidth": 1},
        "legend": {"labelColor": INK_2, "titleColor": INK_2, "labelFontSize": 11,
                   "titleFontSize": 11, "orient": "top", "symbolType": "circle"},
        "header": {"labelColor": INK, "labelFontSize": 12, "labelFontWeight": 600,
                   "titleColor": INK_2},
        "line": {"strokeWidth": 2},
        "point": {"size": 64, "filled": True},
    }}


alt.theme.register("wallet", enable=True)(theme)


def _pct(field: str, title: str) -> alt.Tooltip:
    return alt.Tooltip(field, title=title, format=".1%")


def _title(title: str, subtitle: str = ""):
    return alt.TitleParams(title, subtitle=subtitle) if subtitle else title


def _localize(chart, lang: str):
    """Apply Turkish month names and decimal comma (Vega-Lite locale config)."""
    return chart.configure(locale=TR_LOCALE) if lang == "tr" else chart


# --------------------------------------------------------------------------- #
# Cross-market comparison
# --------------------------------------------------------------------------- #
def category_heatmap(shares: pd.DataFrame, title: str, subtitle: str = "",
                     lang: str = "en") -> alt.Chart:
    """Category x app matrix of complaint shares (sequential ramp + printed values)."""
    shares = shares.assign(category_label=shares["category"].map(
        lambda k: category_label(k, lang)))
    order = (shares.groupby("category_label")["share"].mean()
                   .sort_values(ascending=False).index.tolist())
    sep = "." if lang == "tr" else ","
    shares = shares.assign(column=shares["app_name"] + " (n=" +
                           shares["total"].map(lambda n: f"{n:,}".replace(",", sep)) + ")")
    apps = (shares.drop_duplicates("app_name").set_index("app_name")
                  .reindex([n for n in NAME_ORDER if n in set(shares["app_name"])])["column"]
                  .tolist())
    base = alt.Chart(shares).encode(
        x=alt.X("column:N", sort=apps, title=None,
                axis=alt.Axis(orient="top", labelColor=INK, labelFontSize=12, domain=False,
                              ticks=False, labelAngle=0)),
        y=alt.Y("category_label:N", sort=order, title=None,
                axis=alt.Axis(domain=False, ticks=False, labelColor=INK_2, labelFontSize=12,
                              labelLimit=260)),
    )
    cells = base.mark_rect(cornerRadius=4, stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("share:Q", scale=alt.Scale(range=SEQ_RAMP, domain=[0, 0.3],
                                                   clamp=True, interpolate="lab"),
                        legend=alt.Legend(title=t("share_of_complaints", lang), format=".0%",
                                          orient="bottom", gradientLength=200)),
        tooltip=[alt.Tooltip("app_name:N", title=t("app", lang)),
                 alt.Tooltip("category_label:N", title=t("category", lang)),
                 _pct("share", t("share", lang)),
                 _pct("ci_low", t("ci_low", lang)), _pct("ci_high", t("ci_high", lang)),
                 alt.Tooltip("complaints:Q", title=t("complaints", lang), format=","),
                 alt.Tooltip("total:Q", title=t("all_complaints", lang), format=",")],
    )
    text = base.mark_text(fontSize=12).encode(
        text=alt.Text("share:Q", format=".0%"),
        color=alt.condition("datum.share > 0.17", alt.value("#ffffff"), alt.value(INK)),
    )
    chart = (cells + text).properties(width=alt.Step(110), height=alt.Step(30),
                                      title=_title(title, subtitle))
    return _localize(chart, lang)


def complaint_rate_bars(ov: pd.DataFrame, lang: str = "en") -> alt.Chart:
    data = ov.reset_index().rename(columns={"index": "app"})
    data["app_name"] = data["app"].map(APP_NAMES)
    base = alt.Chart(data).encode(
        y=alt.Y("app_name:N", sort=NAME_ORDER, title=None,
                axis=alt.Axis(domain=False, ticks=False, labelColor=INK, labelFontSize=12)),
        x=alt.X("complaint_rate:Q", title=t("rate_axis", lang),
                axis=alt.Axis(format=".0%", grid=True), scale=alt.Scale(domain=[0, 1])),
    )
    bars = base.mark_bar(cornerRadiusEnd=4, height=18).encode(
        color=alt.Color("app_name:N", scale=APP_SCALE, legend=None),
        tooltip=[alt.Tooltip("app_name:N", title=t("app", lang)),
                 _pct("complaint_rate", t("complaint_rate", lang)),
                 alt.Tooltip("complaints:Q", title=t("complaints", lang), format=","),
                 alt.Tooltip("clean_reviews:Q", title=t("reviews_with_text", lang),
                             format=",")])
    labels = base.mark_text(align="left", dx=6, color=INK, fontSize=12).encode(
        text=alt.Text("complaint_rate:Q", format=".0%"))
    chart = (bars + labels).properties(
        width=420, height=alt.Step(34),
        title=_title(t("rate_title", lang), t("rate_subtitle", lang)))
    return _localize(chart, lang)


# --------------------------------------------------------------------------- #
# Trends
# --------------------------------------------------------------------------- #
def _spread_labels(values: pd.Series, min_gap: float) -> pd.Series:
    """Nudge end-label positions apart so labels never overlap."""
    order = values.sort_values()
    placed: list[float] = []
    for v in order:
        placed.append(max(v, placed[-1] + min_gap) if placed else v)
    # Re-centre so the nudged block stays around the original values.
    shift = (sum(placed) - order.sum()) / len(placed)
    return pd.Series([p - shift for p in placed], index=order.index).reindex(values.index)


def trend_lines(trend: pd.DataFrame, field: str, title: str, y_title: str,
                y_domain: tuple[float, float], fmt: str = ".2f", subtitle: str = "",
                freq: str = "month", lang: str = "en") -> alt.LayerChart:
    """One line per app, end labels, crosshair tooltip."""
    smooth = f"{field}_smooth"
    data = trend.dropna(subset=[smooth])
    apps = [n for n in NAME_ORDER if n in set(data["app_name"])]
    period_title = t("month", lang) if freq == "month" else t("week_of", lang)
    tfmt = "%b %Y" if freq == "month" else "%d %b %Y"
    base = alt.Chart(data).encode(
        x=alt.X("period:T", title=None, axis=alt.Axis(format="%b %Y", grid=False,
                                                      tickCount="month")),
        y=alt.Y(f"{smooth}:Q", title=y_title, scale=alt.Scale(domain=list(y_domain)),
                axis=alt.Axis(format=fmt)),
        color=alt.Color("app_name:N", scale=APP_SCALE, sort=apps,
                        legend=alt.Legend(title=None)),
    )
    lines = base.mark_line(interpolate="monotone")
    hover = alt.selection_point(fields=["period"], nearest=True, on="pointerover",
                                empty=False, clear="pointerout")
    rule = alt.Chart(data).mark_rule(color=BASELINE).encode(
        x="period:T",
        opacity=alt.condition(hover, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("period:T", title=period_title, format=tfmt)]
        + [alt.Tooltip(f"{a}:Q", format=fmt) for a in apps],
    ).transform_pivot("app_name", value=smooth, groupby=["period"]).add_params(hover)
    points = base.mark_point(size=60, stroke=SURFACE, strokeWidth=2).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0)))
    last = data.loc[data.groupby("app_name")["period"].idxmax()].copy()
    last["label_y"] = _spread_labels(last[smooth], 0.07 * (y_domain[1] - y_domain[0]))
    end_labels = alt.Chart(last).mark_text(align="left", dx=8, fontSize=11, color=INK_2).encode(
        x="period:T", y="label_y:Q", text="app_name:N")
    chart = (lines + rule + points + end_labels).properties(
        width=640, height=260, title=_title(title, subtitle))
    return _localize(chart, lang)


# --------------------------------------------------------------------------- #
# Version impact
# --------------------------------------------------------------------------- #
def version_chart(vs: pd.DataFrame, lang: str = "en") -> alt.LayerChart:
    """Average rating per version with 95% CI; significant drops in red with a label."""
    app = vs["app"].iloc[0]
    version, drop = t("version", lang), t("significant_drop", lang)
    data = vs.assign(lo=vs["avg_stars"] - vs["ci"], hi=vs["avg_stars"] + vs["ci"],
                     status=vs["significant_drop"].map({True: drop, False: version}),
                     biggest_rise=vs["biggest_rise"].map(
                         lambda s: translate_label(s, lang) if isinstance(s, str) else s))
    base = alt.Chart(data).encode(
        x=alt.X("first_seen:T", title=t("version_axis", lang),
                axis=alt.Axis(format="%b %Y", grid=False, tickCount="month")))
    line = base.mark_line(color=NEUTRAL, strokeWidth=1.5).encode(
        y=alt.Y("avg_stars:Q", title=t("avg_rating_axis", lang),
                scale=alt.Scale(domain=[1, 5])))
    err = base.mark_rule(strokeWidth=2).encode(
        y="lo:Q", y2="hi:Q",
        color=alt.Color("status:N", scale=alt.Scale(domain=[version, drop],
                                                    range=[APP_COLORS[app], CRITICAL]),
                        legend=alt.Legend(title=None)))
    pts = base.mark_point(size=80, filled=True, stroke=SURFACE, strokeWidth=2).encode(
        y="avg_stars:Q", color=alt.Color("status:N", legend=None),
        tooltip=[alt.Tooltip("version:N", title=version),
                 alt.Tooltip("first_seen:T", title=t("first_seen", lang), format="%d %b %Y"),
                 alt.Tooltip("reviews:Q", title=t("reviews", lang), format=","),
                 alt.Tooltip("avg_stars:Q", title=t("avg_rating", lang), format=".2f"),
                 alt.Tooltip("delta:Q", title=t("change_vs_prev", lang), format="+.2f"),
                 alt.Tooltip("biggest_rise:N", title=t("largest_rise", lang)),
                 alt.Tooltip("rise_pp:Q", title=t("rise_pp", lang), format="+.1f")])
    unit = t("stars_unit", lang)
    labels = base.transform_filter("datum.significant_drop").mark_text(
        dy=-10, baseline="bottom", fontSize=11, color=CRITICAL, fontWeight=600).encode(
        y="hi:Q", text=alt.Text("label:N")).transform_calculate(
        label=f"'v' + datum.version + ': ' + format(datum.delta, '+.2f') + '{unit}'")
    chart = (line + err + pts + labels).properties(
        width=640, height=240, title=t("version_title", lang, app=APP_NAMES[app]))
    return _localize(chart, lang)


def paired_bars(shares: pd.DataFrame, old: str, new: str, app: str, title: str,
                subtitle: str = "", lang: str = "en") -> alt.Chart:
    """Old vs new (e.g. major version) shares: grey = before, app colour = after."""
    shares = shares.rename(index=lambda s: translate_label(s, lang))
    data = shares.reset_index().melt(id_vars="category", var_name="group", value_name="share")
    labels = {old: f"v{old}", new: f"v{new}"}
    data["group"] = data["group"].map(labels)
    order = shares[new].sort_values(ascending=False).index.tolist()
    chart = alt.Chart(data).mark_bar(cornerRadiusEnd=4, height=12).encode(
        y=alt.Y("category:N", sort=order, title=None,
                axis=alt.Axis(domain=False, ticks=False, labelColor=INK_2, labelLimit=260)),
        yOffset=alt.YOffset("group:N", sort=[labels[old], labels[new]]),
        x=alt.X("share:Q", title=t("share_of_complaints", lang), axis=alt.Axis(format=".0%")),
        color=alt.Color("group:N", sort=[labels[old], labels[new]],
                        scale=alt.Scale(range=[NEUTRAL, APP_COLORS[app]]),
                        legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("category:N", title=t("category", lang)),
                 alt.Tooltip("group:N", title=t("group", lang)),
                 _pct("share", t("share", lang))],
    ).properties(width=420, height=alt.Step(14), title=_title(title, subtitle))
    return _localize(chart, lang)


# --------------------------------------------------------------------------- #
# Papara event impact
# --------------------------------------------------------------------------- #
def _phase_bands(phases: list[Phase], lang: str) -> alt.Chart:
    bands = pd.DataFrame([{"phase": phase_name(p.name, lang), "start": p.start, "end": p.end}
                          for p in phases if p.is_event])
    return alt.Chart(bands).mark_rect(color="#f0efec", opacity=0.9).encode(
        x="start:T", x2="end:T",
        tooltip=[alt.Tooltip("phase:N", title=t("phase", lang)),
                 alt.Tooltip("start:T", title=t("start", lang), format="%d %b %Y"),
                 alt.Tooltip("end:T", title=t("end", lang), format="%d %b %Y")])


def papara_timeline(weekly: pd.DataFrame, phases: list[Phase],
                    lang: str = "en") -> alt.VConcatChart:
    """Weekly volume and rating as two aligned charts (never a dual axis)."""
    data = weekly.reset_index().rename(columns={"at": "week"})
    data["stars_smooth"] = data["stars"].rolling(3, min_periods=1, center=True).mean()
    x = alt.X("week:T", title=None, axis=alt.Axis(format="%b %Y", grid=False,
                                                  tickCount="month"))
    bands = _phase_bands(phases, lang)
    marked = pd.DataFrame([{"phase": phase_name(p.name, lang), "start": p.start,
                            "relaunch": p.name == "Relaunch"} for p in phases
                           if p.name.startswith("Shock") or p.name == "Relaunch"])
    shock_labels = alt.Chart(marked).mark_text(
        align="left", dx=4, dy=-4, baseline="bottom", fontSize=11, color=INK_2,
        fontWeight=600).encode(x="start:T", y=alt.value(0), text="phase:N")
    relaunch_rule = alt.Chart(marked[marked["relaunch"]]).mark_rule(
        color=INK_2, strokeWidth=1).encode(x="start:T")
    week_tip = alt.Tooltip("week:T", title=t("week_of", lang), format="%d %b %Y")
    stars_tip = alt.Tooltip("stars:Q", title=t("avg_rating", lang), format=".2f")
    volume = alt.Chart(data).mark_bar(color=APP_COLORS["papara"], cornerRadiusEnd=2).encode(
        x=x, y=alt.Y("reviews:Q", title=t("reviews_per_week", lang)),
        tooltip=[week_tip, alt.Tooltip("reviews:Q", title=t("reviews", lang), format=","),
                 stars_tip, _pct("complaint_share", t("complaint_share", lang)),
                 _pct("shutdown_share", t("shutdown_share", lang))])
    rating = alt.Chart(data).mark_line(color=APP_COLORS["papara"], interpolate="monotone").encode(
        x=x, y=alt.Y("stars_smooth:Q", title=t("rating_3wk", lang),
                     scale=alt.Scale(domain=[1, 5])),
        tooltip=[week_tip, stars_tip])
    top = (bands + relaunch_rule + volume + shock_labels).properties(width=640, height=170)
    bottom = (bands + relaunch_rule + rating).properties(width=640, height=150)
    chart = alt.vconcat(top, bottom, spacing=8).resolve_scale(x="shared").properties(
        title=_title(t("timeline_title", lang), t("timeline_subtitle", lang)))
    return _localize(chart, lang)


def phase_heatmap(shares: pd.DataFrame, lang: str = "en") -> alt.Chart:
    shares = shares.rename(index=lambda s: translate_label(s, lang),
                           columns=lambda p: phase_name(p, lang))
    data = shares.reset_index().melt(id_vars="category", var_name="phase", value_name="share")
    phases = list(shares.columns)
    order = shares.mean(axis=1).sort_values(ascending=False).index.tolist()
    base = alt.Chart(data).encode(
        x=alt.X("phase:N", sort=phases, title=None,
                axis=alt.Axis(orient="top", labelAngle=0, domain=False, ticks=False,
                              labelColor=INK, labelLimit=120)),
        y=alt.Y("category:N", sort=order, title=None,
                axis=alt.Axis(domain=False, ticks=False, labelColor=INK_2, labelLimit=260)))
    cells = base.mark_rect(cornerRadius=4, stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("share:Q", scale=alt.Scale(range=SEQ_RAMP, domain=[0, 0.45], clamp=True,
                                                    interpolate="lab"),
                        legend=alt.Legend(title=t("share_of_complaints", lang), format=".0%",
                                          orient="bottom", gradientLength=200)),
        tooltip=[alt.Tooltip("phase:N", title=t("phase", lang)),
                 alt.Tooltip("category:N", title=t("category", lang)),
                 _pct("share", t("share", lang))])
    text = base.mark_text(fontSize=12).encode(
        text=alt.Text("share:Q", format=".0%"),
        color=alt.condition("datum.share > 0.25", alt.value("#ffffff"), alt.value(INK)))
    chart = (cells + text).properties(width=alt.Step(120), height=alt.Step(30),
                                      title=t("phase_title", lang))
    return _localize(chart, lang)


# --------------------------------------------------------------------------- #
# Strengths and weaknesses
# --------------------------------------------------------------------------- #
# Diverging: blue = fewer complaints than the other apps (better), red = more.
# Equal steps per arm around a neutral grey midpoint.
DIVERGING = ["#256abf", "#6da7ec", "#b7d3f6", "#f0efec", "#f4bdbb", "#e87a76", "#c93a3a"]
GOOD, BAD = "#006300", CRITICAL     # text colours for better / worse, always with an icon


def strengths_matrix(sw: pd.DataFrame, lang: str = "en") -> alt.Chart:
    """App x category matrix of complaint incidence relative to the other apps."""
    cats = sw[sw["kind"] == "category"]
    apps = [a for a in APP_ORDER if a in set(cats["app"])]
    keys = sorted(set(cats["key"]))
    # Full grid, so categories a model cannot measure show as "n/a".
    grid = pd.MultiIndex.from_product([apps, keys], names=["app", "key"]).to_frame(index=False)
    data = grid.merge(cats.drop(columns="app_name"), on=["app", "key"], how="left")
    data["app_name"] = data["app"].map(APP_NAMES)
    data["category_label"] = data["key"].map(lambda k: category_label(k, lang))
    data["log_ratio"] = np.log2(data["ratio"])
    data["notable"] = data["notable"].fillna(False).astype(bool)
    dec = "," if lang == "tr" else "."
    data["label"] = data["ratio"].map(
        lambda x: "n/a" if pd.isna(x) else f"{x:.1f}×".replace(".", dec))
    data["status"] = np.select([data["ratio"].isna(), data["notable"]],
                               [t("sw_na", lang), t("sw_notable", lang)], t("sw_similar", lang))
    order = (data.groupby("category_label")["value"].mean()
                 .sort_values(ascending=False).index.tolist())
    names = [APP_NAMES[a] for a in apps]
    base = alt.Chart(data).encode(
        x=alt.X("app_name:N", sort=names, title=None,
                axis=alt.Axis(orient="top", labelAngle=0, domain=False, ticks=False,
                              labelColor=INK, labelFontSize=12)),
        y=alt.Y("category_label:N", sort=order, title=None,
                axis=alt.Axis(domain=False, ticks=False, labelColor=INK_2, labelFontSize=12,
                              labelLimit=260)))
    cells = base.mark_rect(cornerRadius=4, stroke=SURFACE, strokeWidth=2).encode(
        color=alt.condition(
            "isValid(datum.log_ratio)",
            alt.Color("log_ratio:Q",
                      scale=alt.Scale(range=DIVERGING, domain=[-1.6, 1.6], domainMid=0,
                                      clamp=True, interpolate="lab"),
                      legend=alt.Legend(title=t("sw_legend", lang), orient="bottom",
                                        gradientLength=220, values=[-1.58, -1, 0, 1, 1.58],
                                        labelExpr="format(pow(2, datum.value), '.1f') + '×'")),
            alt.value("#f7f7f5")),
        opacity=alt.condition("datum.notable", alt.value(1), alt.value(0.35)),
        tooltip=[alt.Tooltip("app_name:N", title=t("app", lang)),
                 alt.Tooltip("category_label:N", title=t("category", lang)),
                 alt.Tooltip("value:Q", title=t("sw_this_app", lang), format=".1f"),
                 alt.Tooltip("others:Q", title=t("sw_other_apps", lang), format=".1f"),
                 alt.Tooltip("ratio:Q", title=t("sw_ratio", lang), format=".2f"),
                 alt.Tooltip("status:N", title=t("sw_status", lang))])
    text = base.mark_text(fontSize=12).encode(
        text="label:N",
        color=alt.condition("datum.notable && abs(datum.log_ratio) > 1",
                            alt.value("#ffffff"), alt.value(INK)),
        opacity=alt.condition("datum.notable", alt.value(1), alt.value(0.55)))
    chart = (cells + text).properties(
        width=alt.Step(120), height=alt.Step(30),
        title=_title(t("sw_matrix_title", lang), t("sw_matrix_subtitle", lang)))
    return _localize(chart, lang)


def strengths_dumbbell(sw: pd.DataFrame, app: str, lang: str = "en") -> alt.LayerChart:
    """This app vs the other apps, complaints per 100 reviews, per category."""
    data = sw[(sw["app"] == app) & (sw["kind"] == "category")].copy()
    data["category_label"] = data["key"].map(lambda k: category_label(k, lang))
    order = data.sort_values("value", ascending=False)["category_label"].tolist()
    this, others = APP_NAMES[app], t("sw_other_apps", lang)
    long = pd.concat([data.assign(who=this, x=data["value"]),
                      data.assign(who=others, x=data["others"])])
    dec = "," if lang == "tr" else "."

    def verdict(row) -> str:
        if not row["notable"]:
            return ""
        if row["better"]:
            return "✓ " + t("sw_fewer", lang, pct=f"{(1 - row['ratio']) * 100:.0f}")
        return "▲ " + t("sw_more", lang, x=f"{row['ratio']:.1f}".replace(".", dec))

    data["verdict"] = data.apply(verdict, axis=1)
    data["x_label"] = data[["value", "others"]].max(axis=1)
    y = alt.Y("category_label:N", sort=order, title=None,
              axis=alt.Axis(domain=False, ticks=False, labelColor=INK_2, labelLimit=260))
    tips = [alt.Tooltip("category_label:N", title=t("category", lang)),
            alt.Tooltip("value:Q", title=this, format=".1f"),
            alt.Tooltip("others:Q", title=others, format=".1f"),
            alt.Tooltip("ratio:Q", title=t("sw_ratio", lang), format=".2f")]
    bar = alt.Chart(data).mark_rule(color=BASELINE, strokeWidth=2).encode(
        y=y, x="value:Q", x2="others:Q", tooltip=tips)
    # Leave room on the right for the verdict labels (longer in Turkish).
    x_max = float(data["x_label"].max()) * (1.45 if (data["verdict"] != "").any() else 1.1)
    x_scale = alt.Scale(domain=[0, x_max], nice=False)
    bar = bar.encode(x=alt.X("value:Q", scale=x_scale))
    dots = alt.Chart(long).mark_point(size=110, filled=True, stroke=SURFACE, strokeWidth=2,
                                      opacity=1).encode(
        y=y, x=alt.X("x:Q", title=t("sw_axis", lang), scale=x_scale,
                     axis=alt.Axis(tickCount=6)),
        color=alt.Color("who:N", sort=[this, others],
                        scale=alt.Scale(domain=[this, others], range=[APP_COLORS[app], NEUTRAL]),
                        legend=alt.Legend(title=None)),
        tooltip=tips)
    labels = alt.Chart(data[data["verdict"] != ""]).mark_text(
        align="left", dx=12, fontSize=11, fontWeight=600).encode(
        y=y, x="x_label:Q", text="verdict:N",
        color=alt.condition("datum.better", alt.value(GOOD), alt.value(BAD)))
    chart = (bar + dots + labels).properties(
        width=520, height=alt.Step(30),
        title=_title(t("sw_dumbbell_title", lang, app=this), t("sw_dumbbell_subtitle", lang)))
    return _localize(chart, lang)
