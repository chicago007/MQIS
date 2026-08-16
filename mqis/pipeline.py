from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from mqis.fetch import fetch_korea_flows, fetch_price_map, latest_asof
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
