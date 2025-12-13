"""
2022, 2023년 시가총액 데이터 상세 확인
실행: python test/check_2022_2023_market_cap.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.database import SessionLocal
from app.models import Stock, StockMarketData
from datetime import datetime

print("=" * 60)
print("🔍 2022, 2023년 시가총액 상세 확인")
print("=" * 60)

db = SessionLocal()

try:
    # 삼성전자 조회
    stock = db.query(Stock).filter(Stock.ticker == "005930").first()

    if not stock:
        print("❌ 삼성전자를 찾을 수 없습니다")
        sys.exit(1)

    print(f"\n📊 종목: {stock.name} ({stock.ticker})")
    print(f"Stock ID: {stock.id}")

    # 2022-12-31 전후 데이터 확인
    print(f"\n{'=' * 60}")
    print("📅 2022-12-31 전후 시가총액 데이터")
    print("=" * 60)

    target_2022 = datetime(2022, 12, 31).date()

    # 2022-12-31 또는 그 이전 가장 가까운 날짜
    data_2022 = db.query(StockMarketData).filter(
        StockMarketData.stock_id == stock.id,
        StockMarketData.trade_date <= target_2022
    ).order_by(StockMarketData.trade_date.desc()).limit(5).all()

    if data_2022:
        print(f"\n2022-12-31 이전 가장 가까운 데이터 (최대 5개):")
        for data in data_2022:
            print(f"\n  날짜: {data.trade_date}")
            print(f"  시가총액: {float(data.market_cap):,.0f} 원" if data.market_cap else "  시가총액: NULL")
            print(f"  거래대금: {float(data.trading_value):,.0f} 원" if data.trading_value else "  거래대금: NULL")

            # 날짜 차이 계산
            days_diff = (target_2022 - data.trade_date).days
            print(f"  차이: {days_diff}일")
    else:
        print("\n❌ 2022-12-31 이전 데이터 없음")

    # 2023-12-31 전후 데이터 확인
    print(f"\n{'=' * 60}")
    print("📅 2023-12-31 전후 시가총액 데이터")
    print("=" * 60)

    target_2023 = datetime(2023, 12, 31).date()

    # 2023-12-31 또는 그 이전 가장 가까운 날짜
    data_2023 = db.query(StockMarketData).filter(
        StockMarketData.stock_id == stock.id,
        StockMarketData.trade_date <= target_2023
    ).order_by(StockMarketData.trade_date.desc()).limit(5).all()

    if data_2023:
        print(f"\n2023-12-31 이전 가장 가까운 데이터 (최대 5개):")
        for data in data_2023:
            print(f"\n  날짜: {data.trade_date}")
            print(f"  시가총액: {float(data.market_cap):,.0f} 원" if data.market_cap else "  시가총액: NULL")
            print(f"  거래대금: {float(data.trading_value):,.0f} 원" if data.trading_value else "  거래대금: NULL")

            # 날짜 차이 계산
            days_diff = (target_2023 - data.trade_date).days
            print(f"  차이: {days_diff}일")
    else:
        print("\n❌ 2023-12-31 이전 데이터 없음")

    # 전체 시가총액 데이터 날짜 범위 확인
    print(f"\n{'=' * 60}")
    print("📊 전체 시가총액 데이터 날짜 범위")
    print("=" * 60)

    all_data = db.query(StockMarketData).filter(
        StockMarketData.stock_id == stock.id
    ).order_by(StockMarketData.trade_date).all()

    if all_data:
        print(f"\n총 {len(all_data)}개 데이터")
        print(f"  - 최초: {all_data[0].trade_date}")
        print(f"  - 최신: {all_data[-1].trade_date}")

        # 2022년 데이터 개수
        data_2022_count = sum(1 for d in all_data if d.trade_date.year == 2022)
        print(f"  - 2022년: {data_2022_count}개")

        # 2023년 데이터 개수
        data_2023_count = sum(1 for d in all_data if d.trade_date.year == 2023)
        print(f"  - 2023년: {data_2023_count}개")

        # 2024년 데이터 개수
        data_2024_count = sum(1 for d in all_data if d.trade_date.year == 2024)
        print(f"  - 2024년: {data_2024_count}개")

        # 2025년 데이터 개수
        data_2025_count = sum(1 for d in all_data if d.trade_date.year == 2025)
        print(f"  - 2025년: {data_2025_count}개")
    else:
        print("\n❌ 시가총액 데이터 없음")

finally:
    db.close()

print("\n" + "=" * 60)
print("✅ 확인 완료")
print("=" * 60)

print("\n💡 분석:")
print("  - 시가총액 데이터가 있으면: 재무비율 계산 로직 문제")
print("  - 시가총액 데이터가 없으면: 수집이 제대로 안된 것")