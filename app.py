from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

from src.config import SUPPORTED_CHAINS, UNODC_BLUE, DRUG_COLORS, DATA_DIR
from src.styles import GLOBAL_CSS, metric_card, risk_badge, sanctioned_tag, page_header
from src.integrity import sha256_file
from src.blockchain.client import BlockchainClient
from src.blockchain.graph import build_transaction_graph, render_graph_html
from src.blockchain.sanctions import OFAC_ADDRESSES, is_sanctioned, get_demo_wallets
from src.blockchain.typologies import detect_typologies
from src.blockchain.demo_data import DEMO_TRANSACTIONS, DEMO_SUMMARIES
from src.crime_map.loader import load_seizure_data, apply_filters, get_filter_options, compute_statistics
from src.crime_map.builder import create_base_map, add_marker_layer, add_heatmap_layer

DISCLAIMER = (
    "Independent demonstration project — not affiliated with, endorsed by, or "
    "representing UNODC or the United Nations. All data shown is "
    "synthetic / illustrative and must not be cited as fact."
)

st.set_page_config(
    page_title="OSINT | Southeast Asia Crime Analysis",
    page_icon="\U0001f50d",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_wallet_tracer():
    st.markdown(
        page_header(
            "Crypto Wallet Tracer",
            "Trace cryptocurrency transactions and identify links to OFAC-sanctioned entities",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f":warning: {DISCLAIMER}")

    col_input, col_options = st.columns([3, 1])

    with col_input:
        demo_wallets = get_demo_wallets()
        demo_labels = ["-- Enter address manually --"] + [
            f"{w['label']} ({w['chain'].upper()})" for w in demo_wallets
        ]
        demo_selection = st.selectbox("Quick select a demo wallet", demo_labels)

        if demo_selection != "-- Enter address manually --":
            idx = demo_labels.index(demo_selection) - 1
            selected_wallet = demo_wallets[idx]
            address = st.text_input(
                "Wallet address",
                value=selected_wallet["address"],
                help="Enter a Bitcoin or Tron wallet address to trace",
            )
            chain = selected_wallet["chain"]
            st.caption(f"**{selected_wallet['label']}** — {selected_wallet['description']}")
        else:
            address = st.text_input(
                "Wallet address",
                placeholder="Enter a BTC or Tron address...",
                help="Enter a Bitcoin or Tron wallet address to trace",
            )
            chain = ""

    with col_options:
        if demo_selection == "-- Enter address manually --":
            chain = st.selectbox(
                "Blockchain",
                options=list(SUPPORTED_CHAINS.keys()),
                format_func=lambda x: SUPPORTED_CHAINS[x],
            )
        else:
            st.selectbox(
                "Blockchain",
                options=[chain],
                format_func=lambda x: SUPPORTED_CHAINS.get(x, x),
                disabled=True,
            )

        use_demo = st.toggle("Demo mode", value=True, help="Use pre-cached data instead of live API calls")

    if not address:
        st.markdown(
            '<div class="info-box">'
            "Select a demo wallet above or enter a custom address to begin tracing. "
            "Demo mode uses pre-cached data and works without API keys."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    trace_clicked = st.button("Trace Wallet", type="primary", use_container_width=True)

    if not trace_clicked and f"traced_{address}" not in st.session_state:
        return

    st.session_state[f"traced_{address}"] = True

    with st.spinner("Tracing wallet transactions..."):
        if use_demo and address in DEMO_SUMMARIES:
            summary = DEMO_SUMMARIES[address]
            transactions = DEMO_TRANSACTIONS[address]
        else:
            client = BlockchainClient()
            summary = client.get_address_summary(address, chain)
            transactions = client.get_transactions(address, chain)

    sanctioned, sanction_info = is_sanctioned(address)

    st.markdown("---")
    st.subheader("Wallet Overview")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(
            metric_card(str(summary.get("tx_count", "N/A")), "Transactions"),
            unsafe_allow_html=True,
        )
    with c2:
        balance = summary.get("balance", 0)
        unit = "USDT" if chain == "tron" else "BTC"
        st.markdown(
            metric_card(f"{_format_value(balance, chain)}", f"Balance ({unit})"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(
                f"{_format_value(summary.get('total_received', 0), chain)}",
                "Total Received",
            ),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(
                f"{_format_value(summary.get('total_sent', 0), chain)}",
                "Total Sent",
            ),
            unsafe_allow_html=True,
        )
    with c5:
        if sanctioned:
            st.markdown(
                metric_card(
                    f'{sanctioned_tag()}',
                    "OFAC Status",
                ),
                unsafe_allow_html=True,
            )
        else:
            sanctions_in_graph = sum(
                1 for tx in transactions
                if is_sanctioned(tx.get("from_address", ""))[0]
                or is_sanctioned(tx.get("to_address", ""))[0]
            )
            if sanctions_in_graph > 0:
                st.markdown(
                    metric_card(
                        f'{risk_badge("Medium")}',
                        f"{sanctions_in_graph} linked sanctioned addr",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    metric_card(f'{risk_badge("Low")}', "No sanctions flags"),
                    unsafe_allow_html=True,
                )

    if sanctioned and sanction_info:
        st.error(
            f"**OFAC Sanctioned Entity:** {sanction_info['name']} | "
            f"Program: {sanction_info['program']} | "
            f"Listed: {sanction_info['date_listed']}"
        )

    st.markdown("---")
    st.subheader("Transaction Network")

    if not transactions:
        st.warning("No transactions found for this address.")
        return

    sanctioned_set = set(OFAC_ADDRESSES.keys())
    graph = build_transaction_graph(address, transactions, sanctioned_set, chain)
    graph_html = render_graph_html(graph)

    components.html(graph_html, height=620, scrolling=False)

    legend_cols = st.columns(4)
    with legend_cols[0]:
        st.markdown(":large_blue_circle: **Queried wallet**")
    with legend_cols[1]:
        st.markdown(":red_circle: **OFAC sanctioned**")
    with legend_cols[2]:
        st.markdown(":white_circle: **Unknown wallet**")
    with legend_cols[3]:
        st.markdown(":arrow_right: **Transaction flow**")

    indicators = detect_typologies(address, transactions, OFAC_ADDRESSES)
    if indicators:
        st.markdown(
            '<div class="info-box"><b>Heuristic laundering-typology indicators</b> '
            "(illustrative): " + ", ".join(indicators) + "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("Transaction Details")

    tx_df = pd.DataFrame(transactions)
    if not tx_df.empty:
        display_cols = ["timestamp", "from_address", "to_address", "value", "tx_hash"]
        available = [c for c in display_cols if c in tx_df.columns]
        tx_display = tx_df[available].copy()

        if "value" in tx_display.columns:
            unit = "USDT" if chain == "tron" else "BTC"
            tx_display = tx_display.rename(columns={"value": f"value_{unit}"})
        if "timestamp" in tx_display.columns:
            tx_display["timestamp"] = pd.to_datetime(tx_display["timestamp"], errors="coerce")
            tx_display = tx_display.sort_values("timestamp", ascending=False)

        st.dataframe(
            tx_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "tx_hash": st.column_config.TextColumn("TX Hash", width="medium"),
                "from_address": st.column_config.TextColumn("From", width="medium"),
                "to_address": st.column_config.TextColumn("To", width="medium"),
            },
        )


def render_crime_map():
    st.markdown(
        page_header(
            "Crime Incident Map",
            "Southeast Asia drug seizure patterns — synthetic dataset modeled on publicly reported UNODC trends",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f":warning: {DISCLAIMER}")

    df = load_seizure_data()
    filter_opts = get_filter_options(df)

    with st.sidebar:
        st.markdown("### Filters")

        selected_countries = st.multiselect(
            "Countries",
            options=filter_opts["countries"],
            default=None,
            placeholder="All countries",
        )

        selected_years = st.multiselect(
            "Years",
            options=filter_opts["years"],
            default=None,
            placeholder="All years",
        )

        selected_drugs = st.multiselect(
            "Drug Types",
            options=filter_opts["drug_types"],
            default=None,
            placeholder="All drug types",
        )

        show_heatmap = st.toggle("Show heatmap layer", value=False)

    filtered = apply_filters(
        df,
        selected_countries or None,
        selected_years or None,
        selected_drugs or None,
    )

    stats = compute_statistics(filtered)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(
            metric_card(f"{stats['total_incidents']:,}", "Seizure Events"),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            metric_card(str(stats["total_countries"]), "Countries"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(str(stats["unique_drug_types"]), "Drug Types"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(stats["year_range"], "Period"),
            unsafe_allow_html=True,
        )
    with c5:
        st.markdown(
            metric_card(stats.get("top_country", "N/A"), "Top Country"),
            unsafe_allow_html=True,
        )
    with c6:
        value_m = stats.get("total_estimated_value", 0) / 1_000_000
        st.markdown(
            metric_card(f"${value_m:,.0f}M", "Est. Value (USD)"),
            unsafe_allow_html=True,
        )

    st.markdown("")

    m = create_base_map()
    m = add_marker_layer(m, filtered)
    if show_heatmap:
        m = add_heatmap_layer(m, filtered)
    else:
        folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, use_container_width=True, height=550, returned_objects=[])

    st.markdown("---")

    tab_charts, tab_data = st.tabs(["Analytics", "Raw Data"])

    with tab_charts:
        chart_c1, chart_c2 = st.columns(2)

        with chart_c1:
            by_country = stats.get("by_country", {})
            if by_country:
                fig_country = px.bar(
                    x=list(by_country.values()),
                    y=list(by_country.keys()),
                    orientation="h",
                    labels={"x": "Seizure Events", "y": ""},
                    title="Seizures by Country",
                    color_discrete_sequence=[UNODC_BLUE],
                )
                fig_country.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#fafafa",
                    yaxis=dict(categoryorder="total ascending"),
                    margin=dict(l=0, r=20, t=40, b=20),
                    height=350,
                )
                st.plotly_chart(fig_country, use_container_width=True)

        with chart_c2:
            by_drug = stats.get("by_drug_type", {})
            if by_drug:
                colors = [DRUG_COLORS.get(d, "#95a5a6") for d in by_drug.keys()]
                fig_drug = go.Figure(
                    data=[
                        go.Pie(
                            labels=list(by_drug.keys()),
                            values=list(by_drug.values()),
                            hole=0.45,
                            marker=dict(colors=colors),
                            textinfo="label+percent",
                            textposition="outside",
                        )
                    ]
                )
                fig_drug.update_layout(
                    title="Seizures by Drug Type",
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#fafafa",
                    showlegend=False,
                    margin=dict(l=20, r=20, t=40, b=20),
                    height=350,
                )
                st.plotly_chart(fig_drug, use_container_width=True)

        by_year = stats.get("by_year", {})
        if by_year:
            fig_year = px.line(
                x=list(by_year.keys()),
                y=list(by_year.values()),
                labels={"x": "Year", "y": "Seizure Events"},
                title="Seizure Trend Over Time",
                markers=True,
                color_discrete_sequence=[UNODC_BLUE],
            )
            fig_year.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#fafafa",
                xaxis=dict(dtick=1),
                margin=dict(l=0, r=20, t=40, b=20),
                height=300,
            )
            st.plotly_chart(fig_year, use_container_width=True)

            yoy = stats.get("yoy_value_growth")
            if yoy is not None:
                st.caption(
                    f"Year-over-year change in estimated seizure value "
                    f"({stats.get('latest_year')}): {yoy:+.1f}%"
                )

    with tab_data:
        display_df = filtered.drop(columns=["lat", "lon"], errors="ignore")
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "estimated_value_usd": st.column_config.NumberColumn(
                    "Est. Value (USD)", format="$%d"
                ),
                "quantity": st.column_config.NumberColumn("Quantity", format="%,.1f"),
                "provenance": st.column_config.TextColumn("Provenance"),
                "admiralty_rating": st.column_config.TextColumn("Admiralty", width="small"),
            },
        )
        st.caption(
            "Each record carries an Admiralty Code rating — source reliability "
            "(A–F) and information credibility (1–6). Provenance: synthetic / illustrative."
        )
        digest = sha256_file(DATA_DIR / "sea_drug_seizures.csv")
        st.caption(f"Source dataset integrity — SHA-256: `{digest[:32]}…`")

        csv = filtered.to_csv(index=False)
        st.download_button(
            "Download filtered data (CSV)",
            csv,
            "sea_seizure_data_filtered.csv",
            "text/csv",
        )


def _format_value(value: float, chain: str) -> str:
    if chain == "tron":
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:,.4f}"
    if value >= 0.001:
        return f"{value:.6f}"
    return f"{value:.8f}"


def main():
    with st.sidebar:
        st.markdown(
            """
            <div style="text-align:center; padding: 1rem 0;">
                <h3 style="margin:0; color:#009edb;">OSINT Dashboard</h3>
                <p style="margin:0; font-size:0.75rem; color:#95a5a6;">
                    Southeast Asia Crime Analysis
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("---")

        page = st.radio(
            "Navigation",
            ["Crypto Wallet Tracer", "Crime Incident Map"],
            label_visibility="collapsed",
        )

        st.markdown("---")

        with st.expander("About", expanded=False):
            st.markdown(
                """
                This dashboard demonstrates open-source intelligence
                (OSINT) analytical capabilities for monitoring
                transnational organized crime in Southeast Asia.

                **Independent project** — not affiliated with, endorsed
                by, or representing UNODC or the United Nations.

                **Data is synthetic / illustrative:**
                - Seizures: synthetic records modeled on publicly
                  reported UNODC *trends* (not real incidents)
                - Sanctions: illustrative reference set; verify against
                  the official OFAC SDN list before any real use
                - Blockchain live mode: Blockchair, TronGrid (public APIs)

                **Methodology** follows the Berkeley Protocol
                on Digital Open Source Investigations. See
                METHODOLOGY.md for details.
                """,
                unsafe_allow_html=True,
            )

    if page == "Crypto Wallet Tracer":
        render_wallet_tracer()
    else:
        render_crime_map()


if __name__ == "__main__":
    main()
