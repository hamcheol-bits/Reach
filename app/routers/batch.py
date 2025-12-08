"""
배치 데이터 수집 API 라우터
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.batch_collector import BatchCollector

router = APIRouter(prefix="/batch", tags=["batch-collection"])


@router.post("/collect/korea/{market}")
async def batch_collect_korea_market(
    market: str,
    background_tasks: BackgroundTasks,
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
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    collector = BatchCollector()

    try:
        # 백그라운드 태스크로 실행 가능
        # background_tasks.add_task(
        #     collector.collect_korea_batch,
        #     db, market, incremental, max_stocks
        # )

        # 동기 실행 (결과 즉시 반환)
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


@router.post("/collect/us")
async def batch_collect_us_market(
    background_tasks: BackgroundTasks,
    tickers: Optional[List[str]] = Query(
        None,
        description="수집할 티커 리스트 (미지정시 S&P 500 샘플 사용)"
    ),
    incremental: bool = Query(True, description="증분 업데이트 여부"),
    db: Session = Depends(get_db)
):
    """
    미국 시장 배치 수집

    - tickers: 수집할 티커 리스트 (예: ["AAPL", "MSFT", "GOOGL"])
    - incremental: True면 마지막 수집일 이후만, False면 전체 1년치

    **주의**: API 속도 제한으로 인해 시간이 오래 걸립니다
    (Twelve Data: 8 requests/min → 10개 종목당 ~12분)
    """
    collector = BatchCollector()

    # 티커가 지정되지 않으면 S&P 500 샘플 사용
    if not tickers:
        tickers = collector.us_collector.sp500_sample

    try:
        result = collector.collect_us_batch(db, tickers, incremental)

        return {
            "status": "success",
            "message": f"Batch collection for {len(tickers)} US stocks completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch collection: {str(e)}"
        )


@router.post("/collect/all")
async def batch_collect_all_markets(
    background_tasks: BackgroundTasks,
    korea_markets: Optional[List[str]] = Query(
        None,
        description="한국 시장 리스트 (미지정시 KOSPI, KOSDAQ)"
    ),
    us_tickers: Optional[List[str]] = Query(
        None,
        description="미국 티커 리스트 (미지정시 S&P 500 샘플)"
    ),
    incremental: bool = Query(True, description="증분 업데이트 여부"),
    db: Session = Depends(get_db)
):
    """
    전체 시장 배치 수집 (한국 + 미국)

    - korea_markets: 한국 시장 리스트 (기본: ["KOSPI", "KOSDAQ"])
    - us_tickers: 미국 티커 리스트 (기본: S&P 500 샘플)
    - incremental: True면 마지막 수집일 이후만

    **경고**: 전체 수집은 매우 오래 걸립니다 (수 시간)
    테스트는 개별 시장별로 먼저 진행하는 것을 권장합니다.
    """
    collector = BatchCollector()

    # 기본값 설정
    if not korea_markets:
        korea_markets = ['KOSPI', 'KOSDAQ']

    if not us_tickers:
        us_tickers = collector.us_collector.sp500_sample

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
            us_tickers,
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

    각 시장별로 수집된 종목 수와 최신 가격 데이터 날짜를 반환
    """
    from app.models import Stock, StockPrice
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

        # 미국 시장 통계
        us_count = db.query(Stock).filter(Stock.country == 'US').count()

        # 최신 가격 데이터 날짜
        latest_price = (
            db.query(func.max(StockPrice.trade_date))
            .scalar()
        )

        # 총 가격 레코드 수
        total_prices = db.query(StockPrice).count()

        return {
            "status": "success",
            "stocks": {
                "korea": {
                    "kospi": kospi_count,
                    "kosdaq": kosdaq_count,
                    "total": kospi_count + kosdaq_count
                },
                "us": us_count,
                "total": kospi_count + kosdaq_count + us_count
            },
            "prices": {
                "total_records": total_prices,
                "latest_date": latest_price.isoformat() if latest_price else None
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )