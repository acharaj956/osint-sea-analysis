# Methodology

This document describes the open-source-investigation tradecraft applied in this
demonstration project. It doubles as a short training-style reference for the
analytical workflow.

> This is an independent demonstration project. It is **not affiliated with,
> endorsed by, or representing UNODC or the United Nations**. All data is
> synthetic / illustrative and must not be cited as fact.

## 1. Scope and data status

The project covers two analytical workflows:

1. **Cryptocurrency tracing** — following on-chain value flows and cross-referencing
   counterparties against a sanctions reference set.
2. **Geospatial crime analysis** — mapping and trend analysis of (synthetic) drug
   seizure events across Southeast Asia.

All datasets are **synthetic or illustrative**:

- The seizure dataset (`data/sea_drug_seizures.csv`) is generated/curated to
  resemble publicly reported UNODC trafficking *trends*. No record corresponds to
  a specific real seizure.
- The sanctions reference set (`src/blockchain/sanctions.py`) contains a small
  number of genuine, widely-published OFAC designations (the Tornado Cash
  contracts, flagged `verified: True`) alongside illustrative entries that pair
  real threat-actor *names* with placeholder addresses (`verified: False`).

This separation is deliberate: an OSINT product is only as credible as its
weakest sourcing claim, so synthetic material is never presented as a real,
sourced report.

## 2. Source evaluation — the Admiralty Code

Each seizure record is rated using the Admiralty (NATO) System, a standard
intelligence approach that scores two independent dimensions:

| Source reliability | | Information credibility | |
|---|---|---|---|
| A | Completely reliable | 1 | Confirmed by other sources |
| B | Usually reliable | 2 | Probably true |
| C | Fairly reliable | 3 | Possibly true |
| D | Not usually reliable | 4 | Doubtful |
| E | Unreliable | 5 | Improbable |
| F | Cannot be judged | 6 | Cannot be judged |

In this project the rating is derived (in `data/build_dataset.py`) from the
notional reporting channel — e.g. UN-agency or law-enforcement reporting maps to
`B2` (usually reliable / probably true), open media maps to `D3` (not usually
reliable / possibly true). The combined rating (e.g. `B2`) is shown per record in
the Raw Data view.

## 3. Data integrity and chain of custody

Following the preservation principles of the **Berkeley Protocol on Digital Open
Source Investigations** (UN Human Rights, 2022), the application computes
**SHA-256 digests** (`src/integrity.py`) over the artifacts its conclusions rest
on, and maintains an **evidence register** around them (`src/evidence.py`).

The register is not illustrative. Each registered artifact has a baseline hash
recorded in a committed manifest (`data/evidence_manifest.json`); on every run
the file on disk is re-hashed and compared, and the Evidence Register page
reports one of four states:

| Status | Meaning |
|---|---|
| `VERIFIED` | Current hash matches the recorded baseline |
| `ALTERED` | File has changed since the baseline was recorded |
| `MISSING` | Registered artifact is absent |
| `UNREGISTERED` | File exists but has no baseline, so integrity is *unknown* |

The distinction between `UNREGISTERED` and `VERIFIED` is deliberate: an item that
has never been baselined is reported as unknown rather than assumed sound.

Each exhibit carries its origin, acquisition timestamp (UTC), size, handling
caveat, and a custody log covering the three events that can actually be
evidenced — acquisition, baseline registration, and the current verification.
After any intended change to a registered artifact the baseline is re-recorded
with `python -m src.evidence`; the manifest is deliberately not regenerated
automatically, since a custody record that silently re-baselines itself would
detect nothing.

## 3a. Event chronology

A chronology is the backbone product of most investigations, so
`src/analysis/chronology.py` renders the dataset as one: events in time order,
each entry keeping its own reference number, Admiralty rating and provenance, so
sequence and sourcing stay visible together. Alongside the table are a timeline
view (events by country over time, sized by estimated value) and a monthly tempo
chart with a cumulative overlay, which exposes clustering and acceleration that
an annual total conceals.

**Temporal gaps** are detected and reported rather than smoothed over. A period
with no recorded event may be a genuine lull, a collection blind spot, or a
reporting interruption; those three are not distinguishable from this dataset
alone, so the gap is presented as an open question instead of being read as
absence of activity.

## 4. Cryptocurrency tracing

- **Collection:** in live mode, address summaries and transactions are pulled from
  public block explorers (Blockchair for Bitcoin, TronGrid for Tron/USDT-TRC20).
  Demo mode uses pre-cached synthetic transactions.
- **Graph construction:** transactions are aggregated into a directed graph
  (`src/blockchain/graph.py`); edges are weighted by transferred value and
  annotated with transaction counts and timestamps.
- **Sanctions cross-referencing:** every node is checked against the reference set;
  the queried wallet's risk is scored by direct designation or by linkage to
  sanctioned counterparties.
- **Typology heuristics:** `src/blockchain/typologies.py` flags simple, transparent
  patterns associated with laundering — mixer/tumbler exposure, fan-out (layering),
  fan-in (consolidation), and round-value structuring. These are demonstrative
  indicators, not a production classifier, and are clearly labeled as such in the UI.

## 5. Geospatial and trend analysis

- Seizure events are plotted with Folium (markers sized by quantity, optional
  value-weighted heatmap).
- Descriptive statistics include totals by country, drug type, and year, plus a
  simple **year-over-year change** in estimated value as a trend indicator.

## 5a. Hypothesis testing — Analysis of Competing Hypotheses

`src/analysis/ach.py` implements **ACH**, set out by Richards J. Heuer Jr. in
*Psychology of Intelligence Analysis* (CIA Center for the Study of Intelligence,
1999). ACH exists to counter confirmation bias: instead of assembling support for
the first plausible explanation, the analyst enumerates every credible hypothesis
and works to refute them.

Three implementation choices carry the method's substance:

1. **Ranking is by inconsistency, not consistency.** A hypothesis is judged by
   the weight of evidence that contradicts it, and the least-contradicted
   hypothesis ranks first. Evidence *consistent* with a hypothesis is weak
   support, because it is usually consistent with rival hypotheses too. A low
   inconsistency score is not proof — it means the evidence has so far failed to
   refute that explanation.

2. **Evidence is judged on diagnosticity.** An item consistent with every
   hypothesis cannot discriminate between them, however reliable its source.
   Diagnosticity is measured as the spread of an item's scores across the
   hypothesis set; items with zero spread are excluded from scoring (Heuer's
   step 4) and reported as excluded.

3. **Source ratings drive the weighting.** Each item's Admiralty rating is
   converted into a confidence weight (reliability × credibility), so a `D3`
   item moves the ranking roughly a quarter as much as a `B2` one. If either
   half of a rating is malformed the whole rating is treated as `F6`, since half
   of a corrupt field is not a safe basis for weighting evidence.

**Sensitivity analysis** (Heuer's step 6) removes each item in turn and
re-ranks. Where removing one item changes the leading hypothesis, that
dependency is stated in the interface and in the generated report — a conclusion
resting on a single report is a disclosed risk, since that report may later prove
wrong or have been deliberately planted.

Each hypothesis also carries **monitoring indicators** (step 8): observables
that would strengthen or weaken it, which converts a static judgement into a
collection requirement.

The worked scenario in `src/analysis/scenarios.py` is illustrative, and is built
so the technique does real work: the observation that prompts the question turns
out to be non-diagnostic, the top two hypotheses finish close together, and the
leading hypothesis depends on a single item. A "boring" alternative — that the
apparent rise is a recording artifact — is carried as a hypothesis alongside the
enforcement-success reading, so neither is adopted by default.

## 5b. Analytical reporting

`src/reporting.py` generates a written product in the structure an assessment is
normally expected to follow: handling caveat, key judgement first, then scope and
method, figures, hypothesis ranking, gaps, and integrity.

Two elements are derived rather than written by hand, so the report cannot claim
more than its sourcing supports:

- **Confidence** is computed from the share of records carrying strong Admiralty
  ratings, and is capped at "moderate" for this project regardless of that share,
  because the dataset is synthetic and nothing has been independently
  corroborated.
- **Gaps** are assembled from the data: the proportion of weakly sourced records,
  countries with thin coverage, the longest interval without a recorded event,
  evidence excluded as non-diagnostic, and any single item the leading hypothesis
  depends on.

## 6. Ethical and legal considerations

- Only publicly available on-chain data is queried in live mode.
- No personal data, credentials, or non-public material is collected or stored.
- The UN name and emblem are not used to imply official status.
- Synthetic and illustrative data is labeled as such throughout, so the product
  cannot be mistaken for sourced intelligence.

## 7. References

- UN Human Rights (OHCHR), *Berkeley Protocol on Digital Open Source
  Investigations*, 2022.
- Heuer, Richards J. Jr., *Psychology of Intelligence Analysis*, CIA Center for
  the Study of Intelligence, 1999 — Analysis of Competing Hypotheses.
- Heuer, Richards J. Jr. and Pherson, Randolph H., *Structured Analytic
  Techniques for Intelligence Analysis*.
- U.S. Department of the Treasury, Office of Foreign Assets Control (OFAC),
  *Specially Designated Nationals and Blocked Persons (SDN) List*.
- UNODC, *Synthetic Drugs in East and Southeast Asia* (annual trend reporting).
- NATO Standardization — Admiralty/source-reliability rating system.
