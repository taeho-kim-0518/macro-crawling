import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 페이지 제목 설정
st.title('주식 투자 분석기 📊')
st.write('티커를 입력하고 "분석하기" 버튼을 눌러보세요. 지난 5년간의 주요 재무 지표를 분석해 드립니다.')

# 사용자로부터 티커 입력 받기
ticker_symbol = st.text_input('티커 입력 (예: AAPL)', 'AAPL')

# 데이터를 안전하게 가져와 숫자로 변환하는 함수
def get_clean_financial_data(df, keys, is_balance_sheet=False):
    try:
        series = None
        for key in keys:
            if key in df.index:
                series = df.loc[key]
                break
        
        if series is None:
            # 해당 키를 찾지 못한 경우
            return pd.Series([0] * len(df.columns), index=df.columns)
            
        # 데이터 타입을 숫자로 강제 변환하며, 변환 불가 시 NaN으로 처리
        numeric_series = pd.to_numeric(series, errors='coerce')
        
        if is_balance_sheet:
            # 재무상태표 데이터는 보통 연말 값. 따라서 NaN을 0으로 채우는 대신 이전 값으로 채움
            return numeric_series.ffill().fillna(0)
        else:
            # 손익계산서 데이터는 NaN을 0으로 채움
            return numeric_series.fillna(0)
            
    except Exception as e:
        # 함수 내부에서 오류 발생 시 안전하게 0으로 채워진 Series 반환
        return pd.Series([0] * len(df.columns), index=df.columns)


# 버튼 클릭 시 분석 실행
if st.button('분석하기'):
    if ticker_symbol:
        try:
            # 1. 데이터 가져오기
            ticker_data = yf.Ticker(ticker_symbol)
            financials = ticker_data.financials.iloc[:, :5]
            balance_sheet = ticker_data.balance_sheet.iloc[:, :5]
            historical_prices = yf.download(ticker_symbol, period="5y")
            info = ticker_data.info

            if financials.empty or balance_sheet.empty or historical_prices.empty:
                st.error("재무 정보가 불충분합니다. 다른 티커를 입력해주세요.")
            else:
                # 2. 재무 지표 계산하기
                analysis_df = pd.DataFrame(index=financials.columns)

                # 손익계산서 데이터
                analysis_df['총 매출'] = get_clean_financial_data(financials, ['Total Revenue']).astype(int)
                analysis_df['영업 이익'] = get_clean_financial_data(financials, ['Operating Income']).astype(int)
                net_income = get_clean_financial_data(financials, ['Net Income'])
                analysis_df['순이익'] = net_income.astype(int)

                # 재무상태표 데이터: 다양한 키 이름으로 시도
                equity_keys = ['Total Stockholder Equity', 'Stockholders Equity', 'Total Equity']
                intangible_keys = ['Net Tangible Assets']

                total_equity = get_clean_financial_data(balance_sheet, equity_keys, is_balance_sheet=True)
                net_tangible_assets = get_clean_financial_data(balance_sheet, intangible_keys, is_balance_sheet=True)

             
                analysis_df['순유형자산'] = net_tangible_assets.astype(int)
                
                # 순유형자산 이익률 및 ROE 계산
                net_tangible_assets[net_tangible_assets <= 0] = np.nan
                analysis_df['순유형자산 이익률 (%)'] = (net_income / net_tangible_assets) * 100
                analysis_df['순유형자산 이익률 (%)'] = analysis_df['순유형자산 이익률 (%)'].fillna(0)

                total_equity[total_equity <= 0] = np.nan
                analysis_df['ROE (%)'] = (net_income / total_equity) * 100
                analysis_df['ROE (%)'] = analysis_df['ROE (%)'].fillna(0)
                
                # PER 계산
                eps = get_clean_financial_data(financials, ['Basic EPS'])
                per_series = []
                for date in financials.columns:
                    close_price = historical_prices['Close'].asof(date)
                    
                    if not isinstance(eps.loc[date], (int, float)) or eps.loc[date] == 0:
                        per_series.append(None)
                    else:
                        per_series.append(float(close_price) / float(eps.loc[date]))

                analysis_df['PER'] = per_series
                
                # 3. 결과 출력하기
                st.subheader(f'"{ticker_symbol}" 지난 5년 재무 지표 분석')
                st.dataframe(analysis_df.T.style.format(formatter={
                    '총 매출': '{:,.0f}',
                    '영업 이익': '{:,.0f}',
                    '순이익': '{:,.0f}',
                    '순유형자산': '{:,.0f}',
                    '순유형자산 이익률 (%)': '{:.2f}',
                    'ROE (%)': '{:.2f}',
                    'PER': '{:.2f}'
                }))
                
                forward_per = info.get('forwardPE')
                if forward_per is not None:
                    st.write(f'---')
                    st.write(f'**현재 Forward PER:** {forward_per:.2f}')
                    st.write('*(Forward PER은 미래 예측값으로, 지난 5년간의 표에 포함되지 않습니다.)*')

        except Exception as e:
            st.error(f'데이터를 가져오거나 처리하는 중 오류가 발생했습니다: {e}')
            st.error(f'에러 메시지: {e}')
    else:
        st.warning('티커를 입력해주세요.')