from sqlalchemy import Column, Integer, BigInteger, Date, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class StockPrice(Base):
    """주가 데이터 모델"""

    __tablename__ = "stock_prices"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(DECIMAL(20, 4))
    high = Column(DECIMAL(20, 4))
    low = Column(DECIMAL(20, 4))
    close = Column(DECIMAL(20, 4), nullable=False)
    volume = Column(BigInteger)
    adjusted_close = Column(DECIMAL(20, 4))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<StockPrice(stock_id={self.stock_id}, date={self.date}, close={self.close})>"