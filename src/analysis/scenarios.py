"""Worked ACH scenario.

The scenario below is ILLUSTRATIVE. The hypotheses are realistic analytic
alternatives and the evidence statements are written in the register a real
assessment would use, but the underlying observations are synthetic and are not
sourced reporting. Nothing here should be cited as fact.

The scenario is deliberately built so that the technique does real work:

* One evidence item is consistent with every hypothesis, so it is
  non-diagnostic and is dropped from scoring.
* The two leading hypotheses finish close together, because the evidence does
  not support a confident single answer.
* The leading hypothesis depends on one item. Sensitivity analysis surfaces
  that dependency instead of hiding it behind a headline judgement.
"""
from __future__ import annotations

from src.analysis.ach import Evidence, Hypothesis, Scenario

MEKONG_SURGE = Scenario(
    question=(
        "What best explains the rise in methamphetamine seizure events recorded "
        "in the Mekong border corridor between 2022 and 2024?"
    ),
    analytic_note=(
        "A rise in seizures is an ambiguous indicator: it can reflect more "
        "trafficking, the same trafficking detected more often, the same "
        "trafficking moving to a different route, or nothing more than a change "
        "in how events are recorded. All four readings are carried as hypotheses "
        "so that the enforcement-success reading is not adopted by default."
    ),
    hypotheses=[
        Hypothesis(
            key="H1",
            statement=(
                "Production increase — output from clandestine laboratories in the "
                "source region has risen, pushing greater volume into the corridor."
            ),
            indicators=(
                "Continued fall or stagnation in retail price per unit",
                "Further growth in precursor chemical seizures upstream",
                "Rising seizure volumes on routes other than the Mekong corridor",
            ),
        ),
        Hypothesis(
            key="H2",
            statement=(
                "Route displacement — total flow is broadly unchanged but has "
                "shifted from maritime routes onto overland Mekong routes."
            ),
            indicators=(
                "Sustained decline in maritime seizures with overland growth",
                "Reporting of new overland consolidation points",
                "Stable aggregate regional seizure volume across all routes",
            ),
        ),
        Hypothesis(
            key="H3",
            statement=(
                "Interdiction improvement — flow is broadly unchanged and more is "
                "being detected because enforcement capability has improved."
            ),
            indicators=(
                "Growth in checkpoint numbers, staffing or detection equipment",
                "Rising arrest and prosecution counts alongside seizures",
                "Rising retail price consistent with supply pressure",
            ),
        ),
        Hypothesis(
            key="H4",
            statement=(
                "Reporting artifact — the apparent rise reflects changed recording "
                "or reporting practice rather than any change in the flow itself."
            ),
            indicators=(
                "Discontinuity in a single reporting agency's series",
                "Divergence between agency-reported and independently observed counts",
                "No corresponding movement in price, purity or arrest data",
            ),
        ),
    ],
    evidence=[
        Evidence(
            key="E1",
            statement=(
                "Recorded seizure events in Mekong border provinces rose "
                "approximately 62 per cent between 2022 and 2024."
            ),
            admiralty_rating="B2",
            scores={"H1": "C", "H2": "C", "H3": "C", "H4": "C"},
            note=(
                "This is the observation that prompted the question. It is "
                "consistent with every hypothesis and therefore carries no "
                "discriminating value — retained in the matrix to show why it is "
                "excluded from scoring."
            ),
        ),
        Evidence(
            key="E2",
            statement=(
                "Retail price per methamphetamine tablet in destination markets "
                "fell by roughly 30 per cent over the same period."
            ),
            admiralty_rating="B2",
            scores={"H1": "CC", "H2": "I", "H3": "II", "H4": "II"},
            note=(
                "The most diagnostic item. Sustained interdiction pressure on an "
                "unchanged supply should raise prices, not lower them, and a pure "
                "recording change should not move prices at all."
            ),
        ),
        Evidence(
            key="E3",
            statement=(
                "Precursor chemical seizures in neighbouring jurisdictions rose "
                "sharply across the same period."
            ),
            admiralty_rating="B2",
            scores={"H1": "CC", "H2": "N", "H3": "C", "H4": "N"},
            note=(
                "Ambiguous in direction: larger precursor flows point to expanded "
                "production, but improved enforcement would also find more of them."
            ),
        ),
        Evidence(
            key="E4",
            statement=(
                "Permanent checkpoint numbers and staffing levels in the corridor "
                "are unchanged since 2021."
            ),
            admiralty_rating="C2",
            scores={"H1": "N", "H2": "N", "H3": "II", "H4": "N"},
        ),
        Evidence(
            key="E5",
            statement=(
                "Seizures on alternative maritime routes declined over the same "
                "period."
            ),
            admiralty_rating="C2",
            scores={"H1": "I", "H2": "CC", "H3": "N", "H4": "N"},
            note=(
                "A genuine production increase would be expected to lift volumes "
                "on several routes at once, not only on one."
            ),
        ),
        Evidence(
            key="E6",
            statement=(
                "One national agency adopted a revised seizure-reporting template "
                "in 2023 that lowered the minimum recording threshold."
            ),
            admiralty_rating="D3",
            scores={"H1": "N", "H2": "N", "H3": "N", "H4": "CC"},
            note=(
                "The only item supporting the reporting-artifact reading, and it "
                "rests on a weakly rated source — hence a low weight."
            ),
        ),
        Evidence(
            key="E7",
            statement=(
                "Laboratory dismantlements in the source region rose from about "
                "one to about four per year."
            ),
            admiralty_rating="B2",
            scores={"H1": "C", "H2": "N", "H3": "C", "H4": "N"},
            note=(
                "Consistent with both a larger production base and with more "
                "effective enforcement, so it discriminates only weakly."
            ),
        ),
        Evidence(
            key="E8",
            statement=(
                "Average purity of seized crystal methamphetamine remained stable "
                "or increased."
            ),
            admiralty_rating="B2",
            scores={"H1": "C", "H2": "N", "H3": "N", "H4": "N"},
            note="Stable purity alongside rising volume argues against supply disruption.",
        ),
        Evidence(
            key="E9",
            statement=(
                "Arrests of trafficking-group members in the corridor did not "
                "increase over the period."
            ),
            admiralty_rating="C2",
            scores={"H1": "N", "H2": "N", "H3": "I", "H4": "N"},
            note=(
                "Improved interdiction capability would normally lift arrest "
                "counts alongside seizure counts."
            ),
        ),
    ],
)

SCENARIOS = {"Mekong corridor seizure rise (2022-2024)": MEKONG_SURGE}
