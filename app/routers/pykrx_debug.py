"""
pykrx API 직접 조회 라우터
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/pykrx", tags=["pykrx-debug"])


@router.get("/market-data")
async def get_pykrx_market_data(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)", example="2024-12-13"),
    ticker: Optional[str] = Query(None, description="종목 코드 (예: 005930)", example="005930"),
    market: str = Query("KOSPI", description="시장 (KOSPI, KOSDAQ)")
):
    """
    pykrx API로 시가총액 데이터 직접 조회 (디버깅용)

    특정 날짜의 시가총액 데이터를 pykrx API에서 직접 조회합니다.
    DB를 거치지 않고 실시간 API 응답을 확인할 수 있습니다.

    **예시:**
    ```bash
    # 2024-12-13 전체 KOSPI 시가총액
    curl "http://localhost:8001/api/v1/pykrx/market-data?date=2024-12-13&market=KOSPI"

    # 삼성전자만 조회
    curl "http://localhost:8001/api/v1/pykrx/market-data?date=2024-12-13&ticker=005930&market=KOSPI"

    # 과거 날짜 확인
    curl "http://localhost:8001/api/v1/pykrx/market-data?date=2022-12-30&market=KOSPI"
    ```
    """
    from pykrx import stock
    import pandas as pd

    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    # 날짜 형식 변환
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%Y%m%d")
        day_of_week = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="date must be in YYYY-MM-DD format"
        )

    try:
        # pykrx API 호출
        print(f"🔍 pykrx API 호출: {date_str} ({day_of_week}요일), Market: {market}")
        df = stock.get_market_cap_by_ticker(date_str, market=market)

        # 빈 DataFrame 체크
        if df.empty:
            return {
                "status": "no_data",
                "date": date,
                "date_formatted": date_str,
                "day_of_week": day_of_week,
                "market": market,
                "ticker": ticker,
                "message": "pykrx API returned empty data (likely a holiday or data not available)",
                "total_stocks": 0,
                "data": None
            }

        # 영문 컬럼명으로 변환
        df = df.rename(columns={
            '시가총액': 'market_cap',
            '거래량': 'volume',
            '거래대금': 'trading_value',
            '상장주식수': 'shares_outstanding'
        })

        # 통계 계산
        total_stocks = len(df)
        zero_cap_count = (df['market_cap'] == 0).sum()
        valid_cap_count = total_stocks - zero_cap_count

        # 특정 종목 조회
        if ticker:
            if ticker not in df.index:
                return {
                    "status": "ticker_not_found",
                    "date": date,
                    "date_formatted": date_str,
                    "day_of_week": day_of_week,
                    "market": market,
                    "ticker": ticker,
                    "message": f"Ticker {ticker} not found in {market}",
                    "total_stocks": total_stocks,
                    "data": None
                }

            # 해당 종목 데이터
            stock_data = df.loc[ticker]

            return {
                "status": "success",
                "date": date,
                "date_formatted": date_str,
                "day_of_week": day_of_week,
                "market": market,
                "ticker": ticker,
                "total_stocks": int(total_stocks),
                "statistics": {
                    "total_stocks": int(total_stocks),
                    "market_cap_zero": int(zero_cap_count),
                    "market_cap_valid": int(valid_cap_count)
                },
                "data": {
                    "ticker": ticker,
                    "market_cap": float(stock_data['market_cap']),
                    "trading_value": float(stock_data['trading_value']),
                    "shares_outstanding": int(stock_data['shares_outstanding']),
                    "volume": int(stock_data['volume']) if 'volume' in stock_data and pd.notna(stock_data['volume']) else None
                }
            }

        # 전체 종목 조회 (상위 20개만)
        else:
            # DataFrame을 dict 리스트로 변환
            top_20 = df.head(20)
            stocks_list = []

            for idx, row in top_20.iterrows():
                stocks_list.append({
                    "ticker": idx,
                    "market_cap": float(row['market_cap']),
                    "trading_value": float(row['trading_value']),
                    "shares_outstanding": int(row['shares_outstanding']),
                    "volume": int(row['volume']) if pd.notna(row.get('volume')) else None
                })

            return {
                "status": "success",
                "date": date,
                "date_formatted": date_str,
                "day_of_week": day_of_week,
                "market": market,
                "ticker": None,
                "total_stocks": int(total_stocks),
                "statistics": {
                    "total_stocks": int(total_stocks),
                    "market_cap_zero": int(zero_cap_count),
                    "market_cap_valid": int(valid_cap_count)
                },
                "showing": int(len(stocks_list)),
                "data": stocks_list
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"pykrx API error: {str(e)}"
        )


@router.get("/check-trading-day")
async def check_trading_day(
    date: str = Query(..., description="확인할 날짜 (YYYY-MM-DD)", example="2024-12-31"),
    market: str = Query("KOSPI", description="시장 (KOSPI, KOSDAQ)")
):
    """
    특정 날짜가 거래일인지 확인

    pykrx API로 해당 날짜에 종목 리스트가 조회되는지 확인합니다.

    **예시:**
    ```bash
    # 2024-12-31이 거래일인지 확인
    curl "http://localhost:8001/api/v1/pykrx/check-trading-day?date=2024-12-31"

    # 2022-12-30이 거래일인지 확인
    curl "http://localhost:8001/api/v1/pykrx/check-trading-day?date=2022-12-30"
    ```
    """
    from pykrx import stock

    if market not in ["KOSPI", "KOSDAQ"]:
        raise HTTPException(
            status_code=400,
            detail="market must be either 'KOSPI' or 'KOSDAQ'"
        )

    # 날짜 형식 변환
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        date_str = date_obj.strftime("%Y%m%d")
        day_of_week = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]
        is_weekend = date_obj.weekday() >= 5
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="date must be in YYYY-MM-DD format"
        )

    try:
        # 종목 리스트 조회로 거래일 확인
        tickers = stock.get_market_ticker_list(date_str, market=market)

        # 시가총액 데이터 조회
        market_data = stock.get_market_cap_by_ticker(date_str, market=market)

        is_trading_day = len(tickers) > 0
        has_market_data = not market_data.empty

        # 시가총액 0인 종목 수
        zero_cap_count = 0
        if has_market_data:
            zero_cap_count = (market_data['시가총액'] == 0).sum()

        return {
            "status": "success",
            "date": date,
            "date_formatted": date_str,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "market": market,
            "check_result": {
                "is_trading_day": is_trading_day,
                "stock_count": int(len(tickers)),
                "has_market_data": has_market_data,
                "market_data_count": int(len(market_data)) if has_market_data else 0,
                "market_cap_zero_count": int(zero_cap_count) if has_market_data else None
            },
            "conclusion": (
                "✅ 거래일 (데이터 정상)" if is_trading_day and has_market_data and zero_cap_count == 0
                else "⚠️ 거래일이지만 시가총액 데이터 이상" if is_trading_day and (not has_market_data or zero_cap_count > 0)
                else "❌ 휴장일"
            )
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"pykrx API error: {str(e)}"
        )