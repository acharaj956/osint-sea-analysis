"""Illustrative money-laundering typology heuristics.

These are intentionally simple, transparent heuristics that flag patterns
commonly associated with laundering of illicit cryptocurrency proceeds
(mixer exposure, layering, consolidation, round-value structuring). They are
demonstrative only — not a production typology classifier — and operate on
the synthetic demo transaction set.
"""
from __future__ import annotations


def _laundering_infrastructure(sanctioned: dict) -> set[str]:
    """Addresses in the reference set that represent mixing/laundering rails."""
    flagged: set[str] = set()
    for addr, info in sanctioned.items():
        blob = f"{info.get('name', '')} {info.get('notes', '')}".lower()
        if any(term in blob for term in ("mix", "tornado", "launder", "tumbl")):
            flagged.add(addr)
    return flagged


def detect_typologies(
    center_address: str,
    transactions: list[dict],
    sanctioned: dict,
) -> list[str]:
    """Return a list of heuristic typology indicators for the traced wallet."""
    if not transactions:
        return []

    mixers = _laundering_infrastructure(sanctioned)
    outgoing = [t.get("to_address", "") for t in transactions if t.get("from_address") == center_address]
    incoming = [t.get("from_address", "") for t in transactions if t.get("to_address") == center_address]
    neighbours = set(outgoing) | set(incoming)

    indicators: list[str] = []

    if neighbours & mixers:
        indicators.append("mixer / tumbler exposure")
    if neighbours & set(sanctioned):
        indicators.append("direct sanctioned-entity counterparty")
    if len(set(outgoing)) >= 3:
        indicators.append("fan-out / layering")
    if len(set(incoming)) >= 3:
        indicators.append("fan-in / consolidation")

    round_transfers = [
        t for t in transactions
        if float(t.get("value", 0)) >= 1000 and float(t.get("value", 0)) % 1000 == 0
    ]
    if round_transfers:
        indicators.append("round-value structuring")

    return indicators
