# Changelog

MQIS (Market Quant Investment System) 변경 이력입니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/), 버전은 [SemVer](https://semver.org/lang/ko/)입니다.

## [Unreleased]

## [0.1.0] — 2026-08-16

### Added

- Streamlit 대시보드와 `python -m mqis` CLI
- 미국 지수(S&P500, Nasdaq100, SOX)와 한국 지수(KOSPI, KOSDAQ, KOSPI200)
- 거시: 10Y/2Y, VIX, DXY, WTI, 천연가스, LNG(EU), 금, 구리, 철광석, BDI, Bitcoin
- 한국 외국인 현물·선물, 기관 수급
- 퀀트: 이격도, DMI/ADX/Force, ATR/BB Width, RSI/Stochastic, 거래량/OBV, vs KOSPI RS, 스코어보드
- BDI·철광석·LNG 소스 폴백 (FRED → Stooq → Investing 계열)
