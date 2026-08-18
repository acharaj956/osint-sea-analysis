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
from src.analysis.ach import (
    SCORE_LABELS,
    diagnosticity_ranking,
    matrix_rows,
    non_diagnostic_evidence,
    score_scenario,
    sensitivity_analysis,
)
from src.analysis.scenarios import SCENARIOS
from src.analysis.chronology import (
    build_chronology,
    build_tempo_figure,
    build_timeline_figure,
    reliability_profile,
    temporal_gaps,
)
from src.evidence import (
    STATUS_ALTERED,
    STATUS_MISSING,
    STATUS_VERIFIED,
    custody_log,
    load_manifest,
    register_summary,
    verify_register,
)
from src.reporting import build_analyst_report

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

    trace_clicked = st.button("Trace Wallet", type="primary", width="stretch")

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
            width="stretch",
            hide_index=True,
            column_config={
                "tx_hash": st.column_config.TextColumn("TX Hash", width="medium"),
                "from_address": st.column_config.TextColumn("From", width="medium"),
                "to_address": st.column_config.TextColumn("To", width="medium"),
            },
        )


def _sidebar_filters(df, *, heatmap_toggle: bool = False):
    """Render the shared scope filters and return the filtered frame.

    Widget keys are fixed so a scope selected on one page carries over when the
    analyst switches to another — the filters define the scope of the whole
    assessment, not of a single view.
    """
    filter_opts = get_filter_options(df)

    with st.sidebar:
        st.markdown("### Filters")

        selected_countries = st.multiselect(
            "Countries",
            options=filter_opts["countries"],
            default=None,
            placeholder="All countries",
            key="filter_countries",
        )

        selected_years = st.multiselect(
            "Years",
            options=filter_opts["years"],
            default=None,
            placeholder="All years",
            key="filter_years",
        )

        selected_drugs = st.multiselect(
            "Drug Types",
            options=filter_opts["drug_types"],
            default=None,
            placeholder="All drug types",
            key="filter_drugs",
        )

        show_heatmap = (
            st.toggle("Show heatmap layer", value=False) if heatmap_toggle else False
        )

    filtered = apply_filters(
        df,
        selected_countries or None,
        selected_years or None,
        selected_drugs or None,
    )
    filters = {
        "Countries": selected_countries,
        "Years": selected_years,
        "Drug types": selected_drugs,
    }
    return filtered, filters, show_heatmap


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
    filtered, _filters, show_heatmap = _sidebar_filters(df, heatmap_toggle=True)

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
                st.plotly_chart(fig_country, width="stretch")

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
                st.plotly_chart(fig_drug, width="stretch")

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
            st.plotly_chart(fig_year, width="stretch")

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
            width="stretch",
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


def render_chronology():
    st.markdown(
        page_header(
            "Event Chronology",
            "Time-ordered event sequence with per-entry source ratings, plus a generated analytical report",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f":warning: {DISCLAIMER}")

    df = load_seizure_data()
    filtered, filters, _ = _sidebar_filters(df)

    if filtered.empty:
        st.warning("No records match the current filters. Widen the scope to build a chronology.")
        return

    stats = compute_statistics(filtered)
    chronology = build_chronology(filtered)
    gaps = temporal_gaps(filtered, threshold_days=45)
    weak = filtered[~filtered["source_reliability"].isin(["A", "B"])]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(f"{len(chronology):,}", "Entries"), unsafe_allow_html=True)
    with c2:
        span = f"{filtered['date'].min():%b %Y} – {filtered['date'].max():%b %Y}"
        st.markdown(metric_card(span, "Coverage"), unsafe_allow_html=True)
    with c3:
        widest = f"{gaps[0]['days']}d" if gaps else "None"
        st.markdown(metric_card(widest, "Longest Gap (45d+)"), unsafe_allow_html=True)
    with c4:
        share = len(weak) / len(filtered) * 100 if len(filtered) else 0
        st.markdown(
            metric_card(f"{share:.0f}%", "Weakly Rated Sources"), unsafe_allow_html=True
        )

    st.markdown("")

    timeline = build_timeline_figure(filtered)
    if timeline is not None:
        st.subheader("Timeline")
        st.plotly_chart(timeline, width="stretch")
        st.caption(
            "Marker size reflects estimated value. Hover an event for its "
            "chronology entry and Admiralty source rating."
        )

    tempo = build_tempo_figure(filtered)
    if tempo is not None:
        st.subheader("Event tempo")
        st.plotly_chart(tempo, width="stretch")

    st.markdown("---")

    tab_chron, tab_gaps, tab_report = st.tabs(
        ["Chronology", "Gaps & sourcing", "Analytical report"]
    )

    with tab_chron:
        st.dataframe(
            chronology,
            width="stretch",
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", width="small"),
                "Event": st.column_config.TextColumn("Event", width="large"),
                "Est. Value (USD)": st.column_config.NumberColumn(
                    "Est. Value (USD)", format="$%d"
                ),
                "Admiralty": st.column_config.TextColumn("Admiralty", width="small"),
                "Ref": st.column_config.TextColumn("Ref", width="small"),
            },
        )
        st.download_button(
            "Download chronology (CSV)",
            chronology.to_csv(index=False),
            "sea_event_chronology.csv",
            "text/csv",
        )

    with tab_gaps:
        st.markdown("**Intervals of 45 days or more with no recorded event**")
        if gaps:
            gap_df = pd.DataFrame(
                [
                    {
                        "From": g["start"].date(),
                        "To": g["end"].date(),
                        "Days": g["days"],
                    }
                    for g in gaps
                ]
            )
            st.dataframe(gap_df, width="stretch", hide_index=True)
            st.markdown(
                '<div class="info-box">A gap may be a genuine lull, a collection '
                "blind spot, or a reporting interruption. The three are not "
                "distinguishable from this dataset alone, so the gap is reported "
                "rather than smoothed over.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("No interval of 45 days or more within the current scope.")

        st.markdown("**Source-rating profile**")
        st.dataframe(
            reliability_profile(filtered),
            width="stretch",
            hide_index=True,
            column_config={
                "Share": st.column_config.NumberColumn("Share (%)", format="%.1f"),
            },
        )

    with tab_report:
        st.markdown(
            '<div class="info-box">The report states its key judgement first, '
            "derives its confidence level from the source-rating profile of the "
            "records in scope, and lists the gaps that limit it. Attaching the "
            "hypothesis matrix adds the ranked explanations and the evidence the "
            "leading hypothesis depends on.</div>",
            unsafe_allow_html=True,
        )

        attach_ach = st.checkbox("Attach hypothesis matrix (ACH)", value=True)
        attach_register = st.checkbox("Attach evidence register", value=True)

        scenario = SCENARIOS["Mekong corridor seizure rise (2022-2024)"] if attach_ach else None
        register = verify_register() if attach_register else None

        report = build_analyst_report(filtered, filters, stats, scenario, register)

        st.download_button(
            "Download analytical report (Markdown)",
            report,
            "sea_analytical_report.md",
            "text/markdown",
            type="primary",
        )
        with st.expander("Preview report", expanded=False):
            st.markdown(report)


def _score_css(value: str) -> str:
    palette = {
        "CC": "background-color: rgba(39,174,96,0.35); color: #eafaf1; font-weight: 600;",
        "C": "background-color: rgba(39,174,96,0.16); color: #d6f5e3;",
        "N": "background-color: rgba(149,165,166,0.12); color: #b9c2c4;",
        "I": "background-color: rgba(231,76,60,0.16); color: #fbdcd8;",
        "II": "background-color: rgba(231,76,60,0.35); color: #fdeae7; font-weight: 600;",
    }
    return palette.get(str(value), "")


def render_hypothesis_testing():
    st.markdown(
        page_header(
            "Hypothesis Testing — ACH",
            "Analysis of Competing Hypotheses: rank explanations by the evidence against them, not for them",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f":warning: {DISCLAIMER}")

    scenario_name = st.selectbox("Analytical question", options=list(SCENARIOS.keys()))
    scenario = SCENARIOS[scenario_name]

    st.markdown(f"**{scenario.question}**")
    if scenario.analytic_note:
        st.markdown(
            f'<div class="info-box">{scenario.analytic_note}</div>',
            unsafe_allow_html=True,
        )

    results = score_scenario(scenario)
    keys = scenario.hypothesis_keys
    excluded = non_diagnostic_evidence(scenario)
    sensitivity = sensitivity_analysis(scenario)
    load_bearing = [f for f in sensitivity if f["changes_conclusion"]]

    leader, runner_up = results[0], results[1] if len(results) > 1 else None
    margin = round(runner_up.inconsistency - leader.inconsistency, 3) if runner_up else None

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            metric_card(leader.hypothesis.key, "Least Contradicted"), unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            metric_card(f"{leader.inconsistency:.2f}", "Inconsistency Score"),
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            metric_card(f"{margin:.2f}" if margin is not None else "—", "Margin Over Next"),
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            metric_card(str(len(load_bearing)), "Load-Bearing Items"),
            unsafe_allow_html=True,
        )

    if margin is not None and margin < 0.5:
        st.warning(
            f"**{leader.hypothesis.key}** leads **{runner_up.hypothesis.key}** by only "
            f"{margin:.2f}. The evidence does not separate them; both should be "
            "carried forward rather than reporting a single answer."
        )

    st.markdown("---")
    st.subheader("Hypothesis ranking")
    st.caption(
        "Ranked by weighted inconsistency, ascending. A hypothesis is judged by "
        "the weight of evidence that contradicts it — evidence consistent with a "
        "hypothesis is weak support, because it is usually consistent with rival "
        "hypotheses too."
    )

    ranking = pd.DataFrame(
        [
            {
                "Rank": rank,
                "H": r.hypothesis.key,
                "Hypothesis": r.hypothesis.statement,
                "Inconsistency": r.inconsistency,
                "Consistency": r.consistency,
                "Contradicted by": ", ".join(r.contradicting) or "—",
            }
            for rank, r in enumerate(results, 1)
        ]
    )
    st.dataframe(
        ranking,
        width="stretch",
        hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "H": st.column_config.TextColumn("ID", width="small"),
            "Hypothesis": st.column_config.TextColumn("Hypothesis", width="large"),
            "Inconsistency": st.column_config.NumberColumn("Inconsistency", format="%.2f"),
            "Consistency": st.column_config.NumberColumn("Consistency", format="%.2f"),
        },
    )

    st.markdown("---")
    st.subheader("Evidence matrix")

    matrix = pd.DataFrame(matrix_rows(scenario))
    styled = matrix.style.apply(
        lambda frame: pd.DataFrame(
            [[_score_css(v) for v in row] for row in frame.values],
            index=frame.index,
            columns=frame.columns,
        ),
        axis=None,
        subset=keys,
    )
    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        column_config={
            "Evidence": st.column_config.TextColumn("Ref", width="small"),
            "Statement": st.column_config.TextColumn("Evidence statement", width="large"),
            "Admiralty": st.column_config.TextColumn("Rating", width="small"),
            "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
            "Diagnosticity": st.column_config.NumberColumn("Diagnosticity", format="%.2f"),
        },
    )
    legend = "  •  ".join(f"**{code}** {label}" for code, label in SCORE_LABELS.items())
    st.caption(legend)
    st.caption(
        "Weight is derived from the Admiralty rating: source reliability and "
        "information credibility multiplied together, so a weakly sourced item "
        "moves the ranking less."
    )

    if excluded:
        st.markdown(
            '<div class="info-box"><b>Excluded as non-diagnostic:</b> '
            + ", ".join(e.key for e in excluded)
            + ". An item consistent with every hypothesis cannot discriminate "
            "between them, however reliable its source, so it is dropped from "
            "scoring.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    col_diag, col_sens = st.columns(2)

    with col_diag:
        st.subheader("Diagnosticity")
        st.caption("Which evidence actually discriminates between the hypotheses.")
        diag = pd.DataFrame(
            [
                {"Ref": e.key, "Rating": e.admiralty_rating, "Diagnosticity": d}
                for e, d in diagnosticity_ranking(scenario)
            ]
        )
        st.dataframe(
            diag,
            width="stretch",
            hide_index=True,
            column_config={
                "Diagnosticity": st.column_config.ProgressColumn(
                    "Diagnosticity", min_value=0.0, max_value=2.0, format="%.2f"
                ),
            },
        )

    with col_sens:
        st.subheader("Sensitivity")
        st.caption("Remove one item at a time and re-rank; does the answer survive?")
        if load_bearing:
            for finding in load_bearing:
                st.error(
                    f"**{finding['evidence_key']}** ({finding['admiralty_rating']}) is "
                    f"load-bearing — without it the leading hypothesis becomes "
                    f"**{finding['leader_without_item']}**."
                )
            st.caption(
                "A conclusion resting on a single item is a disclosed dependency, "
                "not a finished judgement: that item may later prove wrong, or "
                "have been planted."
            )
        else:
            st.success(
                "No single evidence item changes the ranking — the leading "
                "hypothesis does not rest on one report."
            )

    st.markdown("---")
    st.subheader("Hypotheses and monitoring indicators")
    for result in results:
        with st.expander(
            f"{result.hypothesis.key} — {result.hypothesis.statement}", expanded=False
        ):
            st.markdown(
                f"Inconsistency **{result.inconsistency:.2f}** · "
                f"consistency **{result.consistency:.2f}** · "
                f"contradicted by {', '.join(result.contradicting) or '—'}"
            )
            if result.hypothesis.indicators:
                st.markdown("**Indicators that would confirm or weaken this:**")
                for indicator in result.hypothesis.indicators:
                    st.markdown(f"- {indicator}")

    with st.expander("About this technique", expanded=False):
        st.markdown(
            """
            **Analysis of Competing Hypotheses** was set out by Richards J. Heuer Jr.
            in *Psychology of Intelligence Analysis* (CIA Center for the Study of
            Intelligence, 1999). It exists to counter confirmation bias: rather than
            assembling support for the first plausible explanation, the analyst lists
            all credible hypotheses and works to refute them.

            The steps applied here:

            1. Enumerate the hypotheses, including the dull ones — a recording
               artifact and an enforcement-success reading are both carried, so
               neither is adopted by default.
            2. Score every evidence item against every hypothesis.
            3. Drop items that are consistent with all hypotheses: they have no
               discriminating value.
            4. Rank by **inconsistency**, ascending. The surviving hypothesis is the
               one the evidence has failed to refute.
            5. Weight each item by its Admiralty source rating, so sourcing quality
               affects the conclusion.
            6. Test sensitivity by removing items one at a time, to expose
               conclusions that rest on a single report.
            7. State indicators to monitor, turning a static judgement into a
               collection requirement.
            """
        )


def render_evidence_register():
    st.markdown(
        page_header(
            "Evidence Register",
            "Chain-of-custody record with live SHA-256 integrity verification",
        ),
        unsafe_allow_html=True,
    )
    st.caption(f":warning: {DISCLAIMER}")

    entries = verify_register()
    summary = register_summary(entries)
    manifest = load_manifest()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card(str(summary["total"]), "Registered Items"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card(str(summary["verified"]), "Verified"), unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card(str(summary["altered"]), "Altered"), unsafe_allow_html=True)
    with c4:
        st.markdown(
            metric_card(str(summary["missing"] + summary["unregistered"]), "Missing / Unbaselined"),
            unsafe_allow_html=True,
        )

    if summary["altered"]:
        st.error(
            f"{summary['altered']} artifact(s) no longer match the recorded "
            "baseline. Any finding drawn from them is not reproducible until the "
            "discrepancy is explained, and the manifest should only be "
            "regenerated once the change is understood and intended."
        )
    elif manifest is None:
        st.warning(
            "No custody manifest found. Run `python -m src.evidence` to record a "
            "baseline; until then integrity is unknown rather than confirmed."
        )
    else:
        st.success(
            "All registered artifacts match their recorded SHA-256 baseline."
        )

    st.markdown(
        '<div class="info-box">The Berkeley Protocol requires that an '
        "investigation be able to show, for every item it relies on, where it came "
        "from, when it was acquired, who handled it, and that it has not changed "
        "since. The check below is real: hashes are recomputed from the files on "
        "disk and compared against a committed manifest, so editing any registered "
        "artifact makes this page report ALTERED.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Register")

    register_df = pd.DataFrame(
        [
            {
                "Exhibit": e.exhibit_id,
                "Description": e.description,
                "Artifact": e.relative_path,
                "Acquired (UTC)": e.acquired_utc,
                "Size (bytes)": e.size_bytes,
                "SHA-256": e.sha256,
                "Status": e.status,
            }
            for e in entries
        ]
    )

    def _status_css(value: str) -> str:
        if value == STATUS_VERIFIED:
            return "background-color: rgba(39,174,96,0.25); color: #eafaf1; font-weight: 600;"
        if value in (STATUS_ALTERED, STATUS_MISSING):
            return "background-color: rgba(231,76,60,0.30); color: #fdeae7; font-weight: 600;"
        return "background-color: rgba(243,156,18,0.22); color: #fdf3e2;"

    styled_register = register_df.style.apply(
        lambda frame: pd.DataFrame(
            [[_status_css(v) for v in row] for row in frame.values],
            index=frame.index,
            columns=frame.columns,
        ),
        axis=None,
        subset=["Status"],
    )
    st.dataframe(
        styled_register,
        width="stretch",
        hide_index=True,
        column_config={
            "Exhibit": st.column_config.TextColumn("Exhibit", width="small"),
            "Description": st.column_config.TextColumn("Description", width="medium"),
            "SHA-256": st.column_config.TextColumn("SHA-256", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )

    with st.expander("Handling caveats per exhibit", expanded=False):
        for entry in entries:
            st.markdown(f"**{entry.exhibit_id} — {entry.description}**")
            st.caption(f"Origin: {entry.origin}")
            st.caption(f"Handling: {entry.handling}")

    st.markdown("---")
    st.subheader("Custody log")
    st.caption(
        "Acquisition, baseline registration, and this session's verification — "
        "the three events that can be evidenced for these artifacts."
    )
    st.dataframe(
        pd.DataFrame(custody_log(entries)),
        width="stretch",
        hide_index=True,
    )

    if manifest:
        st.caption(
            f"Manifest baseline recorded {manifest.get('generated_utc', 'unknown')} "
            f"using {manifest.get('hash_algorithm', 'SHA-256')}. "
            "Regenerate with `python -m src.evidence` after any intended change."
        )

    st.download_button(
        "Download register (CSV)",
        register_df.to_csv(index=False),
        "evidence_register.csv",
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
            [
                "Crypto Wallet Tracer",
                "Crime Incident Map",
                "Event Chronology",
                "Hypothesis Testing",
                "Evidence Register",
            ],
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

                **Analytic techniques:** Admiralty Code source
                evaluation, event chronology, Analysis of
                Competing Hypotheses (ACH), SHA-256 chain-of-
                custody verification.
                """,
                unsafe_allow_html=True,
            )

    pages = {
        "Crypto Wallet Tracer": render_wallet_tracer,
        "Crime Incident Map": render_crime_map,
        "Event Chronology": render_chronology,
        "Hypothesis Testing": render_hypothesis_testing,
        "Evidence Register": render_evidence_register,
    }
    pages[page]()


if __name__ == "__main__":
    main()
