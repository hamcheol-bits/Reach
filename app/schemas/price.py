from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockPriceBase(BaseModel):
    """주가 기본 스키마"""
    stock_id: int = Field(..., description="주식 ID")
    trade_date: date = Field(..., description="날짜")
    open: Optional[float] = Field(None, description="시가")
    high: Optional[float] = Field(None, description="고가")
    low: Optional[float] = Field(None, description="저가")
    close: float = Field(..., description="종가")
    volume: Optional[int] = Field(None, description="거래량")
    adjusted_close: Optional[float] = Field(None, description="조정 종가")


class StockPriceCreate(StockPriceBase):
    """주가 생성 스키마"""
    pass


class StockPriceResponse(StockPriceBase):
    """주가 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: datetime


    class Config:
        from_attributes = True


class StockPriceListResponse(BaseModel):
    """주가 목록 응답 스키마"""
    ticker: str
    total: int
    items: list[StockPriceResponse]