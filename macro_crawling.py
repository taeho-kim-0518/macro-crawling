import os
import time
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import yfinance as yf
from bs4 import BeautifulSoup
from scipy.stats import linregress
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from zoneinfo import ZoneInfo


from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from md_updater import MarginDebtUpdater
from ism_pmi_updater import ISMPMIUpdater
from SNP_forward_pe_updater import forwardpe_updater
from putcall_ratio_updater import PutCallRatioUpdater
from bullbear_spread_updater import BullBearSpreadUpdater
from lei_updater import LEIUpdater

# 한글 폰트 설정 (Windows에서는 기본적으로 'Malgun Gothic' 가능)
mpl.rcParams['font.family'] = 'Malgun Gothic'  # 또는 'NanumGothic', 'AppleGothic' (Mac)
mpl.rcParams['axes.unicode_minus'] = False  # 마이너스(-) 깨짐 방지

# 🔑 환경변수 로딩용 (필요 시 pip install python-dotenv)
from dotenv import load_dotenv
load_dotenv()  # .env 파일 읽어서 os.environ에 자동으로 등록


class MacroCrawler:
    def __init__(self):
        self.fred_api_key = os.environ.get("FRED_API_KEY")
        self.eia_api_key = os.environ.get("EIA_API_KEY")
        
        if not self.fred_api_key:
            raise ValueError("FRED_API_KEY가 환경변수에 설정되어 있지 않습니다.")
        if not self.eia_api_key:
            raise ValueError("EIA_API_KEY가 환경변수에 설정되어 있지 않습니다.")
        
        print("✅ FRED & EIA API 키 불러오기 성공")

        # 마진 부채 업데이트기 연결
        self.margin_updater = MarginDebtUpdater("md_df.csv")
        # ISM PMI 업데이트기 연결
        self.pmi_updater = ISMPMIUpdater("pmi_data.csv")
        # Forward PE 업데이트기 연결
        self.snp_forwardpe_updater = forwardpe_updater("forward_pe_data.csv")
        # PUT CALL Ratio 업데이트기 연결
        self.put_call_ratio_updater = PutCallRatioUpdater("put_call_ratio.csv")
        # Bull Bear Spread 업데이트기 연결
        self.bull_bear_spread_updater = BullBearSpreadUpdater("bull_bear_spread.csv")
        # LEI 업데이트기 연결
        self.lei_updater = LEIUpdater("lei_data.csv")


    # Clear 1개월 딜레이 데이터
    def get_10years_treasury_yeild(self):
        '''
        FRED API : 미국 10년물 국채 수익률
        '''

        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id' : 'GS10', # 10년물 국채 금리
            'api_key' : self.fred_api_key,
            'file_type' : 'json',
            'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        }

        try:
            response = requests.get(url, params= params, timeout=10)
            response.raise_for_status() # HTTP 에러 발생 시 예외 처리
            data = response.json()

            if 'observations' not in data:
                raise ValueError(F"'observations' 키가 없음 : {data}")

            # 데이터프레임 변환
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

            return df
        
        except Exception as e:
            print(f"[ERROR] FRED API 호출 실패 : {e}")
            return pd.DataFrame()

    # Clear - 1개월 딜레이 데이터    
    def get_2years_treasury_yeild(self):
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id' : 'GS2', # 2년물 국채 금리
            'api_key' : self.fred_api_key,
            'file_type' : 'json',
            'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        }

        try:
            response = requests.get(url, params= params, timeout=10)
            response.raise_for_status() # HTTP 에러 발생 시 예외 처리
            data = response.json()

            if 'observations' not in data:
                raise ValueError(F"'observations' 키가 없음 : {data}") 

            # 데이터프레임 변환
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors= 'coerce')


            return df
        
        except Exception as e:
            print(f"[ERROR] FRED API 호출 실패 : {e}")
            return pd.DataFrame()

    # Clear - 1개월 딜레이 데이터     
    def get_cpi(self):
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'CPIAUCSL',  # CPI
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '1999-01-01'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print("❌ API 요청 또는 JSON 파싱 실패:", e)
            print("📦 응답 내용:", response.text)
            return pd.DataFrame()

        if 'observations' not in data:
            print("❌ 'observations' 키 없음. 응답 내용:", data)
            return pd.DataFrame()

        if not data['observations']:
            print("❌ observations 리스트 비어있음:", data)
            return pd.DataFrame()

        df = pd.DataFrame(data['observations'])

        if 'date' not in df.columns:
            print("❌ 'date' 컬럼이 존재하지 않음. df.columns:", df.columns)
            return pd.DataFrame()

        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        df.to_csv("cpi_data.csv", encoding='utf-8-sig')

        return df
    
    def get_cpi_yoy(self):
        df = self.get_cpi() # 원래 CPIAUCSL 지수 불러오기
        df = df.sort_values('date').dropna()

        df['CPI YOY(%)'] = df['value'].pct_change(periods=12)*100 # 12개월 전 대비 변화율
        return df
    
    # Clear - 1개월 딜레이 데이터  
    def get_m2(self) : 
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'M2SL',  # M2 통화량
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        try:
            response = requests.get(url, params=params)
            data = response.json()
        except Exception as e:
            print("❌ API 요청 또는 JSON 파싱 실패:", e)
            print("📦 응답 내용:", response.text)
            return pd.DataFrame()
        
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df
    
  
    def get_m2_yoy(self):
        df = self.get_m2()
        df = df.sort_values('date')
        df['m2_yoy'] = df['value'].pct_change(periods=12) * 100
        return df[['date', 'm2_yoy']]

    # Clear 1개월 딜레이 데이터
    def update_margin_debt_data(self):
        '''
        로컬에 저장된 margin_debt 파일 불러오기
        '''
        try:
            md_df = self.margin_updater.update_csv()
            print("✅ 마진 부채 CSV 업데이트 완료")
        except Exception as e:
            print("📛 마진 데이터 업데이트 실패:", e)
        return md_df


    # def get_margin_debt_data(self):
    #     '''
    #     마진 부채 데이터 가져오기(고점 판단)
    #     '''
    #     # 1년치 데이터 크롤링
    #     url = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"

    #     try:
    #         response = requests.get(url, timeout=20)
    #         response.raise_for_status()
    #         soup = BeautifulSoup(response.text, "html.parser")

    #     except Exception as e:
    #         print("❌ API 요청 또는 JSON 파싱 실패:", e)
    #         print("📦 응답 내용:", response.text)
    #         return pd.DataFrame()
        
    #     table = soup.select_one("table")  # 가장 첫 번째 테이블 선택
    #     rows = table.find_all("tr")
        
    #     data = []
    #     headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]

    #     for row in rows[1:]:
    #         cols = [td.get_text(strip=True).replace(",", "") for td in row.find_all("td")]
    #         if len(cols) == len(headers):
    #             data.append(cols)

    #     df = pd.DataFrame(data, columns=headers)
    #     df['Month/Year'] = pd.to_datetime(df['Month/Year'], format='%b-%y')
    #     # df = df.rename(columns={"Debit Balances in Customers' Securities Margin Accounts" : "margin_debt"})
    #     for col in df.columns[1:]:
    #         df[col] = pd.to_numeric(df[col], errors='coerce')
    #     return df
    
      # 전체 데이터 엑셀로 다운로드 후 불러오기
        # try:
        #     df = pd.read_excel('margin-statistics001.xlsx')

        #     # 컬럼명 정리
        #     df = df.rename(columns={
        #         'Year-Month': 'date',
        #         "Debit Balances in Customers' Securities Margin Accounts": 'margin_debt'
        #     })

        #     # 날짜 타입 변환
        #     df['date'] = pd.to_datetime(df['date'], format='%Y-%m')
        #     df['margin_debt'] = pd.to_numeric(df['margin_debt'].astype(str).str.replace(',', ''), errors='coerce')

        #     # 2000년 이후 데이터만 필터링
        #     df = df[df['date'] >= '2000-01-01'].dropna(subset=['margin_debt'])

        #     # 필요 컬럼만 반환
        #     return df[['date', 'margin_debt']]

        # except Exception as e:
        #     print("❌ Excel 파일 읽기 또는 처리 오류:", e)
        #     return pd.DataFrame()

    
    # Clear  
    def get_margin_yoy_change(self):
        '''
        마진 부채의 전년 대비 YOY (%) 변화율 계산
        '''
        df = self.update_margin_debt_data()
        if df.empty:
            return pd.DataFrame()

        df = df.sort_values("Month/Year")
        df["margin_debt"] = df["Debit Balances in Customers' Securities Margin Accounts"]
        df["margin_debt_clean"] = df["margin_debt"].astype(str).str.replace(',', '', regex=False)
        df["margin_debt"] = pd.to_numeric(df["margin_debt_clean"], errors="coerce").fillna(0).astype(int)
        df = df.drop(columns=["margin_debt_clean"])
        df["Margin YoY (%)"] = df["margin_debt"].pct_change(periods=12) * 100
        return df[["Month/Year", "margin_debt", "Margin YoY (%)"]]


    ## 유동성 관련
    # Clear
    def generate_zscore_trend_signals(self):
        """
        Margin Debt / M2 비율의 z-score 및 추세 조건 기반 전략

        매수 조건:
            - margin_debt / m2 비율의 z-score < -1.5
            - 비율이 전월 대비 상승 (반등 시작)

        매도 조건:
            - z-score > 1.5
            - 비율이 전월 대비 -5% 이상 급락

        실제 매매는 신호일 기준 +2개월 후 진입
        수익률은 진입일부터 3개월 후까지의 S&P500 종가 기준

        Parameters:
            df : DataFrame with 'date', 'm2', 'margin_debt', 'sp500_close' columns

        Returns:
            DataFrame with signal type, signal date, action date, and 3-month return
        """
        df = self.merge_m2_margin_sp500_abs()
        df = df.sort_values("date").copy()
        df["ratio"] = df["margin_debt"] / df["m2"]
        df["ratio_z"] = (df["ratio"] - df["ratio"].rolling(window=36, min_periods=12).mean()) / \
                        df["ratio"].rolling(window=36, min_periods=12).std()
        df["ratio_change_pct"] = df["ratio"].pct_change() * 100

        # 신호 정의
        df["buy_signal"] = (df["ratio_z"] < -1.2) & (df["ratio_change_pct"] > 0)
        df["sell_signal"] = (df["ratio_z"] > 1.5) & (df["ratio_change_pct"] < -5)

        results = []
        for idx, row in df.iterrows():
            if row["buy_signal"] or row["sell_signal"]:
                signal = "BUY" if row["buy_signal"] else "SELL"
                signal_date = row["date"]
                action_date = signal_date + relativedelta(months=2)

                future_df = df[df["date"] >= action_date].reset_index(drop=True)
                if len(future_df) < 3:
                    continue

                entry_price = future_df.loc[0, "sp500_close"]
                exit_price = future_df.loc[2, "sp500_close"]
                return_pct = (exit_price - entry_price) / entry_price

                results.append({
                    "signal": signal,
                    "original_signal_date": signal_date,
                    "action_date": future_df.loc[0, "date"],
                    "return_3m": return_pct
                })

        return pd.DataFrame(results)
    
    # Clear
    def generate_mdyoy_signals(self):
        '''
        Margin Debt YoY 전략 기반 매수/매도 신호 생성 함수 (2개월 발표 지연 반영)
        df : 병합된 데이터프레임(merge_m2_margin_sp500_abs)
        '''

        df = self.merge_m2_margin_sp500_abs()
        df = df.copy()
        df["margin_yoy"] = df["margin_debt"].pct_change(periods=12) * 100

        # 신호 조건
        df["buy_signal"] = (df["margin_yoy"] > 0) & (df["margin_yoy"].shift(1) <= 0)
        df["sell_signal"] = (df["margin_yoy"] < -10) & (df["margin_yoy"].shift(1) >= -10)

        # 발표 지연 감안한 진입 시점 계산
        df["signal_date"] = df["date"]
        df["action_date"] = df["signal_date"] + pd.DateOffset(months=2)

        return df

    # Clear - 실시간 데이터
    def get_sp500(self):
        '''
        S&P500 지수 조회
        '''

        ticker = '^GSPC'
        df = yf.download(ticker, start='2000-01-01', interval="1d", progress=False)

        # 인덱스가 날짜인 경우 reset_index 필요
        if not isinstance(df.index, pd.RangeIndex):
            df = df.reset_index()

        # Date 컬럼 이름 처리 (환경마다 다름)
        possible_date_cols = ['Date', 'Datetime', 'date']
        for col in possible_date_cols:
            if col in df.columns:
                df = df.rename(columns={col: 'date'})
                break

        # Close 컬럼 이름 처리
        if 'Close' in df.columns:
            df = df.rename(columns={'Close': 'sp500_close'})
        elif ('Close', ticker) in df.columns:
            df = df.rename(columns={('Close', ticker): 'sp500_close'})

        # 멀티인덱스 컬럼 방어코드
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

        # date 컬럼 타입 변환
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

        # 필요한 컬럼만 남기기
        df = df[['date', 'sp500_close']].dropna(subset=['date', 'sp500_close'])

        return df
        # ticker = '^GSPC'
        # df = yf.download(ticker, start='2000-01-01', interval="1d", progress=False )
        # # 인덱스를 컬럼으로 변환
        # df = df.reset_index()

        # # 멀티인덱스 컬럼 --> 단일 컬럼으로 변환
        # df.columns = [col[0] if isinstance(col,tuple) else col for col in df.columns]

        # # 컬럼명 정리
        # df = df.rename(columns={'Date': 'date', 'Close': 'sp500_close'})
        
        # # 월 단위로 맞춰주기 (Period → Timestamp)
        # df['date'] = pd.to_datetime(df['date']) #dt.to_period('M').dt.to_timestamp()

        # # 필요한 컬럼만 반환
        # df = df[['date', 'sp500_close']]
        

        # return df

    
    # Clear
    def merge_m2_margin_sp500_abs(self):
        '''
        M2, margin_debt, S&P500 지수 데이터프레임 병합
        '''
        
        df_m2 = self.get_m2().copy()
        df_m2['date'] = df_m2['date'].dt.to_period('M').dt.to_timestamp()
        df_m2 = df_m2.rename(columns={'value' : 'm2'})

        df_margin = self.get_margin_yoy_change().copy()
        df_margin['date'] = df_margin['Month/Year'].dt.to_period('M').dt.to_timestamp()
        #df_margin["margin_debt"] = df_margin["Debit Balances in Customers' Securities Margin Accounts"]
        #df_margin["margin_debt"] = df_margin["margin_debt"].str.replace(',','').astype(int)

        df_sp500 = self.get_sp500().copy()
        df_sp500['date'] = pd.to_datetime(df_sp500['date'])  # 혹시 모르니 안전하게
        df_sp500['month'] =  df_sp500['date'].dt.to_period('M').dt.to_timestamp()

        # 각 월의 첫 번째 날짜에 해당하는 S&P500 값만 추출
        sp_monthly_first = df_sp500.sort_values('date').groupby('month').first().reset_index()

        # ✅ 기존 'date' 컬럼 제거 (중복 방지)
        sp_monthly_first = sp_monthly_first.drop(columns=['date'])
        
        # ✅ 날짜를 해당 월의 1일로 바꿔줌
        sp_monthly_first = sp_monthly_first.rename(columns={'month': 'date'})
        sp_monthly_first = sp_monthly_first[["date", "sp500_close"]]

        df = pd.merge(df_m2, df_margin[['date', 'margin_debt']], on='date', how='inner')
        df = pd.merge(df, sp_monthly_first, on='date', how='inner')
        df["ratio"] = df["margin_debt"] / df["m2"]   # ← 이 줄 추가
        return df
 
    # Clear
    def plot_sp500_with_signals_and_graph(self, save_to=None):
        """
        S&P500 종가 + Margin Debt/M2 비율 + 발표시차(다음달 25일) 반영 신호 시각화

        - 신호 계산은 월별(MS)로 수행 (36개월 z-score)
        - 각 월의 지표는 '다음 달 25일'에 공개된다고 가정
        - 발표일이 주말/휴일이면 '발표일 이후 첫 거래일'에 신호와 비율이 유효
        """

        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt

        # 1) 원자료 병합 (일단 일별 S&P500과 월별 지표가 함께 들어있는 df라 가정)
        df = self.merge_m2_margin_sp500_abs().copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        # ---- 월별 테이블 만들기 (각 월 1일 기준) ----
        # margin_debt, m2는 월별이므로 월 초 기준으로 대표값을 하나 뽑아온다.
        # (여기서는 해당 월의 첫 값 사용; 필요시 last/mean으로 바꿀 수 있음)
        # m_month = (
        #     df.loc[:, ["date", "margin_debt", "m2"]]
        #     .dropna(subset=["margin_debt", "m2"])
        #     .copy()
        # )
        # m_month["month"] = m_month["date"].values.astype("datetime64[M]")  # 월 단위로 버킷팅 (MS)
        # m_month = (
        #     m_month.sort_values(["month", "date"])
        #         .groupby("month", as_index=False)
        #         .first()[["month", "margin_debt", "m2"]]
        # )
        # m_month = m_month.rename(columns={"month": "month_start"})  # 월 초(예: 2025-07-01)

        m_src = (
        df.loc[:, ["date", "margin_debt", "m2"]]
        .dropna(subset=["margin_debt", "m2"])
        .copy()
        )

        # 월초 라벨로 그룹핑하고 '그 달의 마지막 관측값'을 사용
        monthly = (
            m_src.set_index("date")
                .groupby(pd.Grouper(freq="MS"))
                .last()                # 그 달 말일 시점의 '알고 있던' 값
                .dropna()
                .reset_index()
        )

        # ★ 핵심: 이 값은 '이전 월'의 경제지표이므로 월 라벨을 1개월 뒤로 당겨서(−1M) 실제 기준월로 맞춤
        # monthly["month_start"] = (monthly["date"] - pd.offsets.MonthBegin(1))
        monthly["month_start"] = monthly["date"]
                                  
        m_month = (
            monthly[["month_start", "margin_debt", "m2"]]
                .sort_values("month_start")
                .reset_index(drop=True)
        )

        # 2) 월별 비율 및 z-score 계산 (36개월 롤링)
        m_month["ratio"] = m_month["margin_debt"] / m_month["m2"]
        m_month["ratio_ma"] = m_month["ratio"].rolling(window=36, min_periods=12).mean()
        m_month["ratio_sd"] = m_month["ratio"].rolling(window=36, min_periods=12).std()
        m_month["ratio_z"] = (m_month["ratio"] - m_month["ratio_ma"]) / m_month["ratio_sd"]
        m_month["ratio_change_pct"] = m_month["ratio"].pct_change() * 100

        # 3) 월별 신호 (완화 조건 그대로 사용)
        m_month["buy_signal"]  = (m_month["ratio_z"] < -1.2) & (m_month["ratio_change_pct"] > 0)
        m_month["sell_signal"] = (m_month["ratio_change_pct"] < -7)
        # m_month["sell_signal"] = (m_month["ratio_z"] > 1.2) & (m_month["ratio_change_pct"] < -5)

        # 4) '발표일' 계산: 다음 달 25일
        #    예: 7월 데이터 -> 8월 25일
        m_month["release_date"] = (
            m_month["month_start"] + pd.offsets.MonthBegin(1) + pd.DateOffset(days=24)
        )

    
        # 5) 발표일을 '발표일 이후 첫 거래일'로 맞추기
        # ✅ 반드시 '일별' S&P500 라인 확보
        sp_daily = self.get_sp500().copy()  # 일별로 받는 함수 사용(없으면 self.get_sp500())
        sp_daily["date"] = pd.to_datetime(sp_daily["date"])

        # 컬럼 표준화
        if "close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"close": "sp500_close"})
        elif "Close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"Close": "sp500_close"})
        # 이미 sp500_close면 그대로 사용

        sp_line = (
            sp_daily[["date", "sp500_close"]]
            .dropna()
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )

        # 거래일 캘린더 = 실제 가격이 있는 날짜로 사용 (휴일 자동 제외)
        trade_days = sp_line[["date"]].copy()
        sp_dates = trade_days["date"].to_numpy()

        def next_trading_day(dt):
            i = np.searchsorted(sp_dates, np.datetime64(dt), side="left")
            return pd.NaT if i >= len(sp_dates) else pd.Timestamp(sp_dates[i])

        m_month["effective_date"] = m_month["release_date"].apply(next_trading_day)

        # 6) '발표 후에만 보이는' 일별 비율 시계열 만들기 (거래일 캘린더 기준)
        full_days = trade_days.copy()
        full_days["ratio_published"] = np.nan

        published = (
            m_month.loc[:, ["effective_date", "ratio"]]
                .dropna()
                .sort_values("effective_date")
        )

        eff  = published["effective_date"].to_list()
        vals = published["ratio"].to_list()

        for i, start in enumerate(eff):
            end = eff[i+1] if i+1 < len(eff) else full_days["date"].iloc[-1] + pd.Timedelta(days=1)
            mask = (full_days["date"] >= start) & (full_days["date"] < end)
            full_days.loc[mask, "ratio_published"] = vals[i]

        # 플롯용 DF: 거래일 ⨯ 가격 ⨯ ratio_published
        plot_df = trade_days.merge(sp_line, on="date", how="left").merge(full_days, on="date", how="left")
        plot_df["sp500_close"] = pd.to_numeric(plot_df["sp500_close"], errors="coerce").ffill()  # ✔ 연속 라인 보장

        # --- 시그널 DF 만들기 (가격 붙이기) ---
        signals = m_month.loc[
            (m_month["buy_signal"] | m_month["sell_signal"]) & m_month["effective_date"].notna(),
            ["month_start", "release_date", "effective_date", "ratio_z", "ratio_change_pct", "buy_signal", "sell_signal"]
        ].copy()

        signals["signal_type"] = np.where(signals["buy_signal"], "BUY", "SELL")

        # ✔ 발표일(=주문일) 당일에 가격이 비어 있으면 다음 거래일 가격을 붙이도록 asof 병합
        signals = pd.merge_asof(
            signals.sort_values("effective_date"),
            sp_line.sort_values("date"),
            left_on="effective_date",
            right_on="date",
            direction="forward"   # 발표일 이후 첫 가용 가격
        )
        signals = signals.drop(columns=["date"])
        signals = signals[[
            "effective_date", "release_date", "month_start",
            "signal_type", "sp500_close", "ratio_z", "ratio_change_pct"
        ]]

        # --- 그래프 시각화 (fig, ax1 생성) ---
        fig, ax1 = plt.subplots(figsize=(14, 6))

        ax1.plot(plot_df["date"], plot_df["sp500_close"], linewidth=2, label="S&P500 지수", color="blue")
        ax1.set_ylabel("S&P500 종가", color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")

        buys  = signals[signals["signal_type"] == "BUY"]
        sells = signals[signals["signal_type"] == "SELL"]

        ax1.scatter(buys["effective_date"],  buys["sp500_close"],  marker="^", s=100, label="매수 신호", color="green")
        ax1.scatter(sells["effective_date"], sells["sp500_close"], marker="v", s=100, label="매도 신호", color="red")

        ax2 = ax1.twinx()
        ax2.plot(plot_df["date"], plot_df["ratio_published"], linestyle="--", label="Margin Debt/M2 (발표 반영)", color="gray")
        ax2.set_ylabel("Margin Debt / M2 비율", color="gray")
        ax2.tick_params(axis="y", labelcolor="gray")

        fig.suptitle("S&P500 + 매수/매도 신호(발표시차 반영) + Margin Debt/M2 비율", fontsize=14)

        lines, labels = [], []
        for ax in [ax1, ax2]:
            l, lab = ax.get_legend_handles_labels()
            lines += l; labels += lab
        fig.legend(lines, labels, loc="upper left", bbox_to_anchor=(0.1, 0.92))

        fig.tight_layout()

        # ✅ 컬럼명 변경
        signals = signals.rename(columns={
            "effective_date": "주문일",
            "release_date": "발표일",
            "month_start": "데이터 기준일",
            "ratio_change_pct": "전월대비 상승률"
        })

        if save_to:
            fig.savefig(save_to, format="png")
            # plt.close(fig)
        # else:
        #     plt.show()   # ✅ VS Code에서도 창 뜸

        # ✅ 그래프와 신호 테이블 반환
        return fig, ax1, signals
    
    def get_today_signal_with_m2_and_margin_debt(self, today=None, market_tz="America/New_York"):
        """
        오늘 날짜 기준 매수/매도/대기 의사결정 + 컨텍스트(최근 발표분) 반환
        - 발표시차(다음달 25일) + '발표 후 첫 거래일' 규칙 준수
        - 오늘 신호 없으면 최근 발표분을 WAIT으로 표시
        """
        import numpy as np
        import pandas as pd

        # ── 오늘(미국 시장시간대) ─────────────────────────────────────────────
        if today is None:
            today_ts = pd.Timestamp.now(tz=market_tz).normalize()
        else:
            t = pd.Timestamp(today)
            if t.tzinfo is None:
                t = t.tz_localize(market_tz)
            today_ts = t.normalize()
        today_naive = today_ts.tz_localize(None)

        # ── 월별 지표 테이블 (라벨 보정) ───────────────────────────────────────
        df = self.merge_m2_margin_sp500_abs().copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)  # ✅ 전체 정렬(중요)

        m_src = df.loc[:, ["date", "margin_debt", "m2"]].dropna().copy()

        monthly = (
            m_src.set_index("date")
                .groupby(pd.Grouper(freq="MS"))
                .last()           # 그 달 말일까지 '알고 있던' 값
                .dropna()
                .reset_index()
        )
        # 말일값은 실제로 '이전 월' 지표이므로 라벨 -1M
        # monthly["month_start"] = monthly["date"] - pd.offsets.MonthBegin(1)

        # 수정: 해당 월 그대로 사용
        monthly["month_start"] = monthly["date"] 

        m_month = (
            monthly[["month_start", "margin_debt", "m2"]]
                .sort_values("month_start")
                .reset_index(drop=True)
        )

        # ── ratio / z / 모멘텀 ────────────────────────────────────────────────
        m_month["ratio"] = m_month["margin_debt"] / m_month["m2"]
        m_month["ratio_ma"] = m_month["ratio"].rolling(36, min_periods=12).mean()
        m_month["ratio_sd"] = m_month["ratio"].rolling(36, min_periods=12).std()
        m_month["ratio_z"]  = (m_month["ratio"] - m_month["ratio_ma"]) / m_month["ratio_sd"]
        m_month["ratio_change_pct"] = m_month["ratio"].pct_change() * 100

        # ── 신호 규칙 ─────────────────────────────────────────────────────────
        m_month["buy_signal"]  = (m_month["ratio_z"] < -1.2) & (m_month["ratio_change_pct"] > 0)
        m_month["sell_signal"] = (m_month["ratio_change_pct"] < -7)

        # ── 발표일/주문일(발표 후 첫 거래일) ─────────────────────────────────
        m_month["release_date"] = m_month["month_start"] + pd.offsets.MonthBegin(1) + pd.DateOffset(days=24)

        # 거래일 달력: 가격 일자(최소 요건)로 사용
        sp_daily = self.get_sp500().copy()
        sp_daily["date"] = pd.to_datetime(sp_daily["date"])
        if "close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"close": "sp500_close"})
        elif "Close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"Close": "sp500_close"})
        sp_line = (
            sp_daily[["date", "sp500_close"]]
            .dropna()
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )
        trade_days = sp_line[["date"]].copy()
        if trade_days.empty:
            # 가격 달력이 없다면 평일 달력으로 대체
            start = (m_month["release_date"].min() - pd.Timedelta(days=10)).normalize()
            end   = (max(today_naive, m_month["release_date"].max()) + pd.Timedelta(days=10)).normalize()
            trade_days = pd.DataFrame({"date": pd.bdate_range(start, end)})

        td = trade_days["date"].to_numpy()
        def next_trading_day(dt):
            i = np.searchsorted(td, np.datetime64(dt), side="left")
            return pd.NaT if i >= len(td) else pd.Timestamp(td[i])

        m_month["effective_date"] = m_month["release_date"].apply(next_trading_day)

        # ── 오늘 발생 신호(이벤트) ───────────────────────────────────────────
        mask_today = (
            m_month["effective_date"].notna()
            & (m_month["effective_date"].dt.normalize() == today_naive)
            & (m_month["buy_signal"] | m_month["sell_signal"])
        )
        sig_today = m_month.loc[mask_today].copy()

        # ── 최근 발표분 컨텍스트(오늘 주문 없을 때 보여줄 1행) ────────────────
        mask_ctx = m_month["effective_date"].notna() & (m_month["effective_date"] <= today_naive)
        context = m_month.loc[mask_ctx].sort_values("effective_date").tail(1).copy()

        # 가격 붙이고 포맷하기
        def _attach_and_format(df_in):
            if df_in.empty:
                return df_in
            out = pd.merge_asof(
                df_in.sort_values("effective_date"),
                sp_line.sort_values("date"),
                left_on="effective_date",
                right_on="date",
                direction="forward"
            ).drop(columns=["date"])
            out["signal_type"] = np.where(out["buy_signal"], "BUY",
                                np.where(out["sell_signal"], "SELL", "WAIT"))
            out = out.rename(columns={
                "effective_date": "주문일",
                "release_date":  "발표일",
                "month_start":   "데이터 기준일",
                "ratio_change_pct": "전월비 변화율(%)"
            })[
                ["주문일","발표일","데이터 기준일","signal_type","sp500_close","ratio_z","전월비 변화율(%)"]
            ]
            out["ratio_z"] = out["ratio_z"].round(3)
            out["전월비 변화율(%)"] = out["전월비 변화율(%)"].round(2)
            return out

        if not sig_today.empty:
            details = _attach_and_format(sig_today)
            action = "SELL" if (details["signal_type"] == "SELL").any() else "BUY"
        elif not context.empty:
            # 컨텍스트를 WAIT으로 강제 표기
            context.loc[:, ["buy_signal","sell_signal"]] = False
            details = _attach_and_format(context)
            details.loc[:, "signal_type"] = "WAIT"
            # ✅ 추가: 대기 화면에서는 '주문일'을 오늘 날짜로 덮어쓰기
            details.loc[:, "주문일"] = today_naive   # 또는 today_naive.date()로 '날짜만'
            action = "NONE"

        else:
            # 초기 구간 등 아무 데이터도 없을 때
            cols = ["주문일","발표일","데이터 기준일","signal_type","sp500_close","ratio_z","전월비 변화율(%)"]
            details = pd.DataFrame(columns=cols)
            action = "NONE"

        # ── 오늘 거래일 여부 ─────────────────────────────────────────────────
        is_trading_day = (today_naive.normalize() in set(trade_days["date"])) or (today_naive.weekday() < 5)

        # ── 다음 발표/주문 예정(달력 기준으로 항상 '앞'을 가리키게) ───────────
        rel = (today_naive.replace(day=25)
            if today_naive.day <= 25
            else (today_naive + pd.offsets.MonthBegin(1)).replace(day=25))
        eff = next_trading_day(rel)
        next_rel = {"release_date": rel, "effective_date": eff, "estimated": True}

        return {
            "today": today_ts,
            "is_trading_day": is_trading_day,
            "action": action,      # 오늘 주문 이벤트: BUY/SELL/NONE
            "details": details,    # 오늘 신호 or 최근 발표분 WAIT 1행
            "next_release": next_rel
        }
    
    # Clear
    def check_today_md_signal(self):
        """
        오늘이 generate_zscore_trend_signals 또는 generate_mdyoy_signals 기준
        매수/매도 유효월(month)에 속하는지 확인

        - today가 action_date와 같은 달(Month)이면 유효
        - 그 달 전체를 매매 유효 시점으로 간주
        """

        today = pd.Timestamp.today().normalize()  
        # today = pd.Timestamp("2023-03-15").normalize()  # 테스트용 날짜 강제 설정 
        today_month = today.to_period("M")  # 월 단위 비교용

        print(f"📅 오늘 날짜 (확인 기준): {today.date()}")

        # 데이터 병합
        df = self.merge_m2_margin_sp500_abs()

        # --- 전략 1: z-score 기반
        zscore_signal_df = self.generate_zscore_trend_signals()
        zscore_signal_df["action_month"] = zscore_signal_df["action_date"].dt.to_period("M")
        zscore_today = zscore_signal_df[zscore_signal_df["action_month"] == today_month]

        # --- 전략 2: margin YoY 기반
        mdyoy_df = self.generate_mdyoy_signals()
        mdyoy_df["action_month"] = mdyoy_df["action_date"].dt.to_period("M")
        mdyoy_today = mdyoy_df[mdyoy_df["action_month"] == today_month]

        signal_found = False

        if not zscore_today.empty:
            print("\n📌 [Z-Score 전략] 이번 달 매매 신호 있음!")
            for _, row in zscore_today.iterrows():
                print(f"👉 {row['action_date'].date()} : {row['signal']} 신호 (발생일: {row['original_signal_date'].date()})")
            signal_found = True

        mdyoy_filtered = mdyoy_today[mdyoy_today["buy_signal"] | mdyoy_today["sell_signal"]]
        if not mdyoy_filtered.empty:
            print("\n📌 [Margin YoY 전략] 이번 달 매매 신호 있음!")
            for _, row in mdyoy_filtered.iterrows():
                if row["buy_signal"]:
                    print(f"👉 {row['action_date'].date()} : BUY 신호 (발생일: {row['signal_date'].date()})")
                elif row["sell_signal"]:
                    print(f"👉 {row['action_date'].date()} : SELL 신호 (발생일: {row['signal_date'].date()})")
            signal_found = True

        if not signal_found:
            print("\n✅ 이번 달은 매수/매도 진입 시점이 아닙니다.")

    # Clear - 월별데이터 - 1개월 지연
    def get_fed_funds_rate(self):
        '''
        미국 기준 금리 계산
        '''
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'FEDFUNDS',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['fed_funds_rate'] = pd.to_numeric(df['value'], errors='coerce')

        return df

    # Clear    
    def generate_fed_rate_turning_points(self):
        """
        기준금리 변화에서 인하 시작점 (rate_cut=True), 인상 시작점 (rate_hike=True)만 잡는 함수
        """
        fed_rate_df = self.get_fed_funds_rate()
        df = fed_rate_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        df["prev_rate"] = df["fed_funds_rate"].shift(1)
        df["rate_diff"] = df["fed_funds_rate"] - df["prev_rate"]

        # 기준금리 변화 방향
        df["trend"] = df["rate_diff"].apply(lambda x: "up" if x > 0 else ("down" if x < 0 else "flat"))
        df["prev_trend"] = df["trend"].shift(1)

        # 전환점: flat → 제외
        df["rate_cut"] = (df["prev_trend"] != "down") & (df["trend"] == "down")
        df["rate_hike"] = (df["prev_trend"] != "up") & (df["trend"] == "up")

        return df[["date", "fed_funds_rate", "rate_cut", "rate_hike"]]

    # Clear
    def get_rate_signal(self):
        '''
        금리 기반 보조 지표 시그널 계산

        Parameters:
            latest_10y (float): 최신 10년물 국채 수익률 (%)
            latest_2y (float): 최신 2년물 국채 수익률 (%)
            latest_fed_rate (float): 최신 미국 기준금리 (%)
            latest_cpi_yoy (float): 최신 CPI YoY (%)
            prev_cpi_yoy (float): 직전월 CPI YoY (%)

        Returns:
            signal (int): -1 (매도), 0 (중립), +1 이상 (매수 우호적)
            comments (list): 판단 근거 설명
        '''
        signal = 0
        comments = []

        latest_10y = self.get_10years_treasury_yeild()['value'].iloc[-1]
        latest_2y = self.get_2years_treasury_yeild()['value'].iloc[-1]
        prev_10y = self.get_10years_treasury_yeild()['value'].iloc[-2]
        prev_2y = self.get_2years_treasury_yeild()['value'].iloc[-2]
        latest_cpi_yoy = self.get_cpi_yoy()['CPI YOY(%)'].iloc[-1]
        latest_fed_rate = self.get_fed_funds_rate()['fed_funds_rate'].iloc[-1]
        prev_cpi_yoy = self.get_cpi_yoy()['CPI YOY(%)'].iloc[-2]

        # 실질금리 계산
        real_10y = latest_10y - latest_cpi_yoy
        real_2y = latest_2y - latest_cpi_yoy

        # 실질금리 조건 (CPI 추세 반영)
        if real_10y < 0:
            print("10년물 금리 : ", latest_10y, "CPI_YoY : ", latest_cpi_yoy)
            if latest_cpi_yoy < prev_cpi_yoy:
                signal += 1
                comments.append("🔼 실질금리 < 0 & CPI YoY 하락 → 완화 신호")
            else:
                signal -= 1
                comments.append("⚠️ 실질금리 < 0 but CPI YoY 상승 → 인플레 압력")
        else:
            comments.append("ℹ️ 실질금리 양호 (10Y > CPI YoY)")

        if real_2y > 2:
            print("2년물 금리 : ", latest_2y, "CPI_YoY : ", latest_cpi_yoy)
            signal -= 1
            comments.append("📉 단기 실질금리 > 2% → 긴축 우려")

        # 금리차 (장단기 스프레드)
        spread = latest_10y - latest_2y
        prev_spread = prev_10y - prev_2y

        # 변화량
        delta_spread = spread - prev_spread

        # 판단
        if spread < -0.5:
            if delta_spread > 0:
                signal += 1
                comments.append("🔼 장단기 금리역전 상태지만 정상화 추세 → 긍정적 변화")
            else:
                signal -= 1
                comments.append("⚠️ 장단기 금리역전 + 추가 악화 → 침체 신호")
        elif spread > 0:
            if delta_spread < 0:
                signal -= 1
                comments.append("⚠️ 장단기 금리차 양수지만 역전 방향으로 축소 중 → 주의")
            else:
                signal += 1
                comments.append("🔼 장단기 금리차 정상 + 확장 추세 → 회복 기대")
        else:
            comments.append("⏸️ 장단기 금리차 중립 구간")

        # # 기준금리 vs 2년물 (미래 금리 인하 기대 여부)
        # if latest_2y < latest_fed_rate:
        #     signal += 1
        #     comments.append("🔽 2Y < 기준금리 → 금리 인하 기대 (완화 시그널)")
        # else:
        #     comments.append("⏸ 2Y ≥ 기준금리 → 긴축 지속 또는 불확실성")

        return signal, comments

    # Clear
    def plot_rate_indicators_vs_sp500(self):
        # 데이터 준비
        sp500 = self.get_sp500()
        df_10y = self.get_10years_treasury_yeild()
        df_2y = self.get_2years_treasury_yeild()
        cpi_yoy = self.get_cpi_yoy()
        fed = self.get_fed_funds_rate()

        # 월 단위 정렬
      
        sp500['date'] = pd.to_datetime(sp500['date'])  # 혹시 모르니 안전하게
        sp500['month'] = pd.to_datetime(sp500['date']).dt.to_period('M').dt.to_timestamp()

        # 각 월의 첫 번째 날짜에 해당하는 S&P500 값만 추출
        sp_monthly_first = sp500.sort_values('date').groupby('month').first().reset_index()

        # ✅ 기존 'date' 컬럼 제거 (중복 방지)
        sp_monthly_first = sp_monthly_first.drop(columns=['date'])
        
        # ✅ 날짜를 해당 월의 1일로 바꿔줌
        sp_monthly_first = sp_monthly_first.rename(columns={'month': 'date'})
        sp_monthly_first = sp_monthly_first[["date", "sp500_close"]]


        df_10y['date'] = df_10y['date'].dt.to_period('M').dt.to_timestamp()
        df_2y['date'] = df_2y['date'].dt.to_period('M').dt.to_timestamp()
        cpi_yoy['date'] = cpi_yoy['date'].dt.to_period('M').dt.to_timestamp()
        fed['date'] = fed['date'].dt.to_period('M').dt.to_timestamp()

        # 병합
        df = sp_monthly_first.copy()
        df = df.merge(df_10y[['date', 'value']], on='date', how='inner').rename(columns={'value': '10y'})
        df = df.merge(df_2y[['date', 'value']], on='date', how='inner').rename(columns={'value': '2y'})
        df = df.merge(cpi_yoy[['date', 'CPI YOY(%)']], on='date', how='inner').rename(columns={'CPI YOY(%)': 'cpi_yoy'})
        df = df.merge(fed[['date', 'fed_funds_rate']], on='date', how='inner')

        # 지표 계산
        df['real_10y'] = df['10y'] - df['cpi_yoy']
        df['spread'] = df['10y'] - df['2y']
        # df['ffr_vs_2y'] = df['fed_funds_rate'] - df['2y']

        # 시각화
        fig, axs = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

        # 1. S&P500
        axs[0].plot(df['date'], df['sp500_close'], label='S&P500', color='black')
        axs[0].set_ylabel('S&P500')
        axs[0].legend(loc='upper left')
        axs[0].grid(True)

        # 2. 실질금리 (10Y - CPI YoY)
        axs[1].plot(df['date'], df['real_10y'], label='실질 10Y 금리', color='green')
        axs[1].axhline(0, color='gray', linestyle='--')
        axs[1].set_ylabel('10Y - CPI YoY (%)')
        axs[1].legend(loc='upper left')
        axs[1].grid(True)

        # 3. 장단기 금리차 (10Y - 2Y)
        axs[2].plot(df['date'], df['spread'], label='10Y - 2Y', color='blue')
        axs[2].axhline(0, color='gray', linestyle='--')
        axs[2].fill_between(df['date'], df['spread'], 0, where=(df['spread'] < 0), color='red', alpha=0.2, label='역전 구간')
        axs[2].set_ylabel('10Y - 2Y (%)')
        axs[2].legend(loc='upper left')
        axs[2].grid(True)

        # # 4. 기준금리 - 2Y
        # axs[3].plot(df['date'], df['ffr_vs_2y'], label='기준금리 - 2Y', color='orange')
        # axs[3].axhline(0, color='gray', linestyle='--')
        # axs[3].set_ylabel('FFR - 2Y (%)')
        # axs[3].legend(loc='upper left')
        # axs[3].grid(True)

        fig.suptitle("📊 금리 기반 주요 지표 vs S&P500", fontsize=16)
        plt.tight_layout()
        plt.show()

    # Clear
    def plot_rate_indicators_vs_sp500_with_signal(self):
        # 데이터 준비
        sp500 = self.get_sp500()
        df_10y = self.get_10years_treasury_yeild()
        df_2y = self.get_2years_treasury_yeild()
        cpi_yoy = self.get_cpi_yoy()
        fed = self.get_fed_funds_rate()

        # 월 단위 정렬
      
        sp500['date'] = pd.to_datetime(sp500['date'])  # 혹시 모르니 안전하게
        sp500['month'] = pd.to_datetime(sp500['date']).dt.to_period('M').dt.to_timestamp()

        # 각 월의 첫 번째 날짜에 해당하는 S&P500 값만 추출
        sp_monthly_first = sp500.sort_values('date').groupby('month').first().reset_index()

        # ✅ 기존 'date' 컬럼 제거 (중복 방지)
        sp_monthly_first = sp_monthly_first.drop(columns=['date'])
        
        # ✅ 날짜를 해당 월의 1일로 바꿔줌
        sp_monthly_first = sp_monthly_first.rename(columns={'month': 'date'})
        sp_monthly_first = sp_monthly_first[["date", "sp500_close"]]


        # 날짜 처리
        for df in [df_10y, df_2y, cpi_yoy, fed]:
            df['date'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()

        # 병합
        df = sp_monthly_first.copy()
        df = df.merge(df_10y[['date', 'value']], on='date').rename(columns={'value': '10y'})
        df = df.merge(df_2y[['date', 'value']], on='date').rename(columns={'value': '2y'})
        df = df.merge(cpi_yoy[['date', 'CPI YOY(%)']], on='date').rename(columns={'CPI YOY(%)': 'cpi_yoy'})
        df = df.merge(fed[['date', 'fed_funds_rate']], on='date')

        # 지표 계산
        df['real_10y'] = df['10y'] - df['cpi_yoy']
        df['spread'] = df['10y'] - df['2y']
        # df['ffr_vs_2y'] = df['fed_funds_rate'] - df['2y']

        # 📌 과거 시점별 rate_signal 계산
        signal_list = []
        for i in range(1, len(df)):
            try:
                latest_10y = df.iloc[i]['10y']
                latest_2y = df.iloc[i]['2y']
                prev_10y = df.iloc[i-1]['10y']
                prev_2y = df.iloc[i-1]['2y']
                latest_cpi_yoy = df.iloc[i]['cpi_yoy']
                prev_cpi_yoy = df.iloc[i-1]['cpi_yoy']
                latest_fed_rate = df.iloc[i]['fed_funds_rate']

                # 재현한 rate_signal 로직
                signal = 0
                real_10y = latest_10y - latest_cpi_yoy
                real_2y = latest_2y - latest_cpi_yoy
                spread = latest_10y - latest_2y
                prev_spread = prev_10y - prev_2y
                delta_spread = spread - prev_spread

                if real_10y < 0:
                    if latest_cpi_yoy < prev_cpi_yoy:
                        signal += 1
                    else:
                        signal -= 1
                if real_2y > 2:
                    signal -= 1
                if spread < -0.5:
                    signal += 1 if delta_spread > 0 else -1
                elif spread > 0:
                    signal += 1 if delta_spread >= 0 else -1
                if latest_2y < latest_fed_rate:
                    signal += 1

                signal_list.append(signal)
            except:
                signal_list.append(None)

        df = df.iloc[1:].copy()
        df['rate_signal'] = signal_list

        # 시각화
        fig, axs = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

        # 1. S&P500
        axs[0].plot(df['date'], df['sp500_close'], label='S&P500', color='black')
        axs[0].scatter(df[df['rate_signal'] >= 2]['date'], df[df['rate_signal'] >= 2]['sp500_close'], marker='^', color='green', label='📈 매수 신호', s=80)
        axs[0].scatter(df[df['rate_signal'] <= -2]['date'], df[df['rate_signal'] <= -2]['sp500_close'], marker='v', color='red', label='📉 매도 신호', s=80)
        axs[0].set_ylabel('S&P500')
        axs[0].legend(loc='upper left')
        axs[0].grid(True)

        # 2. 실질금리 (10Y - CPI YoY)
        axs[1].plot(df['date'], df['real_10y'], label='실질 10Y 금리', color='green')
        axs[1].axhline(0, color='gray', linestyle='--')
        axs[1].set_ylabel('10Y - CPI YoY (%)')
        axs[1].legend(loc='upper left')
        axs[1].grid(True)

        # 3. 장단기 금리차 (10Y - 2Y)
        axs[2].plot(df['date'], df['spread'], label='10Y - 2Y', color='blue')
        axs[2].axhline(0, color='gray', linestyle='--')
        axs[2].fill_between(df['date'], df['spread'], 0, where=(df['spread'] < 0), color='red', alpha=0.2)
        axs[2].set_ylabel('10Y - 2Y (%)')
        axs[2].legend(loc='upper left')
        axs[2].grid(True)

        # 4. 기준금리 - 2Y
        # axs[3].plot(df['date'], df['ffr_vs_2y'], label='기준금리 - 2Y', color='orange')
        # axs[3].axhline(0, color='gray', linestyle='--')
        # axs[3].set_ylabel('FFR - 2Y (%)')
        # axs[3].legend(loc='upper left')
        # axs[3].grid(True)

        fig.suptitle("📊 금리 기반 주요 지표 vs S&P500 + 시그널 마킹", fontsize=16)
        plt.tight_layout()
        plt.show()

    def analyze_rate_correlations(self, show_plot: bool = True):
        """
        S&P500 종가와 금리 관련 주요 지표 간 상관관계 분석 및 시각화
        - 실질 10년 금리 (10Y - CPI YoY)
        - 장단기 금리차 (10Y - 2Y)
        - 기준금리 - 2년물

        Returns:
            dict: 각 지표와 S&P500 간의 피어슨 상관계수
        """
        # 1. 데이터 불러오기
        sp500 = self.get_sp500()
        df_10y = self.get_10years_treasury_yeild()
        df_2y = self.get_2years_treasury_yeild()
        cpi_yoy = self.get_cpi_yoy()
        fed = self.get_fed_funds_rate()

        # 2. 날짜 통일 (월 단위)
        for df in [sp500, df_10y, df_2y, cpi_yoy, fed]:
            df['date'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()

        # 3. 병합
        df = sp500.copy()
        df = df.merge(df_10y[['date', 'value']], on='date').rename(columns={'value': '10y'})
        df = df.merge(df_2y[['date', 'value']], on='date').rename(columns={'value': '2y'})
        df = df.merge(cpi_yoy[['date', 'CPI YOY(%)']], on='date').rename(columns={'CPI YOY(%)': 'cpi_yoy'})
        df = df.merge(fed[['date', 'fed_funds_rate']], on='date')

        # 4. 지표 계산
        df['real_10y'] = df['10y'] - df['cpi_yoy']
        df['spread'] = df['10y'] - df['2y']
        # df['ffr_vs_2y'] = df['fed_funds_rate'] - df['2y']

        # 5. 상관관계 계산
        corr_matrix = df[['sp500_close', 'real_10y', 'spread']].corr()
        result = {
            'S&P500 vs 실질 10Y 금리': round(corr_matrix.loc['sp500_close', 'real_10y'], 3),
            'S&P500 vs 장단기 금리차': round(corr_matrix.loc['sp500_close', 'spread'], 3)
            #'S&P500 vs 기준금리 - 2Y': round(corr_matrix.loc['sp500_close', 'ffr_vs_2y'], 3)
        }
        
        print(result)

        # 6. 시각화 (선택적)
        if show_plot:
            import matplotlib.pyplot as plt
            import seaborn as sns
            plt.figure(figsize=(8, 6))
            sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', square=True)
            plt.title("S&P500과 금리 관련 지표 간 상관관계", fontsize=13)
            plt.tight_layout()
            plt.show()

        return result    

    # Clear - 월별데이터 - 1개월 지연
    def get_unemployment_rate(self):
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'UNRATE',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['unemployment_rate'] = pd.to_numeric(df['value'], errors='coerce')
    
        return df
    
    def get_ism_pmi(self):
        """
        TradingEconomics 한국어 사이트에서 ISM 제조업 PMI 지표를 추출하는 함수
        """
        url = "https://ko.tradingeconomics.com/united-states/manufacturing-pmi"

        options = Options()
        # options.add_argument('--headless')  # ← 일단 꺼두세요
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table.table"))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')
        except Exception as e:
            driver.quit()
            raise Exception("❌ 페이지 로딩 실패: table 요소를 찾을 수 없습니다.") from e
        finally:
            driver.quit()

        table = soup.find('table', class_='table table-hover')
        if not table:
            raise Exception("❌ 테이블을 찾을 수 없습니다.")

        rows = table.find('tbody').find_all('tr')
        for row in rows:
            columns = row.find_all('td')
            if len(columns) >= 5:
                name = columns[0].get_text(strip=True)
                if "ISM 제조업 PMI" in name:
                    value = columns[1].get_text(strip=True)
                    date = columns[4].get_text(strip=True)
                    return {
                        "지표명": name,
                        "값": value,
                        "발표일": date
                    }

        raise Exception("❌ 'ISM 제조업 PMI' 항목을 찾을 수 없습니다.")
    
    # Clear - 월별 데이터 - 1개월 지연
    def update_ism_pmi_data(self):
        '''
        로컬에 저장된 ism_pmi 파일 불러오기
        '''
        try:
            pmi_df = self.pmi_updater.update_csv()
            print("✅ ISM PMI data CSV 업데이트 완료")
        except Exception as e:
            print("📛 ISM PMI data 업데이트 실패:", e)
        return pmi_df

    # Clear - 월별데이터 - 2개월 지연
    def get_UMCSENT_index(self):
        '''
        미시간 소비자 심리지수
        100이상 : 낙관적 분위기
        80~100 : 양호한 심리, 건전한 소비 예상
        60~80 : 소비자 불안정, 소비 위축 가능성
        60 이하 : 경기 침체 신호 가능성(소비 급감 우려려)
        '''

        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'UMCSENT',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['umcsent_index'] = pd.to_numeric(df['value'], errors='coerce')
  
        return df 

    # 미국 선행 지수 - 월별데이터
    def get_us_leading_index_actual(self):
        """
        TradingEconomics 웹 페이지에서 미국 선행 지수의 실제값을 가져옵니다.

        Args:
            url (str): 데이터를 가져올 TradingEconomics 페이지의 URL.

        Returns:
            str: 실제값 (예: '98.80') 또는 찾을 수 없는 경우 None.
        """

        url = "https://ko.tradingeconomics.com/united-states/leading-economic-index"
    
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        extracted_data = []

        try:
            # 웹 페이지에 GET 요청 보내기
            print(f"URL에 접속 중: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status() # HTTP 오류가 발생하면 예외 발생

            # BeautifulSoup으로 HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 'ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers' ID를 가진 div를 찾습니다.
            panel_peers_div = soup.find('div', id='ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers')
            
            if panel_peers_div:
                # 해당 div 안에서 'table-responsive' 클래스를 가진 div를 찾고 그 안의 'table table-hover' 테이블을 찾습니다.
                table_responsive_div = panel_peers_div.find('div', class_='table-responsive')
                if table_responsive_div:
                    data_table = table_responsive_div.find('table', class_='table table-hover')
                    
                    if data_table:
                        # 테이블 헤더 추출
                        header_row = data_table.find('thead').find('tr')
                        if header_row:
                            headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                            # 첫 번째 빈 헤더 제거
                            if headers and headers[0] == '':
                                headers = headers[1:]
                            print(f"추출된 헤더: {headers}") # 디버깅용

                            # '마지막'과 '참고' 열의 인덱스 찾기
                            try:
                                last_index = headers.index("마지막")
                                ref_date_index = headers.index("참고")
                            except ValueError as e:
                                print(f"ERROR: 필요한 헤더('마지막' 또는 '참고')를 찾을 수 없습니다: {e}")
                                return []

                            # 데이터 행 순회: tbody 유무와 상관없이 테이블 내의 모든 <tr>을 찾고, 헤더 다음 행부터 데이터로 처리
                            all_table_rows = data_table.find_all('tr')
                            
                            # 헤더 행 다음부터 실제 데이터 행으로 간주
                            # 헤더가 <thead> 안에 있고, 데이터는 <tbody> 안에 명시될 수도 있지만,
                            # <tbody>가 없는 경우 <tr>이 <table> 바로 아래에 올 수 있음.
                            # 따라서 thead 안의 tr을 제외한 나머지 tr을 가져옵니다.
                            data_rows = [row for row in all_table_rows if row.find_parent('thead') is None]

                            if data_rows:
                                for row in data_rows:
                                    # 첫 번째 td는 지표 이름이므로 따로 처리
                                    indicator_name_tag = row.find('td', style="padding-left: 10px; text-align: left;")
                                    indicator_name = indicator_name_tag.get_text(strip=True) if indicator_name_tag else "N/A"

                                    # 지표 이름 셀을 제외한 나머지 셀에서 값을 추출합니다.
                                    data_cells_excluding_indicator_name = row.find_all('td')[1:] 
                                    processed_data_cells = [cell.get_text(strip=True) for cell in data_cells_excluding_indicator_name]

                                    last_value = None
                                    ref_date = None

                                    # 추출된 헤더의 인덱스에 따라 값을 가져옵니다.
                                    if last_index < len(processed_data_cells):
                                        last_value = processed_data_cells[last_index]
                                    if ref_date_index < len(processed_data_cells):
                                        ref_date = processed_data_cells[ref_date_index]
                                    
                                    extracted_data.append({
                                        "indicator": indicator_name,
                                        "value": last_value,
                                        "date": ref_date
                                    })
                            else:
                                print("ERROR: 테이블에서 데이터 행(<tr>)을 찾을 수 없습니다.")
                        else:
                            print("ERROR: 테이블 헤더 행(<thead><tr>)을 찾을 수 없습니다.")
                    else:
                        print("ERROR: 'table table-hover' 클래스를 가진 테이블을 찾을 수 없습니다.")
                else:
                    print("ERROR: 'table-responsive' div를 찾을 수 없습니다.")
            else:
                print("ERROR: 'ctl00_ContentPlaceHolder1_ctl00_ctl00_PanelPeers' ID를 가진 div를 찾을 수 없습니다.")

        except requests.exceptions.RequestException as e:
            print(f"웹 페이지에 접속하는 중 오류 발생: {e}")
        except Exception as e:
            print(f"데이터를 파싱하는 중 오류 발생: {e}")
        
        return extracted_data[0]
    
    # LEI 데이터 불러오기
    def update_lei_data(self):
        '''
        로컬에 저장된 lei 파일 불러오기
        '''
        try:
            lei_df = self.lei_updater.update_csv()
            print("✅ LEI CSV 업데이트 완료")
        except Exception as e:
            print("📛 LEI CSV 업데이트 실패:", e)

        return lei_df    

    def plot_sp500_with_lei_signals(
        self,
        lei_csv_path: str = "lei_data.csv",
        pmi_csv_path: str = "pmi_data.csv",
        sell_delta_pp: float = -0.5,   # 6개월 금리 변화 임계값 (매도) : ≤ -0.5%p
        buy_delta_pp: float = 0.25,     # 6개월 금리 변화 임계값 (매수) : ≥ +0.5%p
        lag_months: int = 1,           # 발표시차(전월값을 다음달 1일에 알 수 있음)
        show_components: bool = False, # True면 LEI/PMI/Fed 라인도 보조축에 함께 그림
        save_to: str | None = None     # 파일로 저장하고 싶으면 경로 지정
    ):
        """
        S&P500 월초(첫 거래일) 종가에 매수/매도 마크업을 찍는 함수
        - LEI/PMI는 CSV에서 읽고, 기준금리는 self.get_fed_funds_rate()로 호출
        - 발표시차(전월 데이터를 다음 달 1일에 확인)를 반영하여 신호를 '발표월의 월초 종가'에 표시

        Returns
        -------
        fig : matplotlib.figure.Figure
        signals : pd.DataFrame  # 신호 발생 행만 모은 요약 테이블
        """

        # 1) 데이터 로드 ----------------------------------------------------------
        # S&P500 (일별) → 월초 종가(첫 거래일)로 변환
        sp = self.get_sp500().copy()
        sp["date"] = pd.to_datetime(sp["date"])
        sp = sp.sort_values("date")
        # 월초 빈(label)으로 리샘플하면 해당 월의 첫 관측치가 들어감
        sp_month_start = (
            sp.set_index("date")
            .resample("MS")            # Month Start
            .first()
            .rename_axis("date")
            .reset_index()[["date", "sp500_close"]]
        )
        sp_month_start["ym"] = sp_month_start["date"].dt.to_period("M")

        # LEI
        lei = pd.read_csv(lei_csv_path)
        # 컬럼 유연 처리
        if "date" not in lei.columns:
            raise ValueError("lei_data.csv에는 'date' 컬럼이 필요합니다.")
        lei["date"] = pd.to_datetime(lei["date"], format="mixed")
        if "LEI" not in lei.columns:
            # 일반적으로 'value'로 들어옴
            if "value" in lei.columns:
                lei = lei.rename(columns={"value": "LEI"})
            else:
                raise ValueError("lei_data.csv에서 LEI 값을 찾을 수 없습니다. ('LEI' 또는 'value' 컬럼 필요)")
        # 월말 기준 대표값
        lei_m = (lei.set_index("date").resample("M").last().reset_index()[["date", "LEI"]])
        lei_m["ym"] = lei_m["date"].dt.to_period("M")

        # PMI
        pmi = pd.read_csv(pmi_csv_path)
        # 날짜 컬럼 유연 처리
        if "date" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["date"])
        elif "Month/Year" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["Month/Year"])
        elif "DATE" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["DATE"])
        else:
            raise ValueError("pmi_data.csv에 날짜 컬럼이 없습니다. (date / Month/Year / DATE 중 하나)")
        # 값 컬럼 유연 처리
        if "PMI" not in pmi.columns:
            if "value" in pmi.columns:
                pmi = pmi.rename(columns={"value": "PMI"})
            else:
                raise ValueError("pmi_data.csv에서 PMI 값을 찾을 수 없습니다. ('PMI' 또는 'value')")
        pmi["PMI"] = pd.to_numeric(pmi["PMI"], errors="coerce")
        pmi_m = (pmi.set_index("date").resample("M").last().reset_index()[["date", "PMI"]])
        pmi_m["ym"] = pmi_m["date"].dt.to_period("M")

        # Fed Funds (FRED API)
        fed = self.get_fed_funds_rate().copy()
        fed["date"] = pd.to_datetime(fed["date"])
        fed["fed_funds_rate"] = pd.to_numeric(fed["fed_funds_rate"], errors="coerce")
        # 월말 대표값
        fed_m = (
            fed.set_index("date")
            .resample("M")
            .last()
            .reset_index()[["date", "fed_funds_rate"]]
            .rename(columns={"fed_funds_rate": "FEDFUNDS"})
        )
        fed_m["ym"] = fed_m["date"].dt.to_period("M")

        # 2) 병합 (월 기준) -------------------------------------------------------
        df = (
            sp_month_start[["date", "ym", "sp500_close"]]
            .merge(lei_m[["ym", "LEI"]], on="ym", how="left")
            .merge(pmi_m[["ym", "PMI"]], on="ym", how="left")
            .merge(fed_m[["ym", "FEDFUNDS"]], on="ym", how="left")
            .sort_values("date")
            .reset_index(drop=True)
        )

        # 3) 금리 6개월 변화(퍼센트 포인트) + 발표시차 반영 --------------------------
        df["FEDFUNDS_6M_chg"] = df["FEDFUNDS"] - df["FEDFUNDS"].shift(6)

        # 발표시차: 전월 데이터를 다음달 1일에 알 수 있으므로 'lag_months'만큼 시프트
        df["LEI_used"] = df["LEI"].shift(lag_months)
        df["PMI_used"] = df["PMI"].shift(lag_months)
        df["FEDFUNDS_6M_chg_used"] = df["FEDFUNDS_6M_chg"].shift(lag_months)

        # 4) 신호 정의 ------------------------------------------------------------
        # sell_mask = (df["LEI_used"] < 100) & (df["PMI_used"] < 50) & (df["FEDFUNDS_6M_chg_used"] <= sell_delta_pp)
        buy_mask  = (df["LEI_used"] > 100) & (df["PMI_used"] > 50) & (df["FEDFUNDS_6M_chg_used"] >= buy_delta_pp)

        # df["sell_signal"] = sell_mask.fillna(False)
        df["buy_signal"]  = buy_mask.fillna(False)

        # 5) 플롯 -----------------------------------------------------------------
        fig, ax1 = plt.subplots(figsize=(13, 6))
        ax1.plot(df["date"], df["sp500_close"], label="S&P500 (월초 종가)", linewidth=1.6)

        # 매수/매도 마크업
        buy_pts  = df[df["buy_signal"]]
        # sell_pts = df[df["sell_signal"]]
        ax1.scatter(buy_pts["date"],  buy_pts["sp500_close"],  marker="^", s=60, color = 'red', label=f"Buy (LEI>100 & PMI>50 & 6M ≥ {buy_delta_pp:+.1f}pp)")
        # ax1.scatter(sell_pts["date"], sell_pts["sp500_close"], marker="v", s=60, color = 'navy', label=f"Sell (LEI<100 & PMI<50 & 6M ≤ {sell_delta_pp:+.1f}pp)")

        ax1.set_title("S&P500 Signals at Month Start (Prev-Month Announced Data)")
        ax1.set_ylabel("S&P500")
        ax1.legend(loc="upper left")

        # 보조축에 구성요소도 보고 싶다면
        if show_components:
            ax2 = ax1.twinx()
            ax2.plot(df["date"], df["LEI"], alpha=0.6, label="LEI")
            ax2.set_ylabel("LEI")
            # PMI는 정규화해서 같은 축에
            pmi_norm = (df["PMI"] - df["PMI"].min()) / (df["PMI"].max() - df["PMI"].min()) * 100
            ax2.plot(df["date"], pmi_norm, linestyle="--", alpha=0.6, label="PMI (norm)")
            # Fed Funds는 바깥쪽 축
            ax3 = ax1.twinx()
            ax3.spines["right"].set_position(("outward", 60))
            ax3.plot(df["date"], df["FEDFUNDS"], linestyle=":", alpha=0.7, label="Fed Funds (%)")
            # 범례 합치기
            lines, labels = [], []
            for ax in [ax1, ax2, ax3]:
                l, lab = ax.get_legend_handles_labels()
                lines += l; labels += lab
            ax1.legend(lines, labels, loc="upper left")

        fig.tight_layout()
        if save_to:
            fig.savefig(save_to, dpi=150)

        plt.show()

        # 6) 신호 테이블 반환 ------------------------------------------------------
        signals = df.loc[df["buy_signal"],
                        ["date", "sp500_close", "LEI_used", "PMI_used", "FEDFUNDS_6M_chg_used",
                        "buy_signal"]].reset_index(drop=True)
        
        # 주문일 = 실제 월초 종가가 찍힌 날짜
        signals = signals.rename(columns={"date": "주문일"})

        # 데이터 기준일 = 주문일에서 lag_months 만큼 당긴 달
        signals["데이터 기준일"] = signals["주문일"] - pd.DateOffset(months=lag_months)

        # 보기 좋게 컬럼 순서 정리
        signals = signals[["데이터 기준일", "주문일", "sp500_close",
                        "LEI_used", "PMI_used", "FEDFUNDS_6M_chg_used",
                        "buy_signal"]]
        
        signals = signals.loc[signals['buy_signal'] == True]

        return fig, signals

    def decide_today_lei_signal_min(
        self,
        lei_csv_path: str = "lei_data.csv",
        pmi_csv_path: str = "pmi_data.csv",
        buy_delta_pp: float = 0.25,
        lag_months: int = 1,
        market_tz: str = "America/New_York",  # S&P500 거래월 판단용
        today_tz: str = "Asia/Seoul",         # "오늘 날짜" 표기용
    ):
        
        """
        오늘 기준(로컬 today_tz)으로, 이번 달 주문일(미국장 월초 첫 거래일)에
        매수 신호가 있는지 요약해서 반환.

        return: dict (키 순서 유지)
        - 오늘 날짜
        - 시그널          ("매수" | "대기" | "데이터없음")
        - 주문일          (이번 달 월초 첫 거래일)
        - 데이터 기준일    (= 주문일 - lag_months개월)
        - LEI             (LEI_used)
        - PMI             (PMI_used)
        - 6개월 간 금리변동 폭 (FEDFUNDS_6M_chg_used)
        """
        import pandas as pd
        import numpy as np

        # --- 오늘 날짜(로컬 표기를 위해 today_tz 사용)
        today_local = pd.Timestamp.now(tz=today_tz).date()

        # --- S&P500: 일별 → 월초(첫 거래일)
        sp = self.get_sp500().copy()
        sp["date"] = pd.to_datetime(sp["date"])
        sp = sp.sort_values("date")
        sp_month_start = (
            sp.set_index("date").resample("MS").first().rename_axis("date").reset_index()
        )
        sp_month_start["ym"] = sp_month_start["date"].dt.to_period("M")

        # --- LEI
        lei = pd.read_csv(lei_csv_path)
        if "date" not in lei.columns:
            raise ValueError("lei_data.csv에는 'date' 컬럼이 필요합니다.")
        lei["date"] = pd.to_datetime(lei["date"], format='mixed')
        if "LEI" not in lei.columns:
            if "value" in lei.columns:
                lei = lei.rename(columns={"value": "LEI"})
            else:
                raise ValueError("lei_data.csv에서 LEI 값을 찾을 수 없습니다. ('LEI' 또는 'value')")
        lei_m = lei.set_index("date").resample("M").last().reset_index()[["date", "LEI"]]
        lei_m["ym"] = lei_m["date"].dt.to_period("M")

        # --- PMI
        pmi = pd.read_csv(pmi_csv_path)
        if "date" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["date"])
        elif "Month/Year" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["Month/Year"])
        elif "DATE" in pmi.columns:
            pmi["date"] = pd.to_datetime(pmi["DATE"])
        else:
            raise ValueError("pmi_data.csv에 날짜 컬럼이 없습니다. (date / Month/Year / DATE 중 하나)")
        if "PMI" not in pmi.columns:
            if "value" in pmi.columns:
                pmi = pmi.rename(columns={"value": "PMI"})
            else:
                raise ValueError("pmi_data.csv에서 PMI 값을 찾을 수 없습니다. ('PMI' 또는 'value')")
        pmi["PMI"] = pd.to_numeric(pmi["PMI"], errors="coerce")
        pmi_m = pmi.set_index("date").resample("M").last().reset_index()[["date", "PMI"]]
        pmi_m["ym"] = pmi_m["date"].dt.to_period("M")

        # --- Fed Funds (월말 대표값 → 6개월 변화)
        fed = self.get_fed_funds_rate().copy()
        fed["date"] = pd.to_datetime(fed["date"])
        fed["fed_funds_rate"] = pd.to_numeric(fed["fed_funds_rate"], errors="coerce")
        fed_m = (
            fed.set_index("date").resample("M").last().reset_index()[["date", "fed_funds_rate"]]
            .rename(columns={"fed_funds_rate": "FEDFUNDS"})
        )
        fed_m["ym"] = fed_m["date"].dt.to_period("M")

        # --- 병합(월 기준) & 발표시차 반영
        df = (
            sp_month_start[["date", "ym", "sp500_close"]]
            .merge(lei_m[["ym", "LEI"]], on="ym", how="left")
            .merge(pmi_m[["ym", "PMI"]], on="ym", how="left")
            .merge(fed_m[["ym", "FEDFUNDS"]], on="ym", how="left")
            .sort_values("date")
            .reset_index(drop=True)
        )

        # --- 발표 시차(매월 25일 규칙) 반영: 오늘 날짜 기준 동적 lag 계산
        now_us = pd.Timestamp.now(tz=market_tz)  # 미국장 기준 오늘
        effective_lag = 2 if now_us.day < 25 else 1


        df["FEDFUNDS_6M_chg"] = df["FEDFUNDS"] - df["FEDFUNDS"].shift(6)

        df["LEI_used"] = df["LEI"].shift(effective_lag)
        df["PMI_used"] = df["PMI"].shift(lag_months)
        df["FEDFUNDS_6M_chg_used"] = df["FEDFUNDS_6M_chg"].shift(lag_months)

        buy_mask = (
            (df["LEI_used"] > 100)
            & (df["PMI_used"] > 50)
            & (df["FEDFUNDS_6M_chg_used"] >= buy_delta_pp)
        )
        df["buy_signal"] = buy_mask.fillna(False)

        # --- 이번 달 주문일(미국장 기준 월) 결정
        now_us = pd.Timestamp.now(tz=market_tz)
        current_period_us = now_us.to_period("M")

        this_row = df[df["date"].dt.to_period("M") == current_period_us].tail(1)
        if this_row.empty:
            # 이번 달 첫 거래일 데이터가 아직 없거나 소스가 비어있는 경우
            return {
                "오늘 날짜": today_local,
                "시그널": "데이터없음",
                "주문일": None,
                "데이터 기준일": None,
                "LEI": None,
                "PMI": None,
                "6개월 간 금리변동 폭": None,
            }

        row = this_row.iloc[0]
        order_day = pd.to_datetime(row["date"]).date()
        base_day = (pd.to_datetime(row["date"]) - pd.DateOffset(months=lag_months)).date()

        # 안전한 소수/결측 처리
        def _fmt(x, nd=2):
            v = None if pd.isna(x) else float(x)
            return None if v is None else (round(v, nd) if nd is not None else v)

        result = {
            "오늘 날짜": today_local,
            "시그널": "BUY" if bool(row["buy_signal"]) else "HOLD",
            "주문일": order_day,
            "데이터 기준일": base_day,
            "LEI": _fmt(row["LEI_used"], 1),
            "PMI": _fmt(row["PMI_used"], 1),
            "Change_rate": _fmt(row["FEDFUNDS_6M_chg_used"], 2),
        }
        return result

   # Clear - 월별데이터(ECRI)
    def get_USSLIND(self):
        '''
        St. Louis Fed가 발표하는 지표를 공식적으로 FRED에 제공하는 형태
        상승시 경기회복/확장 의미, 하락시 경기 둔화/침체 의미
        '''
        
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'USSLIND',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['LI_index'] = pd.to_numeric(df['value'], errors='coerce')
        
        return df
    
    # Clear - 월별데이터
    def get_CLI(self):
        '''
        CLI가 발표하는 지표를 공식적으로 FRED에 제공하는 형태
        상승시 경기회복/확장 의미, 하락시 경기 둔화/침체 의미
        '''
        
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'USALOLITONOSTSAM',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['CLI_index'] = pd.to_numeric(df['value'], errors='coerce')
        
        return df

    def analyze_ecri_trend(self):

        df = self.get_CLI()
        x = np.arange(len(df))
        y = df['CLI_index'].values
        slope, _, r_value, _, _ = linregress(x, y)

        if slope > 0.05:
            return "📈 상승 추세 (경기 회복 기대)"
        elif slope < -0.05:
            return "📉 하락 추세 (경기 둔화 위험)"
        else:
            return "➖ 횡보 추세 (불확실성 지속)"

    
    def generate_rate_cut_signals(self):
        """
        기준금리 인하 시점부터 6개월 이내에 CLI < 130 그리고 PMI < 50인 경우 매도 시그널 표시

        Returns:
            signal_df: 매도 시그널 포함된 DataFrame (date, sp500_close, cli, pmi, rate_cut, signal)
        """
        # 1. 데이터 불러오기
        sp500_df = self.get_sp500()
        fed_df = self.generate_fed_rate_turning_points()  # 전환점만 True
        cli_df = self.get_CLI()
        pmi_df = ISMPMIUpdater().preprocess_raw_csv()

        # 2. 날짜 정제
        sp500_df["date"] = pd.to_datetime(sp500_df["date"])
        sp500_df['month'] = pd.to_datetime(sp500_df['date']).dt.to_period('M').dt.to_timestamp()

        # 각 월의 첫 번째 날짜에 해당하는 S&P500 값만 추출
        sp_monthly_first = sp500_df.sort_values('date').groupby('month').first().reset_index()

        # ✅ 기존 'date' 컬럼 제거 (중복 방지)
        sp_monthly_first = sp_monthly_first.drop(columns=['date'])
        
        # ✅ 날짜를 해당 월의 1일로 바꿔줌
        sp_monthly_first = sp_monthly_first.rename(columns={'month': 'date'})
        sp_monthly_first = sp_monthly_first[["date", "sp500_close"]]


        fed_df["date"] = pd.to_datetime(fed_df["date"])
        cli_df["date"] = pd.to_datetime(cli_df["date"])
        pmi_df.rename(columns={"Month/Year": "date"}, inplace=True)
        pmi_df["date"] = pd.to_datetime(pmi_df["date"])

        # 3. 모든 데이터 병합 (outer merge → date 기준)
        df = sp_monthly_first.merge(cli_df, on="date", how="outer")
        df = df.merge(pmi_df, on="date", how="outer")
        df = df.merge(fed_df[["date", "rate_cut"]], on="date", how="left")

        df = df.sort_values("date").reset_index(drop=True)

        # 4. 매도 시그널 초기화
        df["signal"] = False

        # 5. 기준금리 인하 시점부터 6개월 동안 조건 체크
        cut_dates = df[df["rate_cut"] == True]["date"].tolist()

        for cut_date in cut_dates:
            end_date = cut_date + pd.DateOffset(months=6)
            mask = (df["date"] > cut_date) & (df["date"] <= end_date)
            condition = (df["CLI_index"] < 130) & (df["PMI"] < 50)
            df.loc[mask & condition, "signal"] = True

        return df

    # Clear
    def plot_sp500_with_sell_signals(self, save_to = None):

        signal_df = self.generate_rate_cut_signals()
        df = signal_df.copy()
        fig = plt.figure(figsize=(14, 6))
        plt.plot(df["date"], df["sp500_close"], label="S&P500", color="black")

        # 매도 시그널 시각화
        sell_signals = df[df["signal"] == True]
        plt.scatter(sell_signals["date"], sell_signals["sp500_close"],
                    color="red", label="Sell Signal", zorder=5)

        plt.title("S&P500 with Sell Signals (CLI < 130 and PMI < 50 within 6 months of rate cut)")
        plt.xlabel("Date")
        plt.ylabel("S&P500")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        if save_to:
            fig.savefig(save_to, format='png')
            plt.close(fig)
        else:
            plt.show()

    # Clear
    def generate_buy_signals_from_hike(self):

        """
        기준금리 인상 시작 시점 이후 6개월 이내에
        CLII > 130 AND PMI > 50 인 경우 매수 시그널 생성

        Returns:
            buy_df: ['date', 'cli', 'pmi', 'sp500_close', 'rate_hike', 'buy_signal']
        """
        # 데이터 불러오기
        fed_df = self.generate_fed_rate_turning_points()  # includes 'rate_hike'
        cli_df = self.get_CLI()
        pmi_df = self.update_ism_pmi_data()
        pmi_df.rename(columns={"Month/Year": "date", "PMI": "pmi"}, inplace=True)
        sp_df = self.get_sp500()

        # ✅ 각 달의 첫 거래일만 추출
        sp_df['year_month'] = sp_df['date'].dt.to_period('M')
        sp_monthly_first = sp_df.sort_values('date').groupby('year_month').first().reset_index()
        
        # ✅ 날짜를 해당 월의 1일로 바꿔줌
        sp_monthly_first["date"] = sp_monthly_first["year_month"].dt.to_timestamp()
        sp_monthly_first = sp_monthly_first[["date", "sp500_close"]]


        # 병합
        df = fed_df.merge(cli_df, on="date", how="outer")
        df = df.merge(pmi_df, on="date", how="outer")
        df = df.merge(sp_monthly_first, on="date", how="outer")
        df = df.sort_values("date").reset_index(drop=True)

        # 1. rate_hike 발생 시점 목록
        hike_dates = df[df["rate_hike"] == True]["date"].tolist()

        # 2. 각 기준금리 인상 시작 이후 6개월 동안 조건 충족 여부 확인
        df["buy_signal"] = False

        for hike_date in hike_dates:
            window_end = hike_date + pd.DateOffset(months=6)
            window_mask = (df["date"] > hike_date) & (df["date"] <= window_end)
            condition = (df["CLI_index"] > 130) & (df["pmi"] > 50)
            df.loc[window_mask & condition, "buy_signal"] = True

        return df[["date", "fed_funds_rate", "rate_hike", "CLI_index", "pmi", "sp500_close", "buy_signal"]]

    # Clear
    def plot_buy_signals_from_hike(self, save_to = None):
        """
        generate_buy_signals_from_hike() 결과를 바탕으로
        S&P500 지수 그래프 위에 매수 시그널 시점을 표시하는 시각화 함수
        """
        df = self.generate_buy_signals_from_hike()

        fig = plt.figure(figsize=(14, 6))
        plt.plot(df["date"], df["sp500_close"], label="S&P500", color="blue")

        # 매수 시그널 표시
        buy_signals = df[df["buy_signal"] == True]
        plt.scatter(buy_signals["date"], buy_signals["sp500_close"], color="green", label="Buy Signal", marker="^", s=100)

        plt.title("Buy Signals After Fed Rate Hike Start (CLI > 130 & PMI > 50)")
        plt.xlabel("Date")
        plt.ylabel("S&P500 Index")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        if save_to:
            fig.savefig(save_to, format='png')
            plt.close(fig)
        else:
            plt.show()


    def find_signals_from_erci_indicators(self):
        """
        실업률과 ERCI(USSLIND) 지표 발표 지연을 고려하여 조건 충족 시점을 찾는 함수

        매수 조건: 실업률 > 평균, ECRI < 95
        매도 조건: 실업률 < 평균, ECRI >= 110

        Returns:
            signal_df : 매수/매도 시점과 조건 정보를 포함한 DataFrame
        """
        from pandas.tseries.offsets import MonthBegin
        import pandas as pd

        # 데이터 불러오기
        ecri_df = self.get_USSLIND()  # 'LI_index' 또는 'value', 'date' 포함
        unemp_df = self.get_unemployment_rate()  # 'unemployment_rate' 또는 'value', 'date' 포함

        # date 컬럼이 있으면 인덱스로 지정 + datetime 변환
        if "date" in ecri_df.columns:
            ecri_df["date"] = pd.to_datetime(ecri_df["date"])
            ecri_df = ecri_df.set_index("date")

        if "date" in unemp_df.columns:
            unemp_df["date"] = pd.to_datetime(unemp_df["date"])
            unemp_df = unemp_df.set_index("date")

        # 필요한 컬럼 선택 및 이름 지정
        ecri_series = ecri_df["LI_index"] if "LI_index" in ecri_df.columns else ecri_df["value"]
        ecri_series.name = "ECRI"

        unemp_series = unemp_df["unemployment_rate"] if "unemployment_rate" in unemp_df.columns else unemp_df["value"]
        unemp_series.name = "Unemployment"

        # 1개월 발표 지연 적용
        ecri_shifted = ecri_series.shift(1)
        ecri_shifted.index = ecri_shifted.index + MonthBegin(1)

        unemp_shifted = unemp_series.shift(1)
        unemp_shifted.index = unemp_shifted.index + MonthBegin(1)


        # 병합 후 조건 적용
        cond_df = pd.concat([ecri_shifted, unemp_shifted], axis=1).dropna()
        print("📆 병합 cond_df 마지막 날짜:", cond_df.index.max())

        unemp_mean = cond_df["Unemployment"].mean()
        print("실업률 평균:", cond_df["Unemployment"].mean())

        buy_signals = cond_df[(cond_df["Unemployment"] > unemp_mean) & (cond_df["ECRI"] < 0.95)].copy()
        buy_signals["signal"] = "buy"

        sell_signals = cond_df[(cond_df["Unemployment"] < unemp_mean) & (cond_df["ECRI"] >= 1.10)].copy()
        sell_signals["signal"] = "sell"

        signal_df = pd.concat([buy_signals, sell_signals]).sort_index()
        return signal_df
    
    def plot_sp500_with_ERCI_signals(self):
        import matplotlib.pyplot as plt
        import seaborn as sns
        sns.set_style("whitegrid")

        sp500 = self.get_sp500().copy()
        # "date" 컬럼이 존재한다면, 이걸 datetime으로 변환 후 인덱스로 설정
        sp500["date"] = pd.to_datetime(sp500["date"])
        sp500 = sp500.set_index("date")
        sp500 = sp500.sort_index()

        # 시그널 데이터 정렬
        signal_df = self.find_signals_from_erci_indicators()
        signal_df = signal_df.sort_index()

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(sp500.index, sp500["sp500_close"], label="S&P500", color="black")

        # 각 시그널 날짜에 가까운 S&P500 종가 위에 마커 표시
        for date, row in signal_df.iterrows():
            # 해당 날짜 이후의 첫 S&P500 종가 찾기
            nearest = sp500[sp500.index >= date]
            if not nearest.empty:
                y = nearest.iloc[0]["sp500_close"]
                if row["signal"] == "buy":
                    ax.scatter(date, y, color="green", marker="^", s=100, label="Buy" if "Buy" not in ax.get_legend_handles_labels()[1] else "")
                elif row["signal"] == "sell":
                    ax.scatter(date, y, color="red", marker="v", s=100, label="Sell" if "Sell" not in ax.get_legend_handles_labels()[1] else "")

        ax.set_title("S&P500 with Buy/Sell Signals (Monthly signal date)", fontsize=14)
        ax.set_ylabel("S&P500 Index")
        ax.legend()
        plt.tight_layout()
        plt.show()



    def update_snp_forwardpe_data(self):
        '''
        로컬에 저장된 S&P500 forward pe 파일 불러오기
        '''
        try:
            snp_fp_df = self.snp_forwardpe_updater.update_forward_pe_csv()
            print("✅ S&P500 Forward PE CSV 업데이트 완료")
        except Exception as e:
            print("📛 S&P500 Forward PE 업데이트 실패:", e)

        return snp_fp_df    


    def get_forward_pe(self):
            url = 'https://en.macromicro.me/series/20052/sp500-forward-pe-ratio'

            options = Options()
            # options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
 

            driver = webdriver.Chrome(options=options)
            driver.get(url)


            try:
                # ✅ 해당 요소가 로드될 때까지 대기 (최대 10초)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sidebar-sec.chart-stat-lastrows span.val"))
                )
            except:
                driver.quit()
                raise RuntimeError("📛 페이지 로딩 중 Forward PE 데이터를 찾지 못했습니다.")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()

            latest_val = soup.select_one("div.sidebar-sec.chart-stat-lastrows span.val")
            date = soup.select_one("div.sidebar-sec.chart-stat-lastrows .date-label")

            if latest_val and date:
                date_text = date.text.strip()
                pe_val = float(latest_val.text.strip())
                df = pd.DataFrame([{"date": date_text, "forward_pe": pe_val}])
                return {
                    "date": date_text,
                    "forward_pe": pe_val
                }
            else:
                raise ValueError("📛 Forward PE 값을 찾을 수 없습니다.")
            

    def get_ttm_pe(self):
        url = "https://www.multpl.com/s-p-500-pe-ratio"

        # options = Options()
        # options.add_argument("--headless")
        # options.add_argument("--disable-gpu")
        # options.add_argument("--no-sandbox")

        # driver = webdriver.Chrome(options=options)
        # driver.get(url)
        # time.sleep(5)  # JS 로딩 대기

        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # 날짜 추출
        timestamp_tag = soup.select_one("#timestamp")
        date = timestamp_tag.get_text(strip=True)

        # PE 값 추출
        current_div = soup.select_one("#current")
        
        # <div id="current"> 내에서 <b> 태그 다음에 나오는 텍스트 노드가 우리가 원하는 숫자
        b_tag = current_div.find("b")
        ttm_pe = b_tag.next_sibling.strip()


        return {
            "date": date,
            "ttm_pe": ttm_pe
        }   

        # soup = BeautifulSoup(driver.page_source, "html.parser")
        # driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        # for td in soup.select("td.col-6"):
        #     if "Last Value" in td.get_text(strip=True):
        #         value_td = td.find_next_sibling("td")
        #         if value_td:
        #             return {
        #                 'date : '
        #             }# value_td.get_text(strip=True)

        return None

    def analyze_pe(self,
                fwd_buy_lt: float = 12.0,
                fwd_sell_gt: float = 22.0,
                ttm_sell_gt: float = 25.0):
        """
        Returns dict for Streamlit:
        - date, ttm_pe, forward_pe (소숫점 2자리 반올림)
        - absolute(Forward 기준), absolute_forward, absolute_ttm
        - forward_vs_ttm
        - signal: 'BUY' | 'SELL' | 'HOLD' | 'N/A'
        - signal_reason: 트리거 사유 요약
        - signal_md: st.markdown()/st.write()로 바로 쓸 수 있는 설명 블럭
        - message: 전체 요약 텍스트
        """

        # --- 데이터 취득 ---
        ttm_pe_raw = self.get_ttm_pe().get("ttm_pe", "")
        try:
            ttm_pe = float(str(ttm_pe_raw).replace(",", "").strip())
        except Exception:
            ttm_pe = np.nan

        fwd_df = pd.read_csv("forward_pe_data.csv")
        fwd_df["forward_pe"] = pd.to_numeric(fwd_df["forward_pe"], errors="coerce")
        forward_pe = fwd_df["forward_pe"].dropna().iloc[-1] if not fwd_df["forward_pe"].dropna().empty else np.nan

        # --- 절대평가 ---
        if pd.notna(forward_pe):
            if forward_pe > fwd_sell_gt:
                absolute_forward = "고평가"
            elif forward_pe < fwd_buy_lt:
                absolute_forward = "저평가"
            else:
                absolute_forward = "평균"
        else:
            absolute_forward = "N/A"

        if pd.notna(ttm_pe):
            if ttm_pe > ttm_sell_gt:
                absolute_ttm = "고평가"
            elif ttm_pe < 13:
                absolute_ttm = "저평가"
            else:
                absolute_ttm = "평균"
        else:
            absolute_ttm = "N/A"

        if pd.notna(ttm_pe) and pd.notna(forward_pe):
            if ttm_pe > forward_pe:
                forward_vs_ttm = "향후 실적 개선 기대(낙관적)"
            elif ttm_pe < forward_pe:
                forward_vs_ttm = "실적 둔화 반영(보수적)"
            else:
                forward_vs_ttm = "현재 수준 유지 예상"
        else:
            forward_vs_ttm = "N/A"

        # --- 시그널 로직 ---
        # 기본 규칙:
        # - BUY: Forward P/E < fwd_buy_lt
        # - SELL: Forward P/E > fwd_sell_gt OR TTM P/E > ttm_sell_gt
        # - 그 외: HOLD
        triggers = []
        if pd.notna(forward_pe) and forward_pe < fwd_buy_lt:
            signal = "BUY"
            triggers.append(f"Forward P/E < {fwd_buy_lt:.2f}")
        elif (pd.notna(forward_pe) and forward_pe > fwd_sell_gt) or (pd.notna(ttm_pe) and ttm_pe > ttm_sell_gt):
            signal = "SELL"
            if pd.notna(forward_pe) and forward_pe > fwd_sell_gt:
                triggers.append(f"Forward P/E > {fwd_sell_gt:.2f}")
            if pd.notna(ttm_pe) and ttm_pe > ttm_sell_gt:
                triggers.append(f"TTM P/E > {ttm_sell_gt:.2f}")
        elif pd.notna(forward_pe) or pd.notna(ttm_pe):
            signal = "HOLD"
            triggers.append("임계치 범위 내")
        else:
            signal = "N/A"
            triggers.append("유효한 P/E 데이터 없음")

        signal_reason = " & ".join(triggers)

        # --- 날짜/출력 포맷 ---
        today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()

        # 두 자리 반올림 값
        ttm_pe_2 = float(f"{ttm_pe:.2f}") if pd.notna(ttm_pe) else np.nan
        forward_pe_2 = float(f"{forward_pe:.2f}") if pd.notna(forward_pe) else np.nan

        # 요약 메시지
        message = (
            f"📅 기준일: {today_kst}\n\n"
            f"📊 S&P 500 Forward PER: {forward_pe_2:.2f}\n"
            f"📊 S&P 500 TTM PER: {ttm_pe_2:.2f}\n\n"
            f"🧭 절대평가(Forward 기준): {absolute_forward}\n"
            f"🧭 절대평가(TTM 기준): {absolute_ttm}\n"
            f"🔎 Forward vs TTM: {forward_vs_ttm}\n\n"
            f"🚦 Signal: {signal}  ({signal_reason})"
        )

        # Streamlit 표기용 설명 블럭 (Markdown)
        signal_md = (
            "### 🚦 PER 기반 자동 시그널\n"
            f"- **규칙**  \n"
            f"  - 매수(BUY): Forward P/E **< {fwd_buy_lt:.2f}**  \n"
            f"  - 매도(SELL): Forward P/E **> {fwd_sell_gt:.2f}** 또는 TTM P/E **> {ttm_sell_gt:.2f}**  \n"
            f"  - 그 외: **HOLD**  \n\n"
            f"- **현재 수치**  \n"
            f"  - Forward P/E: **{forward_pe_2:.2f}**  \n"
            f"  - TTM P/E: **{ttm_pe_2:.2f}**  \n\n"
            f"- **판단 결과**  \n"
            f"  - **Signal: {signal}**  \n"
            f"  - 트리거: {signal_reason}  \n"
        )

        return {
            "date": today_kst,
            "ttm_pe": ttm_pe_2,
            "forward_pe": forward_pe_2,
            "absolute": absolute_forward,
            "absolute_forward": absolute_forward,
            "absolute_ttm": absolute_ttm,
            "forward_vs_ttm": forward_vs_ttm,
            "signal": signal,
            "signal_reason": signal_reason,
            "signal_md": signal_md,
            "message": message,
        }

    # def analyze_pe(self):

    #     ttm_pe_result = self.get_ttm_pe()
    #     ttm_pe = ttm_pe_result["ttm_pe"]  # 문자열

    #     forward_pe_result = pd.read_csv("forward_pe_data.csv")
    #     forward_pe = forward_pe_result["forward_pe"].iloc[-1]

    #     # ✅ 문자열일 수 있는 ttm_pe를 float로 변환
    #     ttm_pe = float(ttm_pe) #.replace(",", "").strip()
    #     forward_pe = float(forward_pe)

    #     message = f"📊 S&P 500 Forward PER: {forward_pe:.2f}\n"
    #     message += f"📊 S&P 500 TTM PER: {ttm_pe:.2f}\n\n"

    #     # 절대적 고평가/저평가 판단
    #     if forward_pe > 21:
    #         message += "⚠️ Forward PER 기준으로 **고평가** 구간입니다.\n"
    #     elif forward_pe < 17:
    #         message += "✅ Forward PER 기준으로 **저평가** 구간입니다.\n"
    #     else:
    #         message += "⚖️ Forward PER 기준으로 **평균 범위**입니다.\n"

    #     # TTM 기준 고평가/저평가 판단
    #     if ttm_pe > 20:
    #         message += "⚠️ TTM PER 기준으로 **역사적 고평가** 구간입니다.\n"
    #     elif ttm_pe < 13:
    #         message += "✅ TTM PER 기준으로 **저평가** 구간입니다.\n"
    #     else:
    #         message += "⚖️ TTM PER 기준으로 **평균 수준**입니다.\n"

    #     # TTM 대비 Forward 비교
    #     if ttm_pe > forward_pe:
    #         message += "🟢 시장은 **향후 실적 개선**을 기대하는 낙관적인 흐름입니다."
    #     elif ttm_pe < forward_pe:
    #         message += "🔴 시장은 **실적 둔화**를 반영하는 보수적인 흐름입니다."
    #     else:
    #         message += "⚪ 시장은 현재 실적 수준을 그대로 유지할 것으로 보고 있습니다."

    #     return message
    
    def get_vix_index(self):
        '''
        VIX : VIX는 S&P 500 지수의 옵션 가격에 기초하며, 향후 30일간 지수의 풋옵션1과 콜옵션2 가중 가격을 결합하여 산정
        향후 S&P 500지수가 얼마나 변동할 것으로 투자자들이 생각하는지를 반영
        '''
        df = yf.download('^VIX', start="2000-01-01", interval="1d")
        if df.empty:
            print("❌ VIX 데이터를 불러오지 못했습니다.")
            return pd.DataFrame()

        # 데이터프레임의 멀티레벨 컬럼을 단일 레벨로 평탄화
        df.columns = ['_'.join(col) if isinstance(col, tuple) else col for col in df.columns]
        
        df = df.reset_index()
        
        # 필요한 'Date'와 'Close_^VIX' 컬럼만 선택하고 이름을 변경합니다.
        df = df[['Date', 'Close_^VIX']].rename(columns={'Date': 'date', 'Close_^VIX': 'vix_index'})
        
        df['date'] = pd.to_datetime(df['date'])

        return df
    
    def analyze_vix(self):
        df_vix = self.get_vix_index()
        df_vix = df_vix.sort_values('date')
        latest = df_vix.iloc[-1]

        date = latest['date']
        vix = float(latest['vix'])  # ← 여기서 float 변환

        result = [f"📅 기준일: {date}",
                f"📊 VIX 지수 (S&P 500 변동성): {vix:.2f}"]

        if vix < 12:
            result.append("📉 과도한 낙관 상태 → 저변동성 환경 (고점 경계 가능성)")
        elif vix < 20:
            result.append("🟢 시장이 안정적인 상태 (낙관적 심리)")
        elif vix < 30:
            result.append("⚠️ 시장 불확실성 증가 → 투자자 주의 필요")
        elif vix <40:
            result.append("🟠 시장 위험 상태 → 과매도/저점 반등 가능성 (역발상 매수 고려 구간)")
        else:
            result.append("🔴 시장 극단적 불안 상태 → 과매도/저점 반등 가능성 (역발상 매수 고려 구간) ")

        return "\n".join(result)
    
    # M2/PER(Forward) 데이터 베이스 구할 수 있나?    

    def get_equity_put_call_ratio(self):
        url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    equity_value = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if equity_value and date:
            return {
                "date": date,
                "equity_value": equity_value
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")


    def get_index_put_call_ratio(self):
        url = 'https://ycharts.com/indicators/cboe_index_put_call_ratio'

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    index_value = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if index_value and date:
            return {
                "date": date,
                "equity_value": index_value
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")

    def update_putcall_ratio(self):
        '''
        로컬에 저장된 PUT CALL RATIO 파일 불러오기
        '''
        putcall_df = None  # ✅ 안전한 초깃값

        try:
            putcall_df = self.put_call_ratio_updater.update_csv()
            print("✅ PutCall Ratio CSV 업데이트 완료")
        except Exception as e:
            print("📛 PutCall Ratio 업데이트 실패:", e)

        return putcall_df  
    
    def plot_sp500_with_pcr_signals(self, save_to: str | None = None):
        """
        Put/Call Ratio (equity_value) 기준으로 S&P500 종가 위에 매수/매도 신호를 표기.
        동시에 신호 테이블(DataFrame)을 반환합니다.

        Parameters
        ----------
        pcr_csv : str
            'date, equity_value, index_value' 컬럼을 갖는 CSV 경로
        buy_thr : float
            매수 임계값 (equity_value > buy_thr)
        sell_thr : float
            매도 임계값 (equity_value < sell_thr)
        save_to : str | None
            그래프 저장 경로. None이면 저장하지 않음.

        Returns
        -------
        fig : matplotlib.figure.Figure
        signals_df : pandas.DataFrame  # ['date','sp500_close','equity_value','signal']
        """

        buy_thr = 1.5
        sell_thr = 0.4

        # ---------- 1) S&P500 일별 라인 구성 ----------
        sp_daily = self.get_sp500().copy()  # 반드시 일별 데이터 반환
        sp_daily["date"] = pd.to_datetime(sp_daily["date"])

        # 컬럼 표준화
        if "close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"close": "sp500_close"})
        elif "Close" in sp_daily.columns:
            sp_daily = sp_daily.rename(columns={"Close": "sp500_close"})
        # 이미 'sp500_close'면 그대로 사용

        sp_line = (
            sp_daily[["date", "sp500_close"]]
            .dropna()
            .drop_duplicates(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )

        # ---------- 2) PCR 로드 (형식 고정) ----------
        pcr = pd.read_csv('put_call_ratio.csv')
        expected_cols = {"date", "equity_value", "index_value"}
        if set(pcr.columns) != expected_cols:
            raise ValueError(
                f"PCR 컬럼은 정확히 {expected_cols} 이어야 합니다. 현재: {list(pcr.columns)}"
            )

        pcr["date"] = pd.to_datetime(pcr["date"])
        # 숫자형 보정
        pcr["equity_value"] = pd.to_numeric(pcr["equity_value"], errors="coerce")

        # ---------- 3) 병합 & 신호 계산 ----------
        df = sp_line.merge(pcr[["date", "equity_value"]], on="date", how="left")

        buy_mask = df["equity_value"] > buy_thr
        sell_mask = df["equity_value"] < sell_thr

        signals_df = df.loc[buy_mask | sell_mask, ["date", "sp500_close", "equity_value"]].copy()
        signals_df["signal"] = np.where(signals_df["equity_value"] > 1.5, "BUY", "SELL")
        signals_df = signals_df.sort_values("date").reset_index(drop=True)

        # ---------- 4) 시각화 ----------
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df["date"], df["sp500_close"], label="S&P 500")
        ax.scatter(df.loc[buy_mask, "date"], df.loc[buy_mask, "sp500_close"],
                   marker="^", s=64, label=f"BUY (PCR>{buy_thr})")
        ax.scatter(df.loc[sell_mask, "date"], df.loc[sell_mask, "sp500_close"],
                   marker="v", s=64, label=f"SELL (PCR<{sell_thr})")

        ax.set_title("S&P 500 with Put/Call Ratio (Equity) Signals")
        ax.set_xlabel("Date")
        ax.set_ylabel("S&P 500 Close")
        ax.legend()
        ax.grid(True)
        fig.tight_layout()

        if save_to:
            fig.savefig(save_to, dpi=160)

        return fig, signals_df

    def decide_equity_pcr_today(self):
        """
        put_call_ratio.csv의 가장 최신 관측치를 사용해
        오늘(최근일) 매수/매도/HOLD 시그널을 결정하여 DataFrame으로 반환.

        Returns
        -------
        pandas.DataFrame
            columns = ['date', 'equity_value', 'signal'] (1행)
        """
        
        
        buy_thr: float = 1.5
        sell_thr: float = 0.4

        df = pd.read_csv("put_call_ratio.csv")
        required = {"date", "equity_value", "index_value"}
        if not required.issubset(df.columns):
            raise ValueError(f"put_call_ratio.csv must contain columns: {required}. Got: {list(df.columns)}")

        # 정리
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["equity_value"] = pd.to_numeric(df["equity_value"], errors="coerce")
        df = df.dropna(subset=["date", "equity_value"]).sort_values("date").reset_index(drop=True)

        if df.empty:
            # 비어있으면 빈 DF 반환
            return pd.DataFrame(columns=["date", "equity_value", "signal"])

        last = df.iloc[-1]
        val = float(last["equity_value"])

        if val > buy_thr:
            signal = "BUY"
        elif val < sell_thr:
            signal = "SELL"
        else:
            signal = "HOLD"

        out = pd.DataFrame(
            {
                "date": [last["date"].normalize()],   # 날짜만 보기 좋게
                "equity_value": [round(val, 2)],
                "signal": [signal],
            }
        )
        return out

    def check_put_call_ratio_warning(self):
        """
        풋콜 레이티오 데이터를 받아와서서
        매수 혹은 매도 시점을 출력하는 함수

        ratio_type : equity, index 둘 중 하나 입력
        """

        put_call_ratio = pd.read_csv('put_call_ratio.csv')
        putcall_data_today = put_call_ratio.iloc[-1]
        print("data : ", putcall_data_today)
        date = putcall_data_today['date']
        value = putcall_data_today['equity_value']

        # 간단한 시그널 판단

        result = [f"📅 기준일: {date}",
                f"📊 Equity_putcall_ratio 지수 : {value:.2f}"]
    
        if value > 1.5:
            result.append("📉 Equity: 공포심 과다 → 반등 가능성 (매수 시점 탐색)")
        elif value < 0.4:
            result.append("🚨 Equity: 과열 탐욕 상태 → 매도 경고 또는 조정 가능성")
        else:
            result.append("⚖️ Equity: 중립 구간")

        return "\n".join(result)

    def get_nfci(self):
        '''
        FED가 발표하는 지표를 공식적으로 FRED에 제공하는 형태
        상승시 경기회복/확장 의미, 하락시 경기 둔화/침체 의미
        '''
        
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'NFCI',
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['NFCI_index'] = pd.to_numeric(df['value'], errors='coerce')
        
        return df

    def analyze_nfci(self):
        '''
        nfci < -0.5 금융여건 완화
        nfci > 0.5 금융긴축
        '''
        df = self.get_nfci()

        date = df['date'].iloc[-1]
        nfci_value = df['NFCI_index'].iloc[-1] 

        result = []

        if nfci_value < -0.5:
            result.append("✅ 유동성 풍부 구간으로 꾸준한 상승 경향")
        elif nfci_value > 0.5:
            result.append("🚨 극단적 긴축 구간, 손실 및 높은 변동성")
        else:
            result.append("⚖️ 중립 구간")

        return {
            "date" : date,
            "value" : nfci_value,
            "comment" : result
        }


    def get_dollar_index(self):   #period="26y"
        '''
        FRED API : 달러 인덱스
        '''

        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id' : 'DTWEXBGS', # 달러인덱스
            'api_key' : self.fred_api_key,
            'file_type' : 'json',
            'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        }

        try:
            response = requests.get(url, params= params, timeout=10)
            response.raise_for_status() # HTTP 에러 발생 시 예외 처리
            data = response.json()

            if 'observations' not in data:
                raise ValueError(F"'observations' 키가 없음 : {data}")

            # 데이터프레임 변환
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

            return df
        
        except Exception as e:
            print(f"[ERROR] FRED API 호출 실패 : {e}")
            return pd.DataFrame()
      
        # """
        # 달러 인덱스 (DXY) 데이터를 yfinance에서 가져와서 DataFrame으로 반환
        # period: '1d', '5d', '1mo', '3mo', '6mo', '1y', etc.
        # """
        # ticker = "DX-Y.NYB"  # yfinance 상 DXY 심볼 (ICE 선물시장용)
        # df = yf.download(ticker, start='2020-01-01', interval="1d", progress=False)
        # df = df.reset_index()

        # # 컬럼 정리 : 컬럼 이름을 표준화
        # df = df[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'dxy'})
        # df['date'] = pd.to_datetime(df['date'])
        # return df
    
    # Clear - 실시간 데이터
    def get_euro_index(self):
        '''
        FRED API : 유로 인덱스
        '''

        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id' : 'DEXUSEU', # 10년물 국채 금리
            'api_key' : self.fred_api_key,
            'file_type' : 'json',
            'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        }

        try:
            response = requests.get(url, params= params, timeout=10)
            response.raise_for_status() # HTTP 에러 발생 시 예외 처리
            data = response.json()

            if 'observations' not in data:
                raise ValueError(F"'observations' 키가 없음 : {data}")

            # 데이터프레임 변환
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

            return df
        
        except Exception as e:
            print(f"[ERROR] FRED API 호출 실패 : {e}")
            return pd.DataFrame()
        
    # Clear - 실시간 데이터
    def get_yen_index(self):
        '''
        FRED API : 엔화 인덱스
        '''

        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id' : 'DEXJPUS', # 10년물 국채 금리
            'api_key' : self.fred_api_key,
            'file_type' : 'json',
            'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        }

        try:
            response = requests.get(url, params= params, timeout=10)
            response.raise_for_status() # HTTP 에러 발생 시 예외 처리
            data = response.json()

            if 'observations' not in data:
                raise ValueError(F"'observations' 키가 없음 : {data}")

            # 데이터프레임 변환
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

            return df
        
        except Exception as e:
            print(f"[ERROR] FRED API 호출 실패 : {e}")
            return pd.DataFrame()
    

    # Clear - 월별 데이터 - 1월 딜레이
    def get_copper_price_F(self):
        # HG=F: High Grade Copper Futures (구리 선물)
        df = yf.download("HG=F", start="2000-01-01", interval="1d", group_by="ticker")

        # 1) MultiIndex → 단일 인덱스로 변환
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)  # 'CL=F' 레벨 제거 → Price, Close, High...
            # 또는 df.columns = df.columns.droplevel(0) 하면 'Close', 'High' 등만 남김
            # 원하는 레벨 선택

        # 2) 인덱스(Date)를 컬럼으로
        df = df.reset_index()
        
        return df



        # '''
        # FRED API : 구리 인덱스
        # '''

        # url = 'https://api.stlouisfed.org/fred/series/observations'
        # params = {
        #     'series_id' : 'PCOPPUSDM', # 10년물 국채 금리
        #     'api_key' : self.fred_api_key,
        #     'file_type' : 'json',
        #     'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        # }

        # try:
        #     response = requests.get(url, params= params, timeout=10)
        #     response.raise_for_status() # HTTP 에러 발생 시 예외 처리
        #     data = response.json()

        #     if 'observations' not in data:
        #         raise ValueError(F"'observations' 키가 없음 : {data}")

        #     # 데이터프레임 변환
        #     df = pd.DataFrame(data['observations'])
        #     df['date'] = pd.to_datetime(df['date'])
        #     df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

        #     return df
        
        # except Exception as e:
        #     print(f"[ERROR] FRED API 호출 실패 : {e}")
        #     return pd.DataFrame()
    

    def get_gold_price_F(self):
        '''
        FRED API : 금 인덱스
        '''

        df = yf.download("GC=F", start="2000-01-01", interval="1d", group_by="ticker")

        # 1) MultiIndex → 단일 인덱스로 변환
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)  # 'CL=F' 레벨 제거 → Price, Close, High...
            # 또는 df.columns = df.columns.droplevel(0) 하면 'Close', 'High' 등만 남김
            # 원하는 레벨 선택

        # 2) 인덱스(Date)를 컬럼으로
        df = df.reset_index()
        
        return df


        # url = 'https://api.stlouisfed.org/fred/series/observations'
        # params = {
        #     'series_id' : 'IR14270', # 뉴욕 기준 금가격
        #     'api_key' : self.fred_api_key,
        #     'file_type' : 'json',
        #     'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
        # }

        # try:
        #     response = requests.get(url, params= params, timeout=10)
        #     response.raise_for_status() # HTTP 에러 발생 시 예외 처리
        #     data = response.json()

        #     if 'observations' not in data:
        #         raise ValueError(F"'observations' 키가 없음 : {data}")

        #     # 데이터프레임 변환
        #     df = pd.DataFrame(data['observations'])
        #     df['date'] = pd.to_datetime(df['date'])
        #     df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

        #     return df
        
        # except Exception as e:
        #     print(f"[ERROR] FRED API 호출 실패 : {e}")
        #     return pd.DataFrame()


    def get_oil_price_F(self):
        '''
        FRED API : 미국 서부텍사스산 원유 선물
        '''

        df = yf.download("CL=F", start="2000-01-01", interval="1d", group_by="ticker")

        # 1) MultiIndex → 단일 인덱스로 변환
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(0)  # 'CL=F' 레벨 제거 → Price, Close, High...
            # 또는 df.columns = df.columns.droplevel(0) 하면 'Close', 'High' 등만 남김
            # 원하는 레벨 선택

        # 2) 인덱스(Date)를 컬럼으로
        df = df.reset_index()
        
        return df

    def get_high_yield_spread(self):
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'BAMLH0A0HYM2',  # 하이일드 스프레드
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
        }
        response = requests.get(url, params=params)
        data = response.json()
        df = pd.DataFrame(data['observations'])
        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        return df
    

    def check_high_yield_spread_warning(self):
        """
        하이일드 스프레드 데이터프레임을 받아
        최신값과 전일 대비 변화율을 체크해 경고를 출력하는 함수
        """
        df = self.get_high_yield_spread()
        df = df.dropna(subset=['value'])  # NaN 제거
        df = df.sort_values('date')       # 날짜순 정렬
        
        today_row = df.iloc[-1]
        date = today_row["date"]
        yesterday_row = df.iloc[-2]
        
        today_value = today_row['value']
        yesterday_value = yesterday_row['value']
        
        change = today_value - yesterday_value  # 변화량 (포인트)

        messages = []
        messages.append(f"🔎 하이일드 스프레드 오늘({today_row['date'].date()}) 값: {today_value:.2f}%")
        messages.append(f"🔎 어제({yesterday_row['date'].date()}) 대비 변화: {change:+.2f}p")
        
        if today_value >= 7:
            messages.append("🚨 하락장 경고: 하이일드 스프레드가 7%를 넘었습니다!")
        elif today_value >= 5:
            messages.append("⚠️ 조정장 경고: 하이일드 스프레드가 5%를 넘었습니다!")
        
        if change >= 0.5:
            messages.append("⚡ 급등 경고: 하루 만에 스프레드가 0.5%p 이상 상승했습니다!")
        
        if (today_value < yesterday_value) and (today_value >= 5):
            messages.append("📈 저점 매수 가능성 신호: 스프레드가 꺾이기 시작했습니다!")

        return {
            "date" : date,
            'value' : today_value,
            'message' : messages
        }


    def get_ma_above_ratio(self):

        url = "https://www.barchart.com/stocks/momentum"
    
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() # HTTP 오류가 발생하면 예외 발생

            soup = BeautifulSoup(response.text, 'html.parser')

            ma_50_day = None
            ma_200_day = None

            # 'Market Average'라는 텍스트를 가진 <h5> 태그를 찾습니다.
            h5_market_average = soup.find('h5', string='Market Average')
            
            market_average_table = None
            if h5_market_average:
                # <h5> 태그의 부모 (class="block-title"인 div)를 찾습니다.
                block_title_div = h5_market_average.find_parent('div', class_='block-title')
                
                if block_title_div:
                    # 'block-title' div의 바로 다음 형제 요소 중에서 'table-wrapper' 클래스를 가진 div를 찾습니다.
                    table_wrapper = block_title_div.find_next_sibling('div', class_='table-wrapper')
                    
                    if table_wrapper:
                        # 'table-wrapper' 안에서 'table' 태그를 찾습니다.
                        market_average_table = table_wrapper.find('table')
                    else:
                        print("ERROR: 'table-wrapper' div를 찾을 수 없습니다.")
                else:
                    print("ERROR: 'Market Average' <h5> 태그의 부모 'block-title' div를 찾을 수 없습니다.")
            else:
                print("ERROR: 'Market Average' <h5> 태그를 찾을 수 없습니다.")


            if market_average_table:
                # 테이블 헤더 추출 (첫 번째 행의 th 태그들)
                header_row = market_average_table.find('tr') # 테이블의 첫 번째 tr
                if header_row:
                    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
                    # print(f"추출된 헤더: {headers}") # 디버깅용

                    # 테이블의 모든 행(<tr>)을 가져옵니다. tbody가 있든 없든 동작하도록 합니다.
                    rows_in_table = market_average_table.find_all('tr')
                    
                    today_row = None
                    # 가져온 행들을 순회하며 'Today' 행을 찾습니다.
                    for row in rows_in_table:
                        # 첫 번째 td가 'Today'인 경우를 찾습니다.
                        first_cell = row.find('td', class_='text-left') 
                        if first_cell and first_cell.get_text(strip=True) == 'Today':
                            today_row = row
                            break
                    
                    if today_row:
                        # 'Today' 행의 모든 데이터 셀(td 태그들) 추출
                        # 첫 번째 td(Today)를 제외한 나머지 td 값들을 가져옵니다.
                        data_cells = [td.get_text(strip=True) for td in today_row.find_all('td')[1:]] # [1:]로 'Today' 셀 제외
                        # print(f"Today 행의 데이터: {data_cells}") # 디버깅용

                        # 헤더 인덱스를 사용하여 50-Day MA와 200-Day MA 값 추출
                        try:
                            index_50_day_ma_header = headers.index("50-Day MA")
                            ma_50_day = data_cells[index_50_day_ma_header -1] 

                        except ValueError:
                            print("헤더에서 '50-Day MA'를 찾을 수 없습니다.")
                        except IndexError:
                            print("50-Day MA에 해당하는 데이터가 없습니다. 인덱스 오류.")

                        try:
                            index_200_day_ma_header = headers.index("200-Day MA")
                            ma_200_day = data_cells[index_200_day_ma_header -1]
                        except ValueError:
                            print("헤더에서 '200-Day MA'를 찾을 수 없습니다.")
                        except IndexError:
                            print("200-Day MA에 해당하는 데이터가 없습니다. 인덱스 오류.")

                    else:
                        print("MARKET AVERAGE 테이블에서 'Today' 행을 찾을 수 없습니다.")
                else:
                    print("MARKET AVERAGE 테이블에서 헤더 행(<tr>)을 찾을 수 없습니다.")
            else:
                print("MARKET AVERAGE 테이블을 찾을 수 없습니다.")

            return {
                "date": datetime.today().strftime("%Y-%m-%d"),
                "50-day MA": ma_50_day,
                "200-day MA": ma_200_day
            }

        except requests.exceptions.RequestException as e:
            print(f"웹 페이지에 접속하는 중 오류 발생: {e}")
            return None, None
        except Exception as e:
            print(f"데이터를 파싱하는 중 오류 발생: {e}")
            return None, None


    def interpret_ma_above_ratio(self):
        """
        이평선 상회 비율 해석:
        - 30% 미만: 매수 추천
        - 70% 이상: 매도 추천
        - 단기적: 50일 / 장기적: 200일

        Parameters:
            result (dict): {'date': 'YYYY-MM-DD', '50-day MA': '62.72%', '200-day MA': '52.33%'}

        Returns:
            list: 추천 메시지 리스트 (현재 수치 포함)
        """

        data = self.get_ma_above_ratio()

        date = data['date']


        # 50-day MA 해석
        ma_50 = float(data.get("50-day MA", "0%").replace("%", ""))
        if ma_50 < 30:
            signal_50 = "BUY"
            icon_50 = "✅"
            commnet_50 = f"✅ 단기적 매수 추천: 50일 이평선 상회 비율이 {ma_50:.2f}%로 낮습니다."
        elif ma_50 >= 70:
            signal_50 = "SELL"
            icon_50 = "🚨"
            comment_50 = f"🚨 단기적 매도 신호: 50일 이평선 상회 비율이 {ma_50:.2f}%로 과열 구간입니다."
        else:
            signal_50 = "HOLD"
            icon_50 = "⚖️"
            comment_50 = f"⚖️ 현재는 뚜렷한 매수/매도 신호가 없습니다. (50일: {ma_50:.2f}%"

        # 200-day MA 해석
        ma_200 = float(data.get("200-day MA", "0%").replace("%", ""))
        if ma_200 < 30:
            signal_200 = "BUY"
            icon_200 = "✅"
            comment_200 = f"✅ 장기적 매수 추천: 200일 이평선 상회 비율이 {ma_200:.2f}%로 낮습니다."
        elif ma_200 >= 70:
            signal_200 = "SELL"
            icon_200 = "🚨"
            comment_200 = f"🚨 장기적 매도 신호: 200일 이평선 상회 비율이 {ma_200:.2f}%로 과열 구간입니다."
        else:
            signal_200 = "HOLD"
            icon_200 = "⚖️"
            comment_200 = f"⚖️ 현재는 뚜렷한 매수/매도 신호가 없습니다. 200일: {ma_200:.2f}%)"

        # 딕셔너리를 활용하여 단일 행의 DataFrame 생성
        ma_result = pd.DataFrame([{
            'date': date,
            'signal_50': signal_50,
            '50_ma': ma_50,
            'comment_50': comment_50,
            'signal_200': signal_200,
            '200_ma': ma_200,
            'comment_200': comment_200
        }])

        return ma_result
    

    def analyze_disparity_with_ma(self):
        """
        50일, 200일 이동평균 기준 이격도 계산 및 해석

        Returns:
            dict : {
                'date': latest_date,
                'sp500_close': latest_price,
                '50-day MA': latest_ma_50,
                '200-day MA': latest_ma_200,
                '50-day disparity (%)': value,
                '200-day disparity (%)': value,
                'short_term_status': 해석 텍스트,
                'long_term_status': 해석 텍스트
            }
        """
        df = self.get_sp500()
        df = df.copy()
        df['MA_50'] = df['sp500_close'].rolling(window=50).mean()
        df['MA_200'] = df['sp500_close'].rolling(window=200).mean()
        df.dropna(inplace=True)

        latest = df.iloc[-1]
        date = latest['date']
        close = latest['sp500_close']
        ma_50 = latest['MA_50']
        ma_200 = latest['MA_200']

        disparity_50 = ((close - ma_50) / ma_50) * 100
        disparity_200 = ((close - ma_200) / ma_200) * 100

        def interpret_disparity_50(val):
            if val <= -5:
                return "📉 단기 침체 구간"
            elif val <= 5:
                return "⚖️ 중립 구간"
            elif val <= 10:
                return "⚠️ 단기 과열"
            else:
                return "🚨 극단적 단기 과열"

        def interpret_disparity_200(val):
            if val <= -10:
                return "📉 장기 침체 구간"
            elif val <= 0:
                return "⚖️ 장기 중립(약세)"
            elif val <= 10:
                return "⚖️ 장기 중립(강세)"
            elif val <= 20:
                return "⚠️ 장기 과열"
            else:
                return "🔥 광기 구간"
        

        ma_disparity_result = pd.DataFrame([{
            'date': date,
            'sp500' : close,
            '50-day MA': round(ma_50, 2),
            '50-day disparity (%)': round(disparity_50, 2),
            'comment_50': interpret_disparity_50(disparity_50),
            '200-day MA': round(ma_200, 2),
            '200-day disparity (%)': round(disparity_200, 2),
            'comment_200': interpret_disparity_200(disparity_200)
        }])


        return ma_disparity_result


      # Clear 주별 데이터 - 1주일 딜레이
    def update_bull_bear_spread(self):
        '''
        로컬에 저장된 bull_bear_spread 파일 불러오기
        '''
        bb_spread = None  # ✅ 변수 초기화
        try:
            bb_spread = self.bull_bear_spread_updater.update_csv()
            print("✅ Bull Bear Spread CSV 업데이트 완료")
        except Exception as e:
            print("📛 Bull Bear Spread 업데이트 실패:", e)
        return bb_spread


    def get_bull_bear_spread(self):

        url = "https://ycharts.com/indicators/us_investor_sentiment_bull_bear_spread"

        options = Options()
        # options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    bull_bear_spread = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if bull_bear_spread and date:
            return {
                "date": date,
                "spread": bull_bear_spread
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")
        
    def plot_snp_with_bull_bear_signals_from_crawler(
        self,
        buy_th: float = -0.2,
        sell_th: float = 0.4,
        nearest_tolerance_days: int = 3,
        align_direction: str = "nearest",  # "nearest" | "backward" | "forward"
        show: bool = True,
        buy_color: str = "green",
        sell_color: str = "red",
        save_csv_path: str | None = None,
    ):
        """
        MacroCrawler.update_bull_bear_spread() + MacroCrawler.get_sp500() 사용.
        - Bull-Bear spread < buy_th  → Buy 신호
        - Bull-Bear spread > sell_th → Sell 신호
        - 신호 날짜를 S&P500 최근접 거래일로 정렬(merge_asof)
        - 반환: 신호별 이벤트 DataFrame
        """
        # 1) 데이터 로드
        bb = pd.read_csv('bull_bear_spread.csv')  # 필요: ['date','spread']
        snp = self.get_sp500()                # 필요: ['date','sp500_close']

        # 2) 전처리
        for df in (bb, snp):
            if "date" not in df.columns:
                raise ValueError("입력 데이터에 'date' 컬럼이 없습니다.")
            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)
            df.drop_duplicates(subset=["date"], keep="last", inplace=True)

        if "spread" not in bb.columns:
            cand = [c for c in bb.columns if "spread" in c.lower()]
            if not cand:
                raise ValueError("Bull-Bear 데이터에 'spread' 컬럼이 없습니다.")
            bb = bb.rename(columns={cand[0]: "spread"})

        if "sp500_close" not in snp.columns:
            raise ValueError("S&P500 데이터에 'sp500_close' 컬럼이 없습니다.")

        # 3) 신호 생성
        buy_df  = bb[bb["spread"] < buy_th].copy()
        sell_df = bb[bb["spread"] > sell_th].copy()

        # 4) 최근접 거래일 매칭
        snp_slim = snp[["date", "sp500_close"]].rename(columns={"sp500_close": "snp"})
        buy_aligned = pd.merge_asof(
            buy_df.sort_values("date"),
            snp_slim.sort_values("date"),
            on="date",
            direction=align_direction,
            tolerance=pd.Timedelta(days=nearest_tolerance_days),
        ).dropna(subset=["snp"])
        buy_aligned["signal"] = "buy"

        sell_aligned = pd.merge_asof(
            sell_df.sort_values("date"),
            snp_slim.sort_values("date"),
            on="date",
            direction=align_direction,
            tolerance=pd.Timedelta(days=nearest_tolerance_days),
        ).dropna(subset=["snp"])
        sell_aligned["signal"] = "sell"

        # 5) 이벤트 DataFrame으로 결합 & 정렬
        events_df = pd.concat([buy_aligned, sell_aligned], ignore_index=True)
        events_df["threshold_buy"] = buy_th
        events_df["threshold_sell"] = sell_th
        events_df = events_df[["date", "signal", "snp", "spread", "threshold_buy", "threshold_sell"]]
        events_df.sort_values("date", inplace=True)

        # (선택) CSV 저장
        # if save_csv_path:
        #     events_df.to_csv(save_csv_path, index=False)

        # 6) 시각화
        fig, ax = plt.subplots(figsize=(14, 7))
        ax.plot(snp["date"], snp["sp500_close"], label="S&P500")

        # 색상: 매수=초록, 매도=빨강
        if not events_df.empty:
            buys  = events_df[events_df["signal"] == "buy"]
            sells = events_df[events_df["signal"] == "sell"]
            if not buys.empty:
                ax.scatter(buys["date"], buys["snp"], marker="^", s=90,
                        color=buy_color, edgecolor="k", linewidths=0.5,
                        label=f"Buy (spread < {buy_th})", zorder=5)
            if not sells.empty:
                ax.scatter(sells["date"], sells["snp"], marker="v", s=90,
                        color=sell_color, edgecolor="k", linewidths=0.5,
                        label=f"Sell (spread > {sell_th})", zorder=5)

        ax.set_title("S&P500 with Bull–Bear Spread Signals")
        ax.set_xlabel("Date"); ax.set_ylabel("S&P500 Close")
        ax.grid(True, alpha=0.3); ax.legend()

        if show:
            plt.show()

        # ✅ dict 대신 DataFrame 반환
        return fig, ax, events_df


    def generate_bull_bear_signals(self):
        """
        Bull-Bear Spread 기준 투자 전략

        매수: spread < -0.2
        매도: spread > 0.4
        """

        buy_th = float(-0.2)
        sell_th = float(0.4)

        df = pd.read_csv("bull_bear_spread.csv")
    
        if df is None or df.empty:
            raise ValueError("bull_bear_spread.csv가 비어 있거나 로드에 실패했습니다.")
        if "date" not in df.columns or "spread" not in df.columns:
            raise ValueError("bull_bear_spread.csv는 'date', 'spread' 컬럼을 포함해야 합니다.")
        
        df = df.dropna(subset=["date", "spread"]).copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        df_latest = df.iloc[-1]
        spread_val = float(df_latest["spread"])
        
        buy_signal  = spread_val < buy_th
        sell_signal = spread_val > sell_th

        if sell_signal:
            signal = "SELL"
            icon = "🔴"
            comment = "🔥 광기 구간(투자자 과도한 낙관) → 차익실현/리스크 관리 고려"
        elif buy_signal:
            signal = "BUY"
            icon = "🟢"
            comment = "✅ 역발상 매수 구간(투자자 공포 심화) → 분할 매수 고려"
        else:
            signal = "HOLD"
            icon = "⚪"
            comment = "⚖️ 판단 유보(혼조/중립) → 관망 또는 보유 유지"

        return {
            "date": pd.to_datetime(df_latest["date"]).strftime("%Y-%m-%d"),
            "spread": spread_val,
            "buy_signal": bool(buy_signal),
            "sell_signal": bool(sell_signal),
            "signal": signal,
            "icon": icon,
            "comment": comment,
            "thresholds": {"buy_th": buy_th, "sell_th": sell_th},
        }
        # 40의 법칙

if __name__ == "__main__":
    crawler = MacroCrawler()

    # md_data = crawler.update_margin_debt_data()
    # pmi_data = crawler.update_ism_pmi_data()
    # fp_data = crawler.update_snp_forwardpe_data()
    # pc_data = crawler.update_putcall_ratio()
    # bb_data = crawler.update_bull_bear_spread()
    # lei_data = crawler.update_lei_data()

    data = crawler.get_sp500()
    print(data)

