"""
curl_cffi + yfinance 테스트 스크립트
실행: python test_us_market.py
"""
import sys
sys.path.append('/Users/user/PycharmProjects/Reach')

from app.services.us_market import USMarketCollector

print("=" * 60)
print("US Market Collector 테스트 (curl_cffi)")
print("=" * 60)

collector = USMarketCollector()

# 1. Apple 정보 조회
print("\n1. Apple (AAPL) 정보 조회")
print("-" * 60)
apple_info = collector.get_stock_info("AAPL")
if apple_info:
    print(f"✅ 성공:")
    for key, value in apple_info.items():
        print(f"  {key}: {value}")
else:
    print("❌ 실패")

# 2. Microsoft 정보 조회
print("\n2. Microsoft (MSFT) 정보 조회")
print("-" * 60)
msft_info = collector.get_stock_info("MSFT")
if msft_info:
    print(f"✅ 성공:")
    for key, value in msft_info.items():
        print(f"  {key}: {value}")
else:
    print("❌ 실패")

# 3. Apple 주가 조회 (최근 5일)
print("\n3. Apple (AAPL) 주가 조회 (최근 5일)")
print("-" * 60)
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=10)
apple_prices = collector.get_stock_price("AAPL", start_date)
if not apple_prices.empty:
    print(f"✅ 성공: {len(apple_prices)}개 레코드")
    print(apple_prices.tail())
else:
    print("❌ 실패")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)