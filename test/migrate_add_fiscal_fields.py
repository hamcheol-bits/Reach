"""
DB 마이그레이션 스크립트
FinancialStatement, FinancialRatio 테이블에 fiscal_date, report_type 컬럼 추가

실행: python test/migrate_add_fiscal_fields.py
"""
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import text
from app.database import SessionLocal, engine

print("=" * 80)
print("🔧 DB 마이그레이션: fiscal_date, report_type 추가")
print("=" * 80)

db = SessionLocal()

try:
    # 1. FinancialStatement 테이블에 컬럼 추가
    print("\n1️⃣  FinancialStatement 테이블 마이그레이션...")
    print("-" * 80)

    # fiscal_date 추가 (기본값: report_date와 동일하게)
    try:
        db.execute(text("""
                        ALTER TABLE financial_statements
                            ADD COLUMN fiscal_date DATE AFTER fiscal_quarter
                        """))
        print("✅ fiscal_date 컬럼 추가 완료")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⏭️  fiscal_date 컬럼이 이미 존재합니다")
        else:
            print(f"❌ fiscal_date 추가 실패: {e}")

    # report_type 추가 (기본값: fiscal_quarter에 따라 설정)
    try:
        db.execute(text("""
                        ALTER TABLE financial_statements
                            ADD COLUMN report_type VARCHAR(20) AFTER fiscal_date
                        """))
        print("✅ report_type 컬럼 추가 완료")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⏭️  report_type 컬럼이 이미 존재합니다")
        else:
            print(f"❌ report_type 추가 실패: {e}")

    db.commit()

    # 2. 기존 데이터 마이그레이션
    print("\n2️⃣  기존 데이터 마이그레이션...")
    print("-" * 80)

    # fiscal_date = report_date로 설정
    result = db.execute(text("""
                             UPDATE financial_statements
                             SET fiscal_date = report_date
                             WHERE fiscal_date IS NULL
                             """))
    print(f"✅ fiscal_date 업데이트: {result.rowcount}개 레코드")

    # report_type 설정 (fiscal_quarter에 따라)
    # NULL(연간) -> 'annual', 1 -> 'Q1', 2 -> 'Q2', 3 -> 'Q3'
    updates = [
        ("UPDATE financial_statements SET report_type = 'annual' WHERE fiscal_quarter IS NULL AND report_type IS NULL",
         "연간"),
        ("UPDATE financial_statements SET report_type = 'Q1' WHERE fiscal_quarter = 1 AND report_type IS NULL", "1분기"),
        ("UPDATE financial_statements SET report_type = 'Q2' WHERE fiscal_quarter = 2 AND report_type IS NULL", "2분기"),
        ("UPDATE financial_statements SET report_type = 'Q3' WHERE fiscal_quarter = 3 AND report_type IS NULL", "3분기"),
    ]

    for query, desc in updates:
        result = db.execute(text(query))
        print(f"✅ report_type '{desc}' 설정: {result.rowcount}개 레코드")

    db.commit()

    # 3. FinancialRatio 테이블에 컬럼 추가
    print("\n3️⃣  FinancialRatio 테이블 마이그레이션...")
    print("-" * 80)

    # fiscal_date 추가 (기본값: date와 동일하게)
    try:
        db.execute(text("""
                        ALTER TABLE financial_ratios
                            ADD COLUMN fiscal_date DATE AFTER stock_id
                        """))
        print("✅ fiscal_date 컬럼 추가 완료")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⏭️  fiscal_date 컬럼이 이미 존재합니다")
        else:
            print(f"❌ fiscal_date 추가 실패: {e}")

    # report_type 추가
    try:
        db.execute(text("""
                        ALTER TABLE financial_ratios
                            ADD COLUMN report_type VARCHAR(20) AFTER fiscal_date
                        """))
        print("✅ report_type 컬럼 추가 완료")
    except Exception as e:
        if "Duplicate column" in str(e):
            print("⏭️  report_type 컬럼이 이미 존재합니다")
        else:
            print(f"❌ report_type 추가 실패: {e}")

    db.commit()

    # 4. FinancialRatio 기존 데이터 마이그레이션
    print("\n4️⃣  FinancialRatio 기존 데이터 마이그레이션...")
    print("-" * 80)

    # fiscal_date = date로 설정
    result = db.execute(text("""
                             UPDATE financial_ratios
                             SET fiscal_date = date
                             WHERE fiscal_date IS NULL
                             """))
    print(f"✅ fiscal_date 업데이트: {result.rowcount}개 레코드")

    # report_type은 일단 'annual'로 설정 (나중에 재계산 필요)
    result = db.execute(text("""
                             UPDATE financial_ratios
                             SET report_type = 'annual'
                             WHERE report_type IS NULL
                             """))
    print(f"✅ report_type 'annual' 설정: {result.rowcount}개 레코드")

    db.commit()

    # 5. 인덱스 추가
    print("\n5️⃣  인덱스 추가...")
    print("-" * 80)

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_statements_fiscal_date
                            ON financial_statements (fiscal_date)
                        """))
        print("✅ financial_statements.fiscal_date 인덱스 생성")
    except Exception as e:
        if "Duplicate key" in str(e) or "already exists" in str(e):
            print("⏭️  인덱스가 이미 존재합니다")
        else:
            print(f"⚠️  인덱스 생성 실패 (무시 가능): {e}")

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_statements_report_type
                            ON financial_statements (report_type)
                        """))
        print("✅ financial_statements.report_type 인덱스 생성")
    except Exception as e:
        if "Duplicate key" in str(e) or "already exists" in str(e):
            print("⏭️  인덱스가 이미 존재합니다")
        else:
            print(f"⚠️  인덱스 생성 실패 (무시 가능): {e}")

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_ratios_fiscal_date
                            ON financial_ratios (fiscal_date)
                        """))
        print("✅ financial_ratios.fiscal_date 인덱스 생성")
    except Exception as e:
        if "Duplicate key" in str(e) or "already exists" in str(e):
            print("⏭️  인덱스가 이미 존재합니다")
        else:
            print(f"⚠️  인덱스 생성 실패 (무시 가능): {e}")

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_ratios_report_type
                            ON financial_ratios (report_type)
                        """))
        print("✅ financial_ratios.report_type 인덱스 생성")
    except Exception as e:
        if "Duplicate key" in str(e) or "already exists" in str(e):
            print("⏭️  인덱스가 이미 존재합니다")
        else:
            print(f"⚠️  인덱스 생성 실패 (무시 가능): {e}")

    db.commit()

    print("\n" + "=" * 80)
    print("✅ 마이그레이션 완료!")
    print("=" * 80)

    print("\n💡 다음 단계:")
    print("1. 서버 재시작")
    print("2. 재무비율 통계 확인:")
    print("   curl 'http://localhost:8001/api/v1/financial/ratios/stats'")
    print("3. 테스트 실행:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/ratios/calculate/005930'")

except Exception as e:
    print(f"\n❌ 마이그레이션 실패: {e}")
    db.rollback()
    raise

finally:
    db.close()