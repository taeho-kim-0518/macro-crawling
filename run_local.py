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


from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from md_updater import MarginDebtUpdater
from ism_pmi_updater import ISMPMIUpdater
from SNP_forward_pe_updater import forwardpe_updater
from putcall_ratio_updater import PutCallRatioUpdater
from bullbear_spread_updater import BullBearSpreadUpdater

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
        df = yf.download(ticker, start='2000-01-01', interval="1d", progress=False )
        # 인덱스를 컬럼으로 변환
        df = df.reset_index()

        # 멀티인덱스 컬럼 --> 단일 컬럼으로 변환
        df.columns = [col[0] if isinstance(col,tuple) else col for col in df.columns]

        # 컬럼명 정리
        df = df.rename(columns={'Date': 'date', 'Close': 'sp500_close'})
        
        # 월 단위로 맞춰주기 (Period → Timestamp)
        df['date'] = pd.to_datetime(df['date']) #dt.to_period('M').dt.to_timestamp()

        # 필요한 컬럼만 반환
        df = df[['date', 'sp500_close']]
        df.to_csv("sp500.csv", encoding='utf-8-sig')
        return df
    
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
        S&P500 종가와 margin_debt/m2 비율 및 매수/매도 신호를 함께 시각화
        df : 병합된 데이터프레임(merge_m2_margin_sp500_abs)
        - 좌측 y축: S&P500
        - 우측 y축: margin_debt / m2 비율
        - 매수 시점: 초록색 ▲
        - 매도 시점: 빨간색 ▼
        """

        df = self.merge_m2_margin_sp500_abs()
        # 비율 및 신호 계산
        df = df.copy()
        df["ratio"] = df["margin_debt"] / df["m2"]
        df["ratio_z"] = (df["ratio"] - df["ratio"].rolling(window=36, min_periods=12).mean()) / \
                        df["ratio"].rolling(window=36, min_periods=12).std()
        df["ratio_change_pct"] = df["ratio"].pct_change() * 100

        # 완화된 조건
        df["buy_signal"] = (df["ratio_z"] < -1.2) & (df["ratio_change_pct"] > 0)
        df["sell_signal"] = (df["ratio_z"] > 1.5) & (df["ratio_change_pct"] < -5)

        # 시각화
        fig, ax1 = plt.subplots(figsize=(14, 6))

        # S&P500 지수 (좌측 y축)
        ax1.plot(df["date"], df["sp500_close"], color="blue", label="S&P500 지수", linewidth=2)
        ax1.scatter(
            df[df["buy_signal"]]["date"],
            df[df["buy_signal"]]["sp500_close"],
            color="green", marker="^", s=100, label="매수 신호"
        )
        ax1.scatter(
            df[df["sell_signal"]]["date"],
            df[df["sell_signal"]]["sp500_close"],
            color="red", marker="v", s=100, label="매도 신호"
        )
        ax1.set_ylabel("S&P500 종가", color="blue")
        ax1.tick_params(axis='y', labelcolor="blue")

        # margin_debt / m2 비율 (우측 y축)
        ax2 = ax1.twinx()
        ax2.plot(df["date"], df["ratio"], color="gray", linestyle="--", label="Margin Debt / M2 비율")
        ax2.set_ylabel("Margin Debt / M2 비율", color="gray")
        ax2.tick_params(axis='y', labelcolor="gray")

        # 제목 및 범례
        fig.suptitle("S&P500 + 매수/매도 신호 + Margin Debt / M2 비율", fontsize=14)
        fig.legend(loc="upper left", bbox_to_anchor=(0.1, 0.9))
        fig.tight_layout()
        if save_to:
            fig.savefig(save_to, format='png')
            plt.close(fig)
        else:
            plt.show()
    

    # Clear
    def plot_sp500_with_mdyoy_signals_and_graph(self, save_to=None):
        '''
        S&P500, Margin Debt / M2, YoY 전략 기반 매수/매도 시점 시각화
        df : 병합된 데이터프레임(generate_mdyoy_signals)
        '''
        df = self.generate_mdyoy_signals()

        fig, ax1 = plt.subplots(figsize=(14, 6))

        # S&P500
        ax1.plot(df["date"], df["sp500_close"], label="S&P500", color="black")
        ax1.set_ylabel("S&P500 지수", fontsize=12)
        ax1.set_xlabel("날짜", fontsize=12)
        ax1.tick_params(axis='y')
        ax1.legend(loc="upper left")

        # 매수/매도 시점
        buy_dates = df[df["buy_signal"]]["action_date"]
        buy_prices = df[df["buy_signal"]]["sp500_close"]
        sell_dates = df[df["sell_signal"]]["action_date"]
        sell_prices = df[df["sell_signal"]]["sp500_close"]

        ax1.scatter(buy_dates, buy_prices, color='blue', label='매수 시점', marker='^', s=100, zorder=5)
        ax1.scatter(sell_dates, sell_prices, color='red', label='매도 시점', marker='v', s=100, zorder=5)

        # 오른쪽 y축: Margin Debt / M2 비율
        ax2 = ax1.twinx()
        ax2.plot(df["date"], df["ratio"], label="Margin Debt / M2", color="green", alpha=0.4)
        ax2.set_ylabel("Margin Debt / M2", fontsize=12)
        ax2.tick_params(axis='y')

        fig.suptitle("📉 Margin Debt YoY 전략: S&P500 및 Margin Debt / M2 비율", fontsize=14)
        fig.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=3)
        plt.tight_layout()
        if save_to:
            fig.savefig(save_to, format='png')
            plt.close(fig)
        else:
            plt.show()

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


    def analyze_pe(self):

        ttm_pe_result = self.get_ttm_pe()
        ttm_pe = ttm_pe_result["ttm_pe"]  # 문자열

        forward_pe_result = self.update_snp_forwardpe_data()
        forward_pe = forward_pe_result["forward_pe"].iloc[-1]

        # ✅ 문자열일 수 있는 ttm_pe를 float로 변환
        ttm_pe = float(ttm_pe) #.replace(",", "").strip()
        forward_pe = float(forward_pe)

        message = f"📊 S&P 500 Forward PER: {forward_pe:.2f}\n"
        message += f"📊 S&P 500 TTM PER: {ttm_pe:.2f}\n\n"

        # 절대적 고평가/저평가 판단
        if forward_pe > 21:
            message += "⚠️ Forward PER 기준으로 **고평가** 구간입니다.\n"
        elif forward_pe < 17:
            message += "✅ Forward PER 기준으로 **저평가** 구간입니다.\n"
        else:
            message += "⚖️ Forward PER 기준으로 **평균 범위**입니다.\n"

        # TTM 기준 고평가/저평가 판단
        if ttm_pe > 20:
            message += "⚠️ TTM PER 기준으로 **역사적 고평가** 구간입니다.\n"
        elif ttm_pe < 13:
            message += "✅ TTM PER 기준으로 **저평가** 구간입니다.\n"
        else:
            message += "⚖️ TTM PER 기준으로 **평균 수준**입니다.\n"

        # TTM 대비 Forward 비교
        if ttm_pe > forward_pe:
            message += "🟢 시장은 **향후 실적 개선**을 기대하는 낙관적인 흐름입니다."
        elif ttm_pe < forward_pe:
            message += "🔴 시장은 **실적 둔화**를 반영하는 보수적인 흐름입니다."
        else:
            message += "⚪ 시장은 현재 실적 수준을 그대로 유지할 것으로 보고 있습니다."

        return message
    
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
        try:
            putcall_df = self.put_call_ratio_updater.update_csv()
            print("✅ PutCall Ratio CSV 업데이트 완료")
        except Exception as e:
            print("📛 PutCall Ratio 업데이트 실패:", e)

        return putcall_df  


    def check_put_call_ratio_warning(self):
        """
        풋콜 레이티오 데이터를 받아와서서
        매수 혹은 매도 시점을 출력하는 함수

        ratio_type : equity, index 둘 중 하나 입력
        """

        put_call_ratio = self.update_putcall_ratio()
        putcall_data_today = put_call_ratio.iloc[-1]
        print("data : ", putcall_data_today)
        date = putcall_data_today['date']
        value = putcall_data_today['equity_value']

        # 간단한 시그널 판단

        result = [f"📅 기준일: {date}",
                f"📊 Equity_putcall_ratio 지수 : {value:.2f}"]
    
        if value > 1.5:
            result.append("📉 Equity: 공포심 과다 → 반등 가능성 (매수 시점 탐색)")
        elif value < 0.5:
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
        
        messages = []

        # 50-day MA 해석
        ma_50 = float(data.get("50-day MA", "0%").replace("%", ""))
        if ma_50 < 30:
            messages.append(f"✅ 단기적 매수 추천: 50일 이평선 상회 비율이 {ma_50:.2f}%로 낮습니다.")
        elif ma_50 >= 70:
            messages.append(f"🚨 단기적 매도 신호: 50일 이평선 상회 비율이 {ma_50:.2f}%로 과열 구간입니다.")

        # 200-day MA 해석
        ma_200 = float(data.get("200-day MA", "0%").replace("%", ""))
        if ma_200 < 30:
            messages.append(f"✅ 장기적 매수 추천: 200일 이평선 상회 비율이 {ma_200:.2f}%로 낮습니다.")
        elif ma_200 >= 70:
            messages.append(f"🚨 장기적 매도 신호: 200일 이평선 상회 비율이 {ma_200:.2f}%로 과열 구간입니다.")

        # 신호 없을 때
        if not messages:
            messages.append(f"⚖️ 현재는 뚜렷한 매수/매도 신호가 없습니다. (50일: {ma_50:.2f}%, 200일: {ma_200:.2f}%)")

        return messages
    

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

        return {
            'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
            'sp500_close': round(close, 2),
            '50-day MA': round(ma_50, 2),
            '200-day MA': round(ma_200, 2),
            '50-day disparity (%)': round(disparity_50, 2),
            '200-day disparity (%)': round(disparity_200, 2),
            'short_term_status': interpret_disparity_50(disparity_50),
            'long_term_status': interpret_disparity_200(disparity_200)
        }


      # Clear 주별 데이터 - 1주일 딜레이
    def update_bull_bear_spread(self):
        '''
        로컬에 저장된 bull_bear_spread 파일 불러오기
        '''
        try:
            bb_spread = self.bull_bear_spread_updater.update_csv()
            print("✅ Bull Bear Spread CSV 업데이트 완료")
        except Exception as e:
            print("📛 Bull Bear Spread 업데이트 실패:", e)
        return bb_spread


    def get_bull_bear_spread(self):

        url = "https://ycharts.com/indicators/us_investor_sentiment_bull_bear_spread"

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
        

    def generate_bull_bear_signals(self):
        """
        Bull-Bear Spread 기준 투자 전략

        매수: spread < -20
        매도: spread > 40
        """
        df = self.update_bull_bear_spread()
        df = df.copy()
        df_latest = df.iloc[-1]
        df_latest["buy_signal"] = df_latest["spread"] < -0.2
        df_latest["sell_signal"] = df_latest["spread"] > 0.4

        result = []

        if df_latest['sell_signal'] == True:
            result.append("🔥 광기 구간(투자자들이 지나치게 낙관적)")
        elif df_latest['buy_signal'] == True:
            result.append("✅ 역발상 매수 기회(투자자들이 공포를 느낌)")
        else:
            result.append("⚖️ 판단 유보(시장 혼조 또는 무관심)")
       
        return {
            'date' : df_latest['date'],
            'spread' : df_latest['spread'],
            'comment' : result

        }

    # 40의 법칙

if __name__ == "__main__":
    crawler = MacroCrawler()


    # md_data = crawler.update_margin_debt_data()
    # pmi_data = crawler.update_ism_pmi_data()
    # fp_data = crawler.update_snp_forwardpe_data()
    # pc_data = crawler.update_putcall_ratio()
    # bb_data = crawler.update_bull_bear_spread()

    data = crawler.update_ism_pmi_data()
    print(data)
