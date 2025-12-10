"""
자본 관련 계정명 디버깅
실행: python test/test_dart_equity.py
"""
import sys
sys.path.append('/Users/user/PycharmProjects/Reach')

from app.services.dart_api import DartApiService

dart = DartApiService()

# 삼성전자 2023년 재무제표 조회
corp_code = dart.get_corp_code("005930")
df = dart.get_financial_statement(corp_code, 2023)

print("=" * 60)
print("자본 관련 모든 계정명")
print("=" * 60)

for _, row in df.iterrows():
    account_nm = row.get('account_nm', '')
    sj_div = row.get('sj_div', '')
    thstrm_amount = row.get('thstrm_amount', '0')

    if '자본' in account_nm:
        print(f"[{sj_div}] {account_nm:50} : {thstrm_amount:>20}")

print("\n" + "=" * 60)
print("'총계' 포함 계정명")
print("=" * 60)

for _, row in df.iterrows():
    account_nm = row.get('account_nm', '')
    sj_div = row.get('sj_div', '')
    thstrm_amount = row.get('thstrm_amount', '0')

    if '총계' in account_nm:
        print(f"[{sj_div}] {account_nm:50} : {thstrm_amount:>20}")