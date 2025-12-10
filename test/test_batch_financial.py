"""
재무제표 배치 수집 테스트 (10개 종목)
실행: python test/test_batch_financial.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.database import SessionLocal
from app.services.financial_batch import FinancialBatchCollector

print("=" * 60)
print("🧪 Testing Financial Batch Collection (10 stocks)")
print("=" * 60)

db = SessionLocal()
collector = FinancialBatchCollector()

try:
    # 테스트: 10개 종목만 2025년만 수집
    result = collector.collect_all_kr_stocks(
        db=db,
        start_year=2025,
        end_year=2025,
        market=None,  # 전체
        limit=10,  # 10개만
        incremental=False  # Full mode
    )

    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print("=" * 60)
    print(f"Total stocks: {result['total_stocks']}")
    print(f"Stocks processed: {result['stocks_processed']}")
    print(f"Stocks success: {result['stocks_success']}")
    print(f"Stocks failed: {result['stocks_failed']}")
    print(f"Stocks skipped: {result['stocks_skipped']}")
    print(f"Statements collected: {result['statements_collected']}")
    print(f"Statements skipped: {result['statements_skipped']}")
    print(f"Duration: {result['duration_seconds'] / 60:.1f} minutes")

    if result['errors']:
        print(f"\n⚠️  Errors ({len(result['errors'])}):")
        for error in result['errors'][:5]:  # 처음 5개만
            print(f"  - {error}")

finally:
    db.close()

print("\n✅ Test completed!")