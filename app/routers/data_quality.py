"""
데이터 품질 검증 API 라우터
app/routers/data_quality.py
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.data_quality_checker import DataQualityChecker

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("/report")
def get_quality_report(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        db: Session = Depends(get_db)
):
    """
    전체 데이터 품질 리포트 조회

    - market: KOSPI, KOSDAQ, None(전체)

    **리포트 내용:**
    - 데이터 완성도 (coverage)
    - 이상치 탐지 (anomalies)
    - 누락 데이터 (missing data)
    - 품질 점수 (0-100)

    **예시:**
    ```bash
    # 전체 시장
    curl "http://localhost:8001/api/v1/data-quality/report"

    # KOSPI만
    curl "http://localhost:8001/api/v1/data-quality/report?market=KOSPI"
    ```
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    checker = DataQualityChecker()

    try:
        report = checker.generate_quality_report(db, market)
        return report

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating quality report: {str(e)}"
        )


@router.get("/completeness")
def check_data_completeness(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        db: Session = Depends(get_db)
):
    """
    데이터 완성도 체크

    - 재무제표 보유율
    - 시가총액 보유율
    - 재무비율 계산 완료율

    **예시:**
    ```bash
    curl "http://localhost:8001/api/v1/data-quality/completeness?market=KOSPI"
    ```
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    checker = DataQualityChecker()

    try:
        completeness = checker.check_data_completeness(db, market)
        return {
            "status": "success",
            "market": market or "ALL",
            "completeness": completeness
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking completeness: {str(e)}"
        )


@router.get("/anomalies")
def check_ratio_anomalies(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        limit: int = Query(100, ge=1, le=500, description="최대 조회 종목 수"),
        db: Session = Depends(get_db)
):
    """
    재무비율 이상치 탐지

    - 극단값 (PER > 1000, PBR < -10 등)
    - 음수 값 (PER, PBR, PSR)
    - NULL 비율이 높은 종목

    **예시:**
    ```bash
    # KOSPI 이상치 확인
    curl "http://localhost:8001/api/v1/data-quality/anomalies?market=KOSPI&limit=100"
    ```
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    checker = DataQualityChecker()

    try:
        anomalies = checker.check_ratio_anomalies(db, market, limit)
        return {
            "status": "success",
            "market": market or "ALL",
            "limit": limit,
            "anomalies": anomalies
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking anomalies: {str(e)}"
        )


@router.get("/missing")
def check_missing_data(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        limit: int = Query(50, ge=1, le=200, description="최대 조회 종목 수"),
        db: Session = Depends(get_db)
):
    """
    누락된 데이터 확인

    - 재무제표가 없는 종목
    - 시가총액이 없는 종목
    - 연도별 누락 데이터

    **예시:**
    ```bash
    curl "http://localhost:8001/api/v1/data-quality/missing?market=KOSDAQ&limit=50"
    ```
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    checker = DataQualityChecker()

    try:
        missing = checker.check_missing_statements(db, market, limit)
        return {
            "status": "success",
            "market": market or "ALL",
            "limit": limit,
            "missing": missing
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking missing data: {str(e)}"
        )


@router.get("/summary")
def get_quality_summary(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ, None=전체)"),
        db: Session = Depends(get_db)
):
    """
    데이터 품질 요약 (간단 버전)

    전체 리포트보다 가볍고 빠른 요약 정보

    **예시:**
    ```bash
    curl "http://localhost:8001/api/v1/data-quality/summary"
    ```
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    checker = DataQualityChecker()

    try:
        # 완성도만 체크 (빠름)
        completeness = checker.check_data_completeness(db, market)

        # 간단한 품질 점수 계산
        quality_score = completeness['coverage_rates']['ratios']

        return {
            "status": "success",
            "market": market or "ALL",
            "quality_score": round(quality_score, 2),
            "quality_grade": checker._get_quality_grade(quality_score),
            "total_stocks": completeness['total_stocks'],
            "coverage": {
                "financial_statements": f"{completeness['coverage_rates']['financial_statements']}%",
                "market_cap": f"{completeness['coverage_rates']['market_cap']}%",
                "ratios": f"{completeness['coverage_rates']['ratios']}%",
            },
            "ready_for_calculation": completeness['calculation_status']['ready'],
            "pending_calculation": completeness['calculation_status']['pending'],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )