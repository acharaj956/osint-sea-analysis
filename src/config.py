from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

BLOCKCHAIR_BASE = "https://api.blockchair.com"
TRONGRID_BASE = "https://api.trongrid.io"

BLOCKCHAIR_API_KEY = os.getenv("BLOCKCHAIR_API_KEY", "")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "")

SUPPORTED_CHAINS = {
    "bitcoin": "Bitcoin (BTC)",
    "tron": "Tron (USDT-TRC20)",
}

UNODC_BLUE = "#009edb"
UNODC_DARK = "#1a1f2e"
ACCENT_RED = "#e74c3c"
ACCENT_ORANGE = "#f39c12"
ACCENT_GREEN = "#27ae60"
NEUTRAL_GRAY = "#95a5a6"

SEA_CENTER = (12.5, 106.0)
SEA_ZOOM = 5

API_TIMEOUT = 15
API_MAX_RETRIES = 2

DRUG_COLORS = {
    "Methamphetamine (tablets)": "#e74c3c",
    "Crystal Methamphetamine": "#c0392b",
    "Heroin": "#8e44ad",
    "Ketamine": "#2980b9",
    "Cannabis": "#27ae60",
    "Cocaine": "#f39c12",
    "MDMA/Ecstasy": "#e67e22",
    "Fentanyl": "#1abc9c",
}

COUNTRY_ISO = {
    "Thailand": "THA",
    "Myanmar": "MMR",
    "Laos": "LAO",
    "Cambodia": "KHM",
    "Vietnam": "VNM",
    "Philippines": "PHL",
    "Malaysia": "MYS",
    "Indonesia": "IDN",
}
