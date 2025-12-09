from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.us_market import USMarketCollector

router = APIRouter(prefix="/us", tags=["us-market"])


@router.post("/collect/stock/{ticker}")
async def collect_us_stock(
        ticker: str,
        db: Session = Depends(get_db)
):
    """
    미국 주식 정보 수집 및 저장

    - ticker: 종목 코드 (예: AAPL, MSFT, GOOGL)
    - 종목 기본 정보를 yfinance에서 조회하여 DB에 저장
    """
    collector = USMarketCollector()

    try:
        success = collector.save_stock_to_db(db, ticker)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Failed to fetch stock info for {ticker}"
            )

        return {
            "status": "success",
            "ticker": ticker,
            "message": f"Successfully saved stock info for {ticker}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting stock: {str(e)}"
        )


@router.post("/collect/prices/{ticker}")
async def collect_us_stock_prices(
        ticker: str,
        start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
        db: Session = Depends(get_db)
):
    """
    미국 주식 주가 데이터 수집 및 저장

    - ticker: 종목 코드 (예: AAPL, MSFT, GOOGL)
    - start_date: 시작일 (미지정시 1년 전부터)
    - end_date: 종료일 (미지정시 오늘까지)
    """
    collector = USMarketCollector()

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


@router.post("/collect/all-stocks")
async def collect_all_us_stocks(
        exchanges: Optional[List[str]] = Query(
            None,
            description="거래소 리스트 (미지정시 전체: US = NYSE + NASDAQ + 기타)"
        ),
        filter_common: bool = Query(
            True,
            description="일반 주식만 필터링 (ETF, Warrant 등 제외)"
        ),
        db: Session = Depends(get_db)
):
    """
    미국 전체 주식 목록 수집 및 저장

    - exchanges: 거래소 리스트 (기본: ['US'] = 전체)
    - filter_common: True면 일반 주식만, False면 ETF 등 포함

    **주의**: 전체 수집은 수천 개 종목을 가져옵니다 (약 5-10분 소요)

    **거래소 코드:**
    - 'US': 미국 전체 (NYSE, NASDAQ, 기타 포함)
    - 개별 지정도 가능하지만 'US' 사용 권장
    """
    collector = USMarketCollector()

    try:
        results = collector.save_all_stocks_to_db(
            db,
            exchanges=exchanges,
            filter_common=filter_common
        )

        return {
            "status": "success",
            "message": "US stock list collection completed",
            "results": {
                "total": results['total'],
                "new": results['saved'],
                "updated": results['updated'],
                "failed": results['failed']
            },
            "errors": results['errors'][:10] if results['errors'] else []  # 최대 10개 에러만
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting US stock list: {str(e)}"
        )


@router.get("/preview/all-stocks")
async def preview_all_us_stocks(
        exchanges: Optional[List[str]] = Query(
            None,
            description="거래소 리스트 (미지정시 전체)"
        ),
        filter_common: bool = Query(
            True,
            description="일반 주식만 필터링"
        ),
        limit: int = Query(50, description="미리보기 개수", ge=1, le=500)
):
    """
    미국 주식 목록 미리보기 (DB 저장 없이 조회만)

    - exchanges: 거래소 리스트
    - filter_common: 일반 주식만 필터링
    - limit: 반환할 종목 수 (최대 500)

    DB에 저장하지 않고 API에서 조회한 결과만 반환합니다.
    """
    collector = USMarketCollector()

    try:
        stocks_df = collector.get_all_us_stocks(exchanges)

        if stocks_df.empty:
            return {
                "status": "success",
                "total_count": 0,
                "preview_count": 0,
                "stocks": []
            }

        # 필터링
        if filter_common:
            stocks_df = collector.filter_common_stocks(stocks_df)

        # 상위 N개만
        preview_df = stocks_df.head(limit)
        stocks_list = preview_df.to_dict('records')

        return {
            "status": "success",
            "total_count": len(stocks_df),
            "preview_count": len(stocks_list),
            "filter_common": filter_common,
            "stocks": stocks_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching US stock list: {str(e)}"
        )


@router.post("/collect/sp500-sample")
async def collect_sp500_sample(
        db: Session = Depends(get_db)
):
    """
    S&P 500 샘플 종목 수집

    주요 10개 종목 정보를 수집:
    - AAPL (Apple)
    - MSFT (Microsoft)
    - GOOGL (Alphabet)
    - AMZN (Amazon)
    - NVDA (NVIDIA)
    - META (Meta)
    - TSLA (Tesla)
    - BRK-B (Berkshire Hathaway)
    - V (Visa)
    - JNJ (Johnson & Johnson)
    """
    collector = USMarketCollector()

    try:
        results = collector.collect_sp500_sample(db)

        return {
            "status": "success",
            "success_count": results['success'],
            "failed_count": results['failed'],
            "tickers": results['tickers'],
            "message": f"Successfully saved {results['success']} stocks, {results['failed']} failed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting S&P 500 sample: {str(e)}"
        )


@router.get("/stock/{ticker}/info")
async def get_us_stock_info(
        ticker: str
):
    """
    미국 주식 정보 미리보기 (DB 저장 안 함)

    - yfinance에서 실시간 종목 정보 조회
    - DB에 저장하지 않음
    """
    collector = USMarketCollector()

    try:
        info = collector.get_stock_info(ticker)

        if not info:
            raise HTTPException(
                status_code=404,
                detail=f"Stock {ticker} not found"
            )

        return {
            "status": "success",
            "ticker": ticker,
            "info": info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stock info: {str(e)}"
        )