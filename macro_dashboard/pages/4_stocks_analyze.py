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

# TTM 데이터를 가져와 시리즈로 반환하는 함수
def get_ttm_financials(ticker_data):
    """
    yfinance에서 TTM 재무 데이터를 계산하여 Series로 반환합니다.
    손익계산서/현금흐름표는 최근 4개 분기 합산, 재무상태표는 가장 최신 분기 데이터 사용.
    """
    try:
        # 분기별 데이터 가져오기
        q_financials = ticker_data.quarterly_financials
        q_balance_sheet = ticker_data.quarterly_balance_sheet
        q_cash_flow = ticker_data.quarterly_cash_flow
        
        # 데이터가 비어있으면 빈 Series 반환
        if q_financials.empty or q_balance_sheet.empty or q_cash_flow.empty:
            return pd.Series([], dtype=object)

        # 1. 손익계산서 & 현금흐름표: 최근 4개 분기 합산
        # 결측치를 0으로 채운 후 계산
        latest_four_q_financials = q_financials.iloc[:, :4].fillna(0)
        latest_four_q_cash_flow = q_cash_flow.iloc[:, :4].fillna(0)
        
        ttm_financials = latest_four_q_financials.sum(axis=1)
        ttm_cash_flow = latest_four_q_cash_flow.sum(axis=1)
        
        # 2. 재무상태표: 가장 최신 분기 데이터 사용
        latest_q_balance_sheet = q_balance_sheet.iloc[:, 0].fillna(0)
        
        # 3. 모든 TTM 데이터를 하나의 Series로 병합
        ttm_series = pd.concat([ttm_financials, latest_q_balance_sheet, ttm_cash_flow])
        
        # 중복된 항목 제거 (e.g. Total Assets가 financials에도 있고 balance sheet에도 있는 경우)
        ttm_series = ttm_series[~ttm_series.index.duplicated(keep='first')]
        
        return ttm_series
    except Exception as e:
        return pd.Series([], dtype=object)
    
# DataFrame에서 항목을 안전하게 가져오는 함수 (없으면 NaN 반환)
def safe_loc(df, item):
    if item in df.index:
        return df.loc[item]
    else:
        return pd.Series(np.nan, index=df.columns)

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

            # 연간 재무 데이터 (4년으로 제한)
            financials = ticker_data.financials.iloc[:, :4]
            balance_sheet = ticker_data.balance_sheet.iloc[:, :4]
            cash_flow = ticker_data.cash_flow.iloc[:, :4]
            historical_data = ticker_data.history(period="4y")

            if financials.empty or balance_sheet.empty or cash_flow.empty:
                st.error("재무 정보가 불충분합니다. 다른 티커를 입력해주세요.")
            else:
                # 2. 재무 지표 계산하기
                
                # 재무 데이터들을 단일 DataFrame으로 병합
                financials_t = financials.T
                balance_sheet_t = balance_sheet.T
                cash_flow_t = cash_flow.T
                
                # 중복 컬럼 제거 후 합치기
                financials_t = financials_t.loc[:, ~financials_t.columns.duplicated(keep='first')]
                balance_sheet_t = balance_sheet_t.loc[:, ~balance_sheet_t.columns.duplicated(keep='first')]
                cash_flow_t = cash_flow_t.loc[:, ~cash_flow_t.columns.duplicated(keep='first')]
                
                raw_data = pd.concat([financials_t, balance_sheet_t, cash_flow_t], axis=1)
                
                # 영문 항목명을 한글명으로 매핑하는 딕셔너리
                item_map = {
                    'Total Revenue': '매출액',
                    'Gross Profit': '매출총이익',
                    'Operating Income': '영업이익',
                    'Net Income': '당기순이익',
                    'Net Income Common Stockholders': '당기순이익',
                    'Basic EPS': '주당순이익',
                    'Basic Average Shares': '주식 수',
                    'Total Assets': '총자산',
                    'Current Assets': '유동자산',
                    "Stockholders' Equity": '총자본',
                    'Total Stockholder Equity': '총자본',
                    'Common Stock Equity': '총자본',
                    'Total Equity': '총자본',
                    'Net Tangible Assets': '순유형자산',
                    'Operating Cash Flow': '영업현금흐름',
                    'Investing Cash Flow': '투자현금흐름',
                    'Financing Cash Flow': '재무현금흐름',
                    'Capital Expenditure': '자본적 지출',
                    'Free Cash Flow': '잉여현금흐름',
                    'Repurchase Of Capital Stock': '자사주매입',
                    'Issuance Of Capital Stock': '유상증자',

                }
                
                # 필요한 항목만 선택하고, 없는 항목은 NaN으로 채움
                required_items = [
                    '매출액', '매출총이익', '영업이익', '당기순이익', '주당순이익', '총자산', '유동자산', '총자본',
                    '순유형자산', '영업현금흐름', '투자현금흐름', '재무현금흐름', '자본적 지출', '잉여현금흐름',
                    '자사주매입', '유상증자'
                ]
                
                # 새로운 DataFrame 생성. 인덱스는 한글 항목명으로 지정
                analysis_df = pd.DataFrame(index=required_items, columns=raw_data.index)
                
                # 영문 인덱스를 한글 인덱스로 매핑하여 데이터 복사
                analysis_df.columns = analysis_df.columns.strftime('%Y-%m-%d')
                
                # 데이터를 채우는 과정
                for eng_name, kor_name in item_map.items():
                    if eng_name in raw_data.columns:
                        analysis_df.loc[kor_name] = raw_data[eng_name].values
                
                # TTM 데이터 가져와서 analysis_df에 병합
                ttm_series = get_ttm_financials(ticker_data)
                if not ttm_series.empty:
                    ttm_series = ttm_series.rename(index=item_map)
                    
                    # 중복 인덱스 제거 후 병합
                    ttm_series = ttm_series[~ttm_series.index.duplicated(keep='first')]
                    ttm_df = ttm_series.to_frame(name='TTM')
                    
                    # TTM DataFrame을 기존 DataFrame의 가장 왼쪽에 삽입
                    analysis_df = pd.concat([ttm_df, analysis_df], axis=1, join='inner')
                    
                # 파생 지표 계산 (새로운 행으로 추가)
                total_assets = safe_loc(analysis_df, '총자산')
                total_equity = safe_loc(analysis_df, '총자본')
                current_assets = safe_loc(analysis_df, '유동자산')
                net_income = safe_loc(analysis_df, '당기순이익')
                net_tangible_assets = safe_loc(analysis_df, '순유형자산')
                
                analysis_df.loc['총부채'] = total_assets - total_equity
                analysis_df.loc['순유동자산'] = current_assets - analysis_df.loc['총부채']


                # 비율 계산
                analysis_df.loc['ROA'] = np.where(analysis_df.loc['총자산'] != 0, analysis_df.loc['당기순이익'] / analysis_df.loc['총자산'], 0)
                analysis_df.loc['ROE'] = np.where(analysis_df.loc['총자본'] != 0, analysis_df.loc['당기순이익'] / analysis_df.loc['총자본'], 0)
                analysis_df.loc['순유형자산수익률'] = np.where(analysis_df.loc['순유형자산'] != 0, analysis_df.loc['당기순이익'] / analysis_df.loc['순유형자산'], 0)
                analysis_df.loc['부채비율'] = np.where(analysis_df.loc['총자본'] != 0, analysis_df.loc['총부채'] / analysis_df.loc['총자본'], 0)

                # --- 추가된 로직: 열 순서 재정렬 ---
                # 'TTM' 열을 제외한 연도 열들을 날짜 순으로 정렬
                annual_cols = [col for col in analysis_df.columns if col != 'TTM']
                annual_cols.sort(key=pd.to_datetime, reverse=True)
                
                # 최종 열 순서 정의: 'TTM' + 정렬된 연도
                final_cols = ['TTM'] + annual_cols
                analysis_df = analysis_df[final_cols]
                
                # --- 추가된 로직: 행 순서 재정렬 ---
                final_row_order = [
                    '매출액', '매출총이익', '영업이익', '당기순이익', '주당순이익', '총자산', '유동자산', '총자본',
                    '총부채', '순유동자산', '순유형자산', 'ROA', 'ROE', '순유형자산수익률', '부채비율',
                    '영업현금흐름', '투자현금흐름', '재무현금흐름', '자본적 지출', '잉여현금흐름',
                    '자사주매입', '유상증자'
                ]
                
                # 최종 행 순서에 맞게 데이터프레임 재정렬
                analysis_df = analysis_df.reindex(final_row_order)

                # PER 관련 지표는 별도로 계산
                current_price = info.get('currentPrice')
                latest_eps = analysis_df.loc['주당순이익', 'TTM'] if 'TTM' in analysis_df.columns else analysis_df.loc['주당순이익'].iloc[0]
                calculated_per = current_price / latest_eps if latest_eps != 0 else np.nan
                
                # 결과 출력
                st.subheader(f'"{ticker_symbol}" 재무 지표 분석')
                
                # 포맷팅 딕셔너리 통합 (더 안정적인 방식으로 수정)
                format_dict = {}
                for item in required_items + ['총부채', '순유동자산', 'ROA', 'ROE', '순유형자산수익률', '부채비율']:
                    for col in analysis_df.columns:
                        if item in ['ROA', 'ROE']:
                            format_dict[(item, col)] = '{:.2%}'
                        elif item in ['주당순이익', '순유형자산수익률', '부채비율']:
                            format_dict[(item, col)] = '{:.2f}'
                        else:
                            format_dict[(item, col)] = '{:,.0f}'
                
                st.dataframe(analysis_df.style.format(format_dict))
                
                # 주요 지표 요약
                st.subheader('주요 투자 지표')
                
                per_ratio = info.get('trailingPE')
                forward_per = info.get('forwardPE')
                peg_ratio = info.get('trailingPegRatio')
                
                st.metric("현재 주가", f"${current_price:,.2f}")
                # PER을 새로운 Metric으로 표시
                st.metric("PER (Trailing)", f"{per_ratio:.2f}" if per_ratio is not None else "데이터 없음")
                st.metric("Forward PER", f"{forward_per:.2f}" if forward_per is not None else "데이터 없음")
                st.metric("PEG Ratio", f"{peg_ratio:.2f}" if peg_ratio is not None else "데이터 없음")

                st.write(cash_flow.index.tolist())

        except Exception as e:
            st.error(f'데이터를 가져오거나 처리하는 중 오류가 발생했습니다. 올바른 티커를 입력했는지 확인해주세요.')
            st.error(f'에러 메시지: {e}')