"""Project-wide configuration: paths and the apps under study."""

from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
CONFIG_DIR = PROJECT_ROOT / "config"       # hand-reviewed topic -> category mappings

# Shared analysis window used for all cross-market comparisons (start inclusive,
# end exclusive). Papara is additionally collected back to PAPARA_EVENT_START
# for the separate event-impact section; that older data never enters the
# cross-market analyses.
MAIN_WINDOW = ("2025-10-31", "2026-11-01")
PAPARA_EVENT_START = "2025-01-01"


@dataclass(frozen=True)
class AppConfig:
    key: str          # short identifier used in file names and tables
    name: str         # display name
    app_id: str       # Google Play package name
    market: str       # market label used in cross-market comparisons
    lang: str         # review language requested from Google Play
    country: str      # storefront country requested from Google Play


APPS: dict[str, AppConfig] = {
    a.key: a
    for a in [
        AppConfig("cashapp", "Cash App", "com.squareup.cash", "USA", "en", "us"),
        AppConfig("paypal", "PayPal", "com.paypal.android.p2pmobile", "Global", "en", "us"),
        AppConfig("revolut", "Revolut", "com.revolut.revolut", "Europe", "en", "gb"),
        AppConfig("papara", "Papara", "com.mobillium.papara", "Turkey", "tr", "tr"),
    ]
}
