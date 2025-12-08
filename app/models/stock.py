from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Stock(Base):
    """주식 기본 정보 모델"""

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    market = Column(String(20), nullable=False, index=True)  # KOSPI, NASDAQ 등
    sector = Column(String(100))
    industry = Column(String(100))
    country = Column(String(10), nullable=False, index=True)  # KR, US
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Stock(ticker={self.ticker}, name={self.name}, market={self.market})>"