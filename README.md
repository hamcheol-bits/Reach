# Reach - 한국 금융 데이터 수집 API 🚀

한국(KOSPI, KOSDAQ) 주식 시장의 금융 데이터를 수집하는 FastAPI 기반 서비스입니다.

## 주요 기능

✨ **포괄적인 한국 시장 커버리지**
- KOSPI (~900개 종목)
- KOSDAQ (~1,500개 종목)

⚡ **다양한 데이터 수집**
- **주식 정보**: 종목 코드, 이름, 시장, 섹터 (pykrx)
- **주가 데이터**: OHLCV (Open, High, Low, Close, Volume)
- **시장 데이터**: 시가총액, 거래대금, 상장주식수
- **재무제표**: 손익계산서, 재무상태표, 현금흐름표 (DART API)
- **재무비율**: ROE, ROA, PER, PBR, PSR 등 자동 계산

🤖 **효율적인 데이터 관리**
- **증분 업데이트**: 마지막 수집일 이후 데이터만 업데이트
- **배치 처리**: 전체 시장 데이터 일괄 수집
- **자동 계산**: 재무제표 기반 재무비율 자동 계산
- **품질 검증**: 데이터 완성도 및 이상치 자동 탐지

📊 **RESTful API**
- Swagger UI 자동 생성 (`/docs`)
- 직관적인 엔드포인트 설계
- 실시간 통계 조회

## 기술 스택

| 카테고리 | 기술 |
|---------|------|
| **Backend** | FastAPI, Python 3.11+ |
| **Database** | MySQL 8.0, SQLAlchemy ORM |
| **Data Sources** | pykrx, FinanceDataReader, DART API |
| **Deployment** | Docker, Docker Compose |

## 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/hamcheol-bits/Reach.git
cd Reach

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
DATABASE_URL=....

# DART API Key (재무제표 수집용)
DART_API_KEY=your_dart_api_key

# Application
APP_NAME=Reach
APP_VERSION=0.2.0
APP_HOST=0.0.0.0
APP_PORT=8001
```

**DART API 키 발급:**
- https://opendart.fss.or.kr/ 회원가입 후 API 키 신청

### 3. 데이터베이스 설정 (Docker)

```bash
# Docker Compose로 MySQL 시작
docker-compose up -d mysql

# 데이터베이스 초기화 확인
docker exec -it valyria-mysql mysql -u finuser -p
```

### 4. 서버 실행

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

### 1️⃣ 주식 리스트 수집

```bash
# KOSPI 전체 종목 리스트 수집
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSPI"

# KOSDAQ 전체 종목 리스트 수집
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSDAQ"
```

### 2️⃣ 배치 수집 (주가 + 시장 데이터)

```bash
# KOSPI 전체 수집 (증분 모드)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true"

# KOSDAQ 전체 수집 (약 40분)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSDAQ?incremental=true"

# 테스트 (10개만)
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true&max_stocks=10"
```

### 3️⃣ 재무제표 수집

```bash
# 삼성전자 2023년 연간 재무제표
curl -X POST "http://localhost:8001/api/v1/financial/collect/005930?year=2023"

# 삼성전자 2023년 1분기
curl -X POST "http://localhost:8001/api/v1/financial/collect/005930?year=2023&quarter=1"

# 여러 연도 수집 (2020~2023, 연간만)
curl -X POST "http://localhost:8001/api/v1/financial/collect/005930/multiple-years?start_year=2020&end_year=2023"

# 여러 연도 수집 (연간 + 분기)
curl -X POST "http://localhost:8001/api/v1/financial/collect/005930/multiple-years?start_year=2023&end_year=2023&include_quarters=true"
```

### 4️⃣ 재무제표 배치 수집

```bash
# 전체 종목 2023~2025년 연간 재무제표
curl -X POST "http://localhost:8001/api/v1/financial/batch/collect-all?start_year=2023&end_year=2025"

# 전체 종목 연간 + 분기 (시간 오래 걸림!)
curl -X POST "http://localhost:8001/api/v1/financial/batch/collect-all?start_year=2023&end_year=2025&include_quarters=true"

# 증분 수집 (누락분만)
curl -X POST "http://localhost:8001/api/v1/financial/batch/collect-all?start_year=2023&end_year=2025&incremental=true"

# 테스트 (10개만)
curl -X POST "http://localhost:8001/api/v1/financial/batch/collect-all?limit=10&start_year=2025&end_year=2025"
```

### 5️⃣ 재무비율 계산

```bash
# 삼성전자 재무비율 계산
curl -X POST "http://localhost:8001/api/v1/financial/ratios/calculate/005930"

# 전체 종목 재무비율 계산
curl -X POST "http://localhost:8001/api/v1/financial/ratios/batch-calculate"

# 테스트 (10개만)
curl -X POST "http://localhost:8001/api/v1/financial/ratios/batch-calculate?limit=10"

# KOSPI만 계산
curl -X POST "http://localhost:8001/api/v1/financial/ratios/batch-calculate?market=KOSPI"
```

### 6️⃣ 데이터 품질 확인

```bash
# 품질 요약
curl "http://localhost:8001/api/v1/data-quality/summary"

# 전체 품질 리포트
curl "http://localhost:8001/api/v1/data-quality/report"

# 데이터 완성도
curl "http://localhost:8001/api/v1/data-quality/completeness"

# 이상치 탐지
curl "http://localhost:8001/api/v1/data-quality/anomalies?limit=100"

# 누락 데이터
curl "http://localhost:8001/api/v1/data-quality/missing?limit=50"
```

### 7️⃣ 통계 조회

```bash
# 전체 통계
curl "http://localhost:8001/api/v1/batch/stats"

# 재무제표 통계
curl "http://localhost:8001/api/v1/financial/stats"

# 재무비율 통계
curl "http://localhost:8001/api/v1/financial/ratios/stats"
```

### 8️⃣ 데이터 조회

```bash
# 주식 목록 조회
curl "http://localhost:8001/api/v1/stocks?country=KR&market=KOSPI&limit=10"

# 특정 종목 정보
curl "http://localhost:8001/api/v1/stocks/005930"

# 주가 데이터 조회
curl "http://localhost:8001/api/v1/stocks/005930/prices?limit=30"

# 재무비율 조회
curl "http://localhost:8001/api/v1/financial/ratios/005930?limit=10"
```

## API 엔드포인트

### 📊 주식 (Stocks)
- `GET /api/v1/stocks` - 주식 목록 조회
- `GET /api/v1/stocks/{ticker}` - 특정 주식 정보
- `GET /api/v1/stocks/{ticker}/prices` - 주가 데이터 조회

### 🇰🇷 한국 시장 (Korea Market)
- `POST /api/v1/korea/collect/stocks` - 종목 리스트 수집
- `POST /api/v1/korea/collect/prices/{ticker}` - 개별 종목 주가 수집
- `POST /api/v1/korea/collect/market-data` - 시장 데이터 수집
- `GET /api/v1/korea/stocks/preview` - 종목 미리보기

### 🔄 배치 수집 (Batch Collection)
- `POST /api/v1/batch/collect/korea/{market}` - 시장별 배치 수집
- `POST /api/v1/batch/collect/all` - 전체 시장 배치 수집
- `GET /api/v1/batch/stats` - 수집 통계

### 📈 재무제표 (Financial Statements)
- `POST /api/v1/financial/collect/{ticker}` - 개별 종목 재무제표 수집
- `POST /api/v1/financial/collect/{ticker}/multiple-years` - 여러 연도 수집
- `POST /api/v1/financial/batch/collect-all` - 전체 종목 배치 수집
- `GET /api/v1/financial/stats` - 재무제표 통계

### 📊 재무비율 (Financial Ratios)
- `POST /api/v1/financial/ratios/calculate/{ticker}` - 개별 종목 비율 계산
- `POST /api/v1/financial/ratios/batch-calculate` - 전체 배치 계산
- `GET /api/v1/financial/ratios/{ticker}` - 비율 조회
- `GET /api/v1/financial/ratios/stats` - 비율 통계

### 🔍 데이터 품질 (Data Quality)
- `GET /api/v1/data-quality/summary` - 품질 요약
- `GET /api/v1/data-quality/report` - 전체 리포트
- `GET /api/v1/data-quality/completeness` - 완성도 체크
- `GET /api/v1/data-quality/anomalies` - 이상치 탐지
- `GET /api/v1/data-quality/missing` - 누락 데이터

### 🛠️ 디버깅 (Debugging)
- `GET /api/v1/pykrx/market-data` - pykrx 직접 조회
- `GET /api/v1/pykrx/check-trading-day` - 거래일 확인

전체 API 문서: http://localhost:8001/docs

## 프로젝트 구조

```
reach/
├── app/
│   ├── main.py                 # FastAPI 앱
│   ├── config.py               # 설정
│   ├── models/                 # DB 모델
│   │   ├── stock.py           # 주식
│   │   ├── price.py           # 주가
│   │   ├── market_data.py     # 시장 데이터
│   │   └── financial.py       # 재무제표, 재무비율
│   ├── schemas/                # Pydantic 스키마
│   ├── routers/                # API 라우터
│   │   ├── stock.py           # 주식 조회
│   │   ├── korea.py           # 한국 시장
│   │   ├── batch.py           # 배치 수집
│   │   ├── financial.py       # 재무제표/비율
│   │   ├── data_quality.py    # 데이터 품질
│   │   └── pykrx_debug.py     # 디버깅
│   ├── services/               # 비즈니스 로직
│   │   ├── korea_market.py    # 한국 시장 수집
│   │   ├── batch_collector.py # 배치 수집
│   │   ├── dart_api.py        # 재무제표 수집
│   │   ├── financial_batch.py # 재무제표 배치
│   │   ├── financial_ratio_calculator.py  # 재무비율 계산
│   │   └── data_quality_checker.py  # 품질 검증
│   └── database/               # DB 연결
├── test/                       # 테스트/마이그레이션 스크립트
├── .env                        # 환경 변수
├── requirements.txt            # 의존성
└── README.md
```

## 데이터 소스

| 데이터 | 소스 | 용도 |
|--------|------|------|
| 종목 리스트 | pykrx | 주식 정보, 섹터 |
| 주가 데이터 | pykrx | OHLCV |
| 시장 데이터 | pykrx | 시가총액, 거래대금, 상장주식수 |
| 재무제표 | DART API | 손익계산서, 재무상태표, 현금흐름표 |
| 재무비율 | 자체 계산 | ROE, ROA, PER, PBR, PSR 등 |

## 계산되는 재무비율

### 수익성 지표
- **ROE** (자기자본이익률) = 당기순이익 / 자본총계 × 100
- **ROA** (총자산이익률) = 당기순이익 / 자산총계 × 100
- **영업이익률** = 영업이익 / 매출액 × 100
- **순이익률** = 당기순이익 / 매출액 × 100

### 안정성 지표
- **부채비율** = 부채총계 / 자본총계 × 100

### 밸류에이션 지표
- **PER** (주가수익비율) = 시가총액 / 당기순이익
- **PBR** (주가순자산비율) = 시가총액 / 자본총계
- **PSR** (주가매출비율) = 시가총액 / 매출액

## 권장 워크플로우

### Phase 1: 초기 설정 (첫날)

```bash
# 1. 종목 리스트 수집
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSPI"
curl -X POST "http://localhost:8001/api/v1/korea/collect/stocks?market=KOSDAQ"

# 2. 소규모 테스트
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true&max_stocks=10"
```

### Phase 2: 본격 수집 (야간/주말)

```bash
# 3. 전체 주가/시장 데이터 수집
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true"
curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSDAQ?incremental=true"

# 4. 재무제표 수집
curl -X POST "http://localhost:8001/api/v1/financial/batch/collect-all?start_year=2023&end_year=2025"

# 5. 재무비율 계산
curl -X POST "http://localhost:8001/api/v1/financial/ratios/batch-calculate"
```

### Phase 3: 품질 확인

```bash
# 6. 데이터 품질 확인
curl "http://localhost:8001/api/v1/data-quality/summary"
curl "http://localhost:8001/api/v1/batch/stats"
```

## 개발 가이드

### 코드 포맷팅

```bash
black app/
isort app/
```

### DB 마이그레이션

```bash
# fiscal_date, report_type 추가
python test/migrate_add_fiscal_fields.py

# date 컬럼 제거
python test/fix_date_column.py

# unique key 수정
python test/fix_unique_key.py
```

## 로드맵

### ✅ 완료
- [x] 한국 시장 데이터 수집 (KOSPI, KOSDAQ)
- [x] 주가 데이터 수집
- [x] 시장 데이터 수집 (시가총액, 거래대금)
- [x] 재무제표 데이터 수집 (DART API)
- [x] 재무비율 자동 계산
- [x] 배치 수집 API
- [x] 증분 업데이트 기능
- [x] 데이터 품질 검증

### 🔜 예정
- [ ] ChromaDB 벡터 저장소 연동
- [ ] RAG 파이프라인 구축 (Stormlands)
- [ ] React 프론트엔드 (Westerlands)
- [ ] 로깅 시스템 강화
- [ ] API 인증/인가

### 🔮 향후 계획
- [ ] LLM 기반 분석 (Ollama 연동)
- [ ] 종목 스크리닝 기능
- [ ] 포트폴리오 관리
- [ ] 실시간 알림

## 문제 해결

### Q: DART API 에러

**A:** API 키 확인
- `.env` 파일의 `DART_API_KEY` 확인
- https://opendart.fss.or.kr/ 에서 키 상태 확인

### Q: 재무비율이 NULL로 저장됨

**A:** 시가총액 데이터 확인
- PER, PBR, PSR은 시가총액이 필요합니다
- 시장 데이터 먼저 수집: `/api/v1/korea/collect/market-data`

### Q: 품질 점수가 낮음

**A:** 정상입니다
- 우선주, ETF 등 재무제표가 없는 종목이 많습니다
- 보통주만 필터링하거나 증분 수집을 활용하세요

## 기여

이슈나 Pull Request는 언제든 환영합니다!

## 라이센스

개인 프로젝트 (MIT License)

---

**Built with ❤️ for Korean Financial Data Analysis**