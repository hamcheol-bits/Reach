"""
재무비율 계산 서비스

재무제표와 시장 데이터를 바탕으로 주요 재무비율을 자동 계산합니다.
"""
from datetime import datetime
from typing import Optional, Dict, List
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import Stock, FinancialStatement, FinancialRatio, StockPrice, StockMarketData


class FinancialRatioCalculator:
    """재무비율 계산기"""

    @staticmethod
    def calculate_roe(net_income: float, total_equity: float) -> Optional[float]:
        """
        ROE (Return on Equity) = 당기순이익 / 자본총계 × 100

        Args:
            net_income: 당기순이익
            total_equity: 자본총계

        Returns:
            ROE (%) 또는 None
        """
        if not total_equity or total_equity <= 0:
            return None

        return (net_income / total_equity) * 100

    @staticmethod
    def calculate_roa(net_income: float, total_assets: float) -> Optional[float]:
        """
        ROA (Return on Assets) = 당기순이익 / 자산총계 × 100

        Args:
            net_income: 당기순이익
            total_assets: 자산총계

        Returns:
            ROA (%) 또는 None
        """
        if not total_assets or total_assets <= 0:
            return None

        return (net_income / total_assets) * 100

    @staticmethod
    def calculate_operating_margin(operating_income: float, revenue: float) -> Optional[float]:
        """
        영업이익률 = 영업이익 / 매출액 × 100

        Args:
            operating_income: 영업이익
            revenue: 매출액

        Returns:
            영업이익률 (%) 또는 None
        """
        if not revenue or revenue <= 0:
            return None

        return (operating_income / revenue) * 100

    @staticmethod
    def calculate_net_margin(net_income: float, revenue: float) -> Optional[float]:
        """
        순이익률 = 당기순이익 / 매출액 × 100

        Args:
            net_income: 당기순이익
            revenue: 매출액

        Returns:
            순이익률 (%) 또는 None
        """
        if not revenue or revenue <= 0:
            return None

        return (net_income / revenue) * 100

    @staticmethod
    def calculate_debt_ratio(total_liabilities: float, total_equity: float) -> Optional[float]:
        """
        부채비율 = 부채총계 / 자본총계 × 100

        Args:
            total_liabilities: 부채총계
            total_equity: 자본총계

        Returns:
            부채비율 (%) 또는 None
        """
        if not total_equity or total_equity <= 0:
            return None

        return (total_liabilities / total_equity) * 100

    @staticmethod
    def calculate_per(market_cap: float, net_income: float) -> Optional[float]:
        """
        PER (Price to Earnings Ratio) = 시가총액 / 당기순이익

        극단값 필터링: PER > 10000 또는 PER < -1000이면 None 반환

        Args:
            market_cap: 시가총액
            net_income: 당기순이익

        Returns:
            PER 또는 None
        """
        if not net_income or net_income <= 0:
            return None

        per = market_cap / net_income

        # 극단값 필터링 (PER이 너무 크거나 작으면 의미 없음)
        if per > 10000 or per < -1000:
            return None

        return per

    @staticmethod
    def calculate_pbr(market_cap: float, total_equity: float) -> Optional[float]:
        """
        PBR (Price to Book Ratio) = 시가총액 / 자본총계

        극단값 필터링: PBR > 1000 또는 PBR < -100이면 None 반환

        Args:
            market_cap: 시가총액
            total_equity: 자본총계

        Returns:
            PBR 또는 None
        """
        if not total_equity or total_equity <= 0:
            return None

        pbr = market_cap / total_equity

        # 극단값 필터링
        if pbr > 1000 or pbr < -100:
            return None

        return pbr

    @staticmethod
    def calculate_psr(market_cap: float, revenue: float) -> Optional[float]:
        """
        PSR (Price to Sales Ratio) = 시가총액 / 매출액

        극단값 필터링: PSR > 1000 또는 PSR < -100이면 None 반환

        Args:
            market_cap: 시가총액
            revenue: 매출액

        Returns:
            PSR 또는 None
        """
        if not revenue or revenue <= 0:
            return None

        psr = market_cap / revenue

        # 극단값 필터링
        if psr > 1000 or psr < -100:
            return None

        return psr

    def calculate_ratios_for_statement(
        self,
        db: Session,
        stock_id: int,
        fiscal_year: int,
        fiscal_quarter: Optional[int] = None
    ) -> Optional[Dict]:
        """
        특정 재무제표의 비율 계산

        Args:
            db: 데이터베이스 세션
            stock_id: 종목 ID
            fiscal_year: 사업연도
            fiscal_quarter: 분기 (None이면 연간)

        Returns:
            계산된 비율 딕셔너리 또는 None
        """
        try:
            # 1. 재무제표 조회
            statement = db.query(FinancialStatement).filter(
                FinancialStatement.stock_id == stock_id,
                FinancialStatement.fiscal_year == fiscal_year,
                FinancialStatement.fiscal_quarter == fiscal_quarter
            ).first()

            if not statement:
                print(f"⚠️  No financial statement found for stock_id={stock_id}, year={fiscal_year}")
                return None

            # 2. 시가총액 조회 (해당 연도 말일 기준)
            # 연간: 12월 31일, 분기: 해당 분기 말일
            if fiscal_quarter is None:
                # 연간: 12월 31일 또는 가장 가까운 날짜
                target_date = datetime(fiscal_year, 12, 31).date()
            else:
                # 분기별 말일
                quarter_end_months = {1: 3, 2: 6, 3: 9}
                month = quarter_end_months.get(fiscal_quarter, 12)
                # 해당 월의 마지막 날
                if month in [3, 6, 9]:
                    day = 31 if month == 3 else 30
                else:
                    day = 31
                target_date = datetime(fiscal_year, month, day).date()

            # 시가총액 데이터 조회 (가장 가까운 날짜, 90일 이내)
            from datetime import timedelta
            min_date = target_date - timedelta(days=90)  # 90일 제한 추가

            market_data = db.query(StockMarketData).filter(
                StockMarketData.stock_id == stock_id,
                StockMarketData.trade_date <= target_date,
                StockMarketData.trade_date >= min_date,  # 범위 제한
                StockMarketData.market_cap.isnot(None),
                StockMarketData.market_cap > 0
            ).order_by(StockMarketData.trade_date.desc()).first()

            market_cap = float(market_data.market_cap) if market_data and market_data.market_cap else None

            # 디버깅: 시가총액 없으면 로그
            if market_cap is None:
                print(f"  ⚠️  시가총액 없음: stock_id={stock_id}, target={target_date}")

            # 3. 재무제표 데이터 추출 (None 체크)
            revenue = float(statement.revenue) if statement.revenue else None
            operating_income = float(statement.operating_income) if statement.operating_income else None
            net_income = float(statement.net_income) if statement.net_income else None
            total_assets = float(statement.total_assets) if statement.total_assets else None
            total_liabilities = float(statement.total_liabilities) if statement.total_liabilities else None
            total_equity = float(statement.total_equity) if statement.total_equity else None

            # 4. 비율 계산
            ratios = {
                'date': target_date,
                'fiscal_year': fiscal_year,
                'fiscal_quarter': fiscal_quarter,

                # 수익성
                'roe': None,
                'roa': None,
                'operating_margin': None,
                'net_margin': None,

                # 안정성
                'debt_ratio': None,

                # 밸류에이션
                'per': None,
                'pbr': None,
                'psr': None,
            }

            # 수익성 지표
            if net_income and total_equity:
                ratios['roe'] = self.calculate_roe(net_income, total_equity)

            if net_income and total_assets:
                ratios['roa'] = self.calculate_roa(net_income, total_assets)

            if operating_income and revenue:
                ratios['operating_margin'] = self.calculate_operating_margin(operating_income, revenue)

            if net_income and revenue:
                ratios['net_margin'] = self.calculate_net_margin(net_income, revenue)

            # 안정성 지표
            if total_liabilities and total_equity:
                ratios['debt_ratio'] = self.calculate_debt_ratio(total_liabilities, total_equity)

            # 밸류에이션 지표 (시가총액 필요)
            if market_cap:
                if net_income:
                    ratios['per'] = self.calculate_per(market_cap, net_income)

                if total_equity:
                    ratios['pbr'] = self.calculate_pbr(market_cap, total_equity)

                if revenue:
                    ratios['psr'] = self.calculate_psr(market_cap, revenue)

            return ratios

        except Exception as e:
            print(f"❌ Error calculating ratios: {e}")
            return None

    def save_ratios_to_db(
        self,
        db: Session,
        stock_id: int,
        ratios: Dict
    ) -> bool:
        """
        계산된 비율을 DB에 저장

        Args:
            db: 데이터베이스 세션
            stock_id: 종목 ID
            ratios: 비율 딕셔너리

        Returns:
            성공 여부
        """
        try:
            # report_type 결정 (fiscal_quarter 기반)
            fiscal_quarter = ratios.get('fiscal_quarter')
            if fiscal_quarter is None:
                report_type = 'annual'
            elif fiscal_quarter == 1:
                report_type = 'Q1'
            elif fiscal_quarter == 2:
                report_type = 'Q2'
            elif fiscal_quarter == 3:
                report_type = 'Q3'
            else:
                report_type = 'annual'  # 예외 처리

            # 기존 데이터 확인
            existing = db.query(FinancialRatio).filter(
                FinancialRatio.stock_id == stock_id,
                FinancialRatio.fiscal_date == ratios['date'],
                FinancialRatio.report_type == report_type
            ).first()

            ratio_data = {
                'roe': ratios.get('roe'),
                'roa': ratios.get('roa'),
                'operating_margin': ratios.get('operating_margin'),
                'net_margin': ratios.get('net_margin'),
                'debt_ratio': ratios.get('debt_ratio'),
                'per': ratios.get('per'),
                'pbr': ratios.get('pbr'),
                'psr': ratios.get('psr'),
            }

            if existing:
                # 업데이트
                for key, value in ratio_data.items():
                    if value is not None:
                        setattr(existing, key, Decimal(str(value)))
            else:
                # 신규 생성
                ratio = FinancialRatio(
                    stock_id=stock_id,
                    fiscal_date=ratios['date'],
                    report_type=report_type,
                    roe=Decimal(str(ratio_data['roe'])) if ratio_data['roe'] is not None else None,
                    roa=Decimal(str(ratio_data['roa'])) if ratio_data['roa'] is not None else None,
                    operating_margin=Decimal(str(ratio_data['operating_margin'])) if ratio_data['operating_margin'] is not None else None,
                    net_margin=Decimal(str(ratio_data['net_margin'])) if ratio_data['net_margin'] is not None else None,
                    debt_ratio=Decimal(str(ratio_data['debt_ratio'])) if ratio_data['debt_ratio'] is not None else None,
                    per=Decimal(str(ratio_data['per'])) if ratio_data['per'] is not None else None,
                    pbr=Decimal(str(ratio_data['pbr'])) if ratio_data['pbr'] is not None else None,
                    psr=Decimal(str(ratio_data['psr'])) if ratio_data['psr'] is not None else None,
                )
                db.add(ratio)

            db.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving ratios: {e}")
            db.rollback()
            return False

    def calculate_and_save_for_stock(
        self,
        db: Session,
        ticker: str,
        fiscal_year: Optional[int] = None
    ) -> Dict:
        """
        특정 종목의 모든 재무비율 계산 및 저장

        Args:
            db: 데이터베이스 세션
            ticker: 종목코드
            fiscal_year: 특정 연도만 계산 (None이면 전체)

        Returns:
            계산 결과 딕셔너리
        """
        try:
            # 종목 조회
            stock = db.query(Stock).filter(Stock.ticker == ticker).first()
            if not stock:
                return {
                    'status': 'error',
                    'message': f'Stock {ticker} not found'
                }

            # 재무제표 조회
            query = db.query(FinancialStatement).filter(
                FinancialStatement.stock_id == stock.id
            )

            if fiscal_year:
                query = query.filter(FinancialStatement.fiscal_year == fiscal_year)

            statements = query.all()

            if not statements:
                return {
                    'status': 'error',
                    'message': f'No financial statements found for {ticker}'
                }

            print(f"\n{'='*60}")
            print(f"📊 Calculating ratios for {ticker} ({stock.name})")
            print(f"{'='*60}\n")

            results = {
                'ticker': ticker,
                'name': stock.name,
                'total_statements': len(statements),
                'ratios_calculated': 0,
                'ratios_saved': 0,
                'ratios_failed': 0,
                'details': []
            }

            for statement in statements:
                year = statement.fiscal_year
                quarter = statement.fiscal_quarter
                period = f"{year}" if quarter is None else f"{year}Q{quarter}"

                print(f"📈 Processing {period}...")

                # 비율 계산
                ratios = self.calculate_ratios_for_statement(
                    db, stock.id, year, quarter
                )

                if ratios:
                    results['ratios_calculated'] += 1

                    # DB 저장
                    if self.save_ratios_to_db(db, stock.id, ratios):
                        results['ratios_saved'] += 1
                        print(f"  ✅ Saved ratios for {period}")

                        # 계산된 비율 출력
                        detail = {
                            'period': period,
                            'date': ratios['date'].isoformat(),
                            'roe': f"{ratios['roe']:.2f}%" if ratios['roe'] is not None else None,
                            'roa': f"{ratios['roa']:.2f}%" if ratios['roa'] is not None else None,
                            'operating_margin': f"{ratios['operating_margin']:.2f}%" if ratios['operating_margin'] is not None else None,
                            'net_margin': f"{ratios['net_margin']:.2f}%" if ratios['net_margin'] is not None else None,
                            'debt_ratio': f"{ratios['debt_ratio']:.2f}%" if ratios['debt_ratio'] is not None else None,
                            'per': f"{ratios['per']:.2f}" if ratios['per'] is not None else None,
                            'pbr': f"{ratios['pbr']:.2f}" if ratios['pbr'] is not None else None,
                            'psr': f"{ratios['psr']:.2f}" if ratios['psr'] is not None else None,
                        }
                        results['details'].append(detail)

                        # 주요 지표만 출력
                        print(f"    ROE: {detail['roe']}, PER: {detail['per']}, PBR: {detail['pbr']}")
                    else:
                        results['ratios_failed'] += 1
                        print(f"  ❌ Failed to save ratios for {period}")
                else:
                    results['ratios_failed'] += 1
                    print(f"  ⚠️  Could not calculate ratios for {period}")

                print()

            print(f"{'='*60}")
            print(f"✅ Calculation completed!")
            print(f"{'='*60}")
            print(f"Statements processed: {results['total_statements']}")
            print(f"  - Calculated: {results['ratios_calculated']}")
            print(f"  - Saved: {results['ratios_saved']}")
            print(f"  - Failed: {results['ratios_failed']}")
            print(f"{'='*60}\n")

            results['status'] = 'success'
            return results

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }

    def calculate_batch(
        self,
        db: Session,
        limit: Optional[int] = None,
        market: Optional[str] = None
    ) -> Dict:
        """
        여러 종목의 재무비율 배치 계산

        Args:
            db: 데이터베이스 세션
            limit: 종목 수 제한
            market: 시장 필터 (KOSPI, KOSDAQ)

        Returns:
            배치 계산 결과
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting Financial Ratio Batch Calculation")
        print(f"{'='*60}\n")

        # 재무제표가 있는 종목 조회
        subquery = db.query(FinancialStatement.stock_id).distinct()

        query = db.query(Stock).filter(
            Stock.id.in_(subquery),
            Stock.country == 'KR'
        )

        if market:
            query = query.filter(Stock.market == market)

        if limit:
            query = query.limit(limit)

        stocks = query.all()

        print(f"Found {len(stocks)} stocks with financial statements\n")

        results = {
            'total_stocks': len(stocks),
            'stocks_processed': 0,
            'stocks_success': 0,
            'stocks_failed': 0,
            'total_ratios_calculated': 0,
            'total_ratios_saved': 0,
            'errors': []
        }

        for idx, stock in enumerate(stocks, 1):
            results['stocks_processed'] += 1

            try:
                print(f"[{idx}/{len(stocks)}] Processing {stock.ticker} ({stock.name})...")

                result = self.calculate_and_save_for_stock(db, stock.ticker)

                if result['status'] == 'success':
                    results['stocks_success'] += 1
                    results['total_ratios_calculated'] += result['ratios_calculated']
                    results['total_ratios_saved'] += result['ratios_saved']
                else:
                    results['stocks_failed'] += 1
                    results['errors'].append(f"{stock.ticker}: {result.get('message', 'Unknown error')}")

            except Exception as e:
                results['stocks_failed'] += 1
                error_msg = f"{stock.ticker}: {str(e)}"
                results['errors'].append(error_msg)
                print(f"  ❌ Error: {e}\n")

        print(f"\n{'='*60}")
        print(f"🎉 Batch Calculation Completed!")
        print(f"{'='*60}")
        print(f"Stocks processed: {results['stocks_processed']}")
        print(f"  - Success: {results['stocks_success']}")
        print(f"  - Failed: {results['stocks_failed']}")
        print(f"Total ratios calculated: {results['total_ratios_calculated']}")
        print(f"Total ratios saved: {results['total_ratios_saved']}")
        print(f"{'='*60}\n")

        return results