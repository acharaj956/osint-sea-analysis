from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import DATA_DIR


@st.cache_data
def load_seizure_data() -> pd.DataFrame:
    path = DATA_DIR / "sea_drug_seizures.csv"
    df = pd.read_csv(path, parse_dates=["date"])
    df["year"] = df["date"].dt.year
    return df


def get_filter_options(df: pd.DataFrame) -> dict:
    return {
        "countries": sorted(df["country"].dropna().unique().tolist()),
        "years": sorted(df["year"].dropna().unique().tolist()),
        "drug_types": sorted(df["drug_type"].dropna().unique().tolist()),
    }


def apply_filters(
    df: pd.DataFrame,
    countries: list[str] | None = None,
    years: list[int] | None = None,
    drug_types: list[str] | None = None,
) -> pd.DataFrame:
    filtered = df.copy()
    if countries:
        filtered = filtered[filtered["country"].isin(countries)]
    if years:
        filtered = filtered[filtered["year"].isin(years)]
    if drug_types:
        filtered = filtered[filtered["drug_type"].isin(drug_types)]
    return filtered


def compute_statistics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_incidents": 0,
            "total_countries": 0,
            "unique_drug_types": 0,
            "year_range": "N/A",
            "top_country": "N/A",
            "top_drug_type": "N/A",
            "total_estimated_value": 0.0,
            "by_country": {},
            "by_drug_type": {},
            "by_year": {},
            "yoy_value_growth": None,
            "latest_year": None,
        }

    years = df["year"].dropna()
    by_country = df["country"].value_counts().to_dict()
    by_drug_type = df["drug_type"].value_counts().to_dict()
    by_year = df.groupby("year").size().to_dict()

    # Year-over-year change in estimated seizure value (a simple trend metric).
    value_by_year = df.groupby("year")["estimated_value_usd"].sum().sort_index()
    yoy_value_growth = None
    latest_year = None
    if len(value_by_year) >= 2:
        latest, previous = value_by_year.iloc[-1], value_by_year.iloc[-2]
        latest_year = int(value_by_year.index[-1])
        if previous:
            yoy_value_growth = (latest - previous) / previous * 100

    return {
        "total_incidents": len(df),
        "total_countries": df["country"].nunique(),
        "unique_drug_types": df["drug_type"].nunique(),
        "year_range": f"{int(years.min())}-{int(years.max())}" if len(years) > 0 else "N/A",
        "top_country": max(by_country, key=by_country.get),
        "top_drug_type": max(by_drug_type, key=by_drug_type.get),
        "total_estimated_value": float(df["estimated_value_usd"].sum()),
        "by_country": by_country,
        "by_drug_type": by_drug_type,
        "by_year": by_year,
        "yoy_value_growth": yoy_value_growth,
        "latest_year": latest_year,
    }
