from __future__ import annotations

import ast
import os
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from typing import Any, Callable

import pandas as pd
import requests
import yfinance as yf

from mqis.config import (
    FLOW_LOOKBACK_DAYS,
    KR_INDICES,
    LOOKBACK_YEARS,
    MACRO,
    TICKER_FALLBACKS,
    US_INDICES,
)

NAVER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com",
}

NAVER_INDEX = {
    "KOSPI": "KOSPI",
    "KOSDAQ": "KOSDAQ",
    "KS200": "KPI200",
}

NAVER_FLOW = {
    "KOSPI": "01",
    "KOSDAQ": "02",
    "FUTURES": "03",
}


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


def _extract_ticker(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if raw is None or raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        level0 = raw.columns.get_level_values(0)
        level1 = raw.columns.get_level_values(1)
        if ticker in level0:
            piece = raw[ticker]
        elif ticker in level1:
            piece = raw.xs(ticker, axis=1, level=1)
        else:
            return pd.DataFrame()
        return _normalize_ohlcv(piece)
    return _normalize_ohlcv(raw)


def _download_one(ticker: str, start: str) -> pd.DataFrame:
    candidates = [ticker, *TICKER_FALLBACKS.get(ticker, [])]
    seen: set[str] = set()
    for symbol in candidates:
        if symbol in seen:
            continue
        seen.add(symbol)
        try:
            raw = yf.download(
                symbol,
                start=start,
                auto_adjust=True,
                progress=False,
                threads=False,
            )
            df = _extract_ticker(raw, symbol)
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()


def _overlay_volume(price: pd.DataFrame, proxy: str, start: str) -> pd.DataFrame:
    if price.empty:
        return price
    if price["Volume"].fillna(0).sum() > 0:
        return price
    proxy_df = _download_one(proxy, start)
    if proxy_df.empty:
        return price
    out = price.copy()
    out["Volume"] = proxy_df["Volume"].reindex(price.index).fillna(0)
    return out


def _naver_index_ohlcv(symbol: str, count: int = 520) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    start = (datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")
    json_url = (
        "https://api.finance.naver.com/siseJson.naver"
        f"?symbol={symbol}&requestType=1&startTime={start}&endTime={end}&timeframe=day"
    )
    try:
        payload = ast.literal_eval(
            requests.get(json_url, headers=NAVER_HEADERS, timeout=20).text.strip()
        )
        header, *body = payload
        mapped = {str(h): i for i, h in enumerate(header)}
        for row in body:
            rows.append(
                {
                    "Date": pd.to_datetime(str(row[mapped["날짜"]]), format="%Y%m%d"),
                    "Open": float(row[mapped["시가"]]),
                    "High": float(row[mapped["고가"]]),
                    "Low": float(row[mapped["저가"]]),
                    "Close": float(row[mapped["종가"]]),
                    "Volume": float(row[mapped["거래량"]]),
                }
            )
    except Exception:
        rows = []

    if not rows:
        url = (
            "https://fchart.stock.naver.com/sise.nhn"
            f"?symbol={symbol}&timeframe=day&count={count}&requestType=0"
        )
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=20)
        resp.raise_for_status()
        xml_text = resp.content.decode("euc-kr", errors="replace")
        xml_text = xml_text.replace('encoding="EUC-KR"', 'encoding="UTF-8"')
        root = ET.fromstring(xml_text)
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


FRED_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
}

STOOQ_HEADERS = {
    **FRED_HEADERS,
    "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
    "Referer": "https://stooq.com/",
}


def _close_only_ohlc(series: pd.Series) -> pd.DataFrame:
    close = pd.to_numeric(series, errors="coerce").dropna()
    if close.empty:
        return pd.DataFrame()
    df = pd.DataFrame(
        {
            "Open": close,
            "High": close,
            "Low": close,
            "Close": close,
            "Volume": 0.0,
        }
    )
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.sort_index()


def _tag(
    df: pd.DataFrame,
    source: str,
    freq: str = "D",
    unit: str | None = None,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    out.attrs["source"] = source
    out.attrs["freq"] = freq
    if unit:
        out.attrs["unit"] = unit
    return out


def _infer_freq(df: pd.DataFrame, default: str = "D") -> str:
    if df is None or len(df) < 3:
        return default
    deltas = df.index.to_series().diff().dt.days.dropna()
    if deltas.empty:
        return default
    return "M" if float(deltas.median()) >= 20 else "D"


def _first_nonempty(factories: list[Callable[[], pd.DataFrame]]) -> pd.DataFrame:
    for factory in factories:
        try:
            df = factory()
        except Exception:
            df = pd.DataFrame()
        if df is not None and not df.empty:
            return df
    return pd.DataFrame()


def _series_from_fred_frame(raw: pd.DataFrame) -> pd.Series:
    if raw is None or raw.empty or raw.shape[1] < 2:
        return pd.Series(dtype=float)
    date_col, value_col = raw.columns[0], raw.columns[1]
    dates = pd.to_datetime(raw[date_col], errors="coerce")
    values = pd.to_numeric(raw[value_col], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates).dropna()
    series.index = pd.to_datetime(series.index).tz_localize(None)
    start = datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)
    return series[series.index >= start].sort_index()


def _fred_from_api(series_id: str) -> pd.Series:
    api_key = os.environ.get("FRED_API_KEY", "").strip()
    if not api_key:
        return pd.Series(dtype=float)
    start = (datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)).strftime("%Y-%m-%d")
    url = "https://api.stlouisfed.org/fred/series/observations"
    try:
        payload = requests.get(
            url,
            params={
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "observation_start": start,
            },
            timeout=8,
            headers=FRED_HEADERS,
        ).json()
        rows = payload.get("observations") or []
        series = pd.Series(
            [row.get("value") for row in rows],
            index=pd.to_datetime([row.get("date") for row in rows]),
        )
        return pd.to_numeric(series, errors="coerce").dropna().sort_index()
    except Exception:
        return pd.Series(dtype=float)


def _fred_from_csv(series_id: str) -> pd.Series:
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)).strftime("%Y-%m-%d")
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        f"?id={series_id}&cosd={start}&coed={end}"
    )
    try:
        resp = requests.get(url, timeout=8, headers=FRED_HEADERS)
        resp.raise_for_status()
        text = resp.text.lstrip()
        if "<html" in text[:80].lower():
            return pd.Series(dtype=float)
        raw = pd.read_csv(StringIO(text))
    except Exception:
        return pd.Series(dtype=float)
    return _series_from_fred_frame(raw)


def _fred_ohlc(series_id: str, freq: str = "D") -> pd.DataFrame:
    series = _fred_from_api(series_id)
    if series.empty:
        series = _fred_from_csv(series_id)
    df = _close_only_ohlc(series)
    if df.empty:
        return df
    return _tag(df, source=f"FRED {series_id}", freq=_infer_freq(df, freq))


def _stooq_ohlc(symbol: str) -> pd.DataFrame:
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    try:
        resp = requests.get(url, timeout=8, headers=STOOQ_HEADERS)
        resp.raise_for_status()
        text = resp.text.lstrip()
        if not text.lower().startswith("date"):
            return pd.DataFrame()
        raw = pd.read_csv(StringIO(text))
    except Exception:
        return pd.DataFrame()
    raw.columns = [str(c).title() for c in raw.columns]
    if raw.empty or "Date" not in raw.columns or "Close" not in raw.columns:
        return pd.DataFrame()
    raw["Date"] = pd.to_datetime(raw["Date"], errors="coerce")
    raw = raw.dropna(subset=["Date"]).set_index("Date").sort_index()
    start = datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)
    df = _normalize_ohlcv(raw[raw.index >= start])
    return _tag(df, source=f"Stooq {symbol}", freq="D")


def _fetch_bdi(start: str) -> pd.DataFrame:
    """BDI. FRED에는 Baltic Dry Index 시리즈가 없어 Stooq → Investing/CNBC 순."""
    del start
    return _first_nonempty(
        [
            lambda: _stooq_ohlc("bdiy"),
            lambda: _stooq_ohlc("bdi"),
            _bdi_from_cnbc,
        ]
    )


def _fetch_iron(start: str) -> pd.DataFrame:
    return _first_nonempty(
        [
            lambda: _fred_ohlc("PIORECRUSDM", freq="M"),
            lambda: _stooq_ohlc("tr.f"),
            lambda: _tag(_download_one("TIO=F", start), "Investing/SGX TIO=F", freq="D"),
        ]
    )


def _fetch_lng(start: str) -> pd.DataFrame:
    return _first_nonempty(
        [
            lambda: _fred_ohlc("PNGASEUUSDM", freq="M"),
            lambda: _tag(_download_one("TTF=F", start), "Investing/ICE TTF=F", freq="D", unit="EUR"),
        ]
    )


def _bdi_from_cnbc() -> pd.DataFrame:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.cnbc.com/quotes/.BADI",
    }
    url = (
        "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
        "?symbols=.BADI&requestMethod=itv&noform=1&partnerId=2&fundPartnerId=2&output=json"
    )
    try:
        payload = requests.get(url, headers=headers, timeout=20).json()
        quote = payload["FormattedQuoteResult"]["FormattedQuote"][0]
        last = float(str(quote["last"]).replace(",", ""))
        prev = float(str(quote["previous_day_closing"]).replace(",", ""))
        last_date = pd.to_datetime(quote.get("last_time") or quote.get("last_timedate"))
        prev_date = last_date - pd.offsets.BDay(1)
        series = pd.Series({prev_date: prev, last_date: last})
        return _tag(_close_only_ohlc(series), "CNBC/Investing .BADI", freq="D")
    except Exception:
        return pd.DataFrame()


def fetch_price_map() -> dict[str, pd.DataFrame]:
    start = (datetime.now() - timedelta(days=365 * LOOKBACK_YEARS + 30)).strftime("%Y-%m-%d")
    us_macro = {**US_INDICES, **MACRO}
    tickers = [meta["ticker"] for meta in us_macro.values() if meta.get("yahoo") is not False]
    raw = pd.DataFrame()
    try:
        raw = yf.download(
            tickers,
            start=start,
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
        )
    except Exception:
        raw = pd.DataFrame()

    out: dict[str, pd.DataFrame] = {}
    for key, meta in us_macro.items():
        if meta.get("yahoo") is False:
            continue
        df = _extract_ticker(raw, meta["ticker"])
        if df.empty:
            df = _download_one(meta["ticker"], start)
        proxy = meta.get("volume_proxy")
        if proxy:
            df = _overlay_volume(df, proxy, start)
        if not df.empty:
            out[key] = df

    for key, meta in KR_INDICES.items():
        df = pd.DataFrame()
        symbol = NAVER_INDEX.get(key)
        if symbol:
            try:
                df = _naver_index_ohlcv(symbol)
            except Exception:
                df = pd.DataFrame()
        if df.empty:
            df = _download_one(meta["ticker"], start)
        proxy = meta.get("volume_proxy")
        if proxy:
            df = _overlay_volume(df, proxy, start)
        if not df.empty:
            out[key] = df

    if "US2Y" not in out or out["US2Y"].empty:
        fred = _fred_ohlc("DGS2")
        if not fred.empty:
            out["US2Y"] = fred

    specials: dict[str, pd.DataFrame] = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            "BDI": pool.submit(_fetch_bdi, start),
            "IRON": pool.submit(_fetch_iron, start),
            "LNG": pool.submit(_fetch_lng, start),
        }
        for key, future in futures.items():
            try:
                specials[key] = future.result()
            except Exception:
                specials[key] = pd.DataFrame()
    for key, df in specials.items():
        if df is not None and not df.empty:
            out[key] = df
    return out


def _parse_naver_date(value: Any) -> pd.Timestamp | None:
    text = str(value).strip()
    for fmt in ("%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            return pd.to_datetime(text, format=fmt)
        except Exception:
            continue
    return None


def _flatten_flow_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [str(col[0]) if str(col[0]) == str(col[-1]) else str(col[-1]) for col in out.columns]
    out.columns = [str(c).strip() for c in out.columns]
    return out


def _naver_flow_pages(sosok: str, pages: int = 20) -> pd.DataFrame:
    bizdate = datetime.now().strftime("%Y%m%d")
    frames = []
    for page in range(1, pages + 1):
        url = (
            "https://finance.naver.com/sise/investorDealTrendDay.nhn"
            f"?bizdate={bizdate}&sosok={sosok}&page={page}"
        )
        resp = requests.get(url, headers=NAVER_HEADERS, timeout=20)
        resp.raise_for_status()
        tables = pd.read_html(BytesIO(resp.content), encoding="euc-kr")
        if not tables:
            break
        table = _flatten_flow_table(tables[0])
        if table.empty or table.shape[1] < 4:
            break
        date_col = table.columns[0]
        parsed = table.copy()
        parsed["_date"] = parsed[date_col].map(_parse_naver_date)
        parsed = parsed.dropna(subset=["_date"])
        if parsed.empty:
            continue
        foreign_col = next((c for c in parsed.columns if "외국" in str(c)), parsed.columns[2])
        inst_col = next(
            (c for c in parsed.columns if str(c) in {"기관계", "기관"} or "기관계" in str(c)),
            parsed.columns[3],
        )
        piece = pd.DataFrame(
            {
                "외국인": pd.to_numeric(parsed[foreign_col], errors="coerce").to_numpy(),
                "기관": pd.to_numeric(parsed[inst_col], errors="coerce").to_numpy(),
            },
            index=pd.DatetimeIndex(parsed["_date"].to_numpy()),
        )
        frames.append(piece)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames).sort_index()
    return out[~out.index.duplicated(keep="last")]


def fetch_kr_spot_flows(lookback_days: int = FLOW_LOOKBACK_DAYS) -> pd.DataFrame:
    pages = max(8, lookback_days // 5 + 2)
    kospi = _naver_flow_pages(NAVER_FLOW["KOSPI"], pages=pages)
    kosdaq = _naver_flow_pages(NAVER_FLOW["KOSDAQ"], pages=pages)
    if kospi.empty and kosdaq.empty:
        return pd.DataFrame()
    merged = pd.DataFrame(index=kospi.index.union(kosdaq.index)).sort_index()
    if not kospi.empty:
        merged["외국인_현물"] = kospi["외국인"]
        merged["기관"] = kospi["기관"]
    else:
        merged["외국인_현물"] = 0.0
        merged["기관"] = 0.0
    if not kosdaq.empty:
        merged["외국인_현물"] = merged["외국인_현물"].fillna(0) + kosdaq["외국인"].reindex(merged.index).fillna(0)
        merged["기관"] = merged["기관"].fillna(0) + kosdaq["기관"].reindex(merged.index).fillna(0)
    return merged[["외국인_현물", "기관"]].tail(lookback_days)


def fetch_kr_futures_flows(lookback_days: int = FLOW_LOOKBACK_DAYS) -> pd.DataFrame:
    pages = max(8, lookback_days // 5 + 2)
    fut = _naver_flow_pages(NAVER_FLOW["FUTURES"], pages=pages)
    if fut.empty:
        return pd.DataFrame()
    out = pd.DataFrame({"외국인_선물": fut["외국인"]}).tail(lookback_days)
    out.attrs["unit"] = "계약"
    return out


def fetch_korea_flows() -> dict[str, Any]:
    spot = fetch_kr_spot_flows()
    futures = fetch_kr_futures_flows()
    unit = futures.attrs.get("unit", "계약") if not futures.empty else "계약"
    return {"spot": spot, "futures": futures, "futures_unit": unit}


def latest_asof(price_map: dict[str, pd.DataFrame]) -> dict[str, str]:
    us_keys = list(US_INDICES)
    kr_keys = list(KR_INDICES)

    def _fmt(keys: list[str]) -> str:
        dates = [price_map[k].index.max() for k in keys if k in price_map and not price_map[k].empty]
        return max(dates).strftime("%Y-%m-%d") if dates else "-"

    return {"us": _fmt(us_keys), "kr": _fmt(kr_keys)}
