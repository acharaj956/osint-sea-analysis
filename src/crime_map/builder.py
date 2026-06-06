from __future__ import annotations

import math

import folium
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster

from src.config import DRUG_COLORS, SEA_CENTER, SEA_ZOOM


def create_base_map(
    center: tuple[float, float] = SEA_CENTER,
    zoom: int = SEA_ZOOM,
) -> folium.Map:
    m = folium.Map(
        location=list(center),
        zoom_start=zoom,
        tiles="CartoDB dark_matter",
        width="100%",
        height=620,
        control_scale=True,
    )
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topographic",
        overlay=False,
    ).add_to(m)
    return m


def _popup_html(row: pd.Series) -> str:
    value_str = f"${row.get('estimated_value_usd', 0):,.0f}"
    return f"""
    <div style="
        font-family: Inter, system-ui, sans-serif;
        background: #1a1f2e;
        color: #e0e0e0;
        padding: 12px 14px;
        border-radius: 8px;
        min-width: 220px;
        line-height: 1.5;
        font-size: 13px;
    ">
        <div style="font-weight:600;font-size:14px;margin-bottom:6px;color:#009edb;">
            {row.get('drug_type', 'Unknown')}
        </div>
        <div><b>Date:</b> {pd.Timestamp(row.get('date')).strftime('%Y-%m-%d') if pd.notna(row.get('date')) else 'N/A'}</div>
        <div><b>Location:</b> {row.get('city', '')}, {row.get('country', '')}</div>
        <div><b>Quantity:</b> {row.get('quantity', 0):,.0f} {row.get('unit', '')}</div>
        <div><b>Est. Value:</b> {value_str}</div>
        <div style="margin-top:4px;color:#95a5a6;font-size:11px;">
            {row.get('seizure_context', '')}
        </div>
    </div>
    """


def _marker_radius(quantity: float, unit: str) -> float:
    if quantity <= 0:
        return 5.0
    if unit == "tablets":
        normalized = quantity / 1000
    else:
        normalized = quantity
    radius = math.log10(max(normalized, 1)) * 3
    return max(5.0, min(radius, 20.0))


def add_marker_layer(m: folium.Map, df: pd.DataFrame) -> folium.Map:
    fg = folium.FeatureGroup(name="Seizure Markers")
    cluster = MarkerCluster(name="Clustered Markers")

    for _, row in df.iterrows():
        color = DRUG_COLORS.get(row.get("drug_type", ""), "#ffffff")
        radius = _marker_radius(
            float(row.get("quantity", 0)),
            str(row.get("unit", "")),
        )
        popup = folium.Popup(
            _popup_html(row),
            max_width=280,
        )

        lat = row.get("lat")
        lon = row.get("lon")
        if pd.isna(lat) or pd.isna(lon):
            continue

        marker = folium.CircleMarker(
            location=[float(lat), float(lon)],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1,
            popup=popup,
        )
        marker.add_to(fg)

        folium.Marker(
            location=[float(lat), float(lon)],
            popup=popup,
            icon=folium.DivIcon(html=f'<div style="display:none"></div>'),
        ).add_to(cluster)

    fg.add_to(m)
    cluster.add_to(m)
    return m


def add_heatmap_layer(m: folium.Map, df: pd.DataFrame) -> folium.Map:
    valid = df.dropna(subset=["lat", "lon", "estimated_value_usd"])
    if valid.empty:
        folium.LayerControl(collapsed=False).add_to(m)
        return m

    max_val = valid["estimated_value_usd"].max()
    if max_val == 0:
        max_val = 1.0

    heat_data = [
        [float(r["lat"]), float(r["lon"]), float(r["estimated_value_usd"]) / max_val]
        for _, r in valid.iterrows()
    ]

    fg = folium.FeatureGroup(name="Value Heatmap", show=False)
    HeatMap(
        heat_data,
        radius=22,
        blur=18,
        max_zoom=8,
        gradient={
            "0.2": "#2980b9",
            "0.4": "#27ae60",
            "0.6": "#f39c12",
            "0.8": "#e74c3c",
            "1.0": "#c0392b",
        },
    ).add_to(fg)

    fg.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m
