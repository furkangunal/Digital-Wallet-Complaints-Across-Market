"""Export the README figures in one language.

The notebook already writes the English figures to ``reports/figures/``;
this script writes the same charts with translated labels, e.g. for the
Turkish README:

    python -m src.export_figures --lang tr     # -> reports/figures/tr/
"""

from __future__ import annotations

import argparse
import warnings

from src import analysis as A, charts as C
from src.config import PROJECT_ROOT
from src.i18n import t


def main() -> None:
    warnings.filterwarnings("ignore")
    p = argparse.ArgumentParser()
    p.add_argument("--lang", default="tr", choices=["en", "tr"])
    lang = p.parse_args().lang
    out = PROJECT_ROOT / "reports" / "figures" / (lang if lang != "en" else "")
    out.mkdir(parents=True, exist_ok=True)

    reviews, complaints = A.load_reviews(), A.load_complaints()
    weekly = A.papara_weekly(reviews, complaints)
    _, phases = A.detect_papara_events(weekly)
    reviews = A.add_comparison_scope(reviews, phases)
    complaints = A.add_comparison_scope(complaints, phases)

    shares = A.category_shares(complaints, exclude=("service_disruption",))
    trend = A.trend(reviews)
    mv = A.major_version_comparison(reviews, complaints, "paypal", "8", "10")
    date = mv["since"].strftime("%d.%m.%Y" if lang == "tr" else "%d %b %Y")
    charts = {
        "category_heatmap": C.category_heatmap(
            shares, t("heatmap_title", lang), t("heatmap_subtitle", lang), lang=lang),
        "complaint_rate": C.complaint_rate_bars(A.overview(reviews, complaints), lang=lang),
        "trend_stars": C.trend_lines(trend, "avg_stars", t("stars_title", lang),
                                     t("avg_rating_axis", lang), (1, 5), ".1f",
                                     t("all_reviews", lang), lang=lang),
        "trend_sentiment": C.trend_lines(trend, "avg_polarity", t("sentiment_title", lang),
                                         t("sentiment_axis", lang), (-1, 1), ".2f",
                                         t("reviews_3words", lang), lang=lang),
        "paypal_v8_v10": C.paired_bars(mv["category_shares"], "8", "10", "paypal",
                                       t("paired_title", lang),
                                       t("paired_subtitle", lang, date=date), lang=lang),
        "papara_timeline": C.papara_timeline(weekly, phases, lang=lang),
        "papara_phases": C.phase_heatmap(A.phase_category_shares(complaints, phases), lang=lang),
    }
    sw = A.strengths_weaknesses(reviews, complaints)
    charts["strengths_matrix"] = C.strengths_matrix(sw, lang=lang)
    for app in A.APP_ORDER:
        charts[f"strengths_{app}"] = C.strengths_dumbbell(sw, app, lang=lang)
    for app in ("paypal", "revolut", "cashapp"):
        charts[f"versions_{app}"] = C.version_chart(
            A.version_stats(reviews, complaints, app), lang=lang)
    for name, chart in charts.items():
        chart.save(out / f"{name}.png", scale_factor=2)
        print("saved", out / f"{name}.png")


if __name__ == "__main__":
    main()
