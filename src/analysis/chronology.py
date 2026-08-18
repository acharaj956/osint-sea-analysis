"""Event chronology and timeline construction.

A chronology is the backbone analytical product of most investigations: events
placed in time order, each carrying its own source rating, so that sequence,
clustering and gaps become visible and every entry remains traceable to its
origin. This module turns the seizure dataset into that product — a narrative
chronology table plus temporal views over it.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import DRUG_COLORS, UNODC_BLUE

CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#fafafa",
)


def _describe(row: pd.Series) -> str:
    """Render one record as a chronology entry."""
    quantity = row.get("quantity")
    unit = row.get("unit", "")
    if pd.notna(quantity):
        amount = f"{quantity:,.0f} {unit}".strip()
    else:
        amount = "quantity not recorded"
    context = str(row.get("seizure_context", "")).lower()
    return f"{row.get('drug_type', 'Unknown substance')} — {amount} ({context})"


def build_chronology(df: pd.DataFrame) -> pd.DataFrame:
    """Return records in time order as a narrative chronology.

    Each entry keeps its Admiralty rating and provenance, so the reader can see
    at a glance which parts of the sequence rest on weakly rated sourcing.
    """
    if df.empty:
        return pd.DataFrame(
            columns=["Date", "Country", "Location", "Event", "Est. Value (USD)",
                     "Admiralty", "Provenance", "Ref"]
        )

    ordered = df.sort_values("date").copy()
    chronology = pd.DataFrame(
        {
            "Date": ordered["date"],
            "Country": ordered["country"],
            "Location": ordered["city"].fillna("") + ", " + ordered["province"].fillna(""),
            "Event": ordered.apply(_describe, axis=1),
            "Est. Value (USD)": ordered["estimated_value_usd"],
            "Admiralty": ordered["admiralty_rating"],
            "Provenance": ordered["provenance"],
            "Ref": ordered["id"].apply(lambda i: f"SEA-{int(i):04d}"),
        }
    )
    return chronology.reset_index(drop=True)


def temporal_gaps(df: pd.DataFrame, threshold_days: int = 45) -> list[dict]:
    """Find unusually long intervals with no recorded event.

    Gaps matter analytically: they may reflect a genuine lull, a collection
    blind spot, or a reporting interruption. Distinguishing between those is an
    analytical question, so the gap is surfaced rather than smoothed over.
    """
    if df.empty or len(df) < 2:
        return []

    dates = df["date"].sort_values().reset_index(drop=True)
    gaps: list[dict] = []
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        if delta >= threshold_days:
            gaps.append(
                {
                    "start": dates[i - 1],
                    "end": dates[i],
                    "days": delta,
                }
            )
    return sorted(gaps, key=lambda g: g["days"], reverse=True)


def build_timeline_figure(df: pd.DataFrame) -> go.Figure | None:
    """Scatter timeline: events across time by country, sized by estimated value."""
    if df.empty:
        return None

    plot_df = df.copy()
    plot_df["Event"] = plot_df.apply(_describe, axis=1)
    plot_df["Ref"] = plot_df["id"].apply(lambda i: f"SEA-{int(i):04d}")

    fig = px.scatter(
        plot_df,
        x="date",
        y="country",
        size="estimated_value_usd",
        color="drug_type",
        color_discrete_map=DRUG_COLORS,
        hover_name="Ref",
        custom_data=["Event", "admiralty_rating", "city"],
        size_max=28,
        labels={"date": "", "country": "", "drug_type": "Substance"},
    )
    fig.update_traces(
        marker=dict(line=dict(width=0.5, color="rgba(255,255,255,0.35)")),
        hovertemplate=(
            "<b>%{hovertext}</b><br>%{x|%d %b %Y} — %{y}, %{customdata[2]}"
            "<br>%{customdata[0]}<br>Source rating: %{customdata[1]}<extra></extra>"
        ),
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=460,
        margin=dict(l=0, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=""),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(categoryorder="category descending"),
    )
    return fig


def build_tempo_figure(df: pd.DataFrame) -> go.Figure | None:
    """Monthly event tempo with a cumulative overlay.

    Monthly counts expose seasonality and clustering that an annual total hides;
    the cumulative line shows whether the underlying rate is accelerating.
    """
    if df.empty:
        return None

    monthly = (
        df.set_index("date").resample("MS").size().rename("events").reset_index()
    )
    monthly["cumulative"] = monthly["events"].cumsum()

    fig = go.Figure()
    fig.add_bar(
        x=monthly["date"],
        y=monthly["events"],
        name="Events per month",
        marker_color=UNODC_BLUE,
        opacity=0.75,
        hovertemplate="%{x|%b %Y}: %{y} events<extra></extra>",
    )
    fig.add_scatter(
        x=monthly["date"],
        y=monthly["cumulative"],
        name="Cumulative",
        yaxis="y2",
        mode="lines",
        line=dict(color="#f39c12", width=2),
        hovertemplate="%{x|%b %Y}: %{y} cumulative<extra></extra>",
    )
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        margin=dict(l=0, r=0, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis=dict(showgrid=False),
        yaxis=dict(title="Events", showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        yaxis2=dict(title="Cumulative", overlaying="y", side="right", showgrid=False),
        hovermode="x unified",
    )
    return fig


def reliability_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Count records by Admiralty rating.

    A chronology whose entries are mostly weakly rated supports weaker
    conclusions, so the sourcing profile is reported alongside the sequence.
    """
    if df.empty:
        return pd.DataFrame(columns=["Admiralty", "Records", "Share"])

    counts = df["admiralty_rating"].value_counts().sort_index()
    return pd.DataFrame(
        {
            "Admiralty": counts.index,
            "Records": counts.values,
            "Share": (counts.values / len(df) * 100).round(1),
        }
    )
