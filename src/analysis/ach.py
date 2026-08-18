"""Analysis of Competing Hypotheses (ACH).

ACH is the best-known structured analytic technique in intelligence analysis,
set out by Richards J. Heuer Jr. in *Psychology of Intelligence Analysis*
(CIA Center for the Study of Intelligence, 1999). It exists to counter
confirmation bias: instead of building a case for the answer that came to mind
first, the analyst enumerates all plausible hypotheses and then works to
*refute* them.

Two methodological points drive this implementation, because they are what
separate ACH from an ordinary scoring spreadsheet:

1. **Hypotheses are ranked by inconsistency, not consistency.** A hypothesis is
   assessed by the weight of evidence that contradicts it. The hypothesis with
   the *least* inconsistent evidence is the most likely one. Evidence consistent
   with a hypothesis is weak support, because it is usually consistent with
   several rival hypotheses at the same time.

2. **Evidence is judged on diagnosticity.** An item that sits equally well with
   every hypothesis cannot discriminate between them, however reliable its
   source. Diagnosticity is the spread of an item's scores across the hypothesis
   set; items with zero spread are flagged for removal (Heuer's step 4).

Evidence weight is derived from the Admiralty Code rating carried by each item,
so source evaluation feeds the analytic conclusion rather than sitting beside it
as decoration.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pstdev

# Consistency scale applied to each evidence/hypothesis pair.
SCORE_VALUES = {
    "CC": 2,   # strongly consistent
    "C": 1,    # consistent
    "N": 0,    # neutral / not applicable
    "I": -1,   # inconsistent
    "II": -2,  # strongly inconsistent
}

SCORE_LABELS = {
    "CC": "Strongly consistent",
    "C": "Consistent",
    "N": "Neutral / not applicable",
    "I": "Inconsistent",
    "II": "Strongly inconsistent",
}

# Admiralty Code -> confidence weight. Source reliability (A-F) and information
# credibility (1-6) are independent dimensions, so the weight is their product:
# a B2 item carries 0.8 * 0.8 = 0.64 of the weight of a hypothetical A1 item.
RELIABILITY_WEIGHTS = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "F": 0.1}
CREDIBILITY_WEIGHTS = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2, 6: 0.1}


_UNJUDGEABLE_WEIGHT = RELIABILITY_WEIGHTS["F"] * CREDIBILITY_WEIGHTS[6]


def admiralty_weight(rating: str) -> float:
    """Convert an Admiralty rating such as "B2" into a confidence weight in (0, 1].

    A rating is only honoured if both of its components parse. If either is
    malformed the whole rating is treated as F6 ("cannot be judged"), because a
    malformed rating signals a data-quality problem in the pipeline and half of
    a corrupt field is not a safe basis for weighting evidence.
    """
    rating = (rating or "").strip().upper()
    if len(rating) < 2:
        return _UNJUDGEABLE_WEIGHT

    reliability = RELIABILITY_WEIGHTS.get(rating[0])
    try:
        credibility = CREDIBILITY_WEIGHTS.get(int(rating[1]))
    except ValueError:
        credibility = None

    if reliability is None or credibility is None:
        return _UNJUDGEABLE_WEIGHT
    return reliability * credibility


@dataclass(frozen=True)
class Hypothesis:
    """One candidate explanation under test."""

    key: str
    statement: str
    indicators: tuple[str, ...] = ()
    """Observables that would strengthen or weaken this hypothesis in future
    collection — Heuer's step 8, which turns a static judgement into a
    monitoring task."""


@dataclass(frozen=True)
class Evidence:
    """One item of evidence, with its source rating and per-hypothesis scores."""

    key: str
    statement: str
    admiralty_rating: str
    scores: dict[str, str]
    note: str = ""

    @property
    def weight(self) -> float:
        return admiralty_weight(self.admiralty_rating)

    def numeric_scores(self, hypothesis_keys: list[str]) -> list[int]:
        return [SCORE_VALUES.get(self.scores.get(k, "N"), 0) for k in hypothesis_keys]

    def diagnosticity(self, hypothesis_keys: list[str]) -> float:
        """Spread of this item's scores across the hypothesis set.

        Zero means the item cannot discriminate between the hypotheses and
        should be dropped from the matrix.
        """
        values = self.numeric_scores(hypothesis_keys)
        if len(values) < 2:
            return 0.0
        return pstdev(values)


@dataclass
class HypothesisResult:
    """Scored outcome for a single hypothesis."""

    hypothesis: Hypothesis
    inconsistency: float
    """Weighted sum of contradicting evidence. Lower is better; this is the
    figure hypotheses are ranked on."""
    consistency: float
    supporting: list[str] = field(default_factory=list)
    contradicting: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    """A complete ACH problem: the question, the hypotheses, and the evidence."""

    question: str
    hypotheses: list[Hypothesis]
    evidence: list[Evidence]
    analytic_note: str = ""

    @property
    def hypothesis_keys(self) -> list[str]:
        return [h.key for h in self.hypotheses]


def score_scenario(scenario: Scenario) -> list[HypothesisResult]:
    """Score every hypothesis, returned most likely first.

    Ranking is ascending by weighted inconsistency, per Heuer: the surviving
    hypothesis is the one the evidence has failed to refute.
    """
    keys = scenario.hypothesis_keys
    results: list[HypothesisResult] = []

    for hypothesis in scenario.hypotheses:
        inconsistency = 0.0
        consistency = 0.0
        supporting: list[str] = []
        contradicting: list[str] = []

        for item in scenario.evidence:
            if item.diagnosticity(keys) == 0:
                continue  # non-diagnostic: excluded from scoring (step 4)
            raw = SCORE_VALUES.get(item.scores.get(hypothesis.key, "N"), 0)
            weighted = abs(raw) * item.weight
            if raw < 0:
                inconsistency += weighted
                contradicting.append(item.key)
            elif raw > 0:
                consistency += weighted
                supporting.append(item.key)

        results.append(
            HypothesisResult(
                hypothesis=hypothesis,
                inconsistency=round(inconsistency, 3),
                consistency=round(consistency, 3),
                supporting=supporting,
                contradicting=contradicting,
            )
        )

    return sorted(results, key=lambda r: (r.inconsistency, -r.consistency))


def non_diagnostic_evidence(scenario: Scenario) -> list[Evidence]:
    """Evidence items that cannot discriminate between the hypotheses."""
    keys = scenario.hypothesis_keys
    return [e for e in scenario.evidence if e.diagnosticity(keys) == 0]


def diagnosticity_ranking(scenario: Scenario) -> list[tuple[Evidence, float]]:
    """Evidence ordered by discriminating power, most diagnostic first."""
    keys = scenario.hypothesis_keys
    scored = [(e, round(e.diagnosticity(keys), 3)) for e in scenario.evidence]
    return sorted(scored, key=lambda pair: pair[1], reverse=True)


def sensitivity_analysis(scenario: Scenario) -> list[dict]:
    """Test how load-bearing each evidence item is (Heuer's step 6).

    Each item is removed in turn and the scenario re-scored. If the leading
    hypothesis changes, the conclusion rests on that single item — which is
    exactly the dependency an analytical product should disclose, since the
    item might later be shown to be wrong or deliberately planted.
    """
    baseline = score_scenario(scenario)
    if not baseline:
        return []
    baseline_leader = baseline[0].hypothesis.key

    findings: list[dict] = []
    for item in scenario.evidence:
        reduced = Scenario(
            question=scenario.question,
            hypotheses=scenario.hypotheses,
            evidence=[e for e in scenario.evidence if e.key != item.key],
        )
        reduced_results = score_scenario(reduced)
        if not reduced_results:
            continue
        new_leader = reduced_results[0].hypothesis.key
        findings.append(
            {
                "evidence_key": item.key,
                "statement": item.statement,
                "admiralty_rating": item.admiralty_rating,
                "leader_without_item": new_leader,
                "changes_conclusion": new_leader != baseline_leader,
            }
        )
    return findings


def matrix_rows(scenario: Scenario) -> list[dict]:
    """Flatten the ACH matrix into rows suitable for tabular display or export."""
    keys = scenario.hypothesis_keys
    rows: list[dict] = []
    for item in scenario.evidence:
        row: dict = {
            "Evidence": item.key,
            "Statement": item.statement,
            "Admiralty": item.admiralty_rating,
            "Weight": round(item.weight, 2),
        }
        for key in keys:
            row[key] = item.scores.get(key, "N")
        row["Diagnosticity"] = round(item.diagnosticity(keys), 3)
        rows.append(row)
    return rows
