"""
MQIS 섹터 퀀트 — Gemini Web 전용 (독립 실행)

사용법: 이 파일 전체를 Gemini Web 코드 실행 창에 붙여넣고 실행.
필요 패키지: pandas, requests (Gemini 기본 제공)

네이버 fchart API에서 ETF 일봉을 가져와 15개 섹터별 수익률·거래대금·이격도를 출력합니다.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests

# ── 설정 ──────────────────────────────────────────────────────────────────────
MA_WINDOWS = (20, 60, 120)
PRICE_COUNT = 220
MAX_WORKERS = 10

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com",
}

# ── ETF 지정 목록 (code\\tname) ───────────────────────────────────────────────
ETF_UNIVERSE_TSV = """\
396500	TIGER 반도체TOP10
0167A0	SOL AI반도체TOP2플러스
091160	KODEX 반도체
395160	KODEX AI반도체TOP2플러스
395270	HANARO Fn K-반도체
139260	TIGER 200 IT
487240	KODEX AI전력핵심설비
091230	TIGER 반도체
469150	ACE AI반도체TOP3+
466920	SOL 조선TOP3플러스
455850	SOL AI반도체소부장
0148J0	TIGER 코리아휴머노이드로봇산업
0117V0	TIGER 코리아AI전력기기TOP3플러스
367760	RISE 네트워크인프라
305720	KODEX 2차전지산업
475300	SOL 반도체전공정
0210A0	ACE K반도체TOP2+
445290	KODEX 로봇액티브
471990	KODEX AI반도체핵심장비
0190C0	RISE 현대차고정피지컬AI
0080G0	KODEX 방산TOP10
102970	KODEX 증권
364980	TIGER 2차전지TOP10
0091P0	TIGER 코리아원자력
462900	KoAct 바이오헬스케어액티브
449450	PLUS K방산
466930	SOL 자동차TOP3플러스
463250	TIGER K방산&우주
091180	KODEX 자동차
494670	TIGER 조선TOP10
0182R0	1Q K반도체TOP2+
091170	KODEX 은행
0115D0	KODEX 조선TOP10
434730	HANARO 원자력iSelect
462010	TIGER 2차전지소재Fn
494220	UNICORN SK하이닉스밸류체인액티브
471760	TIGER AI반도체핵심공정
157500	TIGER 증권
444200	SOL 코리아메가테크액티브
0101N0	RISE AI전력인프라
363580	KODEX 200IT TR
474590	WON 반도체밸류체인액티브
307520	TIGER 지주회사
0098F0	KODEX 원자력SMR
117700	KODEX 건설
228790	TIGER 화장품
305540	TIGER 2차전지테마
457990	PLUS 태양광&ESS
0093A0	RISE AI반도체TOP10
0005D0	SOL 전고체배터리&실리콘음극재
469070	RISE AI&로봇
364970	TIGER 바이오TOP10
388420	RISE 비메모리반도체액티브
0168K0	TIGER 기술이전바이오액티브
491820	HANARO 전력설비투자
139220	TIGER 200 건설
266370	KODEX IT
0177X0	ACE K휴머노이드로봇산업TOP2+
421320	PLUS 우주항공
244580	KODEX 바이오
471780	TIGER 코리아테크액티브
0008T0	SOL 화장품TOP3플러스
475310	SOL 반도체후공정
433500	ACE 원자력TOP10
0151P0	RISE 코리아전략산업액티브
0228G0	ACE 반도체Plus전략산업
476260	HANARO 반도체핵심공정주도주
0209D0	KODEX 전고체배터리ESS TOP2플러스
463050	TIME K바이오액티브
139230	TIGER 200 중공업
0005G0	IBK K-AI반도체코어테크
377990	TIGER Fn신재생에너지
461950	KODEX 2차전지핵심소재10
157490	TIGER 소프트웨어
475050	ACE KPOP포커스
0209Z0	ACE 코리아AI전력TOP10
0089D0	KODEX 금융고배당TOP10
0221Z0	ACE K바이오코스닥액티브
0141S0	SOL 조선기자재
0000Z0	RISE 바이오TOP10액티브
465330	RISE 2차전지TOP10
455860	SOL 2차전지소부장Fn
0092B0	SOL 한국원자력SMR
490480	SOL K방산
367770	RISE 수소경제테마
261070	TIGER 코스닥150바이오테크
0105D0	SOL 한국AI소프트웨어
0111J0	HANARO 증권고배당TOP3플러스
0216Z0	ACE K방산TOP5+
140700	KODEX 보험
380340	ACE 코리아AI테크핵심산업
0074K0	KoAct K수출핵심기업TOP30액티브
0207G0	SOL 우주항공밸류체인
401170	RISE 메타버스
422420	RISE 2차전지액티브
0155N0	HANARO K휴머노이드테마TOP10
487130	KoAct AI인프라액티브
261060	TIGER 코스닥150IT
0115E0	KODEX 코리아소버린AI
381560	HANARO Fn전기&수소차
464600	SOL 자동차소부장Fn
0166S0	PLUS K제조업핵심기업액티브
0103T0	1Q K소버린AI
143860	TIGER 헬스케어
365000	TIGER 인터넷TOP10
487750	BNK 온디바이스AI
091220	TIGER 은행
441540	HANARO Fn조선해운
139250	TIGER 200 에너지화학
454320	HANARO CAPEX설비투자iSelect
0090B0	PLUS K방산소부장
364990	TIGER 게임TOP10
228810	TIGER 미디어컨텐츠
266420	KODEX 헬스케어
228800	TIGER 여행레저
469790	KIWOOM 코리아테크TOP10
266390	KODEX 경기소비재
0150K0	KoAct 수소전력ESS인프라액티브
300950	KODEX 게임산업
479850	HANARO K-뷰티
139270	TIGER 200 금융
117680	KODEX 철강
117460	KODEX 에너지화학
445150	KODEX 친환경조선해운액티브
227540	TIGER 200 헬스케어
315270	TIGER 200커뮤니케이션서비스
139290	TIGER 200 경기소비재
266360	KODEX K콘텐츠
486240	DAISHIN343 AI반도체&인프라액티브
395290	HANARO Fn K-POP&미디어
0219B0	KoAct 광통신&위성네트워크액티브
0184V0	UNICORN K바이오액티브
367740	HANARO Fn5G산업
464610	SOL 의료기기소부장Fn
400970	TIGER Fn메타버스
364960	TIGER BBIG
102960	KODEX 기계장비
0172Y0	ACE K수출핵심TOP10산업액티브
401470	KODEX 메타버스액티브
139240	TIGER 200 철강소재
438900	HANARO Fn K-푸드
140710	KODEX 운송
284980	RISE 200금융
266410	KODEX 필수소비재
498050	HANARO 바이오코리아액티브
0226G0	WON 피지컬AI TOP2플러스액티브
387280	TIGER 퓨처모빌리티액티브
482030	KoAct 반도체&2차전지핵심소재액티브
388280	RISE K엔터&여행레저
139280	TIGER 경기방어
385710	TIME K이노베이션액티브
381570	HANARO Fn친환경에너지
466810	BNK 2차전지양극재
300610	TIGER K게임
395150	KODEX 웹툰&드라마
488200	KIWOOM K-2차전지북미공급망
417630	TIGER KEDI혁신기업ESG30
227550	TIGER 200 산업재
446700	RISE 배터리 리사이클링
300640	RISE 게임테마
0214M0	MIDAS 바이오헬스케어액티브
488210	KIWOOM K-반도체북미공급망
322400	HANARO e커머스
227560	TIGER 200 생활소비재
307510	TIGER 의료기기
402460	HANARO Fn K-메타버스MZ
483020	KIWOOM 의료AI
253280	RISE 헬스케어
140570	RISE 수출주
0001P0	마이티 바이오시밀러&CDMO액티브
395280	HANARO Fn K-게임
470310	UNICORN 생성형AI강소기업액티브
368190	HANARO Fn K-뉴딜디지털플러스
140580	RISE 우량업종대표주
0218K0	BNK 스마트카
457930	BNK 미래전략기술액티브
368680	KODEX K-뉴딜디지털플러스
314700	HANARO 농업융복합산업
407300	HANARO Fn골프테마
"""

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

_ISSUERS = (
    "DAISHIN343", "TIMEFOLIO", "HANARO Fn", "KBSTAR", "ARIRANG", "UNICORN",
    "HANARO", "KIWOOM", "KoAct", "FOCUS", "MIDAS", "마이티", "KOSEF", "TIGER",
    "KODEX", "KINDEX", "TREX", "SMART", "PLUS", "RISE", "WON", "TIME", "ACE",
    "SOL", "BNK", "IBK", "HK", "1Q", "KB",
)

_SKIP = (
    "인버스", "곱버스", "레버리지", "금융채", "은행채", "특수은행채", "채권혼합", "커버드콜",
)

_OVERSEAS = (
    "미국", "중국", "차이나", "일본", "글로벌", "아시아", "유럽", "해외", "한중", "북미",
    "나스닥", "필라델피아", "S&P", "NYSE", "인도", "베트남", "대만", "홍콩", "신흥", "선진국",
)

_SOBUJANG = (
    ("2차전지", "2차전지", "2차전지"),
    ("이차전지", "2차전지", "소부장"),
    ("자동차", "자동차", "소부장"),
    ("방산", "방산우주", "소부장"),
    ("의료", "바이오헬스", "소부장"),
    ("바이오", "바이오헬스", "소부장"),
)

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


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def _pct(value: float) -> str:
    if value is None or value != value:
        return "-"
    return f"{value:+.2%}"


def _num(value: float, digits: int = 2) -> str:
    if value is None or value != value:
        return "-"
    return f"{value:,.{digits}f}"


def _억원(value: float) -> str:
    if value is None or value != value:
        return "-"
    return f"{value / 1e8:,.1f}"


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [str(c).title() for c in out.columns]
    out = out.rename(columns={"Adj Close": "Close"})
    needed = ["Open", "High", "Low", "Close"]
    if not all(col in out.columns for col in needed):
        return pd.DataFrame()
    if "Volume" not in out.columns:
        out["Volume"] = 0.0
    out = out[needed + ["Volume"]].apply(pd.to_numeric, errors="coerce")
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out.dropna(subset=["Close"])


# ── 데이터 수집 ───────────────────────────────────────────────────────────────
def _naver_fchart_ohlcv(symbol: str, count: int = PRICE_COUNT) -> pd.DataFrame:
    url = (
        "https://fchart.stock.naver.com/sise.nhn"
        f"?symbol={symbol}&timeframe=day&count={count}&requestType=0"
    )
    try:
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=15)
        resp.raise_for_status()
        xml_text = resp.content.decode("euc-kr", errors="replace")
        xml_text = xml_text.replace('encoding="EUC-KR"', 'encoding="UTF-8"')
        root = ET.fromstring(xml_text)
    except Exception:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        raw = item.get("data") or ""
        parts = raw.split("|")
        if len(parts) < 6:
            continue
        rows.append(
            {
                "Date": pd.to_datetime(parts[0], format="%Y%m%d"),
                "Open": float(parts[1]),
                "High": float(parts[2]),
                "Low": float(parts[3]),
                "Close": float(parts[4]),
                "Volume": float(parts[5]),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Date").sort_index()
    return _normalize_ohlcv(df)


def fetch_etf_prices(codes: list[str], count: int = PRICE_COUNT) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if not codes:
        return out

    def _one(code: str) -> tuple[str, pd.DataFrame]:
        try:
            return code, _naver_fchart_ohlcv(code, count=count)
        except Exception:
            return code, pd.DataFrame()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for code, df in pool.map(_one, codes):
            if df is not None and not df.empty:
                out[code] = df
    return out


# ── 섹터 분류 ─────────────────────────────────────────────────────────────────
def core_name(name: str) -> str:
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
    for line in ETF_UNIVERSE_TSV.splitlines():
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


def classify_universe(items: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    source = items if items is not None else load_provided_etfs()
    out: list[dict[str, str]] = []
    for item in source:
        hit = classify_etf(item["name"], provided=True)
        sector, theme = hit if hit else ("기타", "-")
        out.append({**item, "sector": sector, "theme": theme, "core": core_name(item["name"])})
    return out


# ── 지표 계산 ─────────────────────────────────────────────────────────────────
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
    ma_vals: dict[int, float] = {}
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


def build_sector_snapshot() -> dict[str, Any]:
    universe = classify_universe()
    prices = fetch_etf_prices([item["code"] for item in universe])

    rows: list[dict[str, Any]] = []
    for item in universe:
        row = etf_row(item, prices.get(item["code"], pd.DataFrame()))
        if row:
            rows.append(row)

    before = len(rows)
    rows, dropped = dedupe_by_core_name(rows)

    by_sector: dict[str, list[dict[str, Any]]] = {name: [] for name in SECTORS}
    for row in rows:
        by_sector.setdefault(row["sector"], []).append(row)
    for name in by_sector:
        by_sector[name].sort(
            key=lambda r: r["to_1d"] if pd.notna(r["to_1d"]) else -1,
            reverse=True,
        )

    summaries = {name: summarize_sector(by_sector.get(name, [])) for name in SECTORS}
    asof_dates = [row["asof"] for row in rows]
    return {
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST"),
        "asof": max(asof_dates) if asof_dates else "-",
        "count": len(rows),
        "dropped": dropped,
        "before_dedupe": before,
        "rows": rows,
        "by_sector": by_sector,
        "summaries": summaries,
    }


# ── 출력 ──────────────────────────────────────────────────────────────────────
def print_sector_report(snap: dict[str, Any]) -> None:
    print(
        f"섹터 퀀트  {snap['generated_at']}  종가 {snap['asof']}  "
        f"{snap['count']}종  (중복 {snap['dropped']}종 제외)"
    )
    print()
    print(f"{'섹터':<10} {'종목':>4} {'1D평균':>8} {'5D평균':>8} {'10D평균':>8} {'1D대금억':>10} {'이격20':>8}")
    for sector in SECTORS:
        block = snap["summaries"][sector]
        print(
            f"{sector:<10} {block['count']:>4} {_pct(block['ret_1d']):>8} "
            f"{_pct(block['ret_5d']):>8} {_pct(block['ret_10d']):>8} "
            f"{_억원(block['to_1d']):>10} {_num(block['이격도20']):>8}"
        )
    print()
    for sector in SECTORS:
        rows = snap["by_sector"].get(sector) or []
        if not rows:
            continue
        print(f"=== {sector} ===")
        for row in rows:
            print(
                f"  {row['code']:<8} {row['name']:<28} "
                f"1D {_pct(row['ret_1d'])} {_억원(row['to_1d'])}억  "
                f"이격 {_num(row['이격도20'])}/{_num(row['이격도60'])}/{_num(row['이격도120'])}  "
                f"{row['배열']}"
            )
        print()


def sector_summary_dataframe(snap: dict[str, Any]) -> pd.DataFrame:
    """Gemini에서 표로 보기 좋은 섹터 요약 DataFrame."""
    rows = []
    for sector in SECTORS:
        block = snap["summaries"][sector]
        rows.append(
            {
                "섹터": sector,
                "종목수": block["count"],
                "1D평균": block["ret_1d"],
                "5D평균": block["ret_5d"],
                "10D평균": block["ret_10d"],
                "1D대금합(억)": block["to_1d"] / 1e8 if pd.notna(block["to_1d"]) else None,
                "평균이격20": block["이격도20"],
            }
        )
    return pd.DataFrame(rows)


# ── 실행 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    snapshot = build_sector_snapshot()
    print_sector_report(snapshot)
    print("── 섹터 요약 DataFrame ──")
    display_df = sector_summary_dataframe(snapshot)
    print(display_df.to_string(index=False, float_format=lambda x: f"{x:.4f}" if abs(x) < 1 else f"{x:.2f}"))
