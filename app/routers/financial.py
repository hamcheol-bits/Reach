"""
재무제표 데이터 수집 API 라우터
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dart_api import DartApiService
from app.services.financial_ratio_calculator import FinancialRatioCalculator

router = APIRouter(prefix="/financial", tags=["financial-statements"])


@router.post("/collect/{ticker}")
async def collect_financial_statement(
        ticker: str,
        year: int = Query(..., description="사업연도 (예: 2023)"),
        quarter: Optional[int] = Query(None, description="분기 (1-3, None이면 연간)", ge=1, le=3),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 재무제표 수집 (DART API)

    - ticker: 종목코드 (예: 005930)
    - year: 사업연도 (예: 2023)
    - quarter: 분기 (1, 2, 3 또는 None)
        - None: 연간 (사업보고서)
        - 1: 1분기
        - 2: 반기 (2분기)
        - 3: 3분기

    **예시:**
    - 삼성전자 2023년 연간: `/api/v1/financial/collect/005930?year=2023`
    - 삼성전자 2023년 1분기: `/api/v1/financial/collect/005930?year=2023&quarter=1`
    """
    dart_service = DartApiService()

    try:
        success = dart_service.save_financial_to_db(db, ticker, year, quarter)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to collect financial data for {ticker}"
            )

        return {
            "status": "success",
            "ticker": ticker,
            "year": year,
            "quarter": quarter,
            "message": f"Successfully collected financial data"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting financial data: {str(e)}"
        )

@router.post("/collect/{ticker}/multiple-years")
async def collect_multiple_years(
        ticker: str,
        start_year: int = Query(..., description="시작 연도 (예: 2020)"),
        end_year: int = Query(..., description="종료 연도 (예: 2023)"),
        include_quarters: bool = Query(False, description="분기 재무제표도 수집"),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 여러 연도 재무제표 수집

    - ticker: 종목코드 (예: 005930)
    - start_year: 시작 연도
    - end_year: 종료 연도
    - include_quarters: 분기 재무제표도 수집 (True면 Q1, Q2, Q3 포함)

    **예시:**
    - 삼성전자 2020~2023 연간만: `/api/v1/financial/collect/005930/multiple-years?start_year=2020&end_year=2023`
    - 삼성전자 2023년 연간+분기: `/api/v1/financial/collect/005930/multiple-years?start_year=2023&end_year=2023&include_quarters=true`

    **주의:**
    - 여러 연도 수집은 시간이 걸립니다 (1년당 약 1-2초)
    - 분기 포함 시 4배 시간 소요 (연간 1개 + 분기 3개)
    """
    if start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year must be less than or equal to end_year"
        )

    if end_year - start_year > 10:
        raise HTTPException(
            status_code=400,
            detail="Cannot collect more than 10 years at once"
        )

    dart_service = DartApiService()

    try:
        result = dart_service.collect_multiple_years(
            db, ticker, start_year, end_year, include_quarters
        )

        return {
            "status": "success",
            "ticker": ticker,
            "years_range": f"{start_year}-{end_year}",
            "include_quarters": include_quarters,
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting financial data: {str(e)}"
        )

@router.post("/batch/collect-all")
async def batch_collect_all_stocks(
        start_year: int = Query(2023, description="시작 연도"),
        end_year: int = Query(2025, description="종료 연도"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        limit: Optional[int] = Query(None, description="수집할 종목 수 제한 (테스트용)"),
        incremental: bool = Query(False, description="증분 모드 (각 종목의 최신 연도부터만 수집)"),
        include_quarters: bool = Query(False, description="분기 재무제표도 수집"),
        db: Session = Depends(get_db)
):
    """
    한국 주식 전체 재무제표 배치 수집

    - start_year: 시작 연도 (기본: 2023)
    - end_year: 종료 연도 (기본: 2025)
    - market: KOSPI 또는 KOSDAQ (None이면 전체)
    - limit: 수집할 종목 수 제한 (테스트용)
    - incremental: 증분 모드 활성화
    - include_quarters: 분기 재무제표도 수집 ✨ **신규**

    **초기 수집 (Full Mode, 연간만):**
    ```
    POST /api/v1/financial/batch/collect-all?start_year=2023&end_year=2025
    ```
    → 전체 종목의 2023-2025년 연간 재무제표 수집

    **초기 수집 (Full Mode, 연간+분기):**
    ```
    POST /api/v1/financial/batch/collect-all?start_year=2023&end_year=2025&include_quarters=true
    ```
    → 전체 종목의 2023-2025년 연간 + 분기(Q1,Q2,Q3) 재무제표 수집

    **증분 수집 (Incremental Mode):**
    ```
    POST /api/v1/financial/batch/collect-all?start_year=2023&end_year=2025&incremental=true
    ```
    → 각 종목의 최신 연도 이후만 수집 (누락분만)

    **테스트 (10개만, 분기 포함):**
    ```
    POST /api/v1/financial/batch/collect-all?limit=10&start_year=2025&end_year=2025&include_quarters=true
    ```

    **주의:**
    - 전체 수집은 몇 시간 걸릴 수 있습니다
      - 연간만: ~2,500 종목 × 3년 × 1초 = 약 2시간
      - 연간+분기: ~2,500 종목 × 3년 × 4개 × 1초 = 약 8시간
    - DART API 속도 제한으로 각 호출마다 1초 대기
    - 증분 모드는 스케줄링에 적합 (신규 데이터만 수집)
    """
    from app.services.financial_batch import FinancialBatchCollector

    if start_year > end_year:
        raise HTTPException(
            status_code=400,
            detail="start_year must be less than or equal to end_year"
        )

    try:
        # 배치 수집 실행
        batch_collector = FinancialBatchCollector()
        result = batch_collector.collect_all_kr_stocks(
            db=db,
            start_year=start_year,
            end_year=end_year,
            market=market,
            limit=limit,
            incremental=incremental,
            include_quarters=include_quarters
        )

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch collection: {str(e)}"
        )

@router.get("/stats")
async def get_financial_stats(db: Session = Depends(get_db)):
    """
    재무제표 수집 통계 조회

    DB에 저장된 재무제표 데이터 통계를 반환합니다.
    - 연간/분기별 통계
    - 종목별 최신 데이터
    """
    from app.models import FinancialStatement, Stock
    from sqlalchemy import func

    try:
        # 총 재무제표 레코드 수
        total_statements = db.query(FinancialStatement).count()

        # 재무제표가 있는 종목 수
        stocks_with_financials = (
            db.query(func.count(func.distinct(FinancialStatement.stock_id)))
            .scalar()
        )

        # 최신/최구 데이터 연도
        latest_year = (
            db.query(func.max(FinancialStatement.fiscal_year))
            .scalar()
        )

        earliest_year = (
            db.query(func.min(FinancialStatement.fiscal_year))
            .scalar()
        )

        # 연도별 통계
        yearly_stats = (
            db.query(
                FinancialStatement.fiscal_year,
                func.count(FinancialStatement.id)
            )
            .group_by(FinancialStatement.fiscal_year)
            .order_by(FinancialStatement.fiscal_year.desc())
            .limit(10)
            .all()
        )

        # 분기별 통계 ✨ 신규
        quarterly_stats = (
            db.query(
                FinancialStatement.fiscal_year,
                FinancialStatement.fiscal_quarter,
                func.count(FinancialStatement.id)
            )
            .filter(FinancialStatement.fiscal_quarter.isnot(None))
            .group_by(FinancialStatement.fiscal_year, FinancialStatement.fiscal_quarter)
            .order_by(
                FinancialStatement.fiscal_year.desc(),
                FinancialStatement.fiscal_quarter.desc()
            )
            .limit(20)
            .all()
        )

        # 연간/분기 개수
        annual_count = (
            db.query(FinancialStatement)
            .filter(FinancialStatement.fiscal_quarter.is_(None))
            .count()
        )

        quarterly_count = (
            db.query(FinancialStatement)
            .filter(FinancialStatement.fiscal_quarter.isnot(None))
            .count()
        )

        return {
            "status": "success",
            "total_statements": total_statements,
            "by_type": {
                "annual": annual_count,
                "quarterly": quarterly_count
            },
            "stocks_with_financials": stocks_with_financials,
            "year_range": {
                "earliest": earliest_year,
                "latest": latest_year
            },
            "by_year": {year: count for year, count in yearly_stats},
            "by_quarter": [
                {
                    "year": year,
                    "quarter": quarter,
                    "count": count
                }
                for year, quarter, count in quarterly_stats
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching financial stats: {str(e)}"
        )

@router.post("/ratios/calculate/{ticker}")
async def calculate_ratios_for_stock(
        ticker: str,
        fiscal_year: Optional[int] = Query(None, description="특정 연도만 계산 (None이면 전체)"),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 재무비율 계산 및 저장

    - ticker: 종목코드 (예: 005930)
    - fiscal_year: 특정 연도만 계산 (None이면 모든 연도)

    **계산되는 비율:**
    - **수익성**: ROE, ROA, 영업이익률, 순이익률
    - **안정성**: 부채비율
    - **밸류에이션**: PER, PBR, PSR

    **예시:**
    - 삼성전자 전체 연도: `/api/v1/financial/ratios/calculate/005930`
    - 삼성전자 2023년만: `/api/v1/financial/ratios/calculate/005930?fiscal_year=2023`

    **주의:**
    - 재무제표 데이터가 먼저 수집되어 있어야 합니다
    - 시가총액 데이터가 있어야 PER, PBR, PSR 계산 가능
    """
    calculator = FinancialRatioCalculator()

    try:
        result = calculator.calculate_and_save_for_stock(db, ticker, fiscal_year)

        if result['status'] == 'error':
            raise HTTPException(
                status_code=404,
                detail=result['message']
            )

        return {
            "status": "success",
            "ticker": ticker,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating ratios: {str(e)}"
        )

@router.post("/ratios/batch-calculate")
async def batch_calculate_ratios(
        limit: Optional[int] = Query(None, description="계산할 종목 수 제한 (테스트용)"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        db: Session = Depends(get_db)
):
    """
    한국 주식 전체 재무비율 배치 계산

    - limit: 계산할 종목 수 제한 (테스트용)
    - market: KOSPI 또는 KOSDAQ (None이면 전체)

    **처리 대상:**
    - 재무제표 데이터가 있는 모든 종목
    - 각 종목의 모든 연도/분기 재무제표

    **테스트 (10개만):**
    ```
    POST /api/v1/financial/ratios/batch-calculate?limit=10
    ```

    **전체 계산:**
    ```
    POST /api/v1/financial/ratios/batch-calculate
    ```

    **주의:**
    - 전체 계산은 시간이 걸릴 수 있습니다 (~수 분)
    - 재무제표와 시가총액 데이터가 먼저 수집되어 있어야 합니다
    """
    calculator = FinancialRatioCalculator()

    try:
        result = calculator.calculate_batch(db, limit, market)

        return {
            "status": "success",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch calculation: {str(e)}"
        )

@router.get("/ratios/stats")
async def get_ratio_stats(db: Session = Depends(get_db)):
    """
    재무비율 계산 통계 조회

    DB에 저장된 재무비율 데이터 통계를 반환합니다.
    """
    from app.models import FinancialRatio
    from sqlalchemy import func

    try:
        # 총 비율 레코드 수
        total_ratios = db.query(FinancialRatio).count()

        # 비율이 계산된 종목 수
        stocks_with_ratios = (
            db.query(func.count(func.distinct(FinancialRatio.stock_id)))
            .scalar()
        )

        # 최신/최구 데이터 날짜
        latest_date = (
            db.query(func.max(FinancialRatio.date))
            .scalar()
        )

        earliest_date = (
            db.query(func.min(FinancialRatio.date))
            .scalar()
        )

        # 평균 비율 (NULL이 아닌 것만)
        avg_roe = db.query(func.avg(FinancialRatio.roe)).filter(
            FinancialRatio.roe.isnot(None)
        ).scalar()

        avg_per = db.query(func.avg(FinancialRatio.per)).filter(
            FinancialRatio.per.isnot(None),
            FinancialRatio.per > 0,
            FinancialRatio.per < 100  # 극단값 제외
        ).scalar()

        avg_pbr = db.query(func.avg(FinancialRatio.pbr)).filter(
            FinancialRatio.pbr.isnot(None),
            FinancialRatio.pbr > 0,
            FinancialRatio.pbr < 10  # 극단값 제외
        ).scalar()

        return {
            "status": "success",
            "total_ratios": total_ratios,
            "stocks_with_ratios": stocks_with_ratios,
            "date_range": {
                "earliest": earliest_date.isoformat() if earliest_date else None,
                "latest": latest_date.isoformat() if latest_date else None
            },
            "averages": {
                "roe": float(avg_roe) if avg_roe else None,
                "per": float(avg_per) if avg_per else None,
                "pbr": float(avg_pbr) if avg_pbr else None
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching ratio stats: {str(e)}"
        )

@router.get("/ratios/{ticker}")
async def get_ratios_for_stock(
        ticker: str,
        limit: int = Query(10, description="조회할 레코드 수", ge=1, le=100),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 재무비율 조회

    - ticker: 종목코드
    - limit: 조회할 레코드 수 (기본 10, 최대 100)

    **반환값:**
    - 최신 데이터부터 역순 정렬
    - ROE, ROA, PER, PBR 등 모든 계산된 비율
    """
    from app.models import Stock, FinancialRatio

    try:
        # 종목 조회
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found"
            )

        # 비율 조회
        ratios = (
            db.query(FinancialRatio)
            .filter(FinancialRatio.stock_id == stock.id)
            .order_by(FinancialRatio.date.desc())
            .limit(limit)
            .all()
        )

        if not ratios:
            return {
                "status": "success",
                "ticker": ticker,
                "name": stock.name,
                "total": 0,
                "items": []
            }

        items = []
        for ratio in ratios:
            items.append({
                "date": ratio.date.isoformat(),
                "roe": float(ratio.roe) if ratio.roe else None,
                "roa": float(ratio.roa) if ratio.roa else None,
                "operating_margin": float(ratio.operating_margin) if ratio.operating_margin else None,
                "net_margin": float(ratio.net_margin) if ratio.net_margin else None,
                "debt_ratio": float(ratio.debt_ratio) if ratio.debt_ratio else None,
                "per": float(ratio.per) if ratio.per else None,
                "pbr": float(ratio.pbr) if ratio.pbr else None,
                "psr": float(ratio.psr) if ratio.psr else None,
            })

        return {
            "status": "success",
            "ticker": ticker,
            "name": stock.name,
            "total": len(items),
            "items": items
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching ratios: {str(e)}"
        )