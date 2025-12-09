"""
배치 데이터 수집 API 라우터
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.batch_collector import BatchCollector

router = APIRouter(prefix="/batch", tags=["batch-collection"])


# Request Body 스키마 정의
class USBatchCollectRequest(BaseModel):
    """미국 시장 배치 수집 요청 스키마"""
    tickers: Optional[List[str]] = Field(None, description="수집할 티커 리스트")
    collect_all: bool = Field(False, description="DB의 모든 US 종목 수집 여부")
    markets: Optional[List[str]] = Field(None, description="특정 market만 수집 (예: ['NYSE', 'NASDAQ'])")
    incremental: bool = Field(True, description="증분 업데이트 여부")


class AllMarketsBatchCollectRequest(BaseModel):
    """전체 시장 배치 수집 요청 스키마"""
    korea_markets: Optional[List[str]] = Field(None, description="한국 시장 리스트")
    us_tickers: Optional[List[str]] = Field(None, description="미국 티커 리스트")
    us_collect_all: bool = Field(False, description="DB의 모든 US 종목 수집 여부")
    us_markets: Optional[List[str]] = Field(None, description="미국 시장 필터")
    incremental: bool = Field(True, description="증분 업데이트 여부")


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
    request: USBatchCollectRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    미국 시장 배치 수집

    **Request Body 예시:**
    ```json
    {
      "tickers": ["AAPL", "MSFT", "GOOGL"],
      "incremental": true
    }
    ```

    또는

    ```json
    {
      "collect_all": true,
      "markets": ["NYSE", "NASDAQ"],
      "incremental": true
    }
    ```

    **옵션 1: 특정 티커 리스트 수집**
    - tickers: ["AAPL", "MSFT", "GOOGL"] 등

    **옵션 2: DB의 모든 US 종목 수집**
    - collect_all: true
    - 먼저 `/api/v1/us/collect/all-stocks`로 종목 리스트 수집 필요

    **옵션 3: 특정 market만 수집 (신규)** ⭐
    - collect_all: true & markets: ["NYSE", "NASDAQ"]
    - OTC, 기타 제외하고 주요 거래소만 수집

    **주의**: API 속도 제한으로 인해 시간이 오래 걸립니다
    - Twelve Data: 8 requests/min
    - 100개 종목: 약 2시간
    - 1000개 종목: 약 20시간

    **권장 전략:**
    1. NYSE, NASDAQ만 수집: markets=["NYSE", "NASDAQ"]
    2. 소규모 테스트 후 야간/주말에 전체 수집
    3. 스케줄러로 일일 증분 업데이트
    """
    collector = BatchCollector()

    try:
        result = collector.collect_us_batch(
            db,
            tickers=request.tickers,
            incremental=request.incremental,
            collect_all=request.collect_all,
            markets=request.markets
        )

        return {
            "status": "success",
            "message": f"Batch collection for US stocks completed",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in batch collection: {str(e)}"
        )


@router.post("/collect/all")
async def batch_collect_all_markets(
    request: AllMarketsBatchCollectRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    전체 시장 배치 수집 (한국 + 미국)

    **Request Body 예시:**
    ```json
    {
      "korea_markets": ["KOSPI", "KOSDAQ"],
      "us_collect_all": true,
      "us_markets": ["NYSE", "NASDAQ"],
      "incremental": true
    }
    ```

    - korea_markets: 한국 시장 리스트 (기본: ["KOSPI", "KOSDAQ"])
    - us_tickers: 미국 티커 리스트 (us_collect_all=False일 때)
    - us_collect_all: True면 DB의 모든 US 종목 수집
    - us_markets: 미국 시장 필터 (신규) ⭐
    - incremental: True면 마지막 수집일 이후만

    **경고**: 전체 수집은 매우 오래 걸립니다
    - 한국: KOSPI + KOSDAQ = 약 1.5시간
    - 미국: 종목 수에 따라 수 시간 ~ 수십 시간

    **권장 순서:**
    1. 먼저 `/api/v1/us/collect/all-stocks`로 US 종목 리스트 수집
    2. 그 다음 이 API로 가격 데이터 수집
       - 주요 거래소만: us_markets=["NYSE", "NASDAQ"]
       - 또는 전체: us_collect_all=true
    """
    collector = BatchCollector()

    # 기본값 설정
    korea_markets = request.korea_markets or ['KOSPI', 'KOSDAQ']

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
            request.us_tickers,
            request.us_collect_all,
            request.us_markets,
            request.incremental
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

        # 미국 시장 통계 (market별)
        us_market_stats = (
            db.query(Stock.market, func.count(Stock.id))
            .filter(Stock.country == 'US')
            .group_by(Stock.market)
            .all()
        )

        us_total = db.query(Stock).filter(Stock.country == 'US').count()

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

        return {
            "status": "success",
            "stocks": {
                "korea": {
                    "kospi": kospi_count,
                    "kosdaq": kosdaq_count,
                    "total": kospi_count + kosdaq_count
                },
                "us": {
                    "by_market": {market: count for market, count in us_market_stats},
                    "total": us_total
                },
                "total": kospi_count + kosdaq_count + us_total
            },
            "prices": {
                "total_records": total_prices,
                "stocks_with_prices": stocks_with_prices,
                "latest_date": latest_price.isoformat() if latest_price else None
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}"
        )