# OSINT Southeast Asia Crime Analysis Dashboard

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://osint-sea-analysis.streamlit.app)

An open-source intelligence (OSINT) analytical tool that demonstrates monitoring
and analysis of transnational organized crime in Southeast Asia, with a focus on
cryptocurrency-enabled financial flows and regional drug trafficking patterns.

**▶ Live demo:** https://osint-sea-analysis.streamlit.app

> ⚠️ **Important — read first**
>
> - **Independent project.** This is a personal portfolio/demonstration project.
>   It is **not affiliated with, endorsed by, or representing UNODC or the United
>   Nations**. The UN name and emblem are not used to imply any official status.
> - **Data is synthetic / illustrative.** The drug-seizure records are
>   **synthetic** — modeled on publicly reported UNODC *trends*, but no row is a
>   real, citable incident. The sanctions reference set is **illustrative**: only
>   a few entries reflect genuine OFAC designations (clearly flagged), and the
>   rest pair real threat-actor *names* with placeholder addresses for
>   demonstration. **Nothing here should be cited as fact.**
> - No classified, restricted, or non-public information is included.

## Features

### Crypto Wallet Tracer
- Trace Bitcoin and Tron (USDT-TRC20) wallet transactions
- Interactive network graph visualization of transaction flows
- Cross-referencing against an illustrative OFAC sanctions reference set
- Heuristic laundering-typology indicators (mixer exposure, layering,
  consolidation, round-value structuring)
- Risk scoring based on proximity to sanctioned entities
- Demo wallets with pre-cached synthetic data for immediate exploration

### Crime Incident Map
- Interactive map of (synthetic) drug seizure events across 8 Southeast Asian countries
- Illustrative dataset spanning 2019–2024, modeled on UNODC-reported trends
- Filter by country, year, and drug type
- Heatmap layer for identifying trafficking hotspots
- Analytical charts: trend over time (with year-over-year change), distribution
  by country and drug type
- Per-record **Admiralty Code** source-reliability / information-credibility ratings
- **SHA-256 dataset integrity** digest displayed in the data view
- Exportable filtered datasets

## Tradecraft & methodology

This tool is built around standard open-source-investigation practice, following
the [Berkeley Protocol on Digital Open Source Investigations](https://www.ohchr.org/en/publications/policy-and-methodological-publications/berkeley-protocol-digital-open-source)
(UN Human Rights, 2022). See [METHODOLOGY.md](METHODOLOGY.md) for the full write-up.

Key principles applied:
- **Source evaluation** — records are rated on the Admiralty/NATO scale
  (source reliability A–F, information credibility 1–6)
- **Data integrity** — a SHA-256 digest is computed over the source dataset to
  demonstrate tamper-evidence
- **Honest provenance** — synthetic data is labeled as synthetic everywhere; no
  fabricated record is presented as a real, sourced report
- **Ethical collection** — live mode queries only publicly available on-chain data
- **Reproducibility** — the dataset is produced by a documented build step
  (`data/build_dataset.py`)

## Data sources

| Source | Type | Use in this project |
|--------|------|---------------------|
| [Blockchair](https://blockchair.com) | Bitcoin blockchain data | Live mode (free API) |
| [TronGrid](https://www.trongrid.io) | Tron / USDT-TRC20 data | Live mode (free API) |
| [OFAC SDN List](https://sanctionssearch.ofac.treas.gov/) | Sanctioned crypto addresses | Basis for an *illustrative* reference set — verify against the official list for any real use |
| [UNODC Data Portal](https://dataunodc.un.org/) | Drug seizure statistics | Trend basis for the *synthetic* seizure dataset (no row is a real record) |

## Quick Start

```bash
# Clone the repository (replace with your fork URL)
git clone https://github.com/acharaj956/osint-sea-analysis.git
cd osint-sea-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) regenerate the illustrative dataset with provenance metadata
python data/build_dataset.py

# Run the dashboard
streamlit run app.py
```

The app runs in **demo mode** by default, using pre-cached synthetic data. No API keys required.

### Optional: Enable live API queries

```bash
cp .env.example .env
# Edit .env with your API keys (all free tier)
```

## Tech Stack

- **Python 3.10+**
- **Streamlit** — Interactive dashboard framework
- **NetworkX + Pyvis** — Transaction network graph analysis and visualization
- **Folium** — Geospatial mapping with interactive markers and heatmaps
- **Pandas** — Data processing and analysis
- **Plotly** — Statistical charts and analytics
- **Requests** — API client for blockchain data

## Project Structure

```
osint-sea-analysis/
├── app.py                     # Main Streamlit application
├── requirements.txt           # Pinned dependencies
├── .env.example               # Environment variable template
├── METHODOLOGY.md             # Tradecraft, source rating, integrity notes
├── .streamlit/config.toml     # Streamlit theme configuration
├── data/
│   ├── sea_drug_seizures.csv  # Synthetic, UNODC-trend-based seizure dataset
│   └── build_dataset.py       # Reproducible dataset build / enrichment step
└── src/
    ├── config.py              # Application configuration
    ├── styles.py              # UI styling and components
    ├── integrity.py           # SHA-256 data-integrity helpers
    ├── blockchain/
    │   ├── client.py          # Blockchair & TronGrid API clients
    │   ├── graph.py           # Network graph construction & rendering
    │   ├── sanctions.py       # Illustrative OFAC sanctions reference set
    │   ├── typologies.py      # Heuristic laundering-typology indicators
    │   └── demo_data.py       # Pre-cached synthetic transaction data
    └── crime_map/
        ├── loader.py          # Data loading, filtering, statistics
        └── builder.py         # Folium map construction
```

## Data dictionary (`data/sea_drug_seizures.csv`)

| Column | Description |
|--------|-------------|
| `id` | Record identifier |
| `date` | Seizure date (synthetic) |
| `country`, `province`, `city` | Location |
| `lat`, `lon` | Coordinates |
| `drug_type` | Substance category |
| `quantity`, `unit` | Amount seized |
| `estimated_value_usd` | Illustrative estimated street value (USD) |
| `seizure_context` | Scenario context (e.g. border checkpoint, lab dismantlement) |
| `provenance` | Always "Synthetic (illustrative)" |
| `source_reliability` | Admiralty source-reliability rating (A–F) |
| `info_credibility` | Admiralty information-credibility score (1–6) |
| `admiralty_rating` | Combined rating (e.g. "B2") |

## Limitations

- Blockchain analysis is limited to 1-hop transaction tracing (direct counterparties only)
- The seizure dataset is **synthetic**; it illustrates patterns, not real events
- Laundering-typology indicators are simple heuristics, not a production classifier
- The sanctions reference set is illustrative and static; production use requires
  loading and verifying against the live OFAC SDN list
- Demo mode uses synthetic transaction data

## Roadmap (not yet implemented)

- Public news / event monitoring (e.g. GDELT) for corroboration
- Image/video metadata (EXIF) extraction and geolocation
- Multi-hop tracing and automated typology classification

## License

MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is built for analytical demonstration and learning purposes only. It is
not affiliated with any organization. The seizure dataset is synthetic and modeled
on publicly reported trends; blockchain analysis in live mode uses only publicly
available on-chain data. No classified, restricted, or non-public information is
included, and nothing in this project should be cited as fact.
