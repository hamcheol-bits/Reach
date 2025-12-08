"""
Finnhub Stock Candles API 테스트
환경변수 로드 문제 해결 후 재테스트
"""
import requests
from datetime import datetime, timedelta

# config.py 사용
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')
from app.config import get_settings

settings = get_settings()
api_key = settings.finnhub_api_key

print("=" * 60)
print("Finnhub Stock Candles API 재테스트")
print("=" * 60)
print(f"API Key: {api_key[:8]}...")
print()

# 1. Apple 주가 조회 (최근 1주일)
ticker = "AAPL"
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

url = "https://finnhub.io/api/v1/stock/candle"
params = {
    'symbol': ticker,
    'resolution': 'D',  # Daily
    'from': int(start_date.timestamp()),
    'to': int(end_date.timestamp()),
    'token': api_key
}

print(f"요청 URL: {url}")
print(f"파라미터: symbol={ticker}, resolution=D")
print()

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"응답 상태: {response.status_code}")
    print()

    if response.status_code == 200:
        data = response.json()
        print("✅ 성공! Finnhub 무료 플랜으로 주가 조회 가능!")
        print(f"상태: {data.get('s')}")
        if data.get('s') == 'ok':
            print(f"데이터 개수: {len(data.get('c', []))}개")
            print(f"Close 가격 샘플: {data.get('c', [])[:3]}")
        print()
        print("결론: 아까 403 에러는 환경변수 로드 문제였음!")
    elif response.status_code == 403:
        print("❌ 403 Forbidden")
        print(f"응답: {response.text}")
        print()
        print("결론: Finnhub 무료 플랜은 Stock Candles 지원 안함 (유료 필요)")
    else:
        print(f"❌ 에러: {response.status_code}")
        print(f"응답: {response.text}")

except Exception as e:
    print(f"❌ 예외 발생: {e}")

print()
print("=" * 60)