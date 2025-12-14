from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from pykrx import stock
from sqlalchemy.orm import Session

from app.models import Stock, StockPrice


class KoreaMarketCollector:
    """한국 시장 데이터 수집기 (pykrx 통합) - v2: 휴장일 필터링 추가"""

    def __init__(self):
        self.market_codes = {
            "KOSPI": "KOSPI",
            "KOSDAQ": "KOSDAQ",
            "KONEX": "KONEX"
        }

    def get_stock_list(self, market: str = "KOSPI") -> pd.DataFrame:
        """
        한국 주식 목록 조회 (pykrx 사용 - 섹터 정보 포함)

        Args:
            market: KOSPI, KOSDAQ, KONEX

        Returns:
            주식 목록 DataFrame (Code, Name, Market, Sector 포함)
        """
        try:
            today = datetime.now().strftime("%Y%m%d")

            if market in ["KOSPI", "KOSDAQ", "KONEX"]:
                tickers = stock.get_market_ticker_list(today, market=market)
            else:
                print(f"Unknown market: {market}")
                return pd.DataFrame()

            print(f"Fetched {len(tickers)} tickers from {market}")

            # 시가총액 데이터 조회 (섹터 정보 포함)
            try:
                market_cap_df = stock.get_market_cap_by_ticker(today, market=market)
                # Columns: 시가총액, 거래량, 거래대금, 상장주식수, Sector
                sector_dict = market_cap_df['Sector'].to_dict() if 'Sector' in market_cap_df.columns else {}
                print(f"Fetched sector info for {len(sector_dict)} stocks")
            except Exception as e:
                print(f"Warning: Could not fetch sector info: {e}")
                sector_dict = {}

            # 각 종목의 이름과 섹터 조합
            stocks_data = []
            for ticker in tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    sector = sector_dict.get(ticker, None)

                    stocks_data.append({
                        'Code': ticker,
                        'Name': name,
                        'Market': market,
                        'Sector': sector
                    })
                except Exception as e:
                    print(f"Error fetching info for {ticker}: {e}")
                    continue

            stocks_df = pd.DataFrame(stocks_data)
            print(f"Successfully processed {len(stocks_df)} stocks from {market}")
            return stocks_df

        except Exception as e:
            print(f"Error fetching {market} stock list: {e}")
            return pd.DataFrame()

    def get_stock_price(
            self,
            ticker: str,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        주식 가격 데이터 조회 (pykrx 사용)

        Args:
            ticker: 종목 코드
            start_date: 시작일 (기본: 1년 전)
            end_date: 종료일 (기본: 오늘)

        Returns:
            가격 데이터 DataFrame (영문 컬럼: Open, High, Low, Close, Volume)
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        try:
            # pykrx 사용 (OHLCV 데이터)
            price_df = stock.get_market_ohlcv_by_date(
                fromdate=start_date.strftime("%Y%m%d"),
                todate=end_date.strftime("%Y%m%d"),
                ticker=ticker
            )

            if price_df.empty:
                return pd.DataFrame()

            # 한글 컬럼명을 영문으로 변환
            price_df = price_df.rename(columns={
                '시가': 'Open',
                '고가': 'High',
                '저가': 'Low',
                '종가': 'Close',
                '거래량': 'Volume'
            })

            # 필요한 컬럼만 선택
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            available_columns = [col for col in required_columns if col in price_df.columns]
            price_df = price_df[available_columns]

            print(f"✅ [pykrx] Fetched {len(price_df)} price records for {ticker}")
            return price_df

        except Exception as e:
            print(f"❌ [pykrx] Error fetching price for {ticker}: {e}")
            return pd.DataFrame()

    def get_market_data(
            self,
            market: str = "KOSPI",
            date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        시장 데이터 조회 (시가총액, 거래대금, 상장주식수)

        Args:
            market: KOSPI, KOSDAQ, KONEX
            date: 조회 날짜 (기본: 오늘)

        Returns:
            시장 데이터 DataFrame
        """
        if date is None:
            date = datetime.now()

        try:
            date_str = date.strftime("%Y%m%d")

            # pykrx로 시가총액 데이터 조회
            df = stock.get_market_cap_by_ticker(date_str, market=market)

            # Columns: 시가총액, 거래량, 거래대금, 상장주식수, Sector
            # 영문 컬럼명으로 변경
            df = df.rename(columns={
                '시가총액': 'MarketCap',
                '거래량': 'Volume',
                '거래대금': 'TradingValue',
                '상장주식수': 'SharesOutstanding'
            })

            print(f"Fetched market data for {len(df)} stocks from {market}")
            return df

        except Exception as e:
            print(f"Error fetching market data for {market}: {e}")
            return pd.DataFrame()

    def save_stocks_to_db(self, db: Session, market: str = "KOSPI") -> int:
        """
        주식 목록을 DB에 저장 (섹터 정보 포함)

        Args:
            db: 데이터베이스 세션
            market: 시장 (KOSPI, KOSDAQ, KONEX)

        Returns:
            저장된 종목 수
        """
        stocks_df = self.get_stock_list(market)

        if stocks_df.empty:
            return 0

        saved_count = 0

        for _, row in stocks_df.iterrows():
            try:
                # 기존 종목 확인
                existing = db.query(Stock).filter(Stock.ticker == row['Code']).first()

                if existing:
                    # 업데이트 (섹터 포함)
                    existing.name = row['Name']
                    existing.market = market
                    existing.sector = row.get('Sector')
                else:
                    # 신규 생성
                    stock = Stock(
                        ticker=row['Code'],
                        name=row['Name'],
                        market=market,
                        sector=row.get('Sector'),
                        country='KR'
                    )
                    db.add(stock)

                saved_count += 1

                # 100개마다 중간 커밋
                if saved_count % 100 == 0:
                    db.commit()
                    print(f"Progress: {saved_count} stocks saved...")

            except Exception as e:
                print(f"Error saving stock {row.get('Code', 'unknown')}: {e}")
                continue

        db.commit()
        print(f"Total saved: {saved_count} stocks")
        return saved_count

    def save_stock_prices_to_db(
            self,
            db: Session,
            ticker: str,
            start_date: Optional[datetime] = None
    ) -> int:
        """
        주식 가격 데이터를 DB에 저장 (pykrx 사용)

        Args:
            db: 데이터베이스 세션
            ticker: 종목 코드
            start_date: 시작일

        Returns:
            저장된 레코드 수
        """
        # 주식 정보 조회
        stock_obj = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock_obj:
            print(f"Stock {ticker} not found in database")
            return 0

        # 가격 데이터 조회 (pykrx)
        price_df = self.get_stock_price(ticker, start_date)

        if price_df.empty:
            print(f"No price data found for {ticker}")
            return 0

        saved_count = 0

        for date_idx, row in price_df.iterrows():
            try:
                # 기존 데이터 확인
                existing = db.query(StockPrice).filter(
                    StockPrice.stock_id == stock_obj.id,
                    StockPrice.trade_date == date_idx.date()
                ).first()

                if existing:
                    # 업데이트
                    existing.open = float(row['Open']) if pd.notna(row['Open']) else None
                    existing.high = float(row['High']) if pd.notna(row['High']) else None
                    existing.low = float(row['Low']) if pd.notna(row['Low']) else None
                    existing.close = float(row['Close']) if pd.notna(row['Close']) else None
                    existing.volume = int(row['Volume']) if pd.notna(row['Volume']) else None
                    existing.adjusted_close = None  # pykrx는 조정 종가 미제공
                else:
                    # 신규 생성
                    price = StockPrice(
                        stock_id=stock_obj.id,
                        trade_date=date_idx.date(),
                        open=float(row['Open']) if pd.notna(row['Open']) else None,
                        high=float(row['High']) if pd.notna(row['High']) else None,
                        low=float(row['Low']) if pd.notna(row['Low']) else None,
                        close=float(row['Close']) if pd.notna(row['Close']) else None,
                        volume=int(row['Volume']) if pd.notna(row['Volume']) else None,
                        adjusted_close=None  # pykrx는 조정 종가 미제공
                    )
                    db.add(price)

                saved_count += 1

            except Exception as e:
                print(f"Error saving price for {ticker} on {date_idx}: {e}")
                continue

        db.commit()
        print(f"Saved {saved_count} price records for {ticker}")
        return saved_count

    def save_market_data_to_db(
            self,
            db: Session,
            market: str = "KOSPI",
            date: Optional[datetime] = None
    ) -> int:
        """
        시장 데이터를 DB에 저장 (✨ 휴장일 필터링 포함)

        Args:
            db: 데이터베이스 세션
            market: 시장 (KOSPI, KOSDAQ, KONEX)
            date: 조회 날짜 (기본: 오늘)

        Returns:
            저장된 레코드 수

        ✨ 개선사항:
            - 휴장일 데이터 자동 필터링 (market_cap=0, trading_value=0)
            - 유효하지 않은 데이터는 저장하지 않음
        """
        from app.models import Stock, StockMarketData

        if date is None:
            date = datetime.now()

        # 시장 데이터 조회
        market_df = self.get_market_data(market, date)

        if market_df.empty:
            print(f"No market data found for {market}")
            return 0

        saved_count = 0
        skipped_count = 0
        holiday_detected = False

        for ticker, row in market_df.iterrows():
            try:
                # 🔍 휴장일 감지: 시가총액과 거래대금이 모두 0
                market_cap = row.get('MarketCap', 0)
                trading_value = row.get('TradingValue', 0)

                # 휴장일 체크 (둘 다 0이면 휴장일)
                if pd.notna(market_cap) and pd.notna(trading_value):
                    if market_cap == 0 and trading_value == 0:
                        if not holiday_detected:
                            print(f"🚫 Holiday detected on {date.date()}: market_cap=0, trading_value=0")
                            print(f"   Skipping all data for this date")
                            holiday_detected = True
                        skipped_count += 1
                        continue  # ✅ 저장하지 않고 건너뜀

                # NULL 체크 (둘 다 NULL이어도 휴장일)
                if pd.isna(market_cap) and pd.isna(trading_value):
                    if not holiday_detected:
                        print(f"🚫 Holiday detected on {date.date()}: market_cap=NULL, trading_value=NULL")
                        print(f"   Skipping all data for this date")
                        holiday_detected = True
                    skipped_count += 1
                    continue

                # ✅ 정상 데이터: 종목 조회
                stock_obj = db.query(Stock).filter(
                    Stock.ticker == ticker,
                    Stock.market == market
                ).first()

                if not stock_obj:
                    skipped_count += 1
                    continue

                # 기존 데이터 확인
                existing = db.query(StockMarketData).filter(
                    StockMarketData.stock_id == stock_obj.id,
                    StockMarketData.trade_date == date.date()
                ).first()

                # ✅ 개선: 0 값도 NULL로 저장 (의미 있는 0과 구분)
                market_data = {
                    'market_cap': float(market_cap) if (pd.notna(market_cap) and market_cap > 0) else None,
                    'trading_value': float(trading_value) if (pd.notna(trading_value) and trading_value > 0) else None,
                    'shares_outstanding': int(row['SharesOutstanding']) if pd.notna(row['SharesOutstanding']) else None,
                }

                if existing:
                    # 업데이트
                    for key, value in market_data.items():
                        setattr(existing, key, value)
                else:
                    # 신규 생성
                    market_data_obj = StockMarketData(
                        stock_id=stock_obj.id,
                        trade_date=date.date(),
                        **market_data
                    )
                    db.add(market_data_obj)

                saved_count += 1

                # 100개마다 중간 커밋
                if saved_count % 100 == 0:
                    db.commit()
                    print(f"Progress: {saved_count} market data records saved...")

            except Exception as e:
                print(f"Error saving market data for {ticker}: {e}")
                continue

        db.commit()

        # 결과 출력
        if holiday_detected:
            print(f"🚫 Holiday on {date.date()}: Skipped {skipped_count} records")
            print(f"✅ Saved: {saved_count} valid records (if any)")
        else:
            print(f"✅ Saved {saved_count} market data records for {market}")
            if skipped_count > 0:
                print(f"⏭️  Skipped {skipped_count} records (stock not found in DB)")

        return saved_count