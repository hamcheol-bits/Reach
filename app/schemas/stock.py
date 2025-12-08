from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StockBase(BaseModel):
    """주식 기본 스키마"""
    ticker: str = Field(..., description="종목 코드")
    name: str = Field(..., description="종목명")
    market: str = Field(..., description="시장 (KOSPI, NASDAQ 등)")
    sector: Optional[str] = Field(None, description="섹터")
    industry: Optional[str] = Field(None, description="산업")
    country: str = Field(..., description="국가 코드 (KR, US)")


class StockCreate(StockBase):
    """주식 생성 스키마"""
    pass


class StockResponse(StockBase):
    """주식 응답 스키마"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class StockListResponse(BaseModel):
    """주식 목록 응답 스키마"""
    total: int
    items: list[StockResponse]