"""Reproducible build step for the illustrative SEA drug-seizure dataset.

IMPORTANT: the seizure records in `sea_drug_seizures.csv` are SYNTHETIC and
illustrative. They are modeled on publicly reported UNODC trafficking *trends*
for Southeast Asia (2019-2024), but no row corresponds to a specific real
seizure and none should be cited as fact.

To demonstrate open-source analytic tradecraft, this script tags each record
with an Admiralty/NATO source-reliability rating (A-F) and an information
credibility score (1-6), derived deterministically from the notional reporting
channel. The script is idempotent — re-running it leaves an already-enriched
file unchanged.

Usage:
    python data/build_dataset.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
CSV_PATH = DATA_DIR / "sea_drug_seizures.csv"

# Map the notional reporting channel to an Admiralty Code rating:
#   reliability  A (completely reliable) ... F (cannot be judged)
#   credibility  1 (confirmed)           ... 6 (cannot be judged)
ADMIRALTY = {
    "UNODC report": ("B", 2),            # usually reliable / probably true
    "Law enforcement report": ("B", 2),  # usually reliable / probably true
    "Regional intelligence": ("C", 2),   # fairly reliable / probably true
    "Media report": ("D", 3),            # not usually reliable / possibly true
}
DEFAULT_RATING = ("F", 6)                # reliability/credibility cannot be judged


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Replace the misleading `source_type` column with honest provenance metadata."""
    if "admiralty_rating" in df.columns:
        return df  # already enriched

    source = df["source_type"] if "source_type" in df.columns else pd.Series([""] * len(df))
    reliability = source.map(lambda s: ADMIRALTY.get(s, DEFAULT_RATING)[0])
    credibility = source.map(lambda s: ADMIRALTY.get(s, DEFAULT_RATING)[1])

    df = df.drop(columns=["source_type"], errors="ignore")
    df["provenance"] = "Synthetic (illustrative)"
    df["source_reliability"] = reliability
    df["info_credibility"] = credibility
    df["admiralty_rating"] = reliability.str.cat(credibility.astype(str))
    return df


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    out = enrich(df)
    out.to_csv(CSV_PATH, index=False)
    print(f"Wrote {len(out)} records to {CSV_PATH.name}")
    print(out[["id", "country", "drug_type", "admiralty_rating", "provenance"]].head().to_string(index=False))


if __name__ == "__main__":
    main()
