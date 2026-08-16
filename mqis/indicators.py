from __future__ import annotations

import numpy as np
import pandas as pd

from mqis.config import (
    ADX_PERIOD,
    ATR_PERIOD,
    BB_PERIOD,
    BB_STD,
    FORCE_SPAN,
    MA_WINDOWS,
    RSI_PERIOD,
    RS_MA,
    STOCH_D,
    STOCH_K,
    VOL_MA,
)


def _wilder(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(alpha=1 / period, adjust=False).mean()


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev = close.shift(1)
    return pd.concat(
        [(high - low), (high - prev).abs(), (low - prev).abs()],
        axis=1,
    ).max(axis=1)


def adx_dmi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = ADX_PERIOD,
) -> pd.DataFrame:
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = true_range(high, low, close)
    atr = _wilder(tr, period)
    plus_di = 100 * _wilder(pd.Series(plus_dm, index=close.index), period) / atr
    minus_di = 100 * _wilder(pd.Series(minus_dm, index=close.index), period) / atr
    di_sum = plus_di + minus_di
    dx = 100 * (plus_di - minus_di).abs() / di_sum.replace(0, np.nan)
    adx = _wilder(dx, period)
    return pd.DataFrame({"+DI": plus_di, "-DI": minus_di, "ADX": adx})


def force_index(close: pd.Series, volume: pd.Series, span: int = FORCE_SPAN) -> pd.Series:
    raw = (close - close.shift(1)) * volume
    return raw.ewm(span=span, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = ATR_PERIOD) -> pd.Series:
    return _wilder(true_range(high, low, close), period)


def bollinger_width(
    close: pd.Series,
    period: int = BB_PERIOD,
    n_std: float = BB_STD,
) -> pd.Series:
    mid = sma(close, period)
    std = close.rolling(period, min_periods=period).std()
    return (2 * n_std * std) / mid.replace(0, np.nan)


def rsi(close: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = _wilder(gain, period)
    avg_loss = _wilder(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = STOCH_K,
    d_period: int = STOCH_D,
) -> pd.DataFrame:
    lowest = low.rolling(k_period, min_periods=k_period).min()
    highest = high.rolling(k_period, min_periods=k_period).max()
    k = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
    d = k.rolling(d_period, min_periods=d_period).mean()
    return pd.DataFrame({"%K": k, "%D": d})


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff().fillna(0))
    return (direction * volume).cumsum()


def relative_strength(series: pd.Series, benchmark: pd.Series) -> pd.DataFrame:
    aligned = pd.concat([series.rename("px"), benchmark.rename("bm")], axis=1).dropna()
    rs = aligned["px"] / aligned["bm"].replace(0, np.nan)
    base = rs.dropna().iloc[0] if not rs.dropna().empty else np.nan
    rs_idx = 100 * rs / base if pd.notna(base) and base != 0 else rs
    return pd.DataFrame(
        {
            "RS": rs_idx,
            "RS_MA": sma(rs_idx, RS_MA),
        }
    )


def enrich(ohlcv: pd.DataFrame) -> pd.DataFrame:
    df = ohlcv.copy()
    close, high, low = df["Close"], df["High"], df["Low"]
    volume = df["Volume"] if "Volume" in df.columns else pd.Series(np.nan, index=df.index)

    for window in MA_WINDOWS:
        df[f"MA{window}"] = sma(close, window)

    dmi = adx_dmi(high, low, close)
    df = df.join(dmi)
    df["Force"] = force_index(close, volume)
    df["ATR"] = atr(high, low, close)
    df["ATR_PCT"] = 100 * df["ATR"] / close.replace(0, np.nan)
    df["BBW"] = bollinger_width(close)
    df["BBW_PCTILE"] = df["BBW"].rolling(252, min_periods=60).rank(pct=True) * 100
    df["RSI"] = rsi(close)
    stoch = stochastic(high, low, close)
    df = df.join(stoch)
    df["OBV"] = obv(close, volume)
    df["OBV_MA20"] = sma(df["OBV"], VOL_MA)
    df["VOL_MA20"] = volume.rolling(VOL_MA, min_periods=VOL_MA).mean()
    df["VOL_RATIO"] = volume / df["VOL_MA20"].replace(0, np.nan)
    df["RET_1D"] = close.pct_change()
    return df
