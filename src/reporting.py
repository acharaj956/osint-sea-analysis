"""Analytical report generation.

Produces a written product in the structure an assessment is normally expected
to follow: handling caveat, key judgement first, then method, findings, source
evaluation, and an explicit statement of what is not known. The gaps and the
confidence statement are derived from the data rather than written by hand, so
the report cannot quietly claim more than its sourcing supports.
"""
from __future__ import annotations

import pandas as pd

from src.analysis.ach import Scenario, non_diagnostic_evidence, score_scenario, sensitivity_analysis
from src.analysis.chronology import temporal_gaps
from src.evidence import RegisterEntry, now_utc_iso, register_summary

HANDLING_CAVEAT = (
    "UNCLASSIFIED / ILLUSTRATIVE — independent demonstration product. Not "
    "affiliated with, endorsed by, or representing UNODC or the United Nations. "
    "All underlying data is synthetic or illustrative and must not be cited as fact."
)

# Share of records that must carry a reliability of A or B, and a credibility of
# 1 or 2, before the report will describe its own confidence as moderate or high.
_HIGH_CONFIDENCE_SHARE = 0.80
_MODERATE_CONFIDENCE_SHARE = 0.50


def _confidence_statement(df: pd.DataFrame) -> tuple[str, str]:
    """Derive an analytical confidence level from the source-rating profile."""
    if df.empty:
        return "None", "No records fall within the selected scope."

    strong = df["source_reliability"].isin(["A", "B"]) & df["info_credibility"].isin([1, 2])
    share = strong.mean()

    if share >= _HIGH_CONFIDENCE_SHARE:
        level = "Moderate"
        reason = (
            f"{share:.0%} of records carry a reliability of A-B and a credibility "
            "of 1-2. Confidence is held at moderate rather than high because the "
            "dataset is synthetic and no finding has been corroborated against "
            "independent reporting."
        )
    elif share >= _MODERATE_CONFIDENCE_SHARE:
        level = "Low to moderate"
        reason = (
            f"Only {share:.0%} of records carry a reliability of A-B with a "
            "credibility of 1-2; a substantial minority rest on weakly rated "
            "sourcing."
        )
    else:
        level = "Low"
        reason = (
            f"Just {share:.0%} of records carry strong ratings. Findings should be "
            "treated as indicative only."
        )
    return level, reason


def _identify_gaps(df: pd.DataFrame, scenario: Scenario | None) -> list[str]:
    """Assemble the collection and analytical gaps implied by the current data."""
    gaps: list[str] = []
    if df.empty:
        return ["No records in scope; no assessment possible."]

    weak = df[~(df["source_reliability"].isin(["A", "B"]))]
    if not weak.empty:
        gaps.append(
            f"{len(weak)} of {len(df)} records ({len(weak) / len(df):.0%}) rest on "
            "sources rated C or weaker; corroboration is required before these "
            "entries carry analytical weight."
        )

    thin = df["country"].value_counts()
    sparse = thin[thin <= 3]
    if not sparse.empty:
        gaps.append(
            "Thin coverage for "
            + ", ".join(f"{country} ({count} records)" for country, count in sparse.items())
            + ". Absence of records may reflect a collection blind spot rather "
            "than absence of activity."
        )

    long_gaps = temporal_gaps(df, threshold_days=60)
    if long_gaps:
        widest = long_gaps[0]
        gaps.append(
            f"Longest interval without a recorded event is {widest['days']} days "
            f"({widest['start']:%d %b %Y} to {widest['end']:%d %b %Y}); it is not "
            "established whether this is a genuine lull or a reporting interruption."
        )

    if scenario is not None:
        non_diagnostic = non_diagnostic_evidence(scenario)
        if non_diagnostic:
            gaps.append(
                "Non-diagnostic evidence excluded from hypothesis scoring: "
                + ", ".join(item.key for item in non_diagnostic)
                + ". Collection that would discriminate between the surviving "
                "hypotheses is the priority requirement."
            )
        load_bearing = [
            finding["evidence_key"]
            for finding in sensitivity_analysis(scenario)
            if finding["changes_conclusion"]
        ]
        if load_bearing:
            gaps.append(
                "The leading hypothesis depends on "
                + ", ".join(load_bearing)
                + ". If that reporting is wrong or planted, the ranking changes; "
                "independent verification is required."
            )

    gaps.append(
        "The dataset is synthetic. No conclusion in this product describes a real "
        "event, and none is transferable to an operational setting."
    )
    return gaps


def _format_filters(filters: dict) -> str:
    active = {key: value for key, value in filters.items() if value}
    if not active:
        return "No filters applied — full dataset in scope."
    return "; ".join(
        f"{key}: {', '.join(str(v) for v in value)}" for key, value in active.items()
    )


def build_analyst_report(
    df: pd.DataFrame,
    filters: dict,
    stats: dict,
    scenario: Scenario | None = None,
    register: list[RegisterEntry] | None = None,
) -> str:
    """Render a structured analytical report as Markdown."""
    generated = now_utc_iso()
    level, reason = _confidence_statement(df)
    lines: list[str] = []

    lines += [
        "# Analytical report — Southeast Asia seizure activity",
        "",
        f"> **Handling:** {HANDLING_CAVEAT}",
        "",
        f"**Generated (UTC):** {generated}  ",
        f"**Records in scope:** {len(df)}  ",
        f"**Analytical confidence:** {level}",
        "",
        "---",
        "",
        "## 1. Key judgement",
        "",
    ]

    if df.empty:
        lines += ["No records fall within the selected scope, so no judgement is offered.", ""]
    else:
        top_country = stats.get("top_country", "n/a")
        top_drug = stats.get("top_drug_type", "n/a")
        yoy = stats.get("yoy_value_growth")
        trend = (
            f"Estimated seizure value moved {yoy:+.1f}% in {stats.get('latest_year')} "
            "against the preceding year."
            if yoy is not None
            else "Insufficient span to state a year-on-year trend."
        )
        lines += [
            f"Recorded activity in scope centres on **{top_country}**, and "
            f"**{top_drug}** is the most frequently recorded substance across "
            f"{stats.get('total_countries', 0)} countries over {stats.get('year_range', 'n/a')}. "
            f"{trend}",
            "",
            f"Confidence: **{level}**. {reason}",
            "",
        ]

    lines += [
        "## 2. Scope and method",
        "",
        f"- **Scope:** {_format_filters(filters)}",
        "- **Source evaluation:** every record carries an Admiralty Code rating "
        "(source reliability A-F, information credibility 1-6).",
        "- **Integrity:** registered artifacts are hashed with SHA-256 and checked "
        "against a committed custody manifest before use.",
        "- **Hypothesis testing:** where a scenario is attached, competing "
        "explanations are ranked by weighted inconsistency under Analysis of "
        "Competing Hypotheses, not by supporting evidence.",
        "",
    ]

    if not df.empty:
        lines += [
            "## 3. Key figures",
            "",
            "| Measure | Value |",
            "|---|---|",
            f"| Recorded events | {stats.get('total_incidents', 0):,} |",
            f"| Countries | {stats.get('total_countries', 0)} |",
            f"| Substance categories | {stats.get('unique_drug_types', 0)} |",
            f"| Period | {stats.get('year_range', 'n/a')} |",
            f"| Estimated value (USD) | {stats.get('total_estimated_value', 0):,.0f} |",
            "",
            "### Distribution by country",
            "",
            "| Country | Events |",
            "|---|---|",
        ]
        for country, count in list(stats.get("by_country", {}).items())[:10]:
            lines.append(f"| {country} | {count} |")
        lines.append("")

        lines += [
            "### Source-rating profile",
            "",
            "| Admiralty rating | Records |",
            "|---|---|",
        ]
        for rating, count in df["admiralty_rating"].value_counts().sort_index().items():
            lines.append(f"| {rating} | {count} |")
        lines.append("")

    if scenario is not None:
        results = score_scenario(scenario)
        lines += [
            "## 4. Competing hypotheses",
            "",
            f"**Question:** {scenario.question}",
            "",
            "Ranked by weighted inconsistency — the least-contradicted hypothesis "
            "ranks first. A low score is not proof; it means the evidence has so "
            "far failed to refute the explanation.",
            "",
            "| Rank | Hypothesis | Inconsistency | Consistency | Contradicted by |",
            "|---|---|---|---|---|",
        ]
        for rank, result in enumerate(results, 1):
            contra = ", ".join(result.contradicting) or "—"
            lines.append(
                f"| {rank} | **{result.hypothesis.key}** — {result.hypothesis.statement} "
                f"| {result.inconsistency} | {result.consistency} | {contra} |"
            )
        lines.append("")

        leader = results[0]
        if leader.hypothesis.indicators:
            lines += [
                f"### Indicators to monitor for {leader.hypothesis.key}",
                "",
            ]
            lines += [f"- {indicator}" for indicator in leader.hypothesis.indicators]
            lines.append("")

    section = "5" if scenario is not None else "4"
    lines += [f"## {section}. Intelligence gaps and limitations", ""]
    lines += [f"- {gap}" for gap in _identify_gaps(df, scenario)]
    lines.append("")

    section = "6" if scenario is not None else "5"
    lines += [f"## {section}. Data integrity", ""]
    if register:
        summary = register_summary(register)
        lines += [
            f"{summary['verified']} of {summary['total']} registered artifacts "
            f"verified against the custody manifest at {generated}.",
            "",
            "| Exhibit | Artifact | Status | SHA-256 (truncated) |",
            "|---|---|---|---|",
        ]
        for entry in register:
            lines.append(
                f"| {entry.exhibit_id} | `{entry.relative_path}` | {entry.status} "
                f"| `{entry.sha256[:24]}…` |"
            )
        if summary["altered"]:
            lines += [
                "",
                f"**Warning:** {summary['altered']} artifact(s) no longer match the "
                "recorded baseline. Findings drawn from them are not reproducible "
                "until the discrepancy is resolved.",
            ]
        lines.append("")
    else:
        lines += ["Custody register not attached to this report.", ""]

    lines += [
        "---",
        "",
        f"*Generated automatically by the OSINT Southeast Asia analysis dashboard "
        f"at {generated}. {HANDLING_CAVEAT}*",
        "",
    ]

    return "\n".join(lines)
