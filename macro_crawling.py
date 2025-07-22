import os
import time
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
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
        
    def get_cpi(self):
        url = 'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': 'CPIAUCSL',  # CPI
            'api_key': self.fred_api_key,
            'file_type': 'json',
            'observation_start': '2000-01-01'
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


    def update_margin_debt_data(self):
        '''
        로컬에 저장된 margin_debt 파일 불러오기
        '''
        md_df = self.margin_updater.update_csv()
        print("✅ 마진 부채 CSV 업데이트 완료")
        return self.margin_updater.df


    def get_margin_debt_data(self):
        '''
        마진 부채 데이터 가져오기(고점 판단)
        '''
        # 1년치 데이터 크롤링
        url = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

        except Exception as e:
            print("❌ API 요청 또는 JSON 파싱 실패:", e)
            print("📦 응답 내용:", response.text)
            return pd.DataFrame()
        
        table = soup.select_one("table")  # 가장 첫 번째 테이블 선택
        rows = table.find_all("tr")
        
        data = []
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]

        for row in rows[1:]:
            cols = [td.get_text(strip=True).replace(",", "") for td in row.find_all("td")]
            if len(cols) == len(headers):
                data.append(cols)

        df = pd.DataFrame(data, columns=headers)
        df['Month/Year'] = pd.to_datetime(df['Month/Year'], format='%b-%y')
        # df = df.rename(columns={"Debit Balances in Customers' Securities Margin Accounts" : "margin_debt"})
        for col in df.columns[1:]:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    
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

    
      
    def get_margin_yoy_change(self):
        '''
        마진 부채의 전년 대비 YOY (%) 변화율 계산
        '''
        df = self.update_margin_debt_data()
        if df.empty:
            return pd.DataFrame()

        df = df.sort_values("Month/Year")
        df["margin_debt"] = df["Debit Balances in Customers' Securities Margin Accounts"]
        df["margin_debt"] = df["margin_debt"].str.replace(',','').astype(int)
        df["Margin YoY (%)"] = df["margin_debt"].pct_change(periods=12) * 100
        return df[["Month/Year", "margin_debt", "Margin YoY (%)"]]


    def generate_zscore_trend_signals(self, df: pd.DataFrame) -> pd.DataFrame:
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
    
    def generate_mdyoy_signals(self, df):
        '''
        Margin Debt YoY 전략 기반 매수/매도 신호 생성 함수 (2개월 발표 지연 반영)
        df : 병합된 데이터프레임(merge_m2_margin_sp500_abs)
        '''
        df = df.copy()
        df["margin_yoy"] = df["margin_debt"].pct_change(periods=12) * 100

        # 신호 조건
        df["buy_signal"] = (df["margin_yoy"] > 0) & (df["margin_yoy"].shift(1) <= 0)
        df["sell_signal"] = (df["margin_yoy"] < -10) & (df["margin_yoy"].shift(1) >= -10)

        # 발표 지연 감안한 진입 시점 계산
        df["signal_date"] = df["date"]
        df["action_date"] = df["signal_date"] + pd.DateOffset(months=2)

        return df
        
    def get_sp500(self):
        '''
        S&P500 지수 조회
        '''
        ticker = '^GSPC'
        df = yf.download(ticker, start='2000-01-01', interval="1mo", progress=False )
        # 인덱스를 컬럼으로 변환
        df = df.reset_index()

        # 멀티인덱스 컬럼 --> 단일 컬럼으로 변환
        df.columns = [col[0] if isinstance(col,tuple) else col for col in df.columns]

        # 컬럼명 정리
        df = df.rename(columns={'Date': 'date', 'Close': 'sp500_close'})
        
        # 월 단위로 맞춰주기 (Period → Timestamp)
        df['date'] = pd.to_datetime(df['date']).dt.to_period('M').dt.to_timestamp()

        # 필요한 컬럼만 반환
        df = df[['date', 'sp500_close']]
        return df
    
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

        df = pd.merge(df_m2, df_margin[['date', 'margin_debt']], on='date', how='inner')
        df = pd.merge(df, df_sp500, on='date', how='inner')
        df["ratio"] = df["margin_debt"] / df["m2"]   # ← 이 줄 추가
        return df
 

    def plot_sp500_with_signals_and_graph(self, df: pd.DataFrame):
        """
        S&P500 종가와 margin_debt/m2 비율 및 매수/매도 신호를 함께 시각화
        df : 병합된 데이터프레임(generate_mdyoy_signals)
        - 좌측 y축: S&P500
        - 우측 y축: margin_debt / m2 비율
        - 매수 시점: 초록색 ▲
        - 매도 시점: 빨간색 ▼
        """

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
        plt.show()
    


    def plot_sp500_with_mdyoy_signals_and_graph(self, df):
        '''
        S&P500, Margin Debt / M2, YoY 전략 기반 매수/매도 시점 시각화
        df : 병합된 데이터프레임(merge_m2_margin_sp500_abs)
        '''
        import matplotlib.pyplot as plt

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
        plt.show()

    def check_today_md_signal(self):
        """
        오늘이 generate_zscore_trend_signals 또는 generate_mdyoy_signals 기준 매수/매도 진입일인지 확인
        
        - 오늘이 action_date에 해당하면 BUY/SELL 출력
        - 두 전략 중 하나라도 해당하면 알려줌
        """

        today = pd.Timestamp.today()

        print(f"📅 오늘 날짜 (확인 기준): {today.date()}")

        # 데이터 병합
        df = self.merge_m2_margin_sp500_abs()

        # --- 전략 1: z-score 기반
        zscore_signal_df = self.generate_zscore_trend_signals(df)
        zscore_today = zscore_signal_df[zscore_signal_df["action_date"] == today]

        # --- 전략 2: margin YOY 기반
        mdyoy_df = self.generate_mdyoy_signals(df)
        mdyoy_today = mdyoy_df[mdyoy_df["action_date"] == today]

        signal_found = False

        if not zscore_today.empty:
            print("\n📌 [Z-Score 전략] 오늘 매매 신호 있음!")
            for _, row in zscore_today.iterrows():
                print(f"👉 {row['action_date'].date()} : {row['signal']} 신호 (발생일: {row['original_signal_date'].date()})")
            signal_found = True

        if not mdyoy_today[mdyoy_today["buy_signal"] | mdyoy_today["sell_signal"]].empty:
            print("\n📌 [Margin YoY 전략] 오늘 매매 신호 있음!")
            for _, row in mdyoy_today.iterrows():
                if row["buy_signal"]:
                    print(f"👉 {row['action_date'].date()} : BUY 신호 (발생일: {row['signal_date'].date()})")
                elif row["sell_signal"]:
                    print(f"👉 {row['action_date'].date()} : SELL 신호 (발생일: {row['signal_date'].date()})")
            signal_found = True

        if not signal_found:
            print("\n✅ 오늘은 매수/매도 진입일이 아닙니다.")


if __name__ == "__main__":
    cralwer = MacroCrawler()


    signal_today = cralwer.check_today_md_signal()

 
    print("signal data")
    print(signal_today)

    # buy_signal = signal_mdyoy_df[signal_mdyoy_df["buy_signal"]==True]
    # print("매수 시점")
    # print(buy_signal)
 


