from __future__ import annotations

from dataclasses import dataclass

LOOKBACK_YEARS = 2
FLOW_LOOKBACK_DAYS = 80
CACHE_TTL_SEC = 300

US_INDICES = {
    "SPX": {"name": "S&P500", "ticker": "^GSPC", "volume_proxy": "SPY"},
    "NDX": {"name": "Nasdaq100", "ticker": "^NDX", "volume_proxy": "QQQ"},
    "SOX": {"name": "SOX", "ticker": "^SOX", "volume_proxy": "SOXX"},
}

KR_INDICES = {
    "KOSPI": {"name": "KOSPI", "ticker": "^KS11", "volume_proxy": "069500.KS"},
    "KOSDAQ": {"name": "KOSDAQ", "ticker": "^KQ11", "volume_proxy": "229200.KS"},
    "KS200": {"name": "KOSPI200", "ticker": "^KS200", "volume_proxy": None},
}

MACRO = {
    "TNX": {"name": "미국 10년물", "ticker": "^TNX", "unit": "%", "group": "rate"},
    "US2Y": {"name": "미국 2년물", "ticker": "2YY=F", "unit": "%", "group": "rate"},
    "VIX": {"name": "VIX", "ticker": "^VIX", "unit": "pt", "group": "rate"},
    "DXY": {"name": "DXY", "ticker": "DX-Y.NYB", "unit": "pt", "group": "rate"},
    "WTI": {"name": "WTI", "ticker": "CL=F", "unit": "USD", "group": "energy"},
    "NG": {"name": "천연가스", "ticker": "NG=F", "unit": "USD", "group": "energy"},
    "LNG": {"name": "LNG(EU)", "ticker": "TTF=F", "unit": "USD", "group": "energy", "yahoo": False},
    "GOLD": {"name": "금", "ticker": "GC=F", "unit": "USD", "group": "metal"},
    "HG": {"name": "구리", "ticker": "HG=F", "unit": "USD", "group": "metal"},
    "IRON": {"name": "철광석", "ticker": "TIO=F", "unit": "USD", "group": "metal", "yahoo": False},
    "BDI": {"name": "BDI", "ticker": "BDRY", "unit": "pt", "group": "metal", "yahoo": False},
    "BTC": {"name": "Bitcoin", "ticker": "BTC-USD", "unit": "USD", "group": "crypto"},
}

MACRO_GROUPS = (
    ("금리·달러", ("TNX", "US2Y", "VIX", "DXY")),
    ("에너지", ("WTI", "NG", "LNG")),
    ("금속·원자재", ("GOLD", "HG", "IRON", "BDI")),
    ("크립토", ("BTC",)),
)

TICKER_FALLBACKS = {
    "^SOX": ["SOX", "SOXX"],
    "DX-Y.NYB": ["DX=F", "UUP"],
    "^KS200": ["^KS200", "069500.KS"],
}

INVERT_TONE_KEYS = {"TNX", "US2Y", "VIX", "DXY"}

QUANT_UNIVERSE = {**US_INDICES, **KR_INDICES}
KOSPI_KEY = "KOSPI"

ADX_PERIOD = 14
ATR_PERIOD = 14
RSI_PERIOD = 14
STOCH_K = 14
STOCH_D = 3
FORCE_SPAN = 13
BB_PERIOD = 20
BB_STD = 2.0
VOL_MA = 20
RS_MA = 20
MA_WINDOWS = (20, 60, 120)


@dataclass(frozen=True)
class Thresholds:
    adx_trend: float = 25.0
    adx_chop: float = 20.0
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    stoch_overbought: float = 80.0
    stoch_oversold: float = 20.0
    bbw_squeeze_pct: float = 20.0
    bbw_expand_pct: float = 80.0
    vol_active: float = 1.5
    vix_elevated: float = 20.0
    vix_stress: float = 30.0


THRESHOLDS = Thresholds()
