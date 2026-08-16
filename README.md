# MQIS (Market Quant Investment System)

미국·한국 지수, 거시 지표, 한국 수급, 퀀트 시그널을 한 화면에 모으는 투자 대시보드입니다.

현재 버전: **0.1.0**

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

# 터미널 스냅샷
python -m mqis
```

캐시 TTL은 5분입니다. 화면에서 **데이터 새로고침**을 누르면 다시 수집합니다.

선택: FRED API를 쓰려면 `FRED_API_KEY`를 환경변수로 넣습니다.

## 구성

| 경로 | 역할 |
| --- | --- |
| `app.py` | Streamlit UI |
| `mqis/` | 수집·지표·시그널·파이프라인 |
| `docs/` | 개발계획서, 버전관리, 아키텍처, 데이터소스 |

문서 목록은 [docs/README.md](docs/README.md)를 참고하세요.

저장소: [github.com/chicago007/MQIS](https://github.com/chicago007/MQIS)

## 범위 (0.1)

- 미국: S&P500, Nasdaq100, SOX
- 거시: 금리·달러, 에너지, 금속·원자재, Bitcoin
- 한국: KOSPI / KOSDAQ / KOSPI200, 외국인 현물·선물, 기관 수급
- 퀀트: 이격도, DMI/ADX/Force, ATR/BB Width, RSI/Stochastic, 거래량/OBV, vs KOSPI RS

투자 자문이 아닙니다. 시세는 거래소·벤더 마감 시각 기준입니다.
