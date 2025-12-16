"""
종목 스크리닝 API 라우터
app/routers/screening.py
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stock_screener import StockScreener

router = APIRouter(prefix="/screening", tags=["stock-screening"])


@router.get("/undervalued")
def screen_undervalued_stocks(
        max_per: float = Query(10.0, description="최대 PER", ge=0, le=100),
        max_pbr: float = Query(1.0, description="최대 PBR", ge=0, le=10),
        min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억 원)"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
        limit: int = Query(50, description="최대 결과 수", ge=1, le=200),
        db: Session = Depends(get_db)
):
    """
    저평가 종목 스크리닝

    **기준:**
    - PER < 10 (저평가)
    - PBR < 1 (장부가치 대비 저평가)
    - 시가총액 필터 (선택)

    **사용 예시:**
    ```bash
    # 기본 (PER < 10, PBR < 1)
    curl "http://localhost:8001/api/v1/screening/undervalued"

    # 시총 1조 이상만
    curl "http://localhost:8001/api/v1/screening/undervalued?min_market_cap=10000"

    # KOSPI만
    curl "http://localhost:8001/api/v1/screening/undervalued?market=KOSPI"

    # 더 엄격한 기준 (PER < 8, PBR < 0.8)
    curl "http://localhost:8001/api/v1/screening/undervalued?max_per=8&max_pbr=0.8"
    ```

    **결과 정렬:** PER + PBR 합계 낮은 순
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    try:
        screener = StockScreener()
        results = screener.screen_undervalued(
            db=db,
            max_per=max_per,
            max_pbr=max_pbr,
            min_market_cap=min_market_cap,
            market=market,
            limit=limit
        )

        return {
            "status": "success",
            "criteria": {
                "max_per": max_per,
                "max_pbr": max_pbr,
                "min_market_cap": min_market_cap,
                "market": market
            },
            "total": len(results),
            "stocks": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error screening stocks: {str(e)}"
        )


@router.get("/quality")
def screen_quality_stocks(
        min_roe: float = Query(15.0, description="최소 ROE (%)", ge=0, le=100),
        max_debt_ratio: float = Query(100.0, description="최대 부채비율 (%)", ge=0, le=1000),
        min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억 원)"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
        limit: int = Query(50, description="최대 결과 수", ge=1, le=200),
        db: Session = Depends(get_db)
):
    """
    우량 종목 스크리닝

    **기준:**
    - ROE > 15% (높은 수익성)
    - 부채비율 < 100% (안정성)

    **사용 예시:**
    ```bash
    # 기본 (ROE > 15%, 부채비율 < 100%)
    curl "http://localhost:8001/api/v1/screening/quality"

    # 더 엄격한 기준 (ROE > 20%, 부채비율 < 50%)
    curl "http://localhost:8001/api/v1/screening/quality?min_roe=20&max_debt_ratio=50"

    # 시총 5천억 이상
    curl "http://localhost:8001/api/v1/screening/quality?min_market_cap=5000"
    ```

    **결과 정렬:** ROE 높은 순
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    try:
        screener = StockScreener()
        results = screener.screen_quality(
            db=db,
            min_roe=min_roe,
            max_debt_ratio=max_debt_ratio,
            min_market_cap=min_market_cap,
            market=market,
            limit=limit
        )

        return {
            "status": "success",
            "criteria": {
                "min_roe": min_roe,
                "max_debt_ratio": max_debt_ratio,
                "min_market_cap": min_market_cap,
                "market": market
            },
            "total": len(results),
            "stocks": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error screening stocks: {str(e)}"
        )


@router.get("/growth")
def screen_growth_stocks(
        min_roe: float = Query(10.0, description="최소 ROE (%)", ge=0, le=100),
        max_per: float = Query(30.0, description="최대 PER", ge=0, le=100),
        min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억 원)"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
        limit: int = Query(50, description="최대 결과 수", ge=1, le=200),
        db: Session = Depends(get_db)
):
    """
    성장 종목 스크리닝

    **기준:**
    - ROE > 10% (수익성)
    - PER < 30 (합리적 밸류에이션)

    **사용 예시:**
    ```bash
    # 기본 (ROE > 10%, PER < 30)
    curl "http://localhost:8001/api/v1/screening/growth"

    # 더 높은 수익성 요구 (ROE > 15%)
    curl "http://localhost:8001/api/v1/screening/growth?min_roe=15"

    # 저평가 성장주 (PER < 20)
    curl "http://localhost:8001/api/v1/screening/growth?max_per=20"
    ```

    **결과 정렬:** ROE/PER 비율 높은 순 (성장 대비 밸류에이션 좋은 순)
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    try:
        screener = StockScreener()
        results = screener.screen_growth(
            db=db,
            min_roe=min_roe,
            max_per=max_per,
            min_market_cap=min_market_cap,
            market=market,
            limit=limit
        )

        return {
            "status": "success",
            "criteria": {
                "min_roe": min_roe,
                "max_per": max_per,
                "min_market_cap": min_market_cap,
                "market": market
            },
            "total": len(results),
            "stocks": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error screening stocks: {str(e)}"
        )


@router.get("/custom")
def screen_custom_filter(
        min_roe: Optional[float] = Query(None, description="최소 ROE (%)", ge=-100, le=100),
        max_roe: Optional[float] = Query(None, description="최대 ROE (%)", ge=-100, le=100),
        min_per: Optional[float] = Query(None, description="최소 PER", ge=-100, le=1000),
        max_per: Optional[float] = Query(None, description="최대 PER", ge=-100, le=1000),
        min_pbr: Optional[float] = Query(None, description="최소 PBR", ge=-10, le=100),
        max_pbr: Optional[float] = Query(None, description="최대 PBR", ge=-10, le=100),
        min_debt_ratio: Optional[float] = Query(None, description="최소 부채비율 (%)", ge=0, le=1000),
        max_debt_ratio: Optional[float] = Query(None, description="최대 부채비율 (%)", ge=0, le=1000),
        min_market_cap: Optional[float] = Query(None, description="최소 시가총액 (억 원)"),
        max_market_cap: Optional[float] = Query(None, description="최대 시가총액 (억 원)"),
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
        sector: Optional[str] = Query(None, description="섹터"),
        sort_by: str = Query("roe", description="정렬 기준 (roe, per, pbr, debt_ratio, market_cap)"),
        sort_order: str = Query("desc", description="정렬 순서 (asc, desc)"),
        limit: int = Query(50, description="최대 결과 수", ge=1, le=200),
        db: Session = Depends(get_db)
):
    """
    커스텀 필터 스크리닝

    원하는 재무비율 조합으로 자유롭게 필터링할 수 있습니다.

    **사용 예시:**
    ```bash
    # 저평가 + 우량주 (PER < 15, ROE > 10%, 부채비율 < 100%)
    curl "http://localhost:8001/api/v1/screening/custom?min_roe=10&max_per=15&max_debt_ratio=100"

    # 중소형주 (시총 5백억~5천억)
    curl "http://localhost:8001/api/v1/screening/custom?min_market_cap=500&max_market_cap=5000"

    # 반도체 섹터 ROE 상위
    curl "http://localhost:8001/api/v1/screening/custom?sector=반도체&sort_by=roe&sort_order=desc"

    # PBR 낮은 순 정렬
    curl "http://localhost:8001/api/v1/screening/custom?sort_by=pbr&sort_order=asc"
    ```

    **정렬 옵션:**
    - `roe`: ROE
    - `per`: PER
    - `pbr`: PBR
    - `debt_ratio`: 부채비율
    - `market_cap`: 시가총액
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    if sort_by not in ["roe", "per", "pbr", "debt_ratio", "market_cap"]:
        raise HTTPException(
            status_code=400,
            detail="sort_by must be one of: roe, per, pbr, debt_ratio, market_cap"
        )

    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=400,
            detail="sort_order must be either 'asc' or 'desc'"
        )

    try:
        screener = StockScreener()
        results = screener.screen_custom(
            db=db,
            min_roe=min_roe,
            max_roe=max_roe,
            min_per=min_per,
            max_per=max_per,
            min_pbr=min_pbr,
            max_pbr=max_pbr,
            min_debt_ratio=min_debt_ratio,
            max_debt_ratio=max_debt_ratio,
            min_market_cap=min_market_cap,
            max_market_cap=max_market_cap,
            market=market,
            sector=sector,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit
        )

        return {
            "status": "success",
            "criteria": {
                "roe": {"min": min_roe, "max": max_roe},
                "per": {"min": min_per, "max": max_per},
                "pbr": {"min": min_pbr, "max": max_pbr},
                "debt_ratio": {"min": min_debt_ratio, "max": max_debt_ratio},
                "market_cap": {"min": min_market_cap, "max": max_market_cap},
                "market": market,
                "sector": sector,
                "sort": {"by": sort_by, "order": sort_order}
            },
            "total": len(results),
            "stocks": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error screening stocks: {str(e)}"
        )


@router.get("/sector-comparison")
def compare_sectors(
        market: Optional[str] = Query(None, description="시장 (KOSPI, KOSDAQ)"),
        limit_per_sector: int = Query(5, description="섹터당 최대 종목 수", ge=1, le=20),
        db: Session = Depends(get_db)
):
    """
    섹터별 상위 종목 비교

    각 섹터의 ROE 상위 종목을 반환합니다.

    **사용 예시:**
    ```bash
    # 전체 섹터 비교 (각 섹터별 상위 5개)
    curl "http://localhost:8001/api/v1/screening/sector-comparison"

    # KOSPI만, 각 섹터별 상위 3개
    curl "http://localhost:8001/api/v1/screening/sector-comparison?market=KOSPI&limit_per_sector=3"

    # KOSDAQ, 각 섹터별 상위 10개
    curl "http://localhost:8001/api/v1/screening/sector-comparison?market=KOSDAQ&limit_per_sector=10"
    ```

    **결과:** 섹터별로 ROE 높은 순으로 정렬된 종목 딕셔너리
    """
    if market and market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    try:
        screener = StockScreener()
        results = screener.compare_by_sector(
            db=db,
            market=market,
            limit_per_sector=limit_per_sector
        )

        return {
            "status": "success",
            "market": market or "ALL",
            "limit_per_sector": limit_per_sector,
            "total_sectors": len(results),
            "sectors": results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing sectors: {str(e)}"
        )