# Reach - 금융 데이터 수집 API

한국(KOSPI, KOSDAQ) 및 미국(S&P 500) 시장의 금융 데이터를 수집하는 FastAPI 기반 서비스입니다.

## 주요 기능

- **배치 데이터 수집**: 전체 시장 데이터 일괄 수집
- **증분 업데이트**: 마지막 수집일 이후 데이터만 효율적으로 업데이트
- **자동 스케줄링**: 정기적인 데이터 수집 작업 자동화
- 한국 주식 시장(KOSPI, KOSDAQ) 데이터 수집
- 미국 주식 시장(S&P 500) 데이터 수집
- 일별 주가 데이터 저장
- RESTful API 제공

## 기술 스택

- **FastAPI**: 고성능 웹 프레임워크
- **SQLAlchemy**: ORM
- **MySQL**: 데이터베이스
- **APScheduler**: 작업 스케줄링
- **FinanceDataReader**: 한국 시장 데이터
- **pykrx**: 한국 시장 데이터
- **Finnhub + Twelve Data**: 미국 시장 데이터

## 설치 및 실행

### 1. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 DATABASE_URL 등을 설정
```

### 4. 서버 실행

```bash
# 개발 모드 (자동 리로드)
python -m app.main

# 또는
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## API 엔드포인트

### Health Check

```bash
# 서비스 상태 확인
GET /health

# 데이터베이스 연결 확인
GET /health/db
```

### 주식 관리

```bash
# 주식 목록 조회
GET /api/v1/stocks?country=KR&market=KOSPI&skip=0&limit=100

# 특정 주식 조회
GET /api/v1/stocks/{ticker}
```

### 배치 수집 (신규)

```bash
# 한국 시장 배치 수집 (KOSPI 또는 KOSDAQ)
POST /api/v1/batch/collect/korea/{market}?incremental=true&max_stocks=10

# 미국 시장 배치 수집
POST /api/v1/batch/collect/us?incremental=true

# 전체 시장 배치 수집
POST /api/v1/batch/collect/all?incremental=true

# 수집 통계 조회
GET /api/v1/batch/stats
```

### 스케줄러 관리 (신규)

```bash
# 스케줄러 시작
POST /api/v1/scheduler/start?korea_schedule=0 18 * * 1-5

# 스케줄러 중지
POST /api/v1/scheduler/stop

# 스케줄러 상태 조회
GET /api/v1/scheduler/status

# 한국 시장 수집 즉시 실행
POST /api/v1/scheduler/run/korea

# 미국 시장 수집 즉시 실행
POST /api/v1/scheduler/run/us
```

### API 문서

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## 프로젝트 구조

```
reach/
├── app/
│   ├── main.py              # FastAPI 앱
│   ├── config.py            # 설정
│   ├── models/              # DB 모델
│   ├── schemas/             # Pydantic 스키마
│   ├── routers/             # API 라우터
│   │   ├── batch.py         # 배치 수집 API (신규)
│   │   ├── scheduler.py     # 스케줄러 관리 API (신규)
│   │   ├── korea.py         # 한국 시장 API
│   │   └── us.py            # 미국 시장 API
│   ├── services/            # 비즈니스 로직
│   │   ├── batch_collector.py   # 배치 수집 서비스 (신규)
│   │   ├── scheduler.py         # 스케줄러 서비스 (신규)
│   │   ├── korea_market.py      # 한국 시장 수집
│   │   └── us_market.py         # 미국 시장 수집
│   └── database/            # DB 연결
├── tests/                   # 테스트
├── requirements.txt
└── README.md
```

## 데이터 수집 예제

### 1. 테스트용 소규모 수집

```bash
# KOSPI 상위 10개 종목만 테스트 (증분)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true&max_stocks=10"

# 미국 S&P 500 샘플 종목 수집 (증분)
curl -X POST "http://localhost:8001/api/v1/batch/collect/us?incremental=true"
```

### 2. 전체 시장 배치 수집

```bash
# KOSPI 전체 종목 수집 (증분 업데이트)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true"

# KOSDAQ 전체 종목 수집 (증분 업데이트)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSDAQ?incremental=true"

# 전체 시장 수집 (한국 + 미국)
curl -X POST "http://localhost:8001/api/v1/batch/collect/all?incremental=true"
```

### 3. 스케줄러 사용

```bash
# 스케줄러 시작 (기본 스케줄: 한국 월-금 18시, 미국 월-금 10시)
curl -X POST "http://localhost:8001/api/v1/scheduler/start"

# 커스텀 스케줄로 시작 (매일 자정)
curl -X POST "http://localhost:8001/api/v1/scheduler/start?korea_schedule=0%200%20*%20*%20*&us_schedule=0%200%20*%20*%20*"

# 스케줄러 상태 확인
curl "http://localhost:8001/api/v1/scheduler/status"

# 한국 시장 즉시 수집 실행
curl -X POST "http://localhost:8001/api/v1/scheduler/run/korea"
```

### 4. Python 스크립트로 데이터 수집

```python
from app.database import SessionLocal
from app.services.batch_collector import BatchCollector

db = SessionLocal()
collector = BatchCollector()

# KOSPI 전체 수집 (증분)
result = collector.collect_korea_batch(
    db, 
    market="KOSPI", 
    incremental=True
)
print(f"Collected {result['stocks_success']} stocks")

# 미국 S&P 500 샘플 수집 (증분)
result = collector.collect_us_batch(
    db, 
    tickers=["AAPL", "MSFT", "GOOGL"],
    incremental=True
)
print(f"Collected {result['stocks_success']} stocks")

db.close()
```

### 5. 수집 통계 확인

```bash
# 현재 DB에 저장된 데이터 통계
curl "http://localhost:8001/api/v1/batch/stats"
```

### Python 스크립트로 데이터 수집 (기존 방식)

```python
from app.database import SessionLocal
from app.services import KoreaMarketCollector, USMarketCollector

db = SessionLocal()

# 한국 시장 종목 수집
kr_collector = KoreaMarketCollector()
count = kr_collector.save_stocks_to_db(db, market="KOSPI")
print(f"Saved {count} Korean stocks")

# 삼성전자 주가 수집
price_count = kr_collector.save_stock_prices_to_db(db, "005930")
print(f"Saved {price_count} price records")

# 미국 시장 종목 수집
us_collector = USMarketCollector()
results = us_collector.collect_sp500_sample(db)
print(f"US stocks: {results}")

db.close()
```

## 스케줄러 설정

스케줄러는 환경 변수 또는 `.env` 파일로 설정할 수 있습니다:

```env
# 스케줄러 자동 시작 여부
ENABLE_SCHEDULER=true

# 한국 시장 수집 스케줄 (cron 표현식)
# 기본값: "0 18 * * 1-5" (월-금 오후 6시)
KOREA_SCHEDULE=0 18 * * 1-5

# 미국 시장 수집 스케줄 (cron 표현식)
# 기본값: "0 10 * * 1-5" (월-금 오전 10시)
US_SCHEDULE=0 10 * * 1-5
```

**Cron 표현식 예시:**
- `0 18 * * 1-5`: 월-금 오후 6시
- `0 */4 * * *`: 매 4시간마다
- `0 0 * * *`: 매일 자정
- `30 9 * * 1-5`: 월-금 오전 9시 30분

## 증분 업데이트 동작 방식

1. **첫 수집**: 마지막 가격 데이터가 없으면 1년치 데이터 수집
2. **증분 수집**: 마지막 수집일 다음날부터 현재까지만 수집
3. **효율성**: 이미 수집된 데이터는 재수집하지 않아 시간/비용 절약

예시:
```
- 2024-01-01에 첫 수집 → 2023-01-01 ~ 2024-01-01 수집
- 2024-01-15에 증분 수집 → 2024-01-02 ~ 2024-01-15만 수집
- 2024-02-01에 증분 수집 → 2024-01-16 ~ 2024-02-01만 수집
```

## 개발 가이드

### 테스트 실행

```bash
pytest tests/
```

### 코드 포맷팅

```bash
black app/
isort app/
```

## 다음 단계

- [x] 배치 수집 API 구현
- [x] 증분 업데이트 기능
- [x] 스케줄러 추가 (일별 자동 수집)
- [ ] 재무제표 데이터 수집 구현
- [ ] 에러 핸들링 강화
- [ ] 로깅 시스템 구축 (파일 로그)
- [ ] API 인증/인가
- [ ] 데이터 검증 로직 추가
- [ ] NYSE 전체 종목 리스트 수집
- [ ] NASDAQ 전체 종목 리스트 수집
- [ ] ChromaDB 벡터 저장소 연동

## 라이센스

개인 프로젝트