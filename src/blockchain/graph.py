from __future__ import annotations

import tempfile
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from src.blockchain.sanctions import OFAC_ADDRESSES

COLOR_CENTER = "#009edb"
COLOR_SANCTIONED = "#e74c3c"
COLOR_REGULAR = "#95a5a6"
COLOR_BG = "#0e1117"

SIZE_CENTER = 40
SIZE_SANCTIONED = 30
SIZE_REGULAR = 20

EDGE_WIDTH_MIN = 1
EDGE_WIDTH_MAX = 8


def _truncate_address(addr: str) -> str:
    if len(addr) <= 12:
        return addr
    return f"{addr[:6]}...{addr[-4:]}"


def build_transaction_graph(
    center_address: str,
    transactions: list[dict],
    sanctioned_set: set[str],
    chain: str,
) -> nx.DiGraph:
    g = nx.DiGraph()

    g.add_node(
        center_address,
        is_center=True,
        is_sanctioned=center_address in sanctioned_set,
        label=_truncate_address(center_address),
        chain=chain,
    )

    edge_agg: dict[tuple[str, str], dict] = {}

    for tx in transactions:
        src = tx.get("from_address", "")
        dst = tx.get("to_address", "")
        if not src or not dst:
            continue

        for addr in (src, dst):
            if addr not in g:
                g.add_node(
                    addr,
                    is_center=False,
                    is_sanctioned=addr in sanctioned_set,
                    label=_truncate_address(addr),
                    chain=chain,
                )

        key = (src, dst)
        if key not in edge_agg:
            edge_agg[key] = {
                "total_value": 0.0,
                "tx_count": 0,
                "last_timestamp": "",
                "tx_hashes": [],
            }

        edge_agg[key]["total_value"] += float(tx.get("value", 0))
        edge_agg[key]["tx_count"] += 1
        ts = tx.get("timestamp", "")
        if ts > edge_agg[key]["last_timestamp"]:
            edge_agg[key]["last_timestamp"] = ts
        edge_agg[key]["tx_hashes"].append(tx.get("tx_hash", ""))

    for (src, dst), agg in edge_agg.items():
        g.add_edge(
            src,
            dst,
            total_value=agg["total_value"],
            tx_count=agg["tx_count"],
            last_timestamp=agg["last_timestamp"],
            tx_hashes=agg["tx_hashes"],
        )

    return g


def render_graph_html(graph: nx.DiGraph, height: int = 600) -> str:
    net = Network(
        height=f"{height}px",
        width="100%",
        directed=True,
        bgcolor=COLOR_BG,
        font_color="white",
        cdn_resources="remote",
    )

    all_values = [
        d.get("total_value", 0) for _, _, d in graph.edges(data=True)
    ]
    max_val = max(all_values) if all_values else 1.0
    if max_val == 0:
        max_val = 1.0

    for node, attrs in graph.nodes(data=True):
        is_center = attrs.get("is_center", False)
        is_sanctioned = attrs.get("is_sanctioned", False)

        if is_center:
            color = COLOR_CENTER
            size = SIZE_CENTER
        elif is_sanctioned:
            color = COLOR_SANCTIONED
            size = SIZE_SANCTIONED
        else:
            color = COLOR_REGULAR
            size = SIZE_REGULAR

        sanction_info = ""
        if is_sanctioned:
            entry = OFAC_ADDRESSES.get(node, {})
            name = entry.get("name", "Unknown")
            program = entry.get("program", "N/A")
            sanction_info = f"\nOFAC SANCTIONED: {name}\nProgram: {program}"

        title = f"{node}{sanction_info}"
        label = attrs.get("label", _truncate_address(node))

        net.add_node(
            node,
            label=label,
            title=title,
            color=color,
            size=size,
            font={"color": "white", "size": 12},
        )

    for src, dst, attrs in graph.edges(data=True):
        total_value = attrs.get("total_value", 0)
        tx_count = attrs.get("tx_count", 1)
        last_ts = attrs.get("last_timestamp", "")

        width = EDGE_WIDTH_MIN + (total_value / max_val) * (
            EDGE_WIDTH_MAX - EDGE_WIDTH_MIN
        )
        width = max(EDGE_WIDTH_MIN, min(EDGE_WIDTH_MAX, width))

        unit = "USDT" if graph.nodes[src].get("chain") == "tron" else "BTC"
        title = (
            f"Value: {total_value:,.4f} {unit}\n"
            f"Transactions: {tx_count}\n"
            f"Last: {last_ts}"
        )

        net.add_edge(
            src,
            dst,
            value=width,
            title=title,
            arrows="to",
            color={"color": "#4a5568", "highlight": COLOR_CENTER},
            smooth={"type": "curvedCW", "roundness": 0.15},
        )

    net.set_options("""
    {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 180,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 0.1
            },
            "stabilization": {
                "iterations": 150
            }
        },
        "interaction": {
            "hover": true,
            "tooltipDelay": 100,
            "navigationButtons": false,
            "keyboard": false
        }
    }
    """)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp_name = tmp.name

    net.save_graph(tmp_name)
    html = Path(tmp_name).read_text(encoding="utf-8")
    Path(tmp_name).unlink(missing_ok=True)
    return html
