"""
DART (전자공시) API 서비스

금융감독원 전자공시시스템에서 재무제표 데이터를 수집합니다.
API 문서: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
"""
from datetime import datetime
from typing import Optional, Dict, List
import requests
import zipfile
import io
import xml.etree.ElementTree as ET

from sqlalchemy.orm import Session
import pandas as pd

from app.models import Stock, FinancialStatement
from app.config import get_settings


class DartApiService:
    """DART API 서비스"""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.dart_api_key
        self.base_url = "https://opendart.fss.or.kr/api"

        if self.api_key:
            print(f"🔑 DART API Key: {self.api_key[:8]}...")
        else:
            print("⚠️  No DART API key found")

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 고유번호 조회

        DART는 종목코드가 아닌 고유번호(corp_code)를 사용합니다.
        예: 삼성전자 005930 → corp_code: 00126380

        Args:
            stock_code: 종목코드 (예: 005930)

        Returns:
            고유번호 또는 None
        """
        try:
            # DART 고유번호 전체 목록 다운로드 (ZIP)
            url = f"{self.base_url}/corpCode.xml"
            params = {'crtfc_key': self.api_key}

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                xml_data = zip_file.read('CORPCODE.xml')

            # XML 파싱
            root = ET.fromstring(xml_data)

            # 종목코드로 검색
            for corp in root.findall('list'):
                stock_cd = corp.find('stock_code')
                if stock_cd is not None and stock_cd.text == stock_code:
                    corp_code = corp.find('corp_code').text
                    corp_name = corp.find('corp_name').text
                    print(f"✅ Found: {stock_code} ({corp_name}) → corp_code: {corp_code}")
                    return corp_code

            print(f"❌ Corp code not found for {stock_code}")
            return None

        except Exception as e:
            print(f"❌ Error getting corp code for {stock_code}: {e}")
            return None

    def get_financial_statement(
        self,
        corp_code: str,
        year: int,
        report_code: str = "11011",  # 사업보고서
        fs_div: str = "CFS"  # 연결재무제표
    ) -> Optional[pd.DataFrame]:
        """
        재무제표 조회

        Args:
            corp_code: 고유번호
            year: 사업연도 (예: 2023)
            report_code: 보고서 코드
                - 11011: 사업보고서
                - 11012: 반기보고서
                - 11013: 1분기보고서
                - 11014: 3분기보고서
            fs_div: 재무제표 구분
                - CFS: 연결재무제표 (기본)
                - OFS: 개별재무제표

        Returns:
            재무제표 DataFrame 또는 None
        """
        try:
            url = f"{self.base_url}/fnlttSinglAcntAll.json"
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bsns_year': str(year),
                'reprt_code': report_code,
                'fs_div': fs_div
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # 상태 확인
            if data.get('status') != '000':
                error_msg = data.get('message', 'Unknown error')
                print(f"❌ DART API Error: {error_msg}")
                return None

            # 데이터 추출
            if 'list' not in data or not data['list']:
                print(f"⚠️ No financial data found")
                return None

            df = pd.DataFrame(data['list'])
            print(f"✅ Retrieved {len(df)} financial records")
            return df

        except Exception as e:
            print(f"❌ Error getting financial statement: {e}")
            return None

    def parse_financial_data(self, df: pd.DataFrame) -> Dict:
        """
        재무제표 DataFrame을 파싱하여 필요한 항목 추출

        Args:
            df: 재무제표 DataFrame

        Returns:
            파싱된 재무 데이터 딕셔너리
        """
        result = {
            # 손익계산서
            'revenue': None,
            'operating_income': None,
            'net_income': None,
            'ebitda': None,

            # 재무상태표
            'total_assets': None,
            'total_liabilities': None,
            'total_equity': None,

            # 현금흐름표
            'operating_cash_flow': None,
            'investing_cash_flow': None,
            'financing_cash_flow': None,
        }

        try:
            # 계정명 매핑 (재무제표 구분 + 계정명 → 우리 필드명)
            # 형식: (sj_div, account_name) -> field_name
            exact_mapping = {
                # 손익계산서 (IS)
                ('IS', '영업수익'): 'revenue',
                ('IS', '영업이익'): 'operating_income',
                ('IS', '지배기업의 소유주에게 귀속되는 당기순이익(손실)'): 'net_income',

                # 재무상태표 (BS)
                ('BS', '자산총계'): 'total_assets',
                ('BS', '부채총계'): 'total_liabilities',
                ('BS', '자본총계'): 'total_equity',

                # 현금흐름표 (CF)
                ('CF', '영업활동현금흐름'): 'operating_cash_flow',
                ('CF', '투자활동현금흐름'): 'investing_cash_flow',
                ('CF', '재무활동현금흐름'): 'financing_cash_flow',
            }

            # 당기 데이터만 (thstrm_amount)
            for _, row in df.iterrows():
                sj_div = row.get('sj_div', '').strip()
                account_nm = row.get('account_nm', '').strip()
                amount_str = row.get('thstrm_amount', '0')

                # 1차: 정확한 일치 확인 (재무제표 구분 + 계정명)
                key = (sj_div, account_nm)
                if key in exact_mapping:
                    field_name = exact_mapping[key]
                    try:
                        amount = float(amount_str.replace(',', ''))
                        result[field_name] = amount
                        print(f"  ✅ [{sj_div}] {account_nm}: {amount:,.0f}")
                    except:
                        pass
                    continue

                # 2차: 부분 일치 (백업) - 재무제표 구분 확인 필수
                if sj_div == 'IS':
                    if '영업수익' in account_nm and result['revenue'] is None:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            result['revenue'] = amount
                            print(f"  📝 [{sj_div}] {account_nm}: {amount:,.0f}")
                        except:
                            pass
                    elif '영업이익' in account_nm and result['operating_income'] is None:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            result['operating_income'] = amount
                            print(f"  📝 [{sj_div}] {account_nm}: {amount:,.0f}")
                        except:
                            pass
                    elif '당기순이익' in account_nm and result['net_income'] is None:
                        try:
                            amount = float(amount_str.replace(',', ''))
                            result['net_income'] = amount
                            print(f"  📝 [{sj_div}] {account_nm}: {amount:,.0f}")
                        except:
                            pass

            return result

        except Exception as e:
            print(f"❌ Error parsing financial data: {e}")
            return result

    def save_financial_to_db(
        self,
        db: Session,
        ticker: str,
        year: int,
        quarter: Optional[int] = None
    ) -> bool:
        """
        재무제표 데이터를 DB에 저장

        Args:
            db: 데이터베이스 세션
            ticker: 종목코드
            year: 사업연도
            quarter: 분기 (None이면 연간)

        Returns:
            성공 여부
        """
        try:
            # 1. 주식 정보 조회
            stock = db.query(Stock).filter(Stock.ticker == ticker).first()
            if not stock:
                print(f"❌ Stock {ticker} not found in database")
                return False

            print(f"\n{'='*60}")
            print(f"📊 Collecting financial data for {ticker} ({stock.name})")
            print(f"{'='*60}\n")

            # 2. 고유번호 조회
            corp_code = self.get_corp_code(ticker)
            if not corp_code:
                return False

            # 3. 보고서 코드 결정
            report_codes = {
                None: "11011",  # 연간: 사업보고서
                1: "11013",     # 1분기
                2: "11012",     # 2분기 (반기)
                3: "11014",     # 3분기
            }
            report_code = report_codes.get(quarter, "11011")

            # 4. 재무제표 조회
            df = self.get_financial_statement(corp_code, year, report_code)
            if df is None or df.empty:
                return False

            # 5. 데이터 파싱
            print(f"\n📈 Parsing financial data...")
            financial_data = self.parse_financial_data(df)

            # 6. DB 저장
            print(f"\n💾 Saving to database...")

            # 기존 데이터 확인
            existing = db.query(FinancialStatement).filter(
                FinancialStatement.stock_id == stock.id,
                FinancialStatement.fiscal_year == year,
                FinancialStatement.fiscal_quarter == quarter
            ).first()

            report_date = datetime(year, 12, 31).date()  # 임시 (실제로는 공시일 사용)

            if existing:
                # 업데이트
                for key, value in financial_data.items():
                    if value is not None:
                        setattr(existing, key, value)
                print(f"✅ Updated financial statement")
            else:
                # 신규 생성
                statement = FinancialStatement(
                    stock_id=stock.id,
                    fiscal_year=year,
                    fiscal_quarter=quarter,
                    statement_type='ALL',  # 통합
                    report_date=report_date,
                    currency='KRW',
                    **financial_data
                )
                db.add(statement)
                print(f"✅ Created new financial statement")

            db.commit()

            print(f"\n{'='*60}")
            print(f"✅ Financial data collection completed!")
            print(f"{'='*60}\n")

            return True

        except Exception as e:
            print(f"❌ Error saving financial data: {e}")
            db.rollback()
            return False


    def collect_multiple_years(
        self,
        db: Session,
        ticker: str,
        start_year: int,
        end_year: int
    ) -> Dict:
        """
        여러 연도 재무제표 수집

        Args:
            db: 데이터베이스 세션
            ticker: 종목코드
            start_year: 시작 연도
            end_year: 종료 연도

        Returns:
            수집 결과 딕셔너리
        """
        results = {
            'ticker': ticker,
            'years_processed': 0,
            'years_success': 0,
            'years_failed': 0,
            'errors': []
        }

        for year in range(start_year, end_year + 1):
            results['years_processed'] += 1

            try:
                success = self.save_financial_to_db(db, ticker, year)

                if success:
                    results['years_success'] += 1
                else:
                    results['years_failed'] += 1

                # API 속도 제한 (1초 대기)
                import time
                time.sleep(1)

            except Exception as e:
                error_msg = f"Error collecting {year}: {str(e)}"
                results['errors'].append(error_msg)
                results['years_failed'] += 1

        return results