import os
import time
import pandas as pd
import numpy as np
import requests
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

        df_margin = self.update_margin_debt_data().copy()
        df_margin['date'] = df_margin['Month/Year'].dt.to_period('M').dt.to_timestamp()
        df_margin["margin_debt"] = df_margin["Debit Balances in Customers' Securities Margin Accounts"]
        df_margin["margin_debt"] = df_margin["margin_debt"].str.replace(',','').astype(int)

        df_sp500 = self.get_sp500().copy()
        df_sp500['date'] = pd.to_datetime(df_sp500['date'])  # 혹시 모르니 안전하게

        df = pd.merge(df_m2, df_margin[['date', 'margin_debt']], on='date', how='inner')
        df = pd.merge(df, df_sp500, on='date', how='inner')
        return df
    
    def plot_macro_absolute(self, merge_df, margin_peak_df, margin_bottom_df):
        '''
        m2, margin_debt, snp500지수 간 상관관계 그래프 그리기
        merge_df : 병합 데이터
        margin_peak_df : margin_debt 추세 하락 표기
        margin_bottom_df : margin_debt 추세 반등 표기
        '''
        
        df_norm = merge_df.copy()
        df_norm['m2_norm'] = df_norm['m2'] / df_norm['m2'].iloc[0] * 100
        df_norm['margin_debt_norm'] = df_norm['margin_debt'] / df_norm['margin_debt'].iloc[0] * 100
        df_norm['sp500_norm'] = df_norm['sp500_close'] / df_norm['sp500_close'].iloc[0] * 100

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(df_norm['date'], df_norm['m2_norm'], label='M2 (정규화)', color='green')
        ax.plot(df_norm['date'], df_norm['margin_debt_norm'], label='마진 부채 (정규화)', color='red')
        ax.plot(df_norm['date'], df_norm['sp500_norm'], label='S&P 500 (정규화)', color='blue', alpha=0.7)

        # margin_drop_date 표시
        try:
            margin_peak_df['margin_drop_date'] = pd.to_datetime(margin_peak_df['margin_drop_date'])
            for d in margin_peak_df['margin_drop_date']:
                ax.axvline(d, color='gray', linestyle='--', alpha=0.6)
                ax.text(d, ax.get_ylim()[1]*0.95, '📉', fontsize=9, color='gray', rotation=90, ha='center')
        
        except KeyError:
            pass

        # entry_date 표시 (매수 후보 시점)
        try:
            for d in margin_bottom_df['entry_date']:
                ax.axvline(d, color='blue', linestyle='--', alpha=0.4)
                ax.text(d, ax.get_ylim()[1]*0.9, '💰', fontsize=9, color='blue', rotation=90, ha='center')

        except KeyError:
            pass

        ax.set_title("M2 / Margin Debt / S&P 500 추이 (정규화 기준 100)")
        ax.set_ylabel("지표 정규화 값 (기준시점 = 100)")
        ax.set_xlabel("날짜")
        ax.grid(True)
        ax.legend()
        plt.tight_layout()
        plt.show()


  

if __name__ == "__main__":
    cralwer = MacroCrawler()
    md_df = cralwer.merge_m2_margin_sp500_abs()
 
    print("merge data")
    print(md_df)

