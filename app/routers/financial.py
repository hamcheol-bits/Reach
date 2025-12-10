"""
재무제표 데이터 수집 API 라우터
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.dart_api import DartApiService

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
        db: Session = Depends(get_db)
):
    """
    특정 종목의 여러 연도 재무제표 수집

    - ticker: 종목코드 (예: 005930)
    - start_year: 시작 연도
    - end_year: 종료 연도

    **예시:**
    - 삼성전자 2020~2023: `/api/v1/financial/collect/005930/multiple-years?start_year=2020&end_year=2023`

    **주의:** 여러 연도 수집은 시간이 걸립니다 (1년당 약 1-2초)
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
        result = dart_service.collect_multiple_years(db, ticker, start_year, end_year)

        return {
            "status": "success",
            "ticker": ticker,
            "years_range": f"{start_year}-{end_year}",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting financial data: {str(e)}"
        )


@router.get("/stats")
async def get_financial_stats(db: Session = Depends(get_db)):
    """
    재무제표 수집 통계 조회

    DB에 저장된 재무제표 데이터 통계를 반환합니다.
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

        return {
            "status": "success",
            "total_statements": total_statements,
            "stocks_with_financials": stocks_with_financials,
            "year_range": {
                "earliest": earliest_year,
                "latest": latest_year
            },
            "by_year": {year: count for year, count in yearly_stats}
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching financial stats: {str(e)}"
        )