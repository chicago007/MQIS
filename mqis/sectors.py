from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from mqis.config import MA_WINDOWS
from mqis.indicators import sma

SECTORS: tuple[str, ...] = (
    "반도체",
    "AI인프라",
    "2차전지",
    "방산우주",
    "조선",
    "바이오헬스",
    "자동차",
    "로봇",
    "건설",
    "원자력",
    "에너지화학",
    "금융",
    "IT서비스",
    "소비재",
    "기타",
)

SECTOR_THEMES: dict[str, tuple[str, ...]] = {
    "반도체": ("반도체", "AI반도체", "비메모리", "소부장", "전공정", "후공정", "장비"),
    "AI인프라": ("AI전력", "전력기기", "전력설비", "AI인프라"),
    "2차전지": ("배터리", "소재", "전고체", "리사이클링"),
    "방산우주": ("방산", "우주항공"),
    "조선": ("조선", "기자재"),
    "바이오헬스": ("바이오", "헬스케어", "의료기기", "CDMO"),
    "자동차": ("자동차", "자동차부품"),
    "로봇": ("로봇", "휴머노이드", "피지컬AI"),
    "건설": ("건설",),
    "원자력": ("원자력", "SMR"),
    "에너지화학": ("에너지화학", "태양광", "신재생", "수소경제"),
    "금융": ("은행", "증권", "보험", "금융"),
    "IT서비스": ("소프트웨어", "인터넷", "네트워크"),
    "소비재": ("화장품", "게임", "콘텐츠", "여행", "소비재"),
    "기타": ("지정 목록 중 위 섹터 밖",),
}

_ISSUERS = (
    "DAISHIN343",
    "TIMEFOLIO",
    "HANARO Fn",
    "KBSTAR",
    "ARIRANG",
    "UNICORN",
    "HANARO",
    "KIWOOM",
    "KoAct",
    "FOCUS",
    "MIDAS",
    "마이티",
    "KOSEF",
    "TIGER",
    "KODEX",
    "KINDEX",
    "TREX",
    "SMART",
    "PLUS",
    "RISE",
    "WON",
    "TIME",
    "ACE",
    "SOL",
    "BNK",
    "IBK",
    "HK",
    "1Q",
    "KB",
)

_SKIP = (
    "인버스",
    "곱버스",
    "레버리지",
    "금융채",
    "은행채",
    "특수은행채",
    "채권혼합",
    "커버드콜",
)

_OVERSEAS = (
    "미국",
    "중국",
    "차이나",
    "일본",
    "글로벌",
    "아시아",
    "유럽",
    "해외",
    "한중",
    "북미",
    "나스닥",
    "필라델피아",
    "S&P",
    "NYSE",
    "인도",
    "베트남",
    "대만",
    "홍콩",
    "신흥",
    "선진국",
)

_SOBUJANG = (
    ("2차전지", "2차전지", "2차전지"),
    ("이차전지", "2차전지", "소부장"),
    ("자동차", "자동차", "소부장"),
    ("방산", "방산우주", "소부장"),
    ("의료", "바이오헬스", "소부장"),
    ("바이오", "바이오헬스", "소부장"),
)

_UNIVERSE_PATH = Path(__file__).resolve().parent / "data" / "etf_universe.txt"

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("로봇", ("휴머노이드", "피지컬AI", "로봇")),
    ("원자력", ("원자력", "SMR")),
    ("건설", ("건설",)),
    ("AI인프라", ("AI전력", "전력기기", "전력설비", "AI인프라", "전력인프라", "전력핵심설비", "수소전력")),
    ("에너지화학", ("에너지화학", "태양광", "신재생", "수소경제", "친환경에너지")),
    ("2차전지", ("2차전지", "이차전지", "전고체", "리사이클링", "리튬", "배터리")),
    ("방산우주", ("우주항공", "방산", "우주")),
    ("조선", ("조선기자재", "조선")),
    ("바이오헬스", ("헬스케어", "의료기기", "의료AI", "CDMO", "바이오")),
    ("자동차", ("자동차부품", "자동차", "현대차", "수소차", "스마트카", "모빌리티")),
    ("반도체", ("AI반도체", "비메모리", "전공정", "후공정", "반도체", "HBM", "하이닉스")),
    ("금융", ("은행", "증권", "보험", "금융")),
    ("IT서비스", ("소프트웨어", "인터넷", "네트워크", "5G", "e커머스")),
    ("소비재", ("화장품", "게임", "콘텐츠", "컨텐츠", "여행", "뷰티", "KPOP", "K-POP", "웹툰", "미디어", "소비재")),
)


def core_name(name: str) -> str:
    """운용사 접두어를 뺀 종목명. KODEX 은행 / TIGER 은행 → 은행."""
    text = " ".join(str(name).split())
    for prefix in _ISSUERS:
        token = prefix + " "
        if text.startswith(token):
            text = text[len(token):].strip()
            break
        if text.startswith(prefix) and len(text) > len(prefix):
            text = text[len(prefix):].strip()
            break
    if text.startswith("Fn "):
        text = text[3:].strip()
    elif text.startswith("Fn"):
        text = text[2:].strip()
    return text


def load_provided_etfs() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in _UNIVERSE_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "\t" not in line:
            continue
        code, name = line.split("\t", 1)
        rows.append({"code": code.strip(), "name": " ".join(name.split())})
    return rows


def _is_kr_it(name: str) -> bool:
    compact = name.replace(" ", "")
    if "200IT" in compact or "코스닥150IT" in compact:
        return True
    if compact.endswith("IT") and "바이오" not in name:
        return True
    return "IT" in name.split()


def classify_universe(items: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    source = items if items is not None else load_provided_etfs()
    out: list[dict[str, str]] = []
    for item in source:
        hit = classify_etf(item["name"], provided=True)
        sector, theme = hit if hit else ("기타", "-")
        out.append(
            {
                **item,
                "sector": sector,
                "theme": theme,
                "core": core_name(item["name"]),
            }
        )
    return out


def classify_etf(name: str, *, provided: bool = False) -> tuple[str, str] | None:
    if any(token in name for token in _SKIP):
        return None
    if not provided and any(token in name for token in _OVERSEAS):
        return None
    if "소부장" in name:
        for needle, sector, theme in _SOBUJANG:
            if needle in name:
                return sector, theme
        return "반도체", "소부장"
    if _is_kr_it(name):
        return "IT서비스", "IT"
    for sector, keys in _RULES:
        for key in keys:
            if key in name:
                return sector, key
    if "기자재" in name:
        return "조선", "기자재"
    if "전력" in name and "원자력" not in name and "반도체" not in name:
        return "AI인프라", "전력설비"
    if "장비" in name and any(token in name for token in ("반도체", "전공정", "후공정", "AI")):
        return "반도체", "장비"
    if "소재" in name and any(token in name for token in ("2차전지", "이차전지", "배터리", "리튬")):
        return "2차전지", "소재"
    if provided:
        return "기타", "-"
    return None


def _chg(close: pd.Series, periods: int) -> float:
    clean = close.dropna()
    if len(clean) <= periods:
        return float("nan")
    prev = clean.iloc[-1 - periods]
    if prev == 0 or pd.isna(prev):
        return float("nan")
    return float(clean.iloc[-1] / prev - 1)


def _disparity(close: float, ma: float) -> float:
    if pd.isna(close) or pd.isna(ma) or ma == 0:
        return float("nan")
    return 100.0 * float(close) / float(ma)


def _align(ma20: float, ma60: float, ma120: float) -> str:
    if any(pd.isna(x) for x in (ma20, ma60, ma120)):
        return "-"
    if ma20 > ma60 > ma120:
        return "정배열"
    if ma20 < ma60 < ma120:
        return "역배열"
    return "혼조"


def _sum_turnover(turnover: pd.Series, periods: int) -> float:
    clean = turnover.dropna()
    if clean.empty:
        return float("nan")
    return float(clean.tail(periods).sum())


def etf_row(meta: dict[str, str], df: pd.DataFrame) -> dict[str, Any] | None:
    if df is None or df.empty or "Close" not in df.columns:
        return None
    close = df["Close"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(0.0, index=df.index)
    turnover = close * volume
    last = float(close.dropna().iloc[-1])
    ma_vals = {}
    for window in MA_WINDOWS:
        series = sma(close, window).dropna()
        ma_vals[window] = float(series.iloc[-1]) if not series.empty else float("nan")
    ma20, ma60, ma120 = ma_vals[20], ma_vals[60], ma_vals[120]
    return {
        "sector": meta["sector"],
        "theme": meta["theme"],
        "code": meta["code"],
        "name": meta["name"],
        "close": last,
        "ret_1d": _chg(close, 1),
        "ret_5d": _chg(close, 5),
        "ret_10d": _chg(close, 10),
        "to_1d": _sum_turnover(turnover, 1),
        "to_5d": _sum_turnover(turnover, 5),
        "to_10d": _sum_turnover(turnover, 10),
        "이격도20": _disparity(last, ma20),
        "이격도60": _disparity(last, ma60),
        "이격도120": _disparity(last, ma120),
        "배열": _align(ma20, ma60, ma120),
        "core": meta.get("core") or core_name(meta["name"]),
        "asof": close.dropna().index.max().strftime("%Y-%m-%d"),
    }


def _turnover(row: dict[str, Any]) -> float:
    value = row.get("to_1d")
    if value is None or pd.isna(value):
        return -1.0
    return float(value)


def dedupe_by_core_name(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """접두어를 뺀 종목명이 같으면 당일 거래대금이 큰 ETF만 남긴다."""
    best: dict[str, dict[str, Any]] = {}
    dropped = 0
    for row in rows:
        key = str(row.get("core") or core_name(row["name"]))
        prev = best.get(key)
        if prev is None:
            best[key] = row
            continue
        if _turnover(row) > _turnover(prev):
            best[key] = row
        dropped += 1
    return list(best.values()), dropped


def summarize_sector(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "count": 0,
            "ret_1d": float("nan"),
            "ret_5d": float("nan"),
            "ret_10d": float("nan"),
            "to_1d": float("nan"),
            "이격도20": float("nan"),
        }
    frame = pd.DataFrame(rows)
    return {
        "count": len(rows),
        "ret_1d": float(frame["ret_1d"].mean()),
        "ret_5d": float(frame["ret_5d"].mean()),
        "ret_10d": float(frame["ret_10d"].mean()),
        "to_1d": float(frame["to_1d"].sum()),
        "이격도20": float(frame["이격도20"].mean()),
    }


def build_sector_snapshot_payload(
    universe: list[dict[str, str]],
    prices: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    classified: list[dict[str, str]] = []
    for item in universe:
        if item.get("sector"):
            classified.append(item)
            continue
        hit = classify_etf(item["name"])
        if not hit:
            continue
        sector, theme = hit
        classified.append({**item, "sector": sector, "theme": theme, "core": core_name(item["name"])})

    rows: list[dict[str, Any]] = []
    for item in classified:
        row = etf_row(item, prices.get(item["code"], pd.DataFrame()))
        if row:
            rows.append(row)

    before = len(rows)
    rows, dropped = dedupe_by_core_name(rows)

    by_sector: dict[str, list[dict[str, Any]]] = {name: [] for name in SECTORS}
    for row in rows:
        by_sector.setdefault(row["sector"], []).append(row)
    for name in by_sector:
        by_sector[name].sort(key=lambda r: r["to_1d"] if pd.notna(r["to_1d"]) else -1, reverse=True)

    summaries = {name: summarize_sector(by_sector.get(name, [])) for name in SECTORS}
    asof_dates = [row["asof"] for row in rows]
    return {
        "rows": rows,
        "by_sector": by_sector,
        "summaries": summaries,
        "count": len(rows),
        "dropped": dropped,
        "before_dedupe": before,
        "asof": max(asof_dates) if asof_dates else "-",
    }
