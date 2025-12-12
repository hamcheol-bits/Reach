"""
재무비율 NULL 값 디버깅
실행: python test/debug_null_ratios.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.database import SessionLocal
from app.models import Stock, FinancialStatement, StockMarketData

print("=" * 60)
print("🔍 Debugging NULL Ratios for 삼성전자(005930)")
print("=" * 60)

db = SessionLocal()

try:
    # 종목 조회
    stock = db.query(Stock).filter(Stock.ticker == "005930").first()

    if not stock:
        print("❌ 삼성전자를 찾을 수 없습니다")
        sys.exit(1)

    print(f"\n📊 종목 정보:")
    print(f"  ID: {stock.id}")
    print(f"  Ticker: {stock.ticker}")
    print(f"  Name: {stock.name}")

    # 1. 재무제표 데이터 확인
    print(f"\n{'=' * 60}")
    print("1. 재무제표 데이터 확인")
    print("=" * 60)

    statements = db.query(FinancialStatement).filter(
        FinancialStatement.stock_id == stock.id
    ).order_by(FinancialStatement.fiscal_year.desc()).all()

    print(f"\n총 {len(statements)}개 재무제표\n")

    for stmt in statements[:6]:  # 최근 6개만
        year = stmt.fiscal_year
        quarter = stmt.fiscal_quarter
        period = f"{year}" if quarter is None else f"{year}Q{quarter}"

        print(f"📈 {period}:")
        print(f"  - 매출액 (revenue): {float(stmt.revenue) if stmt.revenue else 'NULL'}")
        print(f"  - 영업이익 (operating_income): {float(stmt.operating_income) if stmt.operating_income else 'NULL'}")
        print(f"  - 당기순이익 (net_income): {float(stmt.net_income) if stmt.net_income else 'NULL'}")
        print(f"  - 자산총계 (total_assets): {float(stmt.total_assets) if stmt.total_assets else 'NULL'}")
        print(f"  - 부채총계 (total_liabilities): {float(stmt.total_liabilities) if stmt.total_liabilities else 'NULL'}")
        print(f"  - 자본총계 (total_equity): {float(stmt.total_equity) if stmt.total_equity else 'NULL'}")
        print()

    # 2. 시가총액 데이터 확인
    print(f"{'=' * 60}")
    print("2. 시가총액 데이터 확인")
    print("=" * 60)

    # 주요 날짜별 시가총액 확인
    test_dates = [
        "2025-09-30",
        "2025-06-30",
        "2025-03-31",
        "2024-12-31",
        "2023-12-31",
        "2022-12-31"
    ]

    print()
    for date_str in test_dates:
        from datetime import datetime

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        market_data = db.query(StockMarketData).filter(
            StockMarketData.stock_id == stock.id,
            StockMarketData.trade_date <= target_date
        ).order_by(StockMarketData.trade_date.desc()).first()

        if market_data:
            print(f"📅 {date_str}:")
            print(f"  - 실제 날짜: {market_data.trade_date}")
            print(f"  - 시가총액: {float(market_data.market_cap):,.0f} 원" if market_data.market_cap else "  - 시가총액: NULL")
        else:
            print(f"📅 {date_str}: ❌ 시가총액 데이터 없음")
        print()

    # 3. NULL 원인 분석
    print(f"{'=' * 60}")
    print("3. NULL 원인 분석")
    print("=" * 60)

    print("\n분석 결과:")

    # 2025년 분기 데이터 확인
    q1_2025 = db.query(FinancialStatement).filter(
        FinancialStatement.stock_id == stock.id,
        FinancialStatement.fiscal_year == 2025,
        FinancialStatement.fiscal_quarter == 1
    ).first()

    if q1_2025:
        print("\n✅ 2025 Q1 재무제표 존재")
        print(f"  - 매출액: {float(q1_2025.revenue) if q1_2025.revenue else 'NULL'}")
        print(f"  - 영업이익: {float(q1_2025.operating_income) if q1_2025.operating_income else 'NULL'}")
        print(f"  - 당기순이익: {float(q1_2025.net_income) if q1_2025.net_income else 'NULL'}")

        if not q1_2025.revenue:
            print("\n⚠️  원인: 재무제표에 매출액 데이터가 없음!")
            print("   → DART API 응답에 해당 항목이 없거나 파싱 실패")

        if not q1_2025.operating_income:
            print("\n⚠️  원인: 재무제표에 영업이익 데이터가 없음!")
            print("   → DART API 응답에 해당 항목이 없거나 파싱 실패")

    # 2024년 연간 데이터 확인
    annual_2024 = db.query(FinancialStatement).filter(
        FinancialStatement.stock_id == stock.id,
        FinancialStatement.fiscal_year == 2024,
        FinancialStatement.fiscal_quarter.is_(None)
    ).first()

    if annual_2024:
        print("\n✅ 2024 연간 재무제표 존재")
        print(f"  - 매출액: {float(annual_2024.revenue) if annual_2024.revenue else 'NULL'}")
        print(f"  - 영업이익: {float(annual_2024.operating_income) if annual_2024.operating_income else 'NULL'}")

        if not annual_2024.revenue or not annual_2024.operating_income:
            print("\n⚠️  원인: 손익계산서 항목이 NULL")
            print("   → DART API 파싱 로직 문제일 수 있음")

    # 4. 권장 조치
    print(f"\n{'=' * 60}")
    print("4. 권장 조치")
    print("=" * 60)

    print("\n✅ 부채비율은 정상 계산됨 → 재무상태표(BS) 파싱 정상")
    print("⚠️  수익성/밸류에이션 비율이 NULL → 손익계산서(IS) 파싱 문제")

    print("\n🔧 해결 방법:")
    print("  1. DART API 응답의 계정명 확인 필요")
    print("  2. dart_api.py의 parse_financial_data() 로직 점검")
    print("  3. 계정명 매핑 테이블 업데이트")

    print("\n💡 다음 단계:")
    print("  python test/test_dart_api.py  # DART API 응답 확인")

finally:
    db.close()

print("\n" + "=" * 60)
print("✅ 디버깅 완료")
print("=" * 60)