"""
데이터 품질 검증 서비스
app/services/data_quality_checker.py

재무 데이터의 품질을 검증하고 이상치를 탐지합니다.
"""
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.models import Stock, FinancialStatement, StockMarketData, FinancialRatio


class DataQualityChecker:
    """데이터 품질 검증기"""

    def __init__(self):
        # 재무비율 정상 범위 (경험적 임계값)
        self.thresholds = {
            'roe': {'min': -100, 'max': 100, 'extreme': 50},  # %
            'roa': {'min': -100, 'max': 100, 'extreme': 30},  # %
            'per': {'min': -100, 'max': 1000, 'extreme': 100},
            'pbr': {'min': -10, 'max': 100, 'extreme': 20},
            'psr': {'min': -10, 'max': 100, 'extreme': 20},
            'debt_ratio': {'min': 0, 'max': 1000, 'extreme': 200},  # %
            'operating_margin': {'min': -100, 'max': 100, 'extreme': 50},  # %
            'net_margin': {'min': -100, 'max': 100, 'extreme': 50},  # %
        }

    def check_data_completeness(self, db: Session, market: Optional[str] = None) -> Dict:
        """
        데이터 완성도 검증

        Args:
            db: 데이터베이스 세션
            market: 시장 필터 (KOSPI, KOSDAQ, None=전체)

        Returns:
            완성도 리포트
        """
        # 전체 종목 수
        query = db.query(Stock)
        if market:
            query = query.filter(Stock.market == market)

        total_stocks = query.count()

        # 재무제표 보유 종목
        stocks_with_fs = db.query(Stock.id).join(
            FinancialStatement,
            Stock.id == FinancialStatement.stock_id
        )
        if market:
            stocks_with_fs = stocks_with_fs.join(Stock).filter(Stock.market == market)

        stocks_with_fs_count = stocks_with_fs.distinct().count()

        # 시가총액 보유 종목
        stocks_with_mc = db.query(Stock.id).join(
            StockMarketData,
            Stock.id == StockMarketData.stock_id
        ).filter(
            StockMarketData.market_cap.isnot(None),
            StockMarketData.market_cap > 0
        )
        if market:
            stocks_with_mc = stocks_with_mc.join(Stock).filter(Stock.market == market)

        stocks_with_mc_count = stocks_with_mc.distinct().count()

        # 재무비율 보유 종목
        stocks_with_ratios = db.query(Stock.id).join(
            FinancialRatio,
            Stock.id == FinancialRatio.stock_id
        )
        if market:
            stocks_with_ratios = stocks_with_ratios.join(Stock).filter(Stock.market == market)

        stocks_with_ratios_count = stocks_with_ratios.distinct().count()

        # 재무제표는 있지만 시가총액 없음
        fs_ids = set([s[0] for s in stocks_with_fs.all()])
        mc_ids = set([s[0] for s in stocks_with_mc.all()])

        fs_only = len(fs_ids - mc_ids)
        mc_only = len(mc_ids - fs_ids)
        both = len(fs_ids & mc_ids)

        # 계산 가능하지만 비율 없음
        ready_ids = fs_ids & mc_ids
        ratio_ids = set([s[0] for s in stocks_with_ratios.all()])
        need_calculation = len(ready_ids - ratio_ids)

        return {
            "total_stocks": total_stocks,
            "with_financial_statements": stocks_with_fs_count,
            "with_market_cap": stocks_with_mc_count,
            "with_ratios": stocks_with_ratios_count,
            "data_overlap": {
                "fs_and_mc": both,
                "fs_only": fs_only,
                "mc_only": mc_only,
            },
            "calculation_status": {
                "ready": len(ready_ids),
                "calculated": len(ratio_ids),
                "pending": need_calculation,
            },
            "coverage_rates": {
                "financial_statements": round(stocks_with_fs_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
                "market_cap": round(stocks_with_mc_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
                "ratios": round(stocks_with_ratios_count / total_stocks * 100, 2) if total_stocks > 0 else 0,
            }
        }

    def check_ratio_anomalies(
            self,
            db: Session,
            market: Optional[str] = None,
            limit: int = 100
    ) -> Dict:
        """
        재무비율 이상치 탐지

        Args:
            db: 데이터베이스 세션
            market: 시장 필터
            limit: 최대 조회 개수

        Returns:
            이상치 리포트
        """
        anomalies = {
            'extreme_values': [],  # 극단값
            'negative_values': [],  # 음수 (PER, PBR, PSR)
            'high_null_ratio': [],  # NULL 비율이 높은 종목
        }

        # 재무비율이 있는 종목 조회
        query = db.query(Stock).join(
            FinancialRatio,
            Stock.id == FinancialRatio.stock_id
        ).distinct()

        if market:
            query = query.filter(Stock.market == market)

        stocks = query.limit(limit).all()

        for stock in stocks:
            # 해당 종목의 최신 비율 조회
            latest_ratio = db.query(FinancialRatio).filter(
                FinancialRatio.stock_id == stock.id
            ).order_by(FinancialRatio.fiscal_date.desc()).first()

            if not latest_ratio:
                continue

            # NULL 개수 체크
            null_count = sum([
                1 for attr in ['roe', 'roa', 'per', 'pbr', 'psr', 'debt_ratio']
                if getattr(latest_ratio, attr) is None
            ])

            if null_count >= 4:  # 6개 중 4개 이상 NULL
                anomalies['high_null_ratio'].append({
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'null_count': null_count,
                    'total_fields': 6,
                    'fiscal_date': latest_ratio.fiscal_date.isoformat(),
                })

            # 극단값 체크
            extreme_flags = []

            for field, thresholds in self.thresholds.items():
                value = getattr(latest_ratio, field)

                if value is None:
                    continue

                value = float(value)

                # 음수 체크 (PER, PBR, PSR은 음수면 이상)
                if field in ['per', 'pbr', 'psr'] and value < 0:
                    anomalies['negative_values'].append({
                        'ticker': stock.ticker,
                        'name': stock.name,
                        'field': field,
                        'value': round(value, 2),
                        'fiscal_date': latest_ratio.fiscal_date.isoformat(),
                    })

                # 극단값 체크
                if value < thresholds['min'] or value > thresholds['max']:
                    extreme_flags.append({
                        'field': field,
                        'value': round(value, 2),
                        'min': thresholds['min'],
                        'max': thresholds['max'],
                    })

            if extreme_flags:
                anomalies['extreme_values'].append({
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'fiscal_date': latest_ratio.fiscal_date.isoformat(),
                    'anomalies': extreme_flags,
                })

        return {
            "total_checked": len(stocks),
            "anomaly_counts": {
                "extreme_values": len(anomalies['extreme_values']),
                "negative_values": len(anomalies['negative_values']),
                "high_null_ratio": len(anomalies['high_null_ratio']),
            },
            "anomalies": anomalies,
        }

    def check_missing_statements(
            self,
            db: Session,
            market: Optional[str] = None,
            limit: int = 50
    ) -> Dict:
        """
        누락된 재무제표 확인

        Args:
            db: 데이터베이스 세션
            market: 시장 필터
            limit: 최대 조회 개수

        Returns:
            누락 리포트
        """
        missing_report = {
            'no_financial_statements': [],  # 재무제표 없음
            'no_market_cap': [],  # 시가총액 없음
            'incomplete_years': [],  # 연도별 누락
        }

        # 재무제표가 없는 종목
        stocks_without_fs = db.query(Stock).outerjoin(
            FinancialStatement,
            Stock.id == FinancialStatement.stock_id
        ).filter(
            FinancialStatement.id.is_(None)
        )

        if market:
            stocks_without_fs = stocks_without_fs.filter(Stock.market == market)

        for stock in stocks_without_fs.limit(limit).all():
            missing_report['no_financial_statements'].append({
                'ticker': stock.ticker,
                'name': stock.name,
                'market': stock.market,
            })

        # 시가총액이 없는 종목 (재무제표는 있음)
        stocks_with_fs = db.query(Stock.id).join(
            FinancialStatement,
            Stock.id == FinancialStatement.stock_id
        ).distinct().subquery()

        stocks_without_mc = db.query(Stock).filter(
            Stock.id.in_(db.query(stocks_with_fs.c.id))
        ).outerjoin(
            StockMarketData,
            and_(
                Stock.id == StockMarketData.stock_id,
                StockMarketData.market_cap.isnot(None),
                StockMarketData.market_cap > 0
            )
        ).filter(
            StockMarketData.id.is_(None)
        )

        if market:
            stocks_without_mc = stocks_without_mc.filter(Stock.market == market)

        for stock in stocks_without_mc.limit(limit).all():
            missing_report['no_market_cap'].append({
                'ticker': stock.ticker,
                'name': stock.name,
                'market': stock.market,
            })

        return {
            "total_no_fs": len(missing_report['no_financial_statements']),
            "total_no_mc": len(missing_report['no_market_cap']),
            "showing": limit,
            "missing_data": missing_report,
        }

    def generate_quality_report(
            self,
            db: Session,
            market: Optional[str] = None
    ) -> Dict:
        """
        전체 데이터 품질 리포트 생성

        Args:
            db: 데이터베이스 세션
            market: 시장 필터

        Returns:
            종합 품질 리포트
        """
        print(f"\n{'=' * 80}")
        print(f"📊 데이터 품질 검증 리포트 - {market or '전체 시장'}")
        print(f"{'=' * 80}\n")

        # 1. 데이터 완성도
        print("1️⃣  데이터 완성도 체크...")
        completeness = self.check_data_completeness(db, market)

        # 2. 이상치 탐지
        print("2️⃣  이상치 탐지...")
        anomalies = self.check_ratio_anomalies(db, market, limit=100)

        # 3. 누락 데이터
        print("3️⃣  누락 데이터 확인...")
        missing = self.check_missing_statements(db, market, limit=50)

        # 품질 점수 계산 (0-100)
        quality_score = self._calculate_quality_score(completeness, anomalies, missing)

        print(f"\n{'=' * 80}")
        print(f"✅ 품질 검증 완료!")
        print(f"{'=' * 80}\n")

        return {
            "generated_at": datetime.now().isoformat(),
            "market": market or "ALL",
            "quality_score": quality_score,
            "completeness": completeness,
            "anomalies": anomalies,
            "missing_data": missing,
            "summary": {
                "total_stocks": completeness['total_stocks'],
                "data_quality": self._get_quality_grade(quality_score),
                "coverage_rate": completeness['coverage_rates']['ratios'],
                "issues_found": sum([
                    anomalies['anomaly_counts']['extreme_values'],
                    anomalies['anomaly_counts']['negative_values'],
                    anomalies['anomaly_counts']['high_null_ratio'],
                    missing['total_no_fs'],
                    missing['total_no_mc'],
                ])
            }
        }

    def _calculate_quality_score(
            self,
            completeness: Dict,
            anomalies: Dict,
            missing: Dict
    ) -> float:
        """
        데이터 품질 점수 계산 (0-100)

        가중치:
        - 완성도: 50%
        - 이상치: 30%
        - 누락: 20%
        """
        # 완성도 점수 (재무비율 커버리지 기준)
        completeness_score = completeness['coverage_rates']['ratios']

        # 이상치 점수 (이상치가 적을수록 높은 점수)
        total_checked = anomalies['total_checked']
        total_anomalies = sum(anomalies['anomaly_counts'].values())

        if total_checked > 0:
            anomaly_rate = (total_anomalies / total_checked) * 100
            anomaly_score = max(0, 100 - anomaly_rate)
        else:
            anomaly_score = 100

        # 누락 점수
        total_stocks = completeness['total_stocks']
        total_missing = missing['total_no_fs'] + missing['total_no_mc']

        if total_stocks > 0:
            missing_rate = (total_missing / total_stocks) * 100
            missing_score = max(0, 100 - missing_rate)
        else:
            missing_score = 100

        # 가중 평균
        quality_score = (
                completeness_score * 0.5 +
                anomaly_score * 0.3 +
                missing_score * 0.2
        )

        return round(quality_score, 2)

    def _get_quality_grade(self, score: float) -> str:
        """품질 점수를 등급으로 변환"""
        if score >= 90:
            return "A (Excellent)"
        elif score >= 80:
            return "B (Good)"
        elif score >= 70:
            return "C (Fair)"
        elif score >= 60:
            return "D (Poor)"
        else:
            return "F (Critical)"