from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from mqis.fetch import fetch_etf_holdings, fetch_etf_prices, fetch_korea_flows, fetch_price_map, latest_asof
from mqis.sectors import (
    build_holding_analysis_rows,
    build_sector_snapshot_payload,
    classify_universe,
)
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


def build_etf_holding_snapshot(etf_code: str, etf_name: str = "") -> dict[str, Any]:
    holdings = fetch_etf_holdings(etf_code)
    prices = fetch_etf_prices([item["code"] for item in holdings])
    rows = build_holding_analysis_rows(holdings, prices)
    asof_dates = [row["asof"] for row in rows]
    return {
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST"),
        "etf_code": etf_code,
        "etf_name": etf_name,
        "holdings": holdings,
        "rows": rows,
        "count": len(rows),
        "asof": max(asof_dates) if asof_dates else "-",
    }
