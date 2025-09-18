import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np


ticker_symbol = 'AAPL'

ticker_data = yf.Ticker(ticker_symbol)
financials = ticker_data.financials.iloc[:, :5]
balance_sheet = ticker_data.balance_sheet.iloc[:, :5]
cash_flow = ticker_data.cash_flow.iloc[:, :5]
historical_prices = yf.download(ticker_symbol, period="5y")
current_price = ticker_data.info.get('currentPrice')
forward_per = ticker_data.info.get('forwardPE')
peg_ratio = ticker_data.info.get('pegRatio')

analysis_df = pd.DataFrame()

# 데이터를 안전하게 가져와 숫자로 변환하는 함수 (여러 키를 지원하도록 개선)
def get_clean_financial_data(df, keys):
    '''
    df : financials, balance_sheet, cash_flow 중 선택
    '''
    for key in keys:
        if key in df.index:
            # 해당 키를 찾으면 Series를 반환하고, NaN을 0으로 채움
            return df.loc[key].fillna(0)
    # 어떤 키도 찾지 못한 경우, 0으로 채워진 Series 반환
    return pd.Series([0] * len(df.columns), index=df.columns)



# 페이지 제목 설정
# st.title('주식 투자 분석기 📊')
# st.write('티커를 입력하고 "분석하기" 버튼을 눌러보세요. 지난 5년간의 주요 재무 지표를 분석해 드립니다.')

# 사용자로부터 티커 입력 받기
# ticker_symbol = st.text_input('티커 입력 (예: AAPL)', 'AAPL')




# 버튼 클릭 시 분석 실행
if st.button('분석하기'):
    if ticker_symbol:
        try:
            # 1. 데이터 가져오기
            ticker_data = yf.Ticker(ticker_symbol)
            financials = ticker_data.financials.iloc[:, :5]
            balance_sheet = ticker_data.balance_sheet.iloc[:, :5]
            cash_flow = ticker_data.cash_flow.iloc[:, :5]
            historical_prices = yf.download(ticker_symbol, period="5y")

            if financials.empty or balance_sheet.empty or cash_flow.empty or historical_prices.empty:
                st.error("재무 정보가 불충분합니다. 다른 티커를 입력해주세요.")
            else:
                # 2. 재무 지표 계산하기
                analysis_df = pd.DataFrame()

                # 손익계산서 데이터
                analysis_df['매출액'] = financials.loc['Total Revenue'].fillna(0).astype(int)
                analysis_df['매출총이익'] = financials.loc['Gross Profit'].fillna(0).astype(int)
                analysis_df['영업이익'] = financials.loc['Operating Income'].fillna(0).astype(int)
                analysis_df['당기순이익'] = financials.loc['Net Income Common Stockholders'].fillna(0).astype(int)
                analysis_df['주당순이익'] = financials.loc['Basic EPS'].fillna(0).astype(float)
                analysis_df['주식 수'] = financials.loc['Basic Average Shares'].fillna(0).astype(float)


                # 재무상태표 데이터
                analysis_df['총자산'] = balance_sheet.loc['Total Assets'].fillna(0).astype(int)
                analysis_df['유형자산'] = balance_sheet.loc['Current Assets'].fillna(0).astype(int)
                equity_keys = ["Stockholders' Equity", "Total Stockholder Equity", "Common Stock Equity", "Total Equity"]
                analysis_df['총자본'] = get_clean_financial_data(balance_sheet, equity_keys).fillna(0).astype(int)
                analysis_df['총부채'] = analysis_df['총자산'] - analysis_df['총자본']
                analysis_df['순유형자산'] = balance_sheet.loc['Net Tangible Assets'].fillna(0).astype(int)
                analysis_df['순유동자산'] = analysis_df['유동자산'] - analysis_df['총부채']


                # 현금흐름 데이터
                analysis_df['영업현금흐름'] = cash_flow.loc['Operating Cash Flow'].fillna(0).astype(int)
                analysis_df['투자현금흐름'] = cash_flow.loc['Investing Cash Flow'].fillna(0).astype(int)
                analysis_df['재무현금흐름'] = cash_flow.loc['Financing Cash Flow'].fillna(0).astype(int)
                analysis_df['자본적 지출'] = cash_flow.loc['Capital Expenditure'].fillna(0).astype(int)
                analysis_df['자사주매입'] = cash_flow.loc['Repurchase of Capital Stock'].fillna(0).astype(int)
                analysis_df['잉여현금흐름'] = cash_flow.loc['Free Cash Flow'].fillna(0).astype(int)

                analysis_df['ROA'] = analysis_df['당기순이익']/analysis_df['총자산']
                analysis_df['ROE'] = analysis_df['당기순이익']/analysis_df['총자본']
                analysis_df['순유형자산수익률'] = analysis_df['당기순이익']/analysis_df['순유형자산']
                analysis_df['부채비율'] = analysis_df['총부채']/analysis_df['총자본']

                # CAPEX 분석
                #CAPEX와 영업활동 현금흐름 (OCF) 비교:
                # OCF > CAPEX: 기업이 본업으로 벌어들인 현금으로 투자 비용을 충분히 충당하고 있다는 뜻입니다. 이는 매우 건전한 재무 상태를 보여줍니다.
                # OCF < CAPEX: 기업이 투자를 위해 본업 외에 외부 자금(대출, 주식 발행 등)을 조달하고 있다는 뜻입니다. 신생 기업이나 급성장하는 기업에서는 흔한 현상이지만, 장기화될 경우 재무 위험이 커질 수 있습니다.

                # CAPEX와 산업 특성 비교:

                # 제조업, 중공업: 이 산업들은 공장, 설비 등 대규모 유형자산이 필수적이므로 CAPEX가 높습니다. 높은 CAPEX는 해당 산업의 성장세를 반영할 수 있습니다.
                # 소프트웨어, 서비스업: 이 산업들은 유형자산 투자가 상대적으로 적어 CAPEX가 낮습니다.
                # 결론적으로, CAPEX는 기업의 현재 현금 지출을 넘어 미래 성장에 대한 의지와 투자 능력을 보여주는 중요한 지표입니다.

                # 순유형자산 이익률 및 ROE 계산
            
                
                # 3. 결과 출력하기
                st.subheader(f'"{ticker_symbol}" 지난 5년 재무 지표 분석')
                st.dataframe(analysis_df.T.style.format(formatter={
                    '매출액': '{:,.0f}',
                    '매출총이익': '{:,.0f}',
                    '영업이익': '{:,.0f}',
                    '당기순이익': '{:,.0f}',
                    '총자산': '{:,.0f}',
                    '총자본': '{:,.0f}',
                    '총부채': '{:,.0f}',
                    '순유형자산': '{:,.0f}',
                    '순유동자산': '{:,.0f}',
                    '영업현금흐름': '{:,.0f}',
                    '투자현금흐름': '{:,.0f}',
                    '재무현금흐름': '{:,.0f}',
                    '자본적 지출': '{:,.0f}',
                    '자사주매입': '{:,.0f}',
                    '잉여현금흐름': '{:,.0f}',
                    '주당순이익': '{:.2f}',
                    'ROA': '{:.2%}',
                    'ROE': '{:.2%}',
                    '순유형자산수익률': '{:.2f}',
                    '부채비율': '{:.2f}',
                    'PER': '{:.2f}'
                }))
                
                # PER 계산하기
                if current_price is not None:
                    latest_eps = analysis_df['주당순이익'][0]

                    if latest_eps != 0:
                        per = current_price/latest_eps
                    else:
                        st.warning("최신 주당순이익(EPS)가 0이므로, 계산할 수 없습니다.")

                else:
                    st.warning("현재 주가를 가져올 수 없습니다.")

                # Forward PE 가져오기
                if forward_per is not None:
                    st.write(f'---')
                    st.write(f'**현재 Forward PER:** {forward_per:.2f}')
                    st.write('*(Forward PER은 미래 예측값으로, 지난 5년간의 표에 포함되지 않습니다.)*')

                # PEG 가져오기
                if forward_per is not None:
                    st.write(f'---')
                    st.write(f'**현재 Forward PER:** {forward_per:.2f}')
                    st.write('*(Forward PER은 미래 예측값으로, 지난 5년간의 표에 포함되지 않습니다.)*')

        except Exception as e:
            st.error(f'데이터를 가져오거나 처리하는 중 오류가 발생했습니다: {e}')
            st.error(f'에러 메시지: {e}')
    else:
        st.warning('티커를 입력해주세요.')