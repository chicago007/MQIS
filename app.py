from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from mqis.config import CACHE_TTL_SEC, INVERT_TONE_KEYS, MACRO_GROUPS
from mqis.pipeline import build_snapshot

st.set_page_config(page_title="MQIS — Market Quant Investment System", page_icon="M", layout="wide")

TONE = {"up": "#3FB950", "down": "#F85149", "flat": "#8B949E"}


def _pct(value: float) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:+.2%}"


def _num(value: float, digits: int = 2) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.{digits}f}"


def _compact(value: float) -> str:
    if value is None or pd.isna(value):
        return "-"
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.2f}M"
    return _num(value)


def _signed(value: float, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{value:+,.{digits}f}"


def _tone_color(tone: str) -> str:
    return TONE.get(tone, TONE["flat"])


@st.cache_data(ttl=CACHE_TTL_SEC, show_spinner="시장·수급·시그널 데이터를 가져오는 중...")
def load_snapshot() -> dict:
    return build_snapshot()


def metric_card(title: str, value: str, delta: str, note: str = "", tone: str = "flat") -> None:
    color = _tone_color(tone)
    st.markdown(
        f"""
        <div style="background:#161B22;border:1px solid #30363D;padding:14px 16px;min-height:118px;">
          <div style="color:#8B949E;font-size:12px;letter-spacing:0.04em;">{title}</div>
          <div style="font-size:26px;font-weight:600;margin:6px 0 2px 0;color:#E6EDF3;">{value}</div>
          <div style="color:{color};font-size:13px;">{delta}</div>
          <div style="color:#8B949E;font-size:12px;margin-top:4px;">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(label: str, tone: str) -> str:
    color = _tone_color(tone)
    return (
        f'<span style="display:inline-block;min-width:52px;text-align:center;'
        f'padding:2px 8px;border:1px solid {color};color:{color};font-size:12px;">{label}</span>'
    )


def price_ma_chart(history: pd.DataFrame, name: str) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.55, 0.22, 0.23],
        subplot_titles=(f"{name} 가격·이동평균", "RSI / Stochastic", "거래량"),
    )
    fig.add_trace(
        go.Scatter(x=history.index, y=history["Close"], name="종가", line=dict(color="#E6EDF3", width=1.6)),
        row=1,
        col=1,
    )
    for ma, color in (("MA20", "#C9A227"), ("MA60", "#58A6FF"), ("MA120", "#A371F7")):
        if ma in history.columns:
            fig.add_trace(
                go.Scatter(x=history.index, y=history[ma], name=ma, line=dict(color=color, width=1)),
                row=1,
                col=1,
            )
    fig.add_trace(
        go.Scatter(x=history.index, y=history["RSI"], name="RSI", line=dict(color="#C9A227", width=1.2)),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=history.index, y=history["%K"], name="%K", line=dict(color="#58A6FF", width=1)),
        row=2,
        col=1,
    )
    fig.add_hline(y=70, line_dash="dot", line_color="#8B949E", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#8B949E", row=2, col=1)
    colors = ["#3FB950" if v >= 0 else "#F85149" for v in history["RET_1D"].fillna(0)]
    fig.add_trace(
        go.Bar(x=history.index, y=history["Volume"], name="거래량", marker_color=colors, opacity=0.75),
        row=3,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        height=720,
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=40, r=20, t=50, b=30),
    )
    fig.update_yaxes(title_text="지수", row=1, col=1)
    fig.update_yaxes(title_text="RSI / %K", row=2, col=1, range=[0, 100])
    fig.update_yaxes(title_text="거래량", row=3, col=1)
    fig.update_xaxes(title_text="날짜", row=3, col=1)
    return fig


def flow_chart(series: pd.Series, title: str, unit: str) -> go.Figure:
    colors = ["#3FB950" if v >= 0 else "#F85149" for v in series.fillna(0)]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=series.index, y=series.values, marker_color=colors, name=f"일별 ({unit})"))
    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.cumsum(),
            name=f"누적 ({unit})",
            yaxis="y2",
            line=dict(color="#C9A227", width=1.6),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=320,
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        title=title,
        yaxis=dict(title=f"일별 ({unit})"),
        yaxis2=dict(title=f"누적 ({unit})", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=40, r=40, t=60, b=30),
    )
    fig.update_xaxes(title_text="날짜")
    return fig


def main() -> None:
    st.markdown(
        """
        <style>
          .block-container {padding-top: 1.2rem; max-width: 1400px;}
          h1, h2, h3 {font-weight: 600;}
          div[data-testid="stTable"] table {font-size: 13px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.title("MQIS")
        st.caption("Market Quant Investment System · 시장 스냅샷과 미국·한국 주요 지수 퀀트 시그널")
    with top_r:
        if st.button("데이터 새로고침", use_container_width=True):
            load_snapshot.clear()
            st.rerun()

    snap = load_snapshot()
    st.caption(
        f"생성 {snap['generated_at']}  ·  미국 종가 {snap['asof']['us']}  ·  한국 종가 {snap['asof']['kr']}  ·  5분 캐시"
    )

    st.header("1. 시장")
    st.subheader("1) 미국시장")
    us_cols = st.columns(3)
    for col, row in zip(us_cols, snap["market"]["us"]):
        tone = "up" if row["chg_1d"] > 0 else "down" if row["chg_1d"] < 0 else "flat"
        with col:
            metric_card(
                row["name"],
                _num(row["close"]),
                f"1D {_pct(row['chg_1d'])}  ·  5D {_pct(row['chg_5d'])}",
                row["asof"],
                tone,
            )

    st.subheader("2) 거시")
    macro_by_key = {row["key"]: row for row in snap["market"]["macro"]}
    for group_name, keys in MACRO_GROUPS:
        rows = [macro_by_key[k] for k in keys if k in macro_by_key]
        if not rows:
            st.caption(f"{group_name}: 데이터 없음")
            continue
        st.markdown(f"**{group_name}**")
        n = min(4, len(rows))
        cols = st.columns(n)
        for i, row in enumerate(rows):
            tone = "up" if row["chg_1d"] > 0 else "down" if row["chg_1d"] < 0 else "flat"
            if row["key"] in INVERT_TONE_KEYS:
                tone = "down" if row["chg_1d"] > 0 else "up" if row["chg_1d"] < 0 else "flat"
            with cols[i % n]:
                if row.get("freq") == "M":
                    delta = f"MoM {_pct(row['chg_1d'])}"
                else:
                    delta = f"1D {_pct(row['chg_1d'])}  ·  5D {_pct(row['chg_5d'])}"
                note = row["note"]
                if row.get("source"):
                    note = f"{note} · {row['source']}"
                metric_card(
                    row["name"],
                    f"{_num(row['close'])} {row['unit']}",
                    delta,
                    note,
                    tone,
                )

    st.subheader("3) 한국 수급")
    kr_cols = st.columns(3)
    labels = [
        ("외국인_현물", "외국인 현물"),
        ("외국인_선물", "외국인 선물"),
        ("기관", "기관수급"),
    ]
    for col, (key, title) in zip(kr_cols, labels):
        block = snap["market"]["korea"].get(key)
        with col:
            if not block:
                metric_card(title, "데이터 없음", "-", "KRX 응답 없음")
                continue
            metric_card(
                f"{title} ({block['unit']})",
                _signed(block["d1"], 0),
                f"5D {_signed(block['d5'], 0)}  ·  20D {_signed(block['d20'], 0)}",
                block["asof"],
                block["tone"],
            )

    flow_tabs = []
    for key, title in labels:
        block = snap["market"]["korea"].get(key)
        if block and "series" in block and not block["series"].empty:
            flow_tabs.append((title, block))
    if flow_tabs:
        tabs = st.tabs([name for name, _ in flow_tabs])
        for tab, (title, block) in zip(tabs, flow_tabs):
            with tab:
                st.plotly_chart(
                    flow_chart(block["series"], f"{title} 일별·누적", block["unit"]),
                    use_container_width=True,
                )

    st.header("2. 퀀트시그널")
    st.caption("미국: S&P500 / Nasdaq100 / SOX  ·  한국: KOSPI / KOSDAQ / KOSPI200  ·  상대강도는 KOSPI 대비")

    st.subheader("4) 추세 — 이평 이격도")
    st.caption("이격도 = (종가 ÷ 이동평균) × 100  ·  100이면 이평과 일치, 100 초과면 이평 위")
    ma_rows = []
    for row in snap["quant"]:
        ma = row["ma"]
        ma_rows.append(
            {
                "권역": row["region"],
                "지수": row["name"],
                "종가": _num(ma["close"]),
                "20MA": _num(ma["ma20"]),
                "이격도(20)": _num(ma["이격도20"]),
                "60MA": _num(ma["ma60"]),
                "이격도(60)": _num(ma["이격도60"]),
                "120MA": _num(ma["ma120"]),
                "이격도(120)": _num(ma["이격도120"]),
                "배열": ma["배열"],
            }
        )
    st.dataframe(pd.DataFrame(ma_rows), use_container_width=True, hide_index=True)

    st.subheader("5) 모멘텀 — DMI / ADX / Force Index")
    mom_rows = []
    for row in snap["quant"]:
        m = row["metrics"]
        mom_rows.append(
            {
                "지수": row["name"],
                "+DI": _num(m["+DI"]),
                "-DI": _num(m["-DI"]),
                "ADX": _num(m["ADX"]),
                "Force Index": _compact(m["Force"]),
            }
        )
    st.dataframe(pd.DataFrame(mom_rows), use_container_width=True, hide_index=True)

    st.subheader("6) 변동성 — ATR / Bollinger Band Width")
    vol_rows = []
    for row in snap["quant"]:
        m = row["metrics"]
        vol_rows.append(
            {
                "지수": row["name"],
                "ATR": _num(m["ATR"]),
                "ATR%": _num(m["ATR%"]),
                "BB Width": _num(m["BBW"], 4),
                "BBW 백분위": _num(m["BBW_PCTILE"]),
            }
        )
    st.dataframe(pd.DataFrame(vol_rows), use_container_width=True, hide_index=True)

    st.subheader("7) 과열 — RSI / Stochastic")
    hot_rows = []
    for row in snap["quant"]:
        m = row["metrics"]
        hot_rows.append(
            {
                "지수": row["name"],
                "RSI": _num(m["RSI"]),
                "%K": _num(m["%K"]),
                "%D": _num(m["%D"]),
            }
        )
    st.dataframe(pd.DataFrame(hot_rows), use_container_width=True, hide_index=True)

    st.subheader("8) 수급 — 거래량 / OBV")
    flow_rows = []
    for row in snap["quant"]:
        m = row["metrics"]
        flow_rows.append(
            {
                "지수": row["name"],
                "거래량/20MA": _num(m["VOL_RATIO"]),
                "OBV": _compact(m["OBV"]),
                "OBV 20MA": _compact(m["OBV_MA20"]),
            }
        )
    st.dataframe(pd.DataFrame(flow_rows), use_container_width=True, hide_index=True)

    st.subheader("9) 상대강도 — KOSPI 대비")
    rs_rows = []
    for row in snap["quant"]:
        m = row["metrics"]
        rs_rows.append(
            {
                "지수": row["name"],
                "RS": _num(m["RS"]),
                "RS 20MA": _num(m["RS_MA"]) if m["RS_MA"] is not None and not pd.isna(m["RS_MA"]) else "-",
            }
        )
    st.dataframe(pd.DataFrame(rs_rows), use_container_width=True, hide_index=True)

    st.subheader("시그널 스코어보드")
    table_rows = []
    for row in snap["quant"]:
        b = row["blocks"]
        table_rows.append(
            {
                "권역": row["region"],
                "지수": row["name"],
                "종가": _num(row["close"]),
                "1D": _pct(row["chg_1d"]),
                "4) 추세": b["추세"]["label"],
                "5) 모멘텀": b["모멘텀"]["label"],
                "6) 변동성": b["변동성"]["label"],
                "7) 과열": b["과열"]["label"],
                "8) 수급": b["수급"]["label"],
                "9) vs KOSPI": b["상대강도"]["label"],
                "종합": f"{row['composite']['label']} ({row['composite']['score']:+.0f})",
            }
        )
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

    names = [row["name"] for row in snap["quant"]]
    selected = st.selectbox("지수 상세", names, index=0)
    detail = next(row for row in snap["quant"] if row["name"] == selected)

    score_col, *block_cols = st.columns([1.2, 1, 1, 1, 1, 1, 1])
    with score_col:
        metric_card(
            "종합 스코어",
            f"{detail['composite']['score']:+.0f}",
            detail["composite"]["label"],
            f"{detail['name']}  ·  {detail['asof']}",
            detail["composite"]["tone"],
        )
    titles = ["4) 추세", "5) 모멘텀", "6) 변동성", "7) 과열", "8) 수급", "9) 상대강도"]
    keys = ["추세", "모멘텀", "변동성", "과열", "수급", "상대강도"]
    for col, title, key in zip(block_cols, titles, keys):
        block = detail["blocks"][key]
        with col:
            metric_card(title, block["label"], "", "", block["tone"])

    left, right = st.columns([1.15, 0.85])
    with left:
        hist = detail["history"].tail(260)
        st.plotly_chart(price_ma_chart(hist, detail["name"]), use_container_width=True)
    with right:
        st.subheader("지표 값")
        for key, title in zip(keys, titles):
            block = detail["blocks"][key]
            st.markdown(f"**{title}**  {badge(block['label'], block['tone'])}", unsafe_allow_html=True)
            vals = []
            for name, value in block["values"].items():
                if isinstance(value, str):
                    shown = value
                elif name in {"Force Index", "OBV", "OBV 20MA"}:
                    shown = _compact(value)
                elif name in {"거래량/20MA", "ATR%", "BB Width", "BBW 백분위"}:
                    shown = _num(value, 4) if name == "BB Width" else _num(value)
                else:
                    shown = _num(value)
                vals.append({"항목": name, "값": shown})
            st.table(pd.DataFrame(vals))

    st.caption(
        "미국·거시 가격: Yahoo Finance  ·  한국 지수: 네이버 금융  ·  "
        "현물/기관 수급: 네이버 투자자별 매매동향(KOSPI+KOSDAQ, 억원)  ·  "
        "외국인 선물: 네이버 일자별 순매수(계약)  ·  "
        "거래량이 없는 지수는 ETF 거래량으로 대체 (SPY/QQQ/SOXX)  ·  "
        "2년물: CBOE 2YY (실패 시 FRED DGS2)  ·  "
        "BDI: FRED 미수록 → Stooq → CNBC/Investing  ·  "
        "철광석: FRED PIORECRUSDM → Stooq → Investing/SGX TIO  ·  "
        "LNG: FRED Europe PNGASEUUSDM → Investing/ICE TTF"
    )


if __name__ == "__main__":
    main()
