"""
종목 스크리닝 서비스
app/services/stock_screener.py

재무비율 기반으로 종목을 필터링하고 랭킹합니다.
"""
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func

from app.models import Stock, FinancialRatio, StockMarketData


class StockScreener:
    """종목 스크리닝"""

    @staticmethod
    def get_latest_ratios_subquery(db: Session):
        """
        각 종목의 최신 재무비율 서브쿼리

        Returns:
            최신 fiscal_date를 가진 재무비율의 stock_id 서브쿼리
        """
        subquery = (
            db.query(
                FinancialRatio.stock_id,
                func.max(FinancialRatio.fiscal_date).label('latest_date')
            )
            .filter(FinancialRatio.report_type == 'annual')  # 연간 재무제표만
            .group_by(FinancialRatio.stock_id)
            .subquery()
        )
        return subquery

    def screen_undervalued(
        self,
        db: Session,
        max_per: float = 10.0,
        max_pbr: float = 1.0,
        min_market_cap: Optional[float] = None,
        market: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        저평가 종목 스크리닝

        기준:
        - PER < 10 (저평가)
        - PBR < 1 (장부가치 대비 저평가)
        - 시가총액 필터 (선택)

        Args:
            db: 데이터베이스 세션
            max_per: 최대 PER
            max_pbr: 최대 PBR
            min_market_cap: 최소 시가총액 (억 원)
            market: 시장 (KOSPI, KOSDAQ)
            limit: 최대 결과 수

        Returns:
            저평가 종목 리스트
        """
        # 최신 재무비율 서브쿼리
        latest_ratios = self.get_latest_ratios_subquery(db)

        # 최신 시가총액 서브쿼리
        latest_market_cap_sq = (
            db.query(
                StockMarketData.stock_id,
                func.max(StockMarketData.trade_date).label('latest_date')
            )
            .group_by(StockMarketData.stock_id)
            .subquery()
        )

        # 메인 쿼리
        query = (
            db.query(
                Stock.ticker,
                Stock.name,
                Stock.market,
                Stock.sector,
                FinancialRatio.fiscal_date,
                FinancialRatio.roe,
                FinancialRatio.roa,
                FinancialRatio.per,
                FinancialRatio.pbr,
                FinancialRatio.debt_ratio,
                StockMarketData.market_cap
            )
            .join(FinancialRatio, Stock.id == FinancialRatio.stock_id)
            .join(
                latest_ratios,
                and_(
                    FinancialRatio.stock_id == latest_ratios.c.stock_id,
                    FinancialRatio.fiscal_date == latest_ratios.c.latest_date
                )
            )
            .outerjoin(
                latest_market_cap_sq,
                Stock.id == latest_market_cap_sq.c.stock_id
            )
            .outerjoin(
                StockMarketData,
                and_(
                    StockMarketData.stock_id == latest_market_cap_sq.c.stock_id,
                    StockMarketData.trade_date == latest_market_cap_sq.c.latest_date
                )
            )
            .filter(
                Stock.country == 'KR',
                FinancialRatio.per.isnot(None),
                FinancialRatio.per > 0,
                FinancialRatio.per <= max_per,
                FinancialRatio.pbr.isnot(None),
                FinancialRatio.pbr > 0,
                FinancialRatio.pbr <= max_pbr
            )
        )

        # 시장 필터
        if market:
            query = query.filter(Stock.market == market)

        # 시가총액 필터
        if min_market_cap:
            query = query.filter(
                StockMarketData.market_cap >= min_market_cap * 100000000  # 억 원 -> 원
            )

        # 정렬: PER + PBR 낮은 순
        query = query.order_by(
            asc(FinancialRatio.per + FinancialRatio.pbr)
        ).limit(limit)

        results = []
        for row in query.all():
            results.append({
                'ticker': row.ticker,
                'name': row.name,
                'market': row.market,
                'sector': row.sector,
                'fiscal_date': row.fiscal_date.isoformat(),
                'roe': float(row.roe) if row.roe else None,
                'roa': float(row.roa) if row.roa else None,
                'per': float(row.per) if row.per else None,
                'pbr': float(row.pbr) if row.pbr else None,
                'debt_ratio': float(row.debt_ratio) if row.debt_ratio else None,
                'market_cap': float(row.market_cap) / 100000000 if row.market_cap else None,  # 억 원
                'score': float(row.per + row.pbr) if row.per and row.pbr else None
            })

        return results

    def screen_quality(
        self,
        db: Session,
        min_roe: float = 15.0,
        max_debt_ratio: float = 100.0,
        min_market_cap: Optional[float] = None,
        market: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        우량 종목 스크리닝

        기준:
        - ROE > 15% (높은 수익성)
        - 부채비율 < 100% (안정성)
        - 시가총액 필터 (선택)

        Args:
            db: 데이터베이스 세션
            min_roe: 최소 ROE (%)
            max_debt_ratio: 최대 부채비율 (%)
            min_market_cap: 최소 시가총액 (억 원)
            market: 시장 (KOSPI, KOSDAQ)
            limit: 최대 결과 수

        Returns:
            우량 종목 리스트
        """
        latest_ratios = self.get_latest_ratios_subquery(db)

        latest_market_cap_sq = (
            db.query(
                StockMarketData.stock_id,
                func.max(StockMarketData.trade_date).label('latest_date')
            )
            .group_by(StockMarketData.stock_id)
            .subquery()
        )

        query = (
            db.query(
                Stock.ticker,
                Stock.name,
                Stock.market,
                Stock.sector,
                FinancialRatio.fiscal_date,
                FinancialRatio.roe,
                FinancialRatio.roa,
                FinancialRatio.operating_margin,
                FinancialRatio.debt_ratio,
                FinancialRatio.per,
                FinancialRatio.pbr,
                StockMarketData.market_cap
            )
            .join(FinancialRatio, Stock.id == FinancialRatio.stock_id)
            .join(
                latest_ratios,
                and_(
                    FinancialRatio.stock_id == latest_ratios.c.stock_id,
                    FinancialRatio.fiscal_date == latest_ratios.c.latest_date
                )
            )
            .outerjoin(
                latest_market_cap_sq,
                Stock.id == latest_market_cap_sq.c.stock_id
            )
            .outerjoin(
                StockMarketData,
                and_(
                    StockMarketData.stock_id == latest_market_cap_sq.c.stock_id,
                    StockMarketData.trade_date == latest_market_cap_sq.c.latest_date
                )
            )
            .filter(
                Stock.country == 'KR',
                FinancialRatio.roe.isnot(None),
                FinancialRatio.roe >= min_roe,
                FinancialRatio.debt_ratio.isnot(None),
                FinancialRatio.debt_ratio <= max_debt_ratio
            )
        )

        if market:
            query = query.filter(Stock.market == market)

        if min_market_cap:
            query = query.filter(
                StockMarketData.market_cap >= min_market_cap * 100000000
            )

        # 정렬: ROE 높은 순
        query = query.order_by(desc(FinancialRatio.roe)).limit(limit)

        results = []
        for row in query.all():
            results.append({
                'ticker': row.ticker,
                'name': row.name,
                'market': row.market,
                'sector': row.sector,
                'fiscal_date': row.fiscal_date.isoformat(),
                'roe': float(row.roe) if row.roe else None,
                'roa': float(row.roa) if row.roa else None,
                'operating_margin': float(row.operating_margin) if row.operating_margin else None,
                'debt_ratio': float(row.debt_ratio) if row.debt_ratio else None,
                'per': float(row.per) if row.per else None,
                'pbr': float(row.pbr) if row.pbr else None,
                'market_cap': float(row.market_cap) / 100000000 if row.market_cap else None,
                'quality_score': float(row.roe) if row.roe else None
            })

        return results

    def screen_growth(
        self,
        db: Session,
        min_roe: float = 10.0,
        max_per: float = 30.0,
        min_market_cap: Optional[float] = None,
        market: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        성장 종목 스크리닝

        기준:
        - ROE > 10% (수익성)
        - PER < 30 (합리적 밸류에이션)

        Args:
            db: 데이터베이스 세션
            min_roe: 최소 ROE (%)
            max_per: 최대 PER
            min_market_cap: 최소 시가총액 (억 원)
            market: 시장 (KOSPI, KOSDAQ)
            limit: 최대 결과 수

        Returns:
            성장 종목 리스트
        """
        latest_ratios = self.get_latest_ratios_subquery(db)

        latest_market_cap_sq = (
            db.query(
                StockMarketData.stock_id,
                func.max(StockMarketData.trade_date).label('latest_date')
            )
            .group_by(StockMarketData.stock_id)
            .subquery()
        )

        query = (
            db.query(
                Stock.ticker,
                Stock.name,
                Stock.market,
                Stock.sector,
                FinancialRatio.fiscal_date,
                FinancialRatio.roe,
                FinancialRatio.roa,
                FinancialRatio.operating_margin,
                FinancialRatio.per,
                FinancialRatio.pbr,
                FinancialRatio.debt_ratio,
                StockMarketData.market_cap
            )
            .join(FinancialRatio, Stock.id == FinancialRatio.stock_id)
            .join(
                latest_ratios,
                and_(
                    FinancialRatio.stock_id == latest_ratios.c.stock_id,
                    FinancialRatio.fiscal_date == latest_ratios.c.latest_date
                )
            )
            .outerjoin(
                latest_market_cap_sq,
                Stock.id == latest_market_cap_sq.c.stock_id
            )
            .outerjoin(
                StockMarketData,
                and_(
                    StockMarketData.stock_id == latest_market_cap_sq.c.stock_id,
                    StockMarketData.trade_date == latest_market_cap_sq.c.latest_date
                )
            )
            .filter(
                Stock.country == 'KR',
                FinancialRatio.roe.isnot(None),
                FinancialRatio.roe >= min_roe,
                FinancialRatio.per.isnot(None),
                FinancialRatio.per > 0,
                FinancialRatio.per <= max_per
            )
        )

        if market:
            query = query.filter(Stock.market == market)

        if min_market_cap:
            query = query.filter(
                StockMarketData.market_cap >= min_market_cap * 100000000
            )

        # 정렬: ROE/PER 비율 높은 순 (성장 대비 밸류에이션이 좋은 순)
        query = query.order_by(
            desc(FinancialRatio.roe / FinancialRatio.per)
        ).limit(limit)

        results = []
        for row in query.all():
            growth_score = float(row.roe / row.per) if row.roe and row.per else None

            results.append({
                'ticker': row.ticker,
                'name': row.name,
                'market': row.market,
                'sector': row.sector,
                'fiscal_date': row.fiscal_date.isoformat(),
                'roe': float(row.roe) if row.roe else None,
                'roa': float(row.roa) if row.roa else None,
                'operating_margin': float(row.operating_margin) if row.operating_margin else None,
                'per': float(row.per) if row.per else None,
                'pbr': float(row.pbr) if row.pbr else None,
                'debt_ratio': float(row.debt_ratio) if row.debt_ratio else None,
                'market_cap': float(row.market_cap) / 100000000 if row.market_cap else None,
                'growth_score': growth_score
            })

        return results

    def screen_custom(
        self,
        db: Session,
        min_roe: Optional[float] = None,
        max_roe: Optional[float] = None,
        min_per: Optional[float] = None,
        max_per: Optional[float] = None,
        min_pbr: Optional[float] = None,
        max_pbr: Optional[float] = None,
        min_debt_ratio: Optional[float] = None,
        max_debt_ratio: Optional[float] = None,
        min_market_cap: Optional[float] = None,
        max_market_cap: Optional[float] = None,
        market: Optional[str] = None,
        sector: Optional[str] = None,
        sort_by: str = 'roe',
        sort_order: str = 'desc',
        limit: int = 50
    ) -> List[Dict]:
        """
        커스텀 필터 스크리닝

        Args:
            db: 데이터베이스 세션
            min_roe, max_roe: ROE 범위 (%)
            min_per, max_per: PER 범위
            min_pbr, max_pbr: PBR 범위
            min_debt_ratio, max_debt_ratio: 부채비율 범위 (%)
            min_market_cap, max_market_cap: 시가총액 범위 (억 원)
            market: 시장 필터
            sector: 섹터 필터
            sort_by: 정렬 기준 (roe, per, pbr, market_cap)
            sort_order: 정렬 순서 (asc, desc)
            limit: 최대 결과 수

        Returns:
            필터링된 종목 리스트
        """
        latest_ratios = self.get_latest_ratios_subquery(db)

        latest_market_cap_sq = (
            db.query(
                StockMarketData.stock_id,
                func.max(StockMarketData.trade_date).label('latest_date')
            )
            .group_by(StockMarketData.stock_id)
            .subquery()
        )

        query = (
            db.query(
                Stock.ticker,
                Stock.name,
                Stock.market,
                Stock.sector,
                FinancialRatio.fiscal_date,
                FinancialRatio.roe,
                FinancialRatio.roa,
                FinancialRatio.operating_margin,
                FinancialRatio.net_margin,
                FinancialRatio.debt_ratio,
                FinancialRatio.per,
                FinancialRatio.pbr,
                FinancialRatio.psr,
                StockMarketData.market_cap
            )
            .join(FinancialRatio, Stock.id == FinancialRatio.stock_id)
            .join(
                latest_ratios,
                and_(
                    FinancialRatio.stock_id == latest_ratios.c.stock_id,
                    FinancialRatio.fiscal_date == latest_ratios.c.latest_date
                )
            )
            .outerjoin(
                latest_market_cap_sq,
                Stock.id == latest_market_cap_sq.c.stock_id
            )
            .outerjoin(
                StockMarketData,
                and_(
                    StockMarketData.stock_id == latest_market_cap_sq.c.stock_id,
                    StockMarketData.trade_date == latest_market_cap_sq.c.latest_date
                )
            )
            .filter(Stock.country == 'KR')
        )

        # 재무비율 필터
        if min_roe is not None:
            query = query.filter(FinancialRatio.roe >= min_roe)
        if max_roe is not None:
            query = query.filter(FinancialRatio.roe <= max_roe)

        if min_per is not None:
            query = query.filter(FinancialRatio.per >= min_per)
        if max_per is not None:
            query = query.filter(FinancialRatio.per <= max_per)

        if min_pbr is not None:
            query = query.filter(FinancialRatio.pbr >= min_pbr)
        if max_pbr is not None:
            query = query.filter(FinancialRatio.pbr <= max_pbr)

        if min_debt_ratio is not None:
            query = query.filter(FinancialRatio.debt_ratio >= min_debt_ratio)
        if max_debt_ratio is not None:
            query = query.filter(FinancialRatio.debt_ratio <= max_debt_ratio)

        # 시가총액 필터
        if min_market_cap is not None:
            query = query.filter(StockMarketData.market_cap >= min_market_cap * 100000000)
        if max_market_cap is not None:
            query = query.filter(StockMarketData.market_cap <= max_market_cap * 100000000)

        # 시장/섹터 필터
        if market:
            query = query.filter(Stock.market == market)
        if sector:
            query = query.filter(Stock.sector == sector)

        # 정렬
        sort_column_map = {
            'roe': FinancialRatio.roe,
            'per': FinancialRatio.per,
            'pbr': FinancialRatio.pbr,
            'debt_ratio': FinancialRatio.debt_ratio,
            'market_cap': StockMarketData.market_cap
        }

        sort_column = sort_column_map.get(sort_by, FinancialRatio.roe)
        if sort_order == 'desc':
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        query = query.limit(limit)

        results = []
        for row in query.all():
            results.append({
                'ticker': row.ticker,
                'name': row.name,
                'market': row.market,
                'sector': row.sector,
                'fiscal_date': row.fiscal_date.isoformat(),
                'roe': float(row.roe) if row.roe else None,
                'roa': float(row.roa) if row.roa else None,
                'operating_margin': float(row.operating_margin) if row.operating_margin else None,
                'net_margin': float(row.net_margin) if row.net_margin else None,
                'debt_ratio': float(row.debt_ratio) if row.debt_ratio else None,
                'per': float(row.per) if row.per else None,
                'pbr': float(row.pbr) if row.pbr else None,
                'psr': float(row.psr) if row.psr else None,
                'market_cap': float(row.market_cap) / 100000000 if row.market_cap else None
            })

        return results

    def compare_by_sector(
        self,
        db: Session,
        market: Optional[str] = None,
        limit_per_sector: int = 5
    ) -> Dict:
        """
        섹터별 상위 종목 비교

        각 섹터의 ROE 상위 종목을 반환합니다.

        Args:
            db: 데이터베이스 세션
            market: 시장 필터
            limit_per_sector: 섹터당 최대 종목 수

        Returns:
            섹터별 종목 딕셔너리
        """
        latest_ratios = self.get_latest_ratios_subquery(db)

        query = (
            db.query(
                Stock.sector,
                Stock.ticker,
                Stock.name,
                Stock.market,
                FinancialRatio.roe,
                FinancialRatio.per,
                FinancialRatio.pbr,
                FinancialRatio.debt_ratio
            )
            .join(FinancialRatio, Stock.id == FinancialRatio.stock_id)
            .join(
                latest_ratios,
                and_(
                    FinancialRatio.stock_id == latest_ratios.c.stock_id,
                    FinancialRatio.fiscal_date == latest_ratios.c.latest_date
                )
            )
            .filter(
                Stock.country == 'KR',
                Stock.sector.isnot(None),
                FinancialRatio.roe.isnot(None)
            )
        )

        if market:
            query = query.filter(Stock.market == market)

        query = query.order_by(Stock.sector, desc(FinancialRatio.roe))

        # 섹터별 그룹핑
        sectors = {}
        for row in query.all():
            sector = row.sector

            if sector not in sectors:
                sectors[sector] = []

            if len(sectors[sector]) < limit_per_sector:
                sectors[sector].append({
                    'ticker': row.ticker,
                    'name': row.name,
                    'market': row.market,
                    'roe': float(row.roe) if row.roe else None,
                    'per': float(row.per) if row.per else None,
                    'pbr': float(row.pbr) if row.pbr else None,
                    'debt_ratio': float(row.debt_ratio) if row.debt_ratio else None
                })

        return sectors