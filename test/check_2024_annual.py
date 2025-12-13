"""
2024년 연간 재무제표 데이터 확인
실행: python test/check_2024_annual.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.database import SessionLocal
from app.models import Stock, FinancialStatement

print("=" * 60)
print("🔍 2024년 연간 재무제표 데이터 확인")
print("=" * 60)

db = SessionLocal()

try:
    # 삼성전자 조회
    stock = db.query(Stock).filter(Stock.ticker == "005930").first()

    if not stock:
        print("❌ 삼성전자를 찾을 수 없습니다")
        sys.exit(1)

    # 2022, 2023, 2024 연간 재무제표 조회
    for year in [2022, 2023, 2024]:
        stmt = db.query(FinancialStatement).filter(
            FinancialStatement.stock_id == stock.id,
            FinancialStatement.fiscal_year == year,
            FinancialStatement.fiscal_quarter.is_(None)
        ).first()

        print(f"\n{'=' * 60}")
        print(f"📈 {year}년 연간")
        print(f"{'=' * 60}")

        if stmt:
            print(f"손익계산서:")
            print(f"  - 매출액: {float(stmt.revenue):,.0f} 원" if stmt.revenue else "  - 매출액: NULL ❌")
            print(f"  - 영업이익: {float(stmt.operating_income):,.0f} 원" if stmt.operating_income else "  - 영업이익: NULL")
            print(f"  - 당기순이익: {float(stmt.net_income):,.0f} 원" if stmt.net_income else "  - 당기순이익: NULL")

            print(f"\n재무상태표:")
            print(f"  - 자산총계: {float(stmt.total_assets):,.0f} 원" if stmt.total_assets else "  - 자산총계: NULL")
            print(f"  - 부채총계: {float(stmt.total_liabilities):,.0f} 원" if stmt.total_liabilities else "  - 부채총계: NULL")
            print(f"  - 자본총계: {float(stmt.total_equity):,.0f} 원" if stmt.total_equity else "  - 자본총계: NULL")

            # 비율 계산 가능 여부
            print(f"\n계산 가능:")
            if stmt.revenue and stmt.operating_income:
                margin = (float(stmt.operating_income) / float(stmt.revenue)) * 100
                print(f"  ✅ 영업이익률: {margin:.2f}%")
            else:
                print(f"  ❌ 영업이익률: 계산 불가")

            if stmt.revenue and stmt.net_income:
                margin = (float(stmt.net_income) / float(stmt.revenue)) * 100
                print(f"  ✅ 순이익률: {margin:.2f}%")
            else:
                print(f"  ❌ 순이익률: 계산 불가")
        else:
            print(f"❌ {year}년 연간 재무제표 없음")

finally:
    db.close()

print("\n" + "=" * 60)
print("✅ 확인 완료")
print("=" * 60)

print("\n💡 해결방법:")
print("  - 매출액이 NULL이면 해당 연도 재무제표 재수집 필요")
print("  - curl -X POST 'http://localhost:8001/api/v1/financial/collect/005930?year=2024'")