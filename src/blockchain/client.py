from __future__ import annotations

from datetime import datetime, timezone

import requests
import streamlit as st

from src.blockchain.demo_data import DEMO_SUMMARIES, DEMO_TRANSACTIONS
from src.config import API_TIMEOUT, BLOCKCHAIR_BASE, TRONGRID_BASE

TRON_USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


class BlockchainClient:

    def get_address_summary(self, address: str, chain: str) -> dict:
        if address in DEMO_SUMMARIES:
            return DEMO_SUMMARIES[address]

        if chain == "bitcoin":
            return self._btc_summary(address)
        if chain == "tron":
            return self._tron_summary(address)

        return self._empty_summary(address, chain)

    def get_transactions(
        self, address: str, chain: str, limit: int = 20
    ) -> list[dict]:
        if address in DEMO_TRANSACTIONS:
            return DEMO_TRANSACTIONS[address][:limit]

        if chain == "bitcoin":
            return self._btc_transactions(address, limit)
        if chain == "tron":
            return self._tron_transactions(address, limit)

        return []

    def _btc_summary(self, address: str) -> dict:
        url = f"{BLOCKCHAIR_BASE}/bitcoin/dashboards/address/{address}?limit=20"
        data = _cached_get(url)
        if data is None:
            return self._empty_summary(address, "bitcoin")

        try:
            addr_data = data["data"][address]["address"]
            return {
                "address": address,
                "balance": addr_data.get("balance", 0) / 1e8,
                "total_received": addr_data.get("received", 0) / 1e8,
                "total_sent": addr_data.get("spent", 0) / 1e8,
                "tx_count": addr_data.get("transaction_count", 0),
                "chain": "bitcoin",
            }
        except (KeyError, TypeError):
            st.warning(f"Unexpected response format from Blockchair for {address}")
            return self._empty_summary(address, "bitcoin")

    def _btc_transactions(self, address: str, limit: int) -> list[dict]:
        url = f"{BLOCKCHAIR_BASE}/bitcoin/dashboards/address/{address}?limit={limit}"
        data = _cached_get(url)
        if data is None:
            return []

        try:
            raw_txs = data["data"][address].get("transactions", [])
        except (KeyError, TypeError):
            return []

        txs: list[dict] = []
        for tx_hash in raw_txs[:limit]:
            txs.append(
                {
                    "tx_hash": tx_hash,
                    "from_address": address,
                    "to_address": "unknown",
                    "value": 0.0,
                    "timestamp": "",
                    "chain": "bitcoin",
                }
            )
        return txs

    def _tron_summary(self, address: str) -> dict:
        url = f"{TRONGRID_BASE}/v1/accounts/{address}"
        data = _cached_get(url)
        if data is None:
            return self._empty_summary(address, "tron")

        try:
            account = data["data"][0] if data.get("data") else {}
            balance_sun = account.get("balance", 0)
            return {
                "address": address,
                "balance": balance_sun / 1e6,
                "total_received": 0.0,
                "total_sent": 0.0,
                "tx_count": 0,
                "chain": "tron",
            }
        except (KeyError, TypeError, IndexError):
            st.warning(f"Unexpected response format from TronGrid for {address}")
            return self._empty_summary(address, "tron")

    def _tron_transactions(self, address: str, limit: int) -> list[dict]:
        url = (
            f"{TRONGRID_BASE}/v1/accounts/{address}"
            f"/transactions/trc20?limit={limit}"
            f"&contract_address={TRON_USDT_CONTRACT}"
        )
        data = _cached_get(url)
        if data is None:
            return []

        txs: list[dict] = []
        for item in (data.get("data") or [])[:limit]:
            try:
                ts_ms = int(item.get("block_timestamp", 0))
                ts_str = (
                    datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                    if ts_ms
                    else ""
                )
                raw_value = item.get("value", "0")
                value = int(raw_value) / 1e6 if raw_value else 0.0

                txs.append(
                    {
                        "tx_hash": item.get("transaction_id", ""),
                        "from_address": item.get("from", ""),
                        "to_address": item.get("to", ""),
                        "value": value,
                        "timestamp": ts_str,
                        "chain": "tron",
                    }
                )
            except (ValueError, TypeError):
                continue
        return txs

    @staticmethod
    def _empty_summary(address: str, chain: str) -> dict:
        return {
            "address": address,
            "balance": 0.0,
            "total_received": 0.0,
            "total_sent": 0.0,
            "tx_count": 0,
            "chain": chain,
        }


@st.cache_data(ttl=300)
def _cached_get(url: str) -> dict | None:
    try:
        resp = requests.get(url, timeout=API_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        st.warning(f"API request failed: {exc}")
        return None
    except ValueError:
        st.warning(f"Invalid JSON response from {url}")
        return None
