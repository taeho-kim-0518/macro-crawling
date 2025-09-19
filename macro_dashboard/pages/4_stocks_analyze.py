import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 데이터를 안전하게 가져와 Series로 변환하는 함수
def get_clean_financial_series(df, keys):
    '''
    df : financials, balance_sheet, cash_flow 중 선택
    keys : 찾아볼 데이터 키(리스트)
    '''
    for key in keys:
        if key in df.index:
            return df.loc[key].fillna(0)
    # 어떤 키도 찾지 못한 경우, 0으로 채워진 Series 반환
    return pd.Series([0] * len(df.columns), index=df.columns)

# 페이지 제목 설정
st.title('주식 투자 분석기 📊')
st.write('티커를 입력하고 "분석하기" 버튼을 눌러보세요. 지난 5년간의 주요 재무 지표를 분석해 드립니다.')

# 사용자로부터 티커 입력 받기
ticker_symbol = st.text_input('티커 입력 (예: AAPL)', 'AAPL')

# 분석 결과 저장용 DataFrame 초기화
analysis_df = pd.DataFrame()

# 버튼 클릭 시 분석 실행
if st.button('분석하기'):
    if not ticker_symbol:
        st.warning('티커를 입력해주세요.')
    else:
        try:
            # 1. yfinance 객체와 데이터 가져오기
            ticker_data = yf.Ticker(ticker_symbol)
            
            # 데이터가 없을 경우를 대비한 체크
            info = ticker_data.info
            if not info or not info.get('regularMarketPrice'):
                st.error("티커 정보를 가져오는 데 실패했습니다. 올바른 티커를 입력해주세요.")
                st.stop()

            # 연간 재무 데이터 (5년으로 제한)
            financials = ticker_data.financials.iloc[:, :5]
            balance_sheet = ticker_data.balance_sheet.iloc[:, :5]
            cash_flow = ticker_data.cash_flow.iloc[:, :5]
            historical_data = ticker_data.history(period="5y")

            if financials.empty or balance_sheet.empty or cash_flow.empty:
                st.error("재무 정보가 불충분합니다. 다른 티커를 입력해주세요.")
            else:
                # 2. 재무 지표 계산하기
                analysis_df = pd.DataFrame(index=financials.columns)
                
                # 손익계산서
                analysis_df['매출액'] = get_clean_financial_series(financials, ['Total Revenue']).astype(float)
                analysis_df['매출총이익'] = get_clean_financial_series(financials, ['Gross Profit']).astype(float)
                analysis_df['영업이익'] = get_clean_financial_series(financials, ['Operating Income']).astype(float)
                analysis_df['당기순이익'] = get_clean_financial_series(financials, ['Net Income', 'Net Income Common Stockholders']).astype(float)
                analysis_df['주당순이익'] = get_clean_financial_series(financials, ['Basic EPS']).astype(float)
                analysis_df['주식 수'] = get_clean_financial_series(financials, ['Basic Average Shares']).astype(float)
                
                # 재무상태표
                analysis_df['총자산'] = get_clean_financial_series(balance_sheet, ['Total Assets']).astype(float)
                analysis_df['유동자산'] = get_clean_financial_series(balance_sheet, ['Current Assets']).astype(float)
                equity_keys = ["Stockholders' Equity", "Total Stockholder Equity", "Common Stock Equity", "Total Equity"]
                analysis_df['총자본'] = get_clean_financial_series(balance_sheet, equity_keys).astype(float)
                analysis_df['총부채'] = analysis_df['총자산'] - analysis_df['총자본']
                analysis_df['순유형자산'] = get_clean_financial_series(balance_sheet, ['Net Tangible Assets']).astype(float)
                analysis_df['순유동자산'] = analysis_df['유동자산'] - analysis_df['총부채']

                # 현금흐름표
                analysis_df['영업현금흐름'] = get_clean_financial_series(cash_flow, ['Operating Cash Flow']).astype(float)
                analysis_df['투자현금흐름'] = get_clean_financial_series(cash_flow, ['Investing Cash Flow']).astype(float)
                analysis_df['재무현금흐름'] = get_clean_financial_series(cash_flow, ['Financing Cash Flow']).astype(float)
                analysis_df['자본적 지출'] = get_clean_financial_series(cash_flow, ['Capital Expenditure']).astype(float)
                analysis_df['잉여현금흐름'] = get_clean_financial_series(cash_flow, ['Free Cash Flow']).astype(float)
                
                # 자사주 매입 및 유상증자
                analysis_df['자사주매입'] = get_clean_financial_series(cash_flow, ['Repurchase of Capital Stock']).astype(float)
                analysis_df['유상증자'] = get_clean_financial_series(cash_flow, ['Issuance of Capital Stock']).astype(float)
                
                # 배당금 (주의: historical_data에는 일별 데이터이므로, 연간 데이터와 매칭이 필요함)
                # 이 로직은 연간 재무제표와 맞지 않아 오류 가능성이 있으므로 주석 처리
                # analysis_df['배당금'] = historical_data['Dividends'].resample('Y').sum()
                
                # 지표 계산
                with st.spinner('재무 지표를 계산하는 중...'):
                    analysis_df['ROA'] = np.where(analysis_df['총자산'] != 0, analysis_df['당기순이익'] / analysis_df['총자산'], 0)
                    analysis_df['ROE'] = np.where(analysis_df['총자본'] != 0, analysis_df['당기순이익'] / analysis_df['총자본'], 0)
                    analysis_df['순유형자산수익률'] = np.where(analysis_df['순유형자산'] != 0, analysis_df['당기순이익'] / analysis_df['순유형자산'], 0)
                    analysis_df['부채비율'] = np.where(analysis_df['총자본'] != 0, analysis_df['총부채'] / analysis_df['총자본'], 0)
                    
                    # PER 계산
                    current_price = info.get('currentPrice')
                    latest_eps = analysis_df['주당순이익'].iloc[0]
                    analysis_df['PER'] = np.where(latest_eps != 0, current_price / latest_eps, np.nan)
                    
                    # 결과 출력
                    st.subheader(f'"{ticker_symbol}" 지난 5년 재무 지표 분석')
                    
                    # DataFrame T로 전치 후 출력
                    st.dataframe(analysis_df.T.style.format({
                        **{col: '{:,.0f}' for col in ['매출액', '매출총이익', '영업이익', '당기순이익', '총자산', '유동자산', '총자본', '총부채', '순유형자산', '순유동자산', '영업현금흐름', '투자현금흐름', '재무현금흐름', '자본적 지출', '자사주매입', '유상증자', '잉여현금흐름']},
                        '주당순이익': '{:.2f}',
                        'ROA': '{:.2%}',
                        'ROE': '{:.2%}',
                        '순유형자산수익률': '{:.2f}',
                        '부채비율': '{:.2f}',
                        'PER': '{:.2f}'
                    }))
                    
                    # 주요 지표 요약
                    st.subheader('주요 투자 지표')
                    
                    forward_per = info.get('forwardPE')
                    peg_ratio = info.get('pegRatio')
                    
                    st.metric("현재 주가", f"${current_price:,.2f}")
                    st.metric("Forward PER", f"{forward_per:.2f}" if forward_per is not None else "데이터 없음")
                    st.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio is not None else "데이터 없음")

        except Exception as e:
            st.error(f'데이터를 가져오거나 처리하는 중 오류가 발생했습니다. 올바른 티커를 입력했는지 확인해주세요.')
            st.error(f'에러 메시지: {e}')