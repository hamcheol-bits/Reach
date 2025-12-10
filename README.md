# Reach - 금융 데이터 수집 API 🚀

한국(KOSPI, KOSDAQ) 및 미국(전체 US 시장) 금융 데이터를 수집하는 FastAPI 기반 서비스입니다.

## 주요 기능

✨ **포괄적인 시장 커버리지**
- 한국: KOSPI (~900개), KOSDAQ (~1,500개)
- 미국: NYSE, NASDAQ 등 전체 US 시장 (~8,000개 Common Stocks)

⚡ **효율적인 데이터 수집**
- **증분 업데이트**: 마지막 수집일 이후 데이터만 효율적으로 업데이트
- **Market 필터링**: 특정 거래소만 선택적으로 수집 가능
- **배치 처리**: 전체 시장 데이터 일괄 수집

✨ **포괄적인 데이터 수집**
- **주식 정보**: 종목 코드, 이름, 시장, 섹터 (pykrx)
- **주가 데이터**: OHLCV (Open, High, Low, Close, Volume)
- **시장 데이터**: 시가총액, 거래대금, 상장주식수

🤖 **자동화**
- APScheduler 기반 정기 자동 수집
- Cron 표현식으로 유연한 스케줄 설정
- 일별/시간별 자동 증분 업데이트

📊 **RESTful API**
- Swagger UI 자동 생성 (`/docs`)
- Request Body 기반 직관적인 API 설계
- 실시간 통계 조회

## 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **Backend** | FastAPI, Python 3.11+ |
| **Database** | MySQL 8.0, SQLAlchemy ORM |
| **Data Sources** | Finnhub, Twelve Data, pykrx, FinanceDataReader |
| **Scheduler** | APScheduler |
| **Deployment** | Docker, Docker Compose |

## 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yourusername/reach.git
cd reach

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```env
# Database
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/reach_db

# API Keys
FINNHUB_API_KEY=your_finnhub_api_key
TWELVEDATA_API_KEY=your_twelvedata_api_key

# Scheduler (선택)
ENABLE_SCHEDULER=false
KOREA_SCHEDULE=0 18 * * 1-5
US_SCHEDULE=0 10 * * 1-5
```

**무료 API 키 발급:**
- Finnhub: https://finnhub.io/register
- Twelve Data: https://twelvedata.com/pricing

### 3. 서버 실행

```bash
# 개발 모드
python -m app.main

# 또는 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

서버 시작 후 접속:
- API 문서: http://localhost:8001/docs
- Health Check: http://localhost:8001/health

## 사용 예시

### 1️⃣ 미국 주식 리스트 수집

```bash
# 전체 US 주식 리스트 수집 (약 5-10분)
curl -X POST "http://localhost:8001/api/v1/us/collect/all-stocks?filter_common=true"
```

### 2️⃣ 가격 데이터 수집 (소규모 테스트)

```bash
# 샘플 2개 종목 테스트
curl -X POST "http://localhost:8001/api/v1/batch/collect/us" \
  -H "Content-Type: application/json" \
  -d '{
    "tickers": ["AAPL", "MSFT"],
    "incremental": true
  }'
```

### 3️⃣ NYSE + NASDAQ만 수집 (권장)

```bash
# 주요 거래소만 선택적 수집
curl -X POST "http://localhost:8001/api/v1/batch/collect/us" \
  -H "Content-Type: application/json" \
  -d '{
    "collect_all": true,
    "markets": ["NYSE", "NASDAQ"],
    "incremental": true
  }'
```

**예상 소요 시간:**
- NYSE + NASDAQ: ~6,500개 → 약 14시간
- Twelve Data 제약: 8 requests/min

### 4️⃣ 한국 시장 수집

```bash
# KOSPI 전체 수집 (종목정보 + 시장데이터 + 주가)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true"

# KOSDAQ 전체 수집 (약 40분)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSDAQ?incremental=true"
```

### 5️⃣ 통계 확인

```bash
curl "http://localhost:8001/api/v1/batch/stats"
```

**응답 예시:**
```json
{
  "stocks": {
    "korea": {
      "kospi": 900,
      "kosdaq": 1500,
      "total": 2400
    },
    "us": {
      "by_market": {
        "NYSE": 3000,
        "NASDAQ": 3500
      },
      "total": 6500
    }
  },
  "prices": {
    "total_records": 50000,
    "stocks_with_prices": 100,
    "latest_date": "2024-12-09"
  }
}
```

### 6️⃣ 스케줄러 설정 (일일 자동 수집)

```bash
# 스케줄러 시작 (월-금 자동 수집)
curl -X POST "http://localhost:8001/api/v1/scheduler/start"

# 상태 확인
curl "http://localhost:8001/api/v1/scheduler/status"

# 즉시 실행
curl -X POST "http://localhost:8001/api/v1/scheduler/run/korea"
```

## API 엔드포인트

### 📊 주식 조회

```bash
# 주식 목록 조회
GET /api/v1/stocks?country=US&market=NYSE&limit=100

# 특정 주식 정보
GET /api/v1/stocks/{ticker}

# 주가 데이터 조회
GET /api/v1/stocks/{ticker}/prices?limit=100
```

### 🔄 배치 수집

```bash
# 한국 시장 배치 수집
POST /api/v1/batch/collect/korea/{market}

# 미국 시장 배치 수집 (Request Body)
POST /api/v1/batch/collect/us
Body: {
  "collect_all": true,
  "markets": ["NYSE", "NASDAQ"],
  "incremental": true
}

# 통계 조회
GET /api/v1/batch/stats
```

### ⏰ 스케줄러

```bash
# 스케줄러 시작/중지
POST /api/v1/scheduler/start
POST /api/v1/scheduler/stop

# 상태 조회
GET /api/v1/scheduler/status

# 즉시 실행
POST /api/v1/scheduler/run/korea
POST /api/v1/scheduler/run/us
```

전체 API 문서: http://localhost:8001/docs

## 프로젝트 구조

```
reach/
├── app/
│   ├── main.py                 # FastAPI 앱
│   ├── config.py               # 설정 (환경변수)
│   ├── models/                 # DB 모델
│   │   ├── stock.py           # 주식 정보
│   │   ├── price.py           # 주가 데이터
│   │   └── financial.py       # 재무제표 (예정)
│   ├── schemas/                # Pydantic 스키마
│   ├── routers/                # API 라우터
│   │   ├── stock.py           # 주식 조회 API
│   │   ├── batch.py           # 배치 수집 API ⭐
│   │   ├── scheduler.py       # 스케줄러 관리 ⭐
│   │   ├── korea.py           # 한국 시장 API
│   │   └── us.py              # 미국 시장 API
│   ├── services/               # 비즈니스 로직
│   │   ├── batch_collector.py # 배치 수집 서비스 ⭐
│   │   ├── scheduler.py       # 스케줄러 서비스 ⭐
│   │   ├── korea_market.py    # 한국 시장 수집
│   │   └── us_market.py       # 미국 시장 수집
│   └── database/               # DB 연결
├── test/                       # 테스트 스크립트
├── .env                        # 환경 변수
├── requirements.txt            # 의존성
└── README.md
```

## 데이터 소스

| 시장 | 데이터 소스 | 용도 |
|-----|-----------|-----|
| 🇰🇷 한국 | pykrx | 종목 리스트 |
| 🇰🇷 한국 | FinanceDataReader | 주가 데이터 |
| 🇺🇸 미국 | Finnhub | 종목 리스트 (~29,000개) |
| 🇺🇸 미국 | Twelve Data | 주가 데이터 |

### API 제약사항

**Finnhub (무료)**
- 60 requests/min
- Stock Symbols: 무제한

**Twelve Data (무료)**
- 8 requests/min ⚠️
- 일일 제한: 800 requests

## 증분 업데이트 동작 방식

```
Timeline:
─────────────────────────────────────────────
2024-01-01  첫 수집     → 2023-01-01 ~ 2024-01-01 (1년치)
2024-01-15  증분 수집   → 2024-01-02 ~ 2024-01-15 (14일치만)
2024-02-01  증분 수집   → 2024-01-16 ~ 2024-02-01 (17일치만)
```

**장점:**
- ✅ API 호출 수 대폭 감소
- ✅ 수집 시간 단축 (1년 → 며칠)
- ✅ 비용 절감

## 권장 워크플로우

### Phase 1: 초기 설정 (첫날)

```bash
# 1. 미국 주식 리스트 수집
curl -X POST "http://localhost:8001/api/v1/us/collect/all-stocks"

# 2. 한국 주식 리스트 수집
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSPI"
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSDAQ"

# 3. 소규모 테스트 (2개 종목)
curl -X POST "http://localhost:8001/api/v1/batch/collect/us" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["AAPL", "MSFT"], "incremental": true}'
```

### Phase 2: 본격 수집 (야간/주말)

```bash
# NYSE + NASDAQ 가격 데이터 수집 (약 14시간)
curl -X POST "http://localhost:8001/api/v1/batch/collect/us" \
  -H "Content-Type: application/json" \
  -d '{
    "collect_all": true,
    "markets": ["NYSE", "NASDAQ"],
    "incremental": true
  }'
```

### Phase 3: 자동화

```bash
# 스케줄러 활성화 (매일 자동 증분 업데이트)
curl -X POST "http://localhost:8001/api/v1/scheduler/start"
```

## 개발 가이드

### 테스트 실행

```bash
# 단위 테스트
pytest tests/

# 개별 API 테스트
python test/test_finnhub_auth.py
python test/test_pykrx.py
```

### 코드 포맷팅

```bash
black app/
isort app/
```

## 로드맵

### ✅ 완료
- [x] 한국 시장 데이터 수집 (KOSPI, KOSDAQ)
- [x] 미국 시장 데이터 수집 (전체 US)
- [x] 배치 수집 API
- [x] 증분 업데이트 기능
- [x] Market 필터링
- [x] 스케줄러 자동화
- [x] Request Body 기반 API

### 🔜 예정
- [ ] 재무제표 데이터 수집
- [ ] ChromaDB 벡터 저장소 연동
- [ ] RAG 파이프라인 구축
- [ ] 로깅 시스템 강화
- [ ] API 인증/인가
- [ ] 데이터 검증 로직

### 🔮 향후 계획
- [ ] LLM 기반 분석 (Ollama 연동)
- [ ] React 프론트엔드
- [ ] 실시간 알림
- [ ] 포트폴리오 관리

## 문제 해결

### Q: Finnhub 401 Unauthorized 에러

**A:** API 키 확인
```bash
# 테스트 스크립트 실행
python test/test_finnhub_auth.py
```

### Q: Twelve Data 속도 제한

**A:** 8 requests/min 제약으로 인해 대량 수집 시 시간이 오래 걸립니다.
- 권장: 야간/주말에 수집
- 또는: 유료 플랜 고려

### Q: 증분 업데이트가 안 됨

**A:** `incremental=true` 확인 및 DB에 기존 데이터 존재 확인
```bash
curl "http://localhost:8001/api/v1/stocks/{ticker}/prices?limit=1"
```

## 기여

이슈나 Pull Request는 언제든 환영합니다!

## 라이센스

개인 프로젝트 (MIT License)

## 연락처

문의사항이 있으시면 Issue를 등록해주세요.

---

**Built with ❤️ for Financial Data Analysis**