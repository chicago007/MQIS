from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from mqis.fetch import fetch_etf_prices, fetch_korea_flows, fetch_price_map, latest_asof
from mqis.sectors import build_sector_snapshot_payload, classify_universe
from mqis.signals import market_snapshot, quant_signals


def build_snapshot() -> dict[str, Any]:
    prices = fetch_price_map()
    flows = fetch_korea_flows()
    market = market_snapshot(prices, flows)
    quant = quant_signals(prices)
    return {
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST"),
        "asof": latest_asof(prices),
        "market": market,
        "quant": quant,
        "flows": flows,
        "prices": prices,
    }


def build_sector_snapshot() -> dict[str, Any]:
    universe = classify_universe()
    prices = fetch_etf_prices([item["code"] for item in universe])
    payload = build_sector_snapshot_payload(universe, prices)
    return {
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST"),
        **payload,
    }
