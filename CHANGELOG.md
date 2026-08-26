# Changelog

MQIS (Market Quant Investment System) 변경 이력입니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/), 버전은 [SemVer](https://semver.org/lang/ko/)입니다.

## [Unreleased]

## [0.2.2] — 2026-08-26

### Changed

- 화면·메뉴 명칭: **섹터 퀀트** → **섹터분석**

### Added

- 섹터분석: 섹터 표에서 ETF 행을 선택하면 네이버 주요 구성종목과 종목별 분석표(수익률·대금·이격도) 표시

## [0.2.1] — 2026-08-18

### Added

- `gemini_web/sector_quant.py`: Gemini Web에서 붙여 넣어 실행하는 독립 섹터 퀀트 스크립트 (MQIS 패키지와 분리)

### Fixed

- **데이터 새로고침** 버튼을 사이드바로 옮겨 본문 상단에서 글자가 잘리던 문제 수정

### Changed

- README: 캐시·새로고침 동작과 사이드바 버튼 위치 안내 보강

## [0.2.0] — 2026-08-17

### Added

- 섹터 퀀트 화면: `mqis/data/etf_universe.txt`에 적은 한국 ETF만 사용
- 섹터: 반도체, AI인프라, 2차전지, 방산우주, 조선, 바이오헬스, 자동차, 로봇, 건설, 원자력, 에너지화학, 금융, IT서비스, 소비재, 기타
- 동일 종목명(운용사 접두어 제외)은 당일 거래대금이 큰 ETF만 유지
- 1·5·10일 수익률·거래대금(억원), 20/60/120 이격도, 섹터 단순평균
- CLI `python -m mqis --sectors`
- 화면 상단·사이드바·하단과 CLI에 `v{version}` 표시

### Changed

- 섹터 표 정렬: 수익률·거래대금을 숫자로 두어 크기순이 맞게 동작

## [0.1.0] — 2026-08-16

### Added

- Streamlit 대시보드와 `python -m mqis` CLI
- 미국 지수(S&P500, Nasdaq100, SOX)와 한국 지수(KOSPI, KOSDAQ, KOSPI200)
- 거시: 10Y/2Y, VIX, DXY, WTI, 천연가스, LNG(EU), 금, 구리, 철광석, BDI, Bitcoin
- 한국 외국인 현물·선물, 기관 수급
- 퀀트: 이격도, DMI/ADX/Force, ATR/BB Width, RSI/Stochastic, 거래량/OBV, vs KOSPI RS, 스코어보드
- BDI·철광석·LNG 소스 폴백 (FRED → Stooq → Investing 계열)
