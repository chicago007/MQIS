from __future__ import annotations

from typing import Any

import pandas as pd

from mqis.config import KR_INDICES, MACRO, QUANT_UNIVERSE, THRESHOLDS, US_INDICES
from mqis.indicators import enrich, relative_strength


def _last(series: pd.Series) -> float:
    clean = series.dropna()
    if clean.empty:
        return float("nan")
    return float(clean.iloc[-1])


def _chg(series: pd.Series, periods: int = 1) -> float:
    clean = series.dropna()
    if len(clean) <= periods:
        return float("nan")
    prev = clean.iloc[-1 - periods]
    if prev == 0 or pd.isna(prev):
        return float("nan")
    return float(clean.iloc[-1] / prev - 1)


def _tone(label: str) -> str:
    if label in {"상승", "강세", "매수", "과매도", "수축"}:
        return "up"
    if label in {"하락", "약세", "매도", "과열", "확장"}:
        return "down"
    return "flat"


def _sum_last(series: pd.Series, n: int) -> float:
    clean = series.dropna()
    if clean.empty:
        return float("nan")
    return float(clean.tail(n).sum())


def market_snapshot(price_map: dict[str, pd.DataFrame], flows: dict[str, Any]) -> dict[str, Any]:
    us = []
    for key, meta in US_INDICES.items():
        df = price_map.get(key)
        if df is None or df.empty:
            continue
        close = df["Close"]
        us.append(
            {
                "key": key,
                "name": meta["name"],
                "close": _last(close),
                "chg_1d": _chg(close, 1),
                "chg_5d": _chg(close, 5),
                "asof": close.dropna().index.max().strftime("%Y-%m-%d"),
            }
        )

    macro = []
    for key, meta in MACRO.items():
        df = price_map.get(key)
        if df is None or df.empty:
            continue
        close = df["Close"]
        last = _last(close)
        chg = _chg(close, 1)
        note = _macro_note(key, last, chg)
        source = str(df.attrs.get("source") or "")
        freq = str(df.attrs.get("freq") or "D")
        unit = str(df.attrs.get("unit") or meta["unit"])
        macro.append(
            {
                "key": key,
                "name": meta["name"],
                "unit": unit,
                "close": last,
                "chg_1d": chg,
                "chg_5d": _chg(close, 5),
                "note": note,
                "source": source,
                "freq": freq,
                "asof": close.dropna().index.max().strftime("%Y-%m-%d"),
            }
        )

    spot = flows.get("spot", pd.DataFrame())
    fut = flows.get("futures", pd.DataFrame())
    korea = {
        "외국인_현물": _flow_block(spot, "외국인_현물", "억원") if not spot.empty else None,
        "기관": _flow_block(spot, "기관", "억원") if not spot.empty else None,
        "외국인_선물": _flow_block(fut, "외국인_선물", flows.get("futures_unit", "계약"))
        if not fut.empty
        else None,
    }
    return {"us": us, "macro": macro, "korea": korea}


def _macro_note(key: str, last: float, chg: float) -> str:
    if pd.isna(last):
        return "-"

    def direction(up: str, down: str, flat: str) -> str:
        if pd.isna(chg) or abs(chg) < 5e-5:
            return flat
        return up if chg > 0 else down

    if key == "VIX":
        if last >= THRESHOLDS.vix_stress:
            return "스트레스"
        if last >= THRESHOLDS.vix_elevated:
            return "경계"
        return "안정"
    if key == "TNX" or key == "US2Y":
        return direction("금리 상승", "금리 하락", "금리")
    if key == "DXY":
        return direction("달러 강세", "달러 약세", "달러")
    if key == "WTI":
        return direction("유가 상승", "유가 하락", "유가")
    if key == "NG":
        return direction("가스 상승", "가스 하락", "가스")
    if key == "LNG":
        return direction("LNG 상승", "LNG 하락", "LNG")
    if key == "GOLD":
        return direction("금 상승", "금 하락", "금")
    if key == "HG":
        return direction("구리 상승", "구리 하락", "구리")
    if key == "IRON":
        return direction("철광석 상승", "철광석 하락", "철광석")
    if key == "BDI":
        return direction("운임 상승", "운임 하락", "운임")
    if key == "BTC":
        return direction("상승", "하락", "보합")
    return "-"


def _flow_block(df: pd.DataFrame, col: str, unit: str) -> dict[str, Any]:
    series = df[col]
    last = _last(series)
    return {
        "name": col.replace("_", " "),
        "unit": unit,
        "d1": last,
        "d5": _sum_last(series, 5),
        "d20": _sum_last(series, 20),
        "tone": "up" if last > 0 else "down" if last < 0 else "flat",
        "asof": series.dropna().index.max().strftime("%Y-%m-%d") if not series.dropna().empty else "-",
        "series": series,
    }


def _disparity(close: float, ma: float) -> float:
    """이격도=(종가/이평)*100."""
    if pd.isna(close) or pd.isna(ma) or ma == 0:
        return float("nan")
    return 100.0 * float(close) / float(ma)


def _ma_align(ma20: float, ma60: float, ma120: float) -> str:
    if any(pd.isna(x) for x in (ma20, ma60, ma120)):
        return "-"
    if ma20 > ma60 > ma120:
        return "정배열"
    if ma20 < ma60 < ma120:
        return "역배열"
    return "혼조"


def _ma_block(close: float, ma20: float, ma60: float, ma120: float) -> dict[str, Any]:
    d20 = _disparity(close, ma20)
    d60 = _disparity(close, ma60)
    d120 = _disparity(close, ma120)
    return {
        "close": close,
        "ma20": ma20,
        "ma60": ma60,
        "ma120": ma120,
        "이격도20": d20,
        "이격도60": d60,
        "이격도120": d120,
        "배열": _ma_align(ma20, ma60, ma120),
    }


def _trend_signal(row: pd.Series) -> dict[str, Any]:
    close = row.get("Close")
    ma20, ma60, ma120 = row.get("MA20"), row.get("MA60"), row.get("MA120")
    ma = _ma_block(close, ma20, ma60, ma120)
    aligned_up = ma["배열"] == "정배열"
    aligned_dn = ma["배열"] == "역배열"
    if aligned_up and pd.notna(close) and pd.notna(ma20) and close > ma20:
        label, score = "상승", 2
    elif aligned_dn and pd.notna(close) and pd.notna(ma20) and close < ma20:
        label, score = "하락", -2
    elif pd.notna(ma20) and close > ma20:
        label, score = "중립+", 1
    elif pd.notna(ma20) and close < ma20:
        label, score = "중립-", -1
    else:
        label, score = "중립", 0
    return {
        "label": label,
        "tone": _tone(label if label in {"상승", "하락"} else "중립"),
        "score": score,
        "ma": ma,
        "values": {
            "종가": close,
            "20MA": ma20,
            "60MA": ma60,
            "120MA": ma120,
            "이격도(20)": ma["이격도20"],
            "이격도(60)": ma["이격도60"],
            "이격도(120)": ma["이격도120"],
            "배열": ma["배열"],
        },
    }


def _momentum_signal(row: pd.Series) -> dict[str, Any]:
    adx, pdi, mdi = row.get("ADX"), row.get("+DI"), row.get("-DI")
    force = row.get("Force")
    if pd.notna(adx) and adx >= THRESHOLDS.adx_trend and pd.notna(pdi) and pd.notna(mdi):
        if pdi > mdi:
            label, score = "상승", 2
        else:
            label, score = "하락", -2
    elif pd.notna(adx) and adx < THRESHOLDS.adx_chop:
        label, score = "횡보", 0
    elif pd.notna(force):
        label, score = ("상승", 1) if force > 0 else ("하락", -1)
    else:
        label, score = "중립", 0
    if pd.notna(force):
        if force > 0 and score >= 0:
            score = min(2, score + 1) if label == "상승" else score
        elif force < 0 and score <= 0:
            score = max(-2, score - 1) if label == "하락" else score
    return {
        "label": label,
        "tone": _tone(label if label != "횡보" else "중립"),
        "score": score,
        "values": {"+DI": pdi, "-DI": mdi, "ADX": adx, "Force Index": force},
    }


def _volatility_signal(row: pd.Series) -> dict[str, Any]:
    atr_pct, bbw, bbw_pct = row.get("ATR_PCT"), row.get("BBW"), row.get("BBW_PCTILE")
    if pd.notna(bbw_pct) and bbw_pct <= THRESHOLDS.bbw_squeeze_pct:
        label, score = "수축", 0
    elif pd.notna(bbw_pct) and bbw_pct >= THRESHOLDS.bbw_expand_pct:
        label, score = "확장", 0
    else:
        label, score = "보통", 0
    return {
        "label": label,
        "tone": _tone(label),
        "score": score,
        "values": {"ATR": row.get("ATR"), "ATR%": atr_pct, "BB Width": bbw, "BBW 백분위": bbw_pct},
    }


def _overheat_signal(row: pd.Series) -> dict[str, Any]:
    rsi_v, k, d = row.get("RSI"), row.get("%K"), row.get("%D")
    hot = (pd.notna(rsi_v) and rsi_v >= THRESHOLDS.rsi_overbought) or (
        pd.notna(k) and k >= THRESHOLDS.stoch_overbought
    )
    cold = (pd.notna(rsi_v) and rsi_v <= THRESHOLDS.rsi_oversold) or (
        pd.notna(k) and k <= THRESHOLDS.stoch_oversold
    )
    if hot and not cold:
        label, score = "과열", -1
    elif cold and not hot:
        label, score = "과매도", 1
    else:
        label, score = "중립", 0
    return {
        "label": label,
        "tone": _tone(label),
        "score": score,
        "values": {"RSI": rsi_v, "%K": k, "%D": d},
    }


def _flow_signal(row: pd.Series) -> dict[str, Any]:
    vol_ratio, obv, obv_ma, ret = (
        row.get("VOL_RATIO"),
        row.get("OBV"),
        row.get("OBV_MA20"),
        row.get("RET_1D"),
    )
    score = 0
    if pd.notna(obv) and pd.notna(obv_ma):
        score += 1 if obv >= obv_ma else -1
    if pd.notna(vol_ratio) and vol_ratio >= THRESHOLDS.vol_active and pd.notna(ret):
        score += 1 if ret > 0 else -1
    if score > 0:
        label = "매수"
    elif score < 0:
        label = "매도"
    else:
        label = "중립"
    return {
        "label": label,
        "tone": _tone(label),
        "score": max(-2, min(2, score)),
        "values": {"거래량/20MA": vol_ratio, "OBV": obv, "OBV 20MA": obv_ma},
    }


def _rs_signal(rs_df: pd.DataFrame | None) -> dict[str, Any]:
    if rs_df is None or rs_df.empty:
        return {"label": "-", "tone": "flat", "score": 0, "values": {}}
    last = rs_df.dropna(subset=["RS"]).iloc[-1]
    rs, ma = last.get("RS"), last.get("RS_MA")
    chg = _chg(rs_df["RS"], 20)
    if pd.notna(rs) and pd.notna(ma) and rs >= ma and (pd.isna(chg) or chg >= 0):
        label, score = "강세", 2
    elif pd.notna(rs) and pd.notna(ma) and rs < ma and (pd.isna(chg) or chg < 0):
        label, score = "약세", -2
    elif pd.notna(rs) and pd.notna(ma) and rs >= ma:
        label, score = "강세", 1
    elif pd.notna(rs) and pd.notna(ma):
        label, score = "약세", -1
    else:
        label, score = "중립", 0
    return {
        "label": label,
        "tone": _tone(label),
        "score": score,
        "values": {"RS": rs, "RS 20MA": ma, "RS 20D": chg},
        "series": rs_df,
    }


def _composite(blocks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    weights = {
        "추세": 0.30,
        "모멘텀": 0.20,
        "과열": 0.15,
        "수급": 0.15,
        "상대강도": 0.20,
    }
    score = 0.0
    for name, weight in weights.items():
        score += blocks[name]["score"] / 2 * weight * 100
    if score >= 25:
        label, tone = "매수 우세", "up"
    elif score <= -25:
        label, tone = "매도 우세", "down"
    else:
        label, tone = "중립", "flat"
    return {"score": score, "label": label, "tone": tone}


def quant_signals(price_map: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    kospi = price_map.get("KOSPI")
    kospi_close = kospi["Close"] if kospi is not None and not kospi.empty else None
    rows = []
    for key, meta in QUANT_UNIVERSE.items():
        raw = price_map.get(key)
        if raw is None or raw.empty:
            continue
        df = enrich(raw)
        last = df.dropna(subset=["Close"]).iloc[-1]
        rs_df = None
        if kospi_close is not None and key != "KOSPI":
            rs_df = relative_strength(df["Close"], kospi_close)
        elif key == "KOSPI":
            rs_df = pd.DataFrame({"RS": pd.Series(100.0, index=df.index), "RS_MA": 100.0})

        blocks = {
            "추세": _trend_signal(last),
            "모멘텀": _momentum_signal(last),
            "변동성": _volatility_signal(last),
            "과열": _overheat_signal(last),
            "수급": _flow_signal(last),
            "상대강도": _rs_signal(rs_df if key != "KOSPI" else None)
            if key != "KOSPI"
            else {
                "label": "기준",
                "tone": "flat",
                "score": 0,
                "values": {"RS": 100.0},
                "series": rs_df,
            },
        }
        close = float(last["Close"])
        rs_block = blocks["상대강도"]["values"]
        rows.append(
            {
                "key": key,
                "name": meta["name"],
                "region": "미국" if key in US_INDICES else "한국",
                "close": close,
                "chg_1d": float(last["RET_1D"]) if pd.notna(last.get("RET_1D")) else float("nan"),
                "asof": last.name.strftime("%Y-%m-%d"),
                "ma": blocks["추세"]["ma"],
                "metrics": {
                    "+DI": last.get("+DI"),
                    "-DI": last.get("-DI"),
                    "ADX": last.get("ADX"),
                    "Force": last.get("Force"),
                    "ATR": last.get("ATR"),
                    "ATR%": last.get("ATR_PCT"),
                    "BBW": last.get("BBW"),
                    "BBW_PCTILE": last.get("BBW_PCTILE"),
                    "RSI": last.get("RSI"),
                    "%K": last.get("%K"),
                    "%D": last.get("%D"),
                    "VOL_RATIO": last.get("VOL_RATIO"),
                    "OBV": last.get("OBV"),
                    "OBV_MA20": last.get("OBV_MA20"),
                    "RS": rs_block.get("RS"),
                    "RS_MA": rs_block.get("RS 20MA"),
                },
                "blocks": blocks,
                "composite": _composite(blocks),
                "history": df,
            }
        )
    return rows
