from sqlalchemy import Column, Integer, BigInteger, Date, DECIMAL, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class FinancialStatement(Base):
    """재무제표 데이터 모델"""

    __tablename__ = "financial_statements"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_quarter = Column(Integer)  # 1~4, NULL이면 연간
    statement_type = Column(String(20), nullable=False)  # IS, BS, CF
    report_date = Column(Date, nullable=False, index=True)

    # 손익계산서
    revenue = Column(DECIMAL(20, 2))
    operating_income = Column(DECIMAL(20, 2))
    net_income = Column(DECIMAL(20, 2))
    ebitda = Column(DECIMAL(20, 2))

    # 재무상태표
    total_assets = Column(DECIMAL(20, 2))
    total_liabilities = Column(DECIMAL(20, 2))
    total_equity = Column(DECIMAL(20, 2))

    # 현금흐름표
    operating_cash_flow = Column(DECIMAL(20, 2))
    investing_cash_flow = Column(DECIMAL(20, 2))
    financing_cash_flow = Column(DECIMAL(20, 2))

    currency = Column(String(10), default="KRW")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FinancialStatement(stock_id={self.stock_id}, year={self.fiscal_year}, type={self.statement_type})>"


class FinancialRatio(Base):
    """재무 비율 모델"""

    __tablename__ = "financial_ratios"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # 수익성
    roe = Column(DECIMAL(10, 4))
    roa = Column(DECIMAL(10, 4))
    operating_margin = Column(DECIMAL(10, 4))
    net_margin = Column(DECIMAL(10, 4))

    # 안정성
    debt_ratio = Column(DECIMAL(10, 4))
    current_ratio = Column(DECIMAL(10, 4))
    quick_ratio = Column(DECIMAL(10, 4))

    # 밸류에이션
    per = Column(DECIMAL(10, 4))
    pbr = Column(DECIMAL(10, 4))
    psr = Column(DECIMAL(10, 4))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FinancialRatio(stock_id={self.stock_id}, date={self.date})>"