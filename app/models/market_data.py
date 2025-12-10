from sqlalchemy import Column, Integer, BigInteger, Date, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class StockMarketData(Base):
    """일별 시장 데이터 모델"""

    __tablename__ = "stock_market_data"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    market_cap = Column(DECIMAL(20, 2), comment="시가총액")
    trading_value = Column(DECIMAL(20, 2), comment="거래대금")
    shares_outstanding = Column(BigInteger, comment="상장주식수")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<StockMarketData(stock_id={self.stock_id}, date={self.trade_date})>"