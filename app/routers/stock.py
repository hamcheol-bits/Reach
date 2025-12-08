from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Stock, StockPrice
from app.schemas import StockResponse, StockListResponse
from app.schemas.price import StockPriceListResponse

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=StockListResponse)
async def get_stocks(
        country: Optional[str] = Query(None, description="국가 필터 (KR, US)"),
        market: Optional[str] = Query(None, description="시장 필터 (KOSPI, NASDAQ 등)"),
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db)
):
    """주식 목록 조회"""
    query = db.query(Stock)

    if country:
        query = query.filter(Stock.country == country)
    if market:
        query = query.filter(Stock.market == market)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return StockListResponse(total=total, items=items)


@router.get("/{ticker}", response_model=StockResponse)
async def get_stock(
        ticker: str,
        db: Session = Depends(get_db)
):
    """특정 주식 조회"""
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    return stock


@router.get("/{ticker}/prices", response_model=StockPriceListResponse)
async def get_stock_prices(
        ticker: str,
        start_date: Optional[str] = Query(None, description="시작일 (YYYY-MM-DD)"),
        end_date: Optional[str] = Query(None, description="종료일 (YYYY-MM-DD)"),
        limit: int = Query(100, ge=1, le=1000, description="최대 조회 개수"),
        db: Session = Depends(get_db)
):
    """
    특정 종목의 주가 데이터 조회

    - ticker: 종목 코드
    - start_date: 시작일 (옵션)
    - end_date: 종료일 (옵션)
    - limit: 최대 조회 개수 (기본 100, 최대 1000)
    """
    # 종목 확인
    stock = db.query(Stock).filter(Stock.ticker == ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")

    # 가격 데이터 조회
    query = db.query(StockPrice).filter(StockPrice.stock_id == stock.id)

    # 날짜 필터링 - trade_date 사용
    if start_date:
        query = query.filter(StockPrice.trade_date >= start_date)
    if end_date:
        query = query.filter(StockPrice.trade_date <= end_date)

    # 날짜 역순 정렬 (최신 데이터 먼저) - trade_date 사용
    query = query.order_by(StockPrice.trade_date.desc())

    total = query.count()
    items = query.limit(limit).all()

    return StockPriceListResponse(
        ticker=ticker,
        total=total,
        items=items
    )