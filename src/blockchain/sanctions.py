"""Reference set of sanctioned cryptocurrency addresses.

IMPORTANT — read before reuse:

This is a small, ILLUSTRATIVE reference set for demonstrating sanctions
cross-referencing. It is NOT an authoritative or current sanctions source.

- Entries marked ``"verified": True`` reflect genuine OFAC designations whose
  addresses are widely published (the Tornado Cash smart-contract addresses
  sanctioned on 8 Aug 2022).
- Entries marked ``"verified": False`` use real, public threat-actor *names*
  (e.g. Lazarus Group, Hydra) attached to ILLUSTRATIVE addresses for
  demonstration. The specific address-to-event mappings have not been
  individually verified and must not be treated as fact.

For any real-world use, load the current OFAC Specially Designated Nationals
(SDN) list directly from https://sanctionssearch.ofac.treas.gov/ and verify
every address against the official source.
"""
from __future__ import annotations


OFAC_ADDRESSES: dict[str, dict] = {
    "12hdv5bGKmjMXS1CEvhRiXqQnWRnGrCZZN": {
        "name": "Lazarus Group (illustrative)",
        "program": "DPRK / CYBER2",
        "chain": "bitcoin",
        "date_listed": "2022-04-14",
        "verified": False,
        "notes": "Illustrative DPRK-attributed wallet (Ronin Bridge theme). "
                 "Note: OFAC's actual Ronin designation was an Ethereum address.",
    },
    "1Kuf2Rd8mDyAViwBozGTNYnvWL8uRFSGGa": {
        "name": "Lazarus Group (illustrative)",
        "program": "DPRK / CYBER2",
        "chain": "bitcoin",
        "date_listed": "2022-04-14",
        "verified": False,
        "notes": "Illustrative secondary wallet used to demonstrate fund layering.",
    },
    "3EHLuyEh7x7GFSqx8WNQE1ayLNBD7vEkHo": {
        "name": "Lazarus Group (illustrative)",
        "program": "DPRK",
        "chain": "bitcoin",
        "date_listed": "2023-05-23",
        "verified": False,
        "notes": "Illustrative wallet themed on Harmony Horizon Bridge layering.",
    },
    "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh": {
        "name": "Illustrative mixing service (synthetic)",
        "program": "CYBER2",
        "chain": "bitcoin",
        "date_listed": "2021-02-02",
        "verified": False,
        "notes": "Illustrative placeholder address used only for demo graphs. "
                 "Not a real designation.",
    },
    "0x8589427373D6D84E98730D7795D8f6f8731FDA16": {
        "name": "Tornado Cash",
        "program": "CYBER2",
        "chain": "ethereum",
        "date_listed": "2022-08-08",
        "verified": True,
        "notes": "Genuine OFAC SDN designation (8 Aug 2022): Tornado Cash router.",
    },
    "0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b": {
        "name": "Tornado Cash",
        "program": "CYBER2",
        "chain": "ethereum",
        "date_listed": "2022-08-08",
        "verified": True,
        "notes": "Genuine OFAC SDN designation (8 Aug 2022): Tornado Cash 100 ETH pool.",
    },
    "0x722122dF12D4e14e13Ac3b6895a86e84145b6967": {
        "name": "Tornado Cash",
        "program": "CYBER2",
        "chain": "ethereum",
        "date_listed": "2022-08-08",
        "verified": True,
        "notes": "Genuine OFAC SDN designation (8 Aug 2022): Tornado Cash proxy contract.",
    },
    "TNVaKWQzau4pirY1JYfVJHMJxoJ4MTYPKM": {
        "name": "Lazarus Group (Tron, illustrative)",
        "program": "DPRK / CYBER2",
        "chain": "tron",
        "date_listed": "2023-09-07",
        "verified": False,
        "notes": "Illustrative Tron USDT wallet themed on casino-hack laundering.",
    },
    "TKgbfEPajghroMY2PaaYjnDnENads82rKo": {
        "name": "Lazarus Group (Tron, illustrative)",
        "program": "DPRK / CYBER2",
        "chain": "tron",
        "date_listed": "2023-04-24",
        "verified": False,
        "notes": "Illustrative Tron wallet themed on cross-bridge laundering chain.",
    },
    "149w62rY42aZBox8fGcmqNsXUzSStKeq8C": {
        "name": "Hydra Market (illustrative)",
        "program": "RUSSIA-EO14024",
        "chain": "bitcoin",
        "date_listed": "2022-04-05",
        "verified": False,
        "notes": "Illustrative darknet-market deposit wallet (Hydra/Garantex theme).",
    },
}


def is_sanctioned(address: str) -> tuple[bool, dict | None]:
    entry = OFAC_ADDRESSES.get(address)
    if entry is not None:
        return True, entry
    return False, None


def get_demo_wallets() -> list[dict[str, str]]:
    return [
        {
            "address": "12hdv5bGKmjMXS1CEvhRiXqQnWRnGrCZZN",
            "chain": "bitcoin",
            "label": "Lazarus Group — Ronin theme (BTC, illustrative)",
            "description": "Illustrative DPRK-attributed wallet for demonstrating sanctions tracing",
        },
        {
            "address": "149w62rY42aZBox8fGcmqNsXUzSStKeq8C",
            "chain": "bitcoin",
            "label": "Hydra Market (BTC, illustrative)",
            "description": "Illustrative darknet-market deposit wallet",
        },
        {
            "address": "TNVaKWQzau4pirY1JYfVJHMJxoJ4MTYPKM",
            "chain": "tron",
            "label": "Lazarus Group — Tron (USDT-TRC20, illustrative)",
            "description": "Illustrative Tron USDT wallet themed on casino-hack laundering",
        },
    ]
