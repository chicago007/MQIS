# MQIS (Market Quant Investment System)

미국·한국 지수, 거시 지표, 한국 수급, 퀀트 시그널, 한국 ETF 섹터 퀀트를 한 앱에서 보는 투자 대시보드입니다.

현재 버전: **0.2.1** (`mqis/__init__.py`의 `__version__`). 웹 화면 상단·사이드바·하단과 CLI에 같습니다.

## 실행

Python 3.11+ 권장.

```bash
git clone https://github.com/chicago007/MQIS.git
cd MQIS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 웹 대시보드
streamlit run app.py          # http://localhost:8501
# 왼쪽 메뉴: 시장·지수 / 섹터 퀀트

# 터미널 스냅샷
python -m mqis
python -m mqis --sectors      # 섹터 ETF
```

캐시 TTL은 5분입니다. **왼쪽 사이드바**의 **데이터 새로고침**을 누르면 캐시를 비우고 다시 수집합니다. 브라우저 새로고침(F5)만으로는 5분 이내 캐시가 그대로 쓰일 수 있습니다.

선택: FRED API를 쓰려면 `FRED_API_KEY`를 환경변수로 넣습니다.

## 구성

| 경로 | 역할 |
| --- | --- |
| `app.py` | Streamlit UI |
| `mqis/` | 수집·지표·시그널·섹터·파이프라인 |
| `mqis/data/etf_universe.txt` | 섹터 퀀트에 쓰는 ETF 목록 |
| `gemini_web/sector_quant.py` | Gemini Web 전용 독립 섹터 퀀트 (MQIS와 분리 실행) |
| `docs/` | 개발계획서, 버전관리, 아키텍처, 데이터소스 |

문서 목록은 [docs/README.md](docs/README.md)를 참고하세요.

저장소: [github.com/chicago007/MQIS](https://github.com/chicago007/MQIS)

## 범위 (0.2)

- 미국: S&P500, Nasdaq100, SOX
- 거시: 금리·달러, 에너지, 금속·원자재, Bitcoin
- 한국: KOSPI / KOSDAQ / KOSPI200, 외국인 현물·선물, 기관 수급
- 퀀트: 이격도, DMI/ADX/Force, ATR/BB Width, RSI/Stochastic, 거래량/OBV, vs KOSPI RS
- 섹터 ETF 퀀트: 지정 목록만, 동일 종목명은 거래대금 큰 쪽, 1·5·10일 수익률·대금·이격도

투자 자문이 아닙니다. 시세는 거래소·벤더 마감 시각 기준입니다.
