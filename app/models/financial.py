from sqlalchemy import Column, Integer, BigInteger, Date, DECIMAL, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class FinancialStatement(Base):
    """재무제표 데이터 모델"""

    __tablename__ = "financial_statements"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False, index=True)
    fiscal_quarter = Column(Integer)  # 1~3, NULL이면 연간
    fiscal_date = Column(Date, nullable=False, index=True)  # 재무제표 기준일
    report_type = Column(String(20), nullable=False, index=True)  # annual, Q1, Q2, Q3
    report_date = Column(Date, nullable=False, index=True)  # 보고서 제출일

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
        return f"<FinancialStatement(stock_id={self.stock_id}, year={self.fiscal_year}, type={self.report_type})>"


class FinancialRatio(Base):
    """재무 비율 모델"""

    __tablename__ = "financial_ratios"

    id = Column(BigInteger, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True)
    fiscal_date = Column(Date, nullable=False, index=True)  # 재무제표 기준일
    report_type = Column(String(20), nullable=False, index=True)  # annual, Q1, Q2, Q3

    # 수익성
    roe = Column(DECIMAL(10, 4))  # ROE (%)
    roa = Column(DECIMAL(10, 4))  # ROA (%)
    operating_margin = Column(DECIMAL(10, 4))  # 영업이익률 (%)
    net_margin = Column(DECIMAL(10, 4))  # 순이익률 (%)

    # 안정성
    debt_ratio = Column(DECIMAL(10, 4))  # 부채비율 (%)

    # 밸류에이션
    per = Column(DECIMAL(10, 4))  # PER
    pbr = Column(DECIMAL(10, 4))  # PBR
    psr = Column(DECIMAL(10, 4))  # PSR

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FinancialRatio(stock_id={self.stock_id}, fiscal_date={self.fiscal_date}, type={self.report_type})>"