from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.korea_market import KoreaMarketCollector

router = APIRouter(prefix="/korea", tags=["korea-market"])


@router.post("/collect/stocks")
async def collect_korea_stocks(
        market: str = Query("KOSPI", description="시장 (KOSPI 또는 KOSDAQ)"),
        db: Session = Depends(get_db)
):
    """
    한국 주식 목록 수집 및 저장

    - KOSPI 또는 KOSDAQ 전체 종목 리스트를 수집하여 DB에 저장
    - 기존 종목은 업데이트, 신규 종목은 추가
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    collector = KoreaMarketCollector()

    try:
        saved_count = collector.save_stocks_to_db(db, market)
        return {
            "status": "success",
            "market": market,
            "saved_count": saved_count,
            "message": f"Successfully saved {saved_count} stocks from {market}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting stocks: {str(e)}"
        )


@router.post("/collect/prices/{ticker}")
async def collect_stock_prices(
        ticker: str,
        start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 주가 데이터 수집 및 저장

    - ticker: 종목 코드 (예: 005930 for 삼성전자)
    - start_date: 시작일 (미지정시 1년 전부터)
    - end_date: 종료일 (미지정시 오늘까지)
    """
    collector = KoreaMarketCollector()

    # 날짜 파싱
    start_dt = None
    end_dt = None

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="start_date must be in YYYY-MM-DD format"
            )

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="end_date must be in YYYY-MM-DD format"
            )

    try:
        saved_count = collector.save_stock_prices_to_db(db, ticker, start_dt)

        if saved_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for ticker {ticker}. Make sure the stock exists in database."
            )

        return {
            "status": "success",
            "ticker": ticker,
            "saved_count": saved_count,
            "start_date": start_date or "1 year ago",
            "end_date": end_date or "today",
            "message": f"Successfully saved {saved_count} price records for {ticker}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting prices: {str(e)}"
        )


@router.get("/stocks/preview")
async def preview_korea_stocks(
        market: str = Query("KOSPI", description="시장 (KOSPI 또는 KOSDAQ)"),
):
    """
    한국 주식 목록 미리보기 (DB 저장 없이 조회만)

    - FinanceDataReader에서 실시간 데이터 조회
    - DB에 저장하지 않음
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    collector = KoreaMarketCollector()

    try:
        stocks_df = collector.get_stock_list(market)

        if stocks_df.empty:
            return {
                "status": "success",
                "market": market,
                "count": 0,
                "stocks": []
            }

        # DataFrame을 dict 리스트로 변환 (상위 20개만)
        stocks_list = stocks_df.head(20).to_dict('records')

        return {
            "status": "success",
            "market": market,
            "total_count": len(stocks_df),
            "preview_count": len(stocks_list),
            "stocks": stocks_list
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stocks: {str(e)}"
        )

@router.post("/collect/market-data")
async def collect_market_data(
        market: str = Query("KOSPI", description="시장 (KOSPI 또는 KOSDAQ)"),
        date: Optional[str] = Query(None, description="조회 날짜 (YYYY-MM-DD, 미지정시 오늘)"),
        db: Session = Depends(get_db)
):
    """
    시장 데이터 수집 (시가총액, 거래대금, 상장주식수)

    - market: KOSPI 또는 KOSDAQ
    - date: 조회 날짜 (미지정시 오늘)
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    collector = KoreaMarketCollector()

    # 날짜 파싱
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="date must be in YYYY-MM-DD format"
            )

    try:
        saved_count = collector.save_market_data_to_db(db, market, target_date)

        return {
            "status": "success",
            "market": market,
            "date": date or "today",
            "saved_count": saved_count,
            "message": f"Successfully saved {saved_count} market data records"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting market data: {str(e)}"
        )