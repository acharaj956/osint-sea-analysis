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

## 3. Data integrity and preservation

Following the preservation principles of the **Berkeley Protocol on Digital Open
Source Investigations** (UN Human Rights, 2022), the application computes a
**SHA-256 digest** over the source dataset (`src/integrity.py`) and displays it in
the data view. This demonstrates tamper-evidence: any change to the underlying
data changes the digest. In a production workflow the same approach would be
applied at the point of collection to every acquired artifact, alongside capture
of provenance metadata (URL, capture time, collector, hash).

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

## 6. Ethical and legal considerations

- Only publicly available on-chain data is queried in live mode.
- No personal data, credentials, or non-public material is collected or stored.
- The UN name and emblem are not used to imply official status.
- Synthetic and illustrative data is labeled as such throughout, so the product
  cannot be mistaken for sourced intelligence.

## 7. References

- UN Human Rights (OHCHR), *Berkeley Protocol on Digital Open Source
  Investigations*, 2022.
- U.S. Department of the Treasury, Office of Foreign Assets Control (OFAC),
  *Specially Designated Nationals and Blocked Persons (SDN) List*.
- UNODC, *Synthetic Drugs in East and Southeast Asia* (annual trend reporting).
- NATO Standardization — Admiralty/source-reliability rating system.
