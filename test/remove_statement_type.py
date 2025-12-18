"""
기존 재무제표 데이터의 fiscal_date, report_type 업데이트

실행: python test/update_existing_financial_data.py
"""
import sys
sys.path.append('/Users/user/PycharmProjects/Reach')

from sqlalchemy import text
from app.database import SessionLocal
from datetime import datetime

print("=" * 80)
print("🔧 기존 재무제표 데이터 업데이트: fiscal_date, report_type")
print("=" * 80)

db = SessionLocal()

try:
    # 1. 현재 상태 확인
    print("\n1️⃣  현재 상태 확인...")
    print("-" * 80)

    result = db.execute(text("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN fiscal_date IS NULL THEN 1 ELSE 0 END) as null_fiscal_date,
               SUM(CASE WHEN report_type IS NULL THEN 1 ELSE 0 END) as null_report_type
        FROM financial_statements
    """))

    row = result.fetchone()
    total = row[0]
    null_fiscal = row[1]
    null_report = row[2]

    print(f"  전체 레코드: {total:,}개")
    print(f"  fiscal_date NULL: {null_fiscal:,}개")
    print(f"  report_type NULL: {null_report:,}개")

    if null_fiscal == 0 and null_report == 0:
        print("\n✅ 이미 모든 데이터가 업데이트되어 있습니다!")
        sys.exit(0)

    # 2. fiscal_date 업데이트
    print("\n2️⃣  fiscal_date 업데이트...")
    print("-" * 80)

    # fiscal_year와 fiscal_quarter 기반으로 계산
    queries = [
        # 연간 (fiscal_quarter IS NULL) -> 12/31
        ("""
            UPDATE financial_statements
            SET fiscal_date = CONCAT(fiscal_year, '-12-31')
            WHERE fiscal_quarter IS NULL AND fiscal_date IS NULL
        """, "연간 (12/31)"),

        # 1분기 -> 3/31
        ("""
            UPDATE financial_statements
            SET fiscal_date = CONCAT(fiscal_year, '-03-31')
            WHERE fiscal_quarter = 1 AND fiscal_date IS NULL
        """, "1분기 (3/31)"),

        # 2분기 -> 6/30
        ("""
            UPDATE financial_statements
            SET fiscal_date = CONCAT(fiscal_year, '-06-30')
            WHERE fiscal_quarter = 2 AND fiscal_date IS NULL
        """, "2분기 (6/30)"),

        # 3분기 -> 9/30
        ("""
            UPDATE financial_statements
            SET fiscal_date = CONCAT(fiscal_year, '-09-30')
            WHERE fiscal_quarter = 3 AND fiscal_date IS NULL
        """, "3분기 (9/30)"),
    ]

    total_updated = 0
    for query, desc in queries:
        result = db.execute(text(query))
        count = result.rowcount
        total_updated += count
        print(f"  ✅ {desc}: {count:,}개 업데이트")

    db.commit()
    print(f"\n  총 {total_updated:,}개 레코드 업데이트 완료")

    # 3. report_type 업데이트
    print("\n3️⃣  report_type 업데이트...")
    print("-" * 80)

    queries = [
        # 연간
        ("""
            UPDATE financial_statements
            SET report_type = 'annual'
            WHERE fiscal_quarter IS NULL AND report_type IS NULL
        """, "annual"),

        # 1분기
        ("""
            UPDATE financial_statements
            SET report_type = 'Q1'
            WHERE fiscal_quarter = 1 AND report_type IS NULL
        """, "Q1"),

        # 2분기
        ("""
            UPDATE financial_statements
            SET report_type = 'Q2'
            WHERE fiscal_quarter = 2 AND report_type IS NULL
        """, "Q2"),

        # 3분기
        ("""
            UPDATE financial_statements
            SET report_type = 'Q3'
            WHERE fiscal_quarter = 3 AND report_type IS NULL
        """, "Q3"),
    ]

    total_updated = 0
    for query, desc in queries:
        result = db.execute(text(query))
        count = result.rowcount
        total_updated += count
        print(f"  ✅ {desc}: {count:,}개 업데이트")

    db.commit()
    print(f"\n  총 {total_updated:,}개 레코드 업데이트 완료")

    # 4. 최종 확인
    print("\n4️⃣  최종 확인...")
    print("-" * 80)

    result = db.execute(text("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN fiscal_date IS NULL THEN 1 ELSE 0 END) as null_fiscal_date,
               SUM(CASE WHEN report_type IS NULL THEN 1 ELSE 0 END) as null_report_type
        FROM financial_statements
    """))

    row = result.fetchone()
    total = row[0]
    null_fiscal = row[1]
    null_report = row[2]

    print(f"  전체 레코드: {total:,}개")
    print(f"  fiscal_date NULL: {null_fiscal:,}개")
    print(f"  report_type NULL: {null_report:,}개")

    if null_fiscal == 0 and null_report == 0:
        print("\n  ✅ 모든 데이터가 성공적으로 업데이트되었습니다!")
    else:
        print("\n  ⚠️  일부 NULL 값이 남아있습니다")

    # 5. 샘플 데이터 확인
    print("\n5️⃣  샘플 데이터 확인 (최신 5개)...")
    print("-" * 80)

    result = db.execute(text("""
        SELECT fiscal_year, fiscal_quarter, fiscal_date, report_type
        FROM financial_statements
        ORDER BY id DESC
        LIMIT 5
    """))

    print(f"  {'연도':<8} {'분기':<8} {'기준일':<12} {'타입':<8}")
    print("  " + "-" * 40)
    for row in result:
        quarter = f"Q{row[1]}" if row[1] else "연간"
        print(f"  {row[0]:<8} {quarter:<8} {row[2]:<12} {row[3]:<8}")

    print("\n" + "=" * 80)
    print("✅ 마이그레이션 완료!")
    print("=" * 80)

    print("\n💡 다음 단계:")
    print("1. 재무제표 수집 재개:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/collect/039740?year=2025&quarter=1'")
    print("2. 배치 수집:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/batch/collect-all?limit=10&start_year=2025&end_year=2025'")
    print("3. 재무비율 재계산:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/ratios/batch-calculate?limit=100'")

except Exception as e:
    print(f"\n❌ 마이그레이션 실패: {e}")
    db.rollback()
    raise

finally:
    db.close()