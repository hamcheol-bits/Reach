"""
삼성전자 시가총액 데이터 확인
실행: python test/check_market_cap.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.database import SessionLocal
from app.models import Stock, StockMarketData
from datetime import datetime

print("=" * 60)
print("🔍 삼성전자 시가총액 데이터 확인")
print("=" * 60)

db = SessionLocal()

try:
    # 삼성전자 조회
    stock = db.query(Stock).filter(Stock.ticker == "005930").first()

    if not stock:
        print("❌ 삼성전자를 찾을 수 없습니다")
        sys.exit(1)

    print(f"\n📊 종목 정보:")
    print(f"  - ID: {stock.id}")
    print(f"  - Ticker: {stock.ticker}")
    print(f"  - Name: {stock.name}")

    # 시가총액 데이터 조회
    market_data = db.query(StockMarketData).filter(
        StockMarketData.stock_id == stock.id
    ).order_by(StockMarketData.trade_date.desc()).all()

    print(f"\n💰 시가총액 데이터: {len(market_data)}개")

    if not market_data:
        print("\n❌ 시가총액 데이터가 없습니다!")
        print("\n💡 해결방법:")
        print("  curl -X POST 'http://localhost:8001/api/v1/korea/collect/market-data?market=KOSPI'")
    else:
        print(f"\n최근 10개 데이터:")
        print("=" * 60)

        for data in market_data[:10]:
            print(f"\n📅 {data.trade_date}:")
            print(f"  - 시가총액: {float(data.market_cap):,.0f} 원" if data.market_cap else "  - 시가총액: NULL")
            print(f"  - 거래대금: {float(data.trading_value):,.0f} 원" if data.trading_value else "  - 거래대금: NULL")
            print(f"  - 상장주식수: {data.shares_outstanding:,} 주" if data.shares_outstanding else "  - 상장주식수: NULL")

        # 주요 날짜 확인
        print(f"\n{'=' * 60}")
        print("주요 날짜 시가총액 확인")
        print("=" * 60)

        target_dates = [
            "2025-09-30",
            "2025-06-30",
            "2025-03-31",
            "2024-12-31",
            "2023-12-31",
            "2022-12-31"
        ]

        for date_str in target_dates:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # 해당 날짜 또는 그 이전 가장 가까운 날짜
            closest = db.query(StockMarketData).filter(
                StockMarketData.stock_id == stock.id,
                StockMarketData.trade_date <= target_date
            ).order_by(StockMarketData.trade_date.desc()).first()

            if closest:
                print(f"\n📅 {date_str} (또는 가장 가까운 날짜):")
                print(f"  - 실제 날짜: {closest.trade_date}")
                print(f"  - 시가총액: {float(closest.market_cap):,.0f} 원" if closest.market_cap else "  - 시가총액: NULL")
            else:
                print(f"\n📅 {date_str}: ❌ 데이터 없음")

finally:
    db.close()

print("\n" + "=" * 60)
print("✅ 확인 완료")
print("=" * 60)