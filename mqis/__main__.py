from __future__ import annotations

import sys

from mqis import __version__
from mqis.pipeline import build_sector_snapshot, build_snapshot
from mqis.sectors import SECTORS


def _pct(value: float) -> str:
    if value is None or value != value:
        return "-"
    return f"{value:+.2%}"


def _num(value: float, digits: int = 2) -> str:
    if value is None or value != value:
        return "-"
    return f"{value:,.{digits}f}"


def _compact(value: float) -> str:
    if value is None or value != value:
        return "-"
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.2f}M"
    return _num(value)


def _억원(value: float) -> str:
    if value is None or value != value:
        return "-"
    return f"{value / 1e8:,.1f}"


def _print_sectors() -> None:
    snap = build_sector_snapshot()
    print(
        f"MQIS v{__version__}  섹터분석  {snap['generated_at']}  종가 {snap['asof']}  {snap['count']}종"
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
                f"이격 {_num(row['이격도20'])}/{_num(row['이격도60'])}/{_num(row['이격도120'])}"
            )
        print()


def main() -> None:
    if "--sectors" in sys.argv:
        _print_sectors()
        return
    snap = build_snapshot()
    print(f"MQIS v{__version__} (Market Quant Investment System)  {snap['generated_at']}")
    print(f"미국 종가 {snap['asof']['us']}  |  한국 종가 {snap['asof']['kr']}")
    print()
    print("=== 1. 시장 ===")
    print("[미국]")
    for row in snap["market"]["us"]:
        print(f"  {row['name']:<12} {_num(row['close'])}  1D {_pct(row['chg_1d'])}  5D {_pct(row['chg_5d'])}")
    print("[거시]")
    for row in snap["market"]["macro"]:
        period = "MoM" if row.get("freq") == "M" else "1D"
        src = f"  [{row['source']}]" if row.get("source") else ""
        print(
            f"  {row['name']:<12} {_num(row['close'])}{row['unit']}  "
            f"{period} {_pct(row['chg_1d'])}  {row['note']}{src}"
        )
    print("[한국 수급]")
    for key in ("외국인_현물", "외국인_선물", "기관"):
        block = snap["market"]["korea"].get(key)
        if not block:
            print(f"  {key:<12} 데이터 없음")
            continue
        print(
            f"  {block['name']:<12} 1D {_num(block['d1'])}  5D {_num(block['d5'])}  "
            f"20D {_num(block['d20'])} {block['unit']}"
        )

    print()
    print("=== 2. 퀀트시그널 ===")
    print("[4) 추세] 이격도=(종가/이평)*100")
    print(
        f"{'지수':<10} {'종가':>10} {'20MA':>10} {'이격도20':>8} "
        f"{'60MA':>10} {'이격도60':>8} {'120MA':>10} {'이격도120':>8} {'배열':>6}"
    )
    for row in snap["quant"]:
        ma = row["ma"]
        print(
            f"{row['name']:<10} {_num(ma['close']):>10} {_num(ma['ma20']):>10} {_num(ma['이격도20']):>8} "
            f"{_num(ma['ma60']):>10} {_num(ma['이격도60']):>8} "
            f"{_num(ma['ma120']):>10} {_num(ma['이격도120']):>8} {ma['배열']:>6}"
        )

    print()
    print("[5) 모멘텀] DMI / ADX / Force Index")
    print(f"{'지수':<10} {'+DI':>8} {'-DI':>8} {'ADX':>8} {'Force':>10}")
    for row in snap["quant"]:
        m = row["metrics"]
        print(
            f"{row['name']:<10} {_num(m['+DI']):>8} {_num(m['-DI']):>8} "
            f"{_num(m['ADX']):>8} {_compact(m['Force']):>10}"
        )

    print()
    print("[6) 변동성] ATR / Bollinger Band Width")
    print(f"{'지수':<10} {'ATR':>10} {'ATR%':>8} {'BBW':>8} {'BBW%ile':>8}")
    for row in snap["quant"]:
        m = row["metrics"]
        print(
            f"{row['name']:<10} {_num(m['ATR']):>10} {_num(m['ATR%']):>8} "
            f"{_num(m['BBW'], 4):>8} {_num(m['BBW_PCTILE']):>8}"
        )

    print()
    print("[7) 과열] RSI / Stochastic")
    print(f"{'지수':<10} {'RSI':>8} {'%K':>8} {'%D':>8}")
    for row in snap["quant"]:
        m = row["metrics"]
        print(f"{row['name']:<10} {_num(m['RSI']):>8} {_num(m['%K']):>8} {_num(m['%D']):>8}")

    print()
    print("[8) 수급] 거래량 / OBV")
    print(f"{'지수':<10} {'Vol/20':>8} {'OBV':>10} {'OBV20':>10}")
    for row in snap["quant"]:
        m = row["metrics"]
        print(
            f"{row['name']:<10} {_num(m['VOL_RATIO']):>8} "
            f"{_compact(m['OBV']):>10} {_compact(m['OBV_MA20']):>10}"
        )

    print()
    print("[9) 상대강도] KOSPI 대비 RS")
    print(f"{'지수':<10} {'RS':>8} {'RS 20MA':>8}")
    for row in snap["quant"]:
        m = row["metrics"]
        print(f"{row['name']:<10} {_num(m['RS']):>8} {_num(m['RS_MA']):>8}")

    print()
    print("[스코어보드]")
    header = f"{'지수':<10} {'종가':>10} {'1D':>8} {'추세':>6} {'모멘텀':>6} {'변동성':>6} {'과열':>6} {'수급':>6} {'vsKOSPI':>8} {'종합':>8}"
    print(header)
    for row in snap["quant"]:
        b = row["blocks"]
        print(
            f"{row['name']:<10} {_num(row['close']):>10} {_pct(row['chg_1d']):>8} "
            f"{b['추세']['label']:>6} {b['모멘텀']['label']:>6} {b['변동성']['label']:>6} "
            f"{b['과열']['label']:>6} {b['수급']['label']:>6} {b['상대강도']['label']:>8} "
            f"{row['composite']['label']:>8} ({row['composite']['score']:+.0f})"
        )


if __name__ == "__main__":
    main()
