from datetime import datetime, timedelta
from typing import Optional

import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock
from sqlalchemy.orm import Session

from app.models import Stock, StockPrice


class KoreaMarketCollector:
    """한국 시장 데이터 수집기"""

    def __init__(self):
        self.market_codes = {
            "KOSPI": "KOSPI",
            "KOSDAQ": "KOSDAQ",
            "KONEX": "KONEX"
        }

    def get_stock_list(self, market: str = "KOSPI") -> pd.DataFrame:
        """
        한국 주식 목록 조회 (pykrx 사용)

        Args:
            market: KOSPI, KOSDAQ, KONEX

        Returns:
            주식 목록 DataFrame
        """
        try:
            # pykrx로 종목 리스트 조회
            today = datetime.now().strftime("%Y%m%d")

            if market in ["KOSPI", "KOSDAQ", "KONEX"]:
                tickers = stock.get_market_ticker_list(today, market=market)
            else:
                print(f"Unknown market: {market}")
                return pd.DataFrame()

            print(f"Fetched {len(tickers)} tickers from {market}")

            # 각 종목의 이름 조회
            stocks_data = []
            for ticker in tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    stocks_data.append({
                        'Code': ticker,
                        'Name': name,
                        'Market': market
                    })
                except Exception as e:
                    print(f"Error fetching name for {ticker}: {e}")
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
        주식 가격 데이터 조회 (FinanceDataReader 사용)

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
            # FinanceDataReader 사용 (영문 컬럼명)
            price_df = fdr.DataReader(
                ticker,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            # 필요한 컬럼만 선택
            if not price_df.empty:
                # 컬럼 확인 및 정규화
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                available_columns = [col for col in required_columns if col in price_df.columns]
                price_df = price_df[available_columns]

            return price_df
        except Exception as e:
            print(f"Error fetching price for {ticker}: {e}")
            return pd.DataFrame()

    def save_stocks_to_db(self, db: Session, market: str = "KOSPI") -> int:
        """
        주식 목록을 DB에 저장

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
                    # 업데이트
                    existing.name = row['Name']
                    existing.market = market
                else:
                    # 신규 생성
                    stock = Stock(
                        ticker=row['Code'],
                        name=row['Name'],
                        market=market,
                        country='KR'
                    )
                    db.add(stock)

                saved_count += 1

                # 100개마다 중간 커밋 (대량 데이터 처리)
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
        주식 가격 데이터를 DB에 저장

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

        # 가격 데이터 조회
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
                else:
                    # 신규 생성
                    price = StockPrice(
                        stock_id=stock_obj.id,
                        trade_date=date_idx.date(),
                        open=float(row['Open']) if pd.notna(row['Open']) else None,
                        high=float(row['High']) if pd.notna(row['High']) else None,
                        low=float(row['Low']) if pd.notna(row['Low']) else None,
                        close=float(row['Close']) if pd.notna(row['Close']) else None,
                        volume=int(row['Volume']) if pd.notna(row['Volume']) else None
                    )
                    db.add(price)

                saved_count += 1

            except Exception as e:
                print(f"Error saving price for {ticker} on {date_idx}: {e}")
                continue

        db.commit()
        print(f"Saved {saved_count} price records for {ticker}")
        return saved_count