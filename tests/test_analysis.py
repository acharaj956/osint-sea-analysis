"""Tests for the analytical logic.

These cover the parts of the project where a silent error would produce a
plausible-looking but wrong analytical product: the ACH scoring rules, source
weighting, chronology construction, and integrity verification.

Run with:  python -m pytest
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.analysis.ach import (
    Evidence,
    Hypothesis,
    Scenario,
    admiralty_weight,
    diagnosticity_ranking,
    matrix_rows,
    non_diagnostic_evidence,
    score_scenario,
    sensitivity_analysis,
)
from src.analysis.chronology import build_chronology, reliability_profile, temporal_gaps
from src.analysis.scenarios import MEKONG_SURGE
from src.config import BASE_DIR
from src.evidence import (
    REGISTERED_ARTIFACTS,
    STATUS_ALTERED,
    STATUS_MISSING,
    STATUS_UNREGISTERED,
    STATUS_VERIFIED,
    build_manifest,
    custody_log,
    register_summary,
    verify_register,
)
from src.reporting import build_analyst_report


# --------------------------------------------------------------------------
# Source weighting
# --------------------------------------------------------------------------

def test_admiralty_weight_is_product_of_both_dimensions():
    assert admiralty_weight("A1") == pytest.approx(1.0)
    assert admiralty_weight("B2") == pytest.approx(0.64)
    assert admiralty_weight("D3") == pytest.approx(0.24)


def test_stronger_rating_always_outweighs_weaker():
    assert admiralty_weight("A1") > admiralty_weight("B2") > admiralty_weight("D3")


@pytest.mark.parametrize("rating", ["", "X", "B", "ZZ", "BX", None])
def test_unparseable_ratings_fall_back_to_lowest_confidence(rating):
    """An unreadable rating must never be treated as a confident source."""
    assert admiralty_weight(rating) == pytest.approx(admiralty_weight("F6"))


def test_weight_is_never_zero():
    """A zero weight would silently drop an item from scoring instead of
    down-weighting it."""
    for first in "ABCDEF":
        for second in "123456":
            assert admiralty_weight(f"{first}{second}") > 0


# --------------------------------------------------------------------------
# ACH scoring rules
# --------------------------------------------------------------------------

def _toy_scenario() -> Scenario:
    """Two hypotheses; E1 refutes H1 only, E2 is consistent with both."""
    return Scenario(
        question="Toy question",
        hypotheses=[
            Hypothesis(key="H1", statement="First"),
            Hypothesis(key="H2", statement="Second"),
        ],
        evidence=[
            Evidence(key="E1", statement="Refutes H1", admiralty_rating="A1",
                     scores={"H1": "II", "H2": "C"}),
            Evidence(key="E2", statement="Fits both", admiralty_rating="A1",
                     scores={"H1": "CC", "H2": "CC"}),
        ],
    )


def test_ranking_is_by_inconsistency_not_consistency():
    """The core ACH rule: the least-contradicted hypothesis wins, even when a
    rival has more supporting evidence."""
    results = score_scenario(_toy_scenario())
    assert results[0].hypothesis.key == "H2"
    assert results[0].inconsistency < results[1].inconsistency


def test_evidence_consistent_with_all_hypotheses_is_non_diagnostic():
    scenario = _toy_scenario()
    excluded = [e.key for e in non_diagnostic_evidence(scenario)]
    assert excluded == ["E2"]


def test_non_diagnostic_evidence_is_excluded_from_scores():
    """E2 is strongly consistent with both hypotheses, so it must not inflate
    either consistency score."""
    results = {r.hypothesis.key: r for r in score_scenario(_toy_scenario())}
    assert "E2" not in results["H1"].supporting
    assert "E2" not in results["H2"].supporting


def test_diagnosticity_is_zero_only_for_undiscriminating_evidence():
    scenario = _toy_scenario()
    ranked = dict((e.key, d) for e, d in diagnosticity_ranking(scenario))
    assert ranked["E2"] == 0.0
    assert ranked["E1"] > 0.0


def test_sensitivity_flags_the_item_the_conclusion_rests_on():
    scenario = _toy_scenario()
    findings = {f["evidence_key"]: f for f in sensitivity_analysis(scenario)}
    # Without E1 nothing contradicts either hypothesis, so the leader changes.
    assert findings["E1"]["changes_conclusion"] is True
    assert findings["E2"]["changes_conclusion"] is False


def test_missing_scores_default_to_neutral():
    scenario = Scenario(
        question="Sparse",
        hypotheses=[Hypothesis(key="H1", statement="A"), Hypothesis(key="H2", statement="B")],
        evidence=[Evidence(key="E1", statement="Only scores H1", admiralty_rating="B2",
                           scores={"H1": "I"})],
    )
    results = {r.hypothesis.key: r for r in score_scenario(scenario)}
    assert results["H2"].inconsistency == 0
    assert results["H1"].inconsistency > 0


def test_matrix_rows_expose_one_column_per_hypothesis():
    rows = matrix_rows(MEKONG_SURGE)
    assert len(rows) == len(MEKONG_SURGE.evidence)
    for key in MEKONG_SURGE.hypothesis_keys:
        assert key in rows[0]


# --------------------------------------------------------------------------
# The worked scenario
# --------------------------------------------------------------------------

def test_worked_scenario_ranks_production_increase_first():
    results = score_scenario(MEKONG_SURGE)
    assert results[0].hypothesis.key == "H1"
    assert results[-1].hypothesis.key == "H3"


def test_worked_scenario_leaves_the_top_two_close_together():
    """The evidence should not manufacture false confidence."""
    results = score_scenario(MEKONG_SURGE)
    margin = results[1].inconsistency - results[0].inconsistency
    assert 0 < margin < 0.5


def test_worked_scenario_conclusion_depends_on_the_price_evidence():
    load_bearing = [
        f["evidence_key"] for f in sensitivity_analysis(MEKONG_SURGE)
        if f["changes_conclusion"]
    ]
    assert load_bearing == ["E2"]


def test_worked_scenario_excludes_the_prompting_observation():
    """E1 is the observation that raised the question; it fits every hypothesis."""
    assert [e.key for e in non_diagnostic_evidence(MEKONG_SURGE)] == ["E1"]


def test_every_hypothesis_carries_monitoring_indicators():
    for hypothesis in MEKONG_SURGE.hypotheses:
        assert hypothesis.indicators, f"{hypothesis.key} has no indicators"


# --------------------------------------------------------------------------
# Chronology
# --------------------------------------------------------------------------

def _seizure_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "date": pd.to_datetime(["2023-01-10", "2023-06-01", "2023-06-15"]),
            "country": ["Thailand", "Laos", "Thailand"],
            "province": ["Chiang Rai", "Bokeo", "Bangkok"],
            "city": ["Chiang Rai", "Houayxay", "Bangkok"],
            "drug_type": ["Heroin", "Ketamine", "Heroin"],
            "quantity": [85.0, 12.0, 40.0],
            "unit": ["kg", "kg", "kg"],
            "estimated_value_usd": [3_400_000, 500_000, 1_600_000],
            "seizure_context": ["Border checkpoint", "Port seizure", "Warehouse raid"],
            "provenance": ["Synthetic (illustrative)"] * 3,
            "source_reliability": ["B", "D", "B"],
            "info_credibility": [2, 3, 2],
            "admiralty_rating": ["B2", "D3", "B2"],
        }
    )


def test_chronology_is_time_ordered_and_keeps_source_ratings():
    chronology = build_chronology(_seizure_frame())
    assert list(chronology["Date"]) == sorted(chronology["Date"])
    assert list(chronology["Admiralty"]) == ["B2", "D3", "B2"]
    assert list(chronology["Ref"]) == ["SEA-0001", "SEA-0002", "SEA-0003"]


def test_chronology_entry_reads_as_a_narrative_line():
    entry = build_chronology(_seizure_frame())["Event"].iloc[0]
    assert "Heroin" in entry and "85 kg" in entry and "border checkpoint" in entry


def test_temporal_gaps_reports_long_intervals_only():
    gaps = temporal_gaps(_seizure_frame(), threshold_days=45)
    assert len(gaps) == 1
    assert gaps[0]["days"] == 142  # 10 Jan -> 1 Jun 2023


def test_temporal_gaps_handles_too_few_records():
    assert temporal_gaps(_seizure_frame().head(1)) == []


def test_reliability_profile_shares_sum_to_one_hundred():
    profile = reliability_profile(_seizure_frame())
    assert profile["Records"].sum() == 3
    assert profile["Share"].sum() == pytest.approx(100.0, abs=0.2)


def test_chronology_handles_an_empty_frame():
    empty = build_chronology(_seizure_frame().iloc[0:0])
    assert empty.empty
    assert "Admiralty" in empty.columns


# --------------------------------------------------------------------------
# Evidence register
# --------------------------------------------------------------------------

def test_every_registered_artifact_is_hashed_in_the_manifest():
    manifest = build_manifest()
    assert manifest["hash_algorithm"] == "SHA-256"
    assert len(manifest["artifacts"]) == len(REGISTERED_ARTIFACTS)
    for data in manifest["artifacts"].values():
        assert len(data["sha256"]) == 64


def test_verification_reports_a_known_status_for_every_artifact():
    valid = {STATUS_VERIFIED, STATUS_ALTERED, STATUS_MISSING, STATUS_UNREGISTERED}
    entries = verify_register()
    assert len(entries) == len(REGISTERED_ARTIFACTS)
    assert all(e.status in valid for e in entries)


def test_register_summary_accounts_for_every_entry():
    entries = verify_register()
    summary = register_summary(entries)
    assert summary["total"] == len(entries)
    assert (
        summary["verified"] + summary["altered"] + summary["missing"]
        + summary["unregistered"] == summary["total"]
    )


def test_registered_artifacts_use_lf_endings():
    """Guards the custody baseline against line-ending drift.

    A CRLF checkout changes the hash of an otherwise untouched file, so the
    same commit would verify on one platform and report ALTERED on another.
    `.gitattributes` pins the working tree to LF; this test fails if that slips.
    """
    for artifact in REGISTERED_ARTIFACTS:
        raw = (BASE_DIR / artifact.relative_path).read_bytes()
        assert b"\r\n" not in raw, f"{artifact.relative_path} contains CRLF line endings"


def test_committed_baseline_matches_the_current_artifacts():
    """Fails if a registered artifact was edited without re-recording the
    baseline, which is exactly the drift the register exists to catch."""
    unverified = [
        (e.exhibit_id, e.status) for e in verify_register() if e.status != STATUS_VERIFIED
    ]
    assert not unverified, (
        f"Artifacts out of step with the manifest: {unverified}. "
        "Re-record with `python -m src.evidence` once the change is intended."
    )


def test_custody_log_records_verification_for_each_exhibit():
    entries = verify_register()
    log = custody_log(entries)
    exhibits = {row["Exhibit"] for row in log}
    assert exhibits == {e.exhibit_id for e in entries}
    assert any("re-verified" in row["Action"] for row in log)


# --------------------------------------------------------------------------
# Report generation
# --------------------------------------------------------------------------

def test_report_contains_the_expected_sections():
    df = _seizure_frame()
    df["year"] = df["date"].dt.year
    report = build_analyst_report(
        df, {"Countries": ["Thailand"]},
        {"top_country": "Thailand", "top_drug_type": "Heroin", "total_countries": 2,
         "year_range": "2023", "total_incidents": 3, "unique_drug_types": 2,
         "total_estimated_value": 5_500_000, "by_country": {"Thailand": 2, "Laos": 1},
         "yoy_value_growth": None, "latest_year": 2023},
        MEKONG_SURGE, verify_register(),
    )
    for heading in ["Key judgement", "Scope and method", "Competing hypotheses",
                    "Intelligence gaps", "Data integrity"]:
        assert heading in report


def test_report_always_carries_the_handling_caveat_and_synthetic_warning():
    df = _seizure_frame()
    df["year"] = df["date"].dt.year
    report = build_analyst_report(df, {}, {"by_country": {}}, None, None)
    assert "UNCLASSIFIED / ILLUSTRATIVE" in report
    assert "synthetic" in report.lower()


def test_report_declines_to_judge_when_nothing_is_in_scope():
    empty = _seizure_frame().iloc[0:0]
    report = build_analyst_report(empty, {}, {"by_country": {}}, None, None)
    assert "no judgement is offered" in report
