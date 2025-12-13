"""
배치 데이터 수집 API 라우터 (한국 시장 전용)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.batch_collector import BatchCollector

router = APIRouter(prefix="/batch", tags=["batch-collection"])


@router.post("/collect/korea/{market}")
async def batch_collect_korea_market(
    market: str,
    incremental: bool = Query(True, description="증분 업데이트 여부"),
    max_stocks: Optional[int] = Query(None, description="최대 수집 종목 수 (테스트용)"),
    db: Session = Depends(get_db)
):
    """
    한국 시장 배치 수집 (KOSPI 또는 KOSDAQ)

    - market: KOSPI 또는 KOSDAQ
    - incremental: True면 마지막 수집일 이후만, False면 전체 1년치
    - max_stocks: 테스트용 (특정 개수만 수집)

    **주의**: 전체 시장 수집은 시간이 오래 걸립니다 (KOSPI: ~30-40분)

    **예시:**
    ```bash
    # KOSPI 증분 수집
    curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSPI?incremental=true"

    # KOSDAQ 전체 수집 (테스트 10개)
    curl -X POST "http://localhost:8001/api/v1/batch/collect/korea/KOSDAQ?incremental=false&max_stocks=10"
    ```
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    collector = BatchCollector()

    try:
        result = collector.collect_korea_batch(db, market, incremental, max_stocks)

        return {
            "status": "success",
            "message": f"Batch collection for {market} completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch collection: {str(e)}"
        )


@router.post("/collect/all")
async def batch_collect_all_markets(
    korea_markets: Optional[List[str]] = Query(None, description="한국 시장 리스트 (기본: KOSPI, KOSDAQ)"),
    incremental: bool = Query(True, description="증분 업데이트 여부"),
    db: Session = Depends(get_db)
):
    """
    전체 한국 시장 배치 수집 (KOSPI + KOSDAQ)

    - korea_markets: 한국 시장 리스트 (기본: ["KOSPI", "KOSDAQ"])
    - incremental: True면 마지막 수집일 이후만

    **경고**: 전체 수집은 오래 걸립니다
    - KOSPI + KOSDAQ = 약 1-1.5시간

    **예시:**
    ```bash
    # 전체 시장 증분 수집
    curl -X POST "http://localhost:8001/api/v1/batch/collect/all?incremental=true"

    # KOSPI만 전체 수집
    curl -X POST "http://localhost:8001/api/v1/batch/collect/all?korea_markets=KOSPI&incremental=false"
    ```
    """
    collector = BatchCollector()

    # 기본값 설정
    if korea_markets is None:
        korea_markets = ['KOSPI', 'KOSDAQ']

    # 유효성 검사
    for market in korea_markets:
        if market not in ["KOSPI", "KOSDAQ"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid market: {market}. Must be KOSPI or KOSDAQ"
            )

    try:
        result = collector.collect_all_markets(
            db,
            korea_markets,
            incremental
        )

        return {
            "status": "success",
            "message": "Batch collection for all markets completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch collection: {str(e)}"
        )


@router.get("/stats")
async def get_collection_stats(db: Session = Depends(get_db)):
    """
    데이터 수집 통계 조회

    한국 시장별로 수집된 종목 수와 최신 가격/시장 데이터 날짜를 반환

    **예시:**
    ```bash
    curl "http://localhost:8001/api/v1/batch/stats"
    ```
    """
    from app.models import Stock, StockPrice, StockMarketData
    from sqlalchemy import func

    try:
        # 한국 시장 통계
        kospi_count = db.query(Stock).filter(
            Stock.country == 'KR',
            Stock.market == 'KOSPI'
        ).count()

        kosdaq_count = db.query(Stock).filter(
            Stock.country == 'KR',
            Stock.market == 'KOSDAQ'
        ).count()

        # 최신 가격 데이터 날짜
        latest_price = (
            db.query(func.max(StockPrice.trade_date))
            .scalar()
        )

        # 총 가격 레코드 수
        total_prices = db.query(StockPrice).count()

        # 가격 데이터가 있는 종목 수
        stocks_with_prices = (
            db.query(func.count(func.distinct(StockPrice.stock_id)))
            .scalar()
        )

        # 시장 데이터 통계
        latest_market_data = (
            db.query(func.max(StockMarketData.trade_date))
            .scalar()
        )

        total_market_data = db.query(StockMarketData).count()

        stocks_with_market_data = (
            db.query(func.count(func.distinct(StockMarketData.stock_id)))
            .scalar()
        )

        return {
            "status": "success",
            "stocks": {
                "korea": {
                    "kospi": kospi_count,
                    "kosdaq": kosdaq_count,
                    "total": kospi_count + kosdaq_count
                },
                "total": kospi_count + kosdaq_count
            },
            "prices": {
                "total_records": total_prices,
                "stocks_with_prices": stocks_with_prices,
                "latest_date": latest_price.isoformat() if latest_price else None
            },
            "market_data": {
                "total_records": total_market_data,
                "stocks_with_market_data": stocks_with_market_data,
                "latest_date": latest_market_data.isoformat() if latest_market_data else None
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )