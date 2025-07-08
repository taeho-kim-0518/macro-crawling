import pandas as pd
import numpy as np
import requests
import matplotlib
import yfinance as yf
from bs4 import BeautifulSoup
from scipy.stats import linregress
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import streamlit as st
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import os
from dotenv import load_dotenv
import time
import seaborn as sns

# load_dotenv()


# API_KEY = os.getenv("FRED_API_KEY")
# EIA_API_KEY = os.getenv("EIA_API_KEY")

# secrets.toml에서 API 키 불러오기
API_KEY = st.secrets["FRED_API_KEY"]
EIA_API_KEY = st.secrets["EIA_API_KEY"]


@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        ),
        options=options,
    )
    return driver
   

def get_10years_treasury_yeild():
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id' : 'GS10', # 10년물 국채 금리
        'api_key' : API_KEY,
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


def get_2years_treasury_yeild():
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id' : 'GS2', # 2년물 국채 금리
        'api_key' : API_KEY,
        'file_type' : 'json',
        'observation_start' : '2000-01-01' # 시작일(원하는 날짜짜)
    }

    response = requests.get(url, params= params)
    data = response.json()

    # 데이터프레임 변환
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors= 'coerce')

    return df

def get_cpi():
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'CPIAUCSL',  # CPI
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def get_cpi_yoy():
    df = get_cpi() # 원래 CPIAUCSL 지수 불러오기
    df = df.sort_values('date').dropna()

    df['CPI YOY(%)'] = df['value'].pct_change(periods=12)*100 # 12개월 전 대비 변화율
    return df

def get_m2() : 
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'M2SL',  # M2 통화량
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def get_m2_yoy():
    df = get_m2()
    df = df.sort_values('date')
    df['m2_yoy'] = df['value'].pct_change(periods=12) * 100
    return df[['date', 'm2_yoy']]

def analyze_m2_investment_signal(m2_df, m2_yoy_df, cpi_df):
    """
    M2, M2 YoY, CPI YoY를 바탕으로 유동성 환경 평가 및 투자 시그널 분석
    """
    # 최신 공통 날짜로 병합
    df = pd.merge(m2_df, m2_yoy_df, on='date', how='inner')
    df = pd.merge(df, cpi_df[['date', 'CPI YOY(%)']], on='date', how='inner')
    df = df.dropna().sort_values('date')

    latest = df.iloc[-1]
    m2_val = latest['value']
    m2_yoy = latest['m2_yoy']
    cpi_yoy = latest['CPI YOY(%)']
    date = latest['date'].date()

    signal = [f"📅 기준일: {date}"]
    signal.append(f"💰 M2 수준: {m2_val:,.2f}")
    signal.append(f"📈 M2 YoY: {m2_yoy:.2f}%")
    signal.append(f"🏷️ CPI YoY: {cpi_yoy:.2f}%")
    signal.append("---")

    # 시그널 해석
    if m2_yoy > 5 and cpi_yoy < 3:
        signal.append("🟢 유동성 풍부 + 인플레 안정 → **성장주/주식시장 호재**")
    elif m2_yoy < 0:
        signal.append("🔴 유동성 축소 (QT) 경고 → **현금 비중 확대 고려**")
    elif m2_yoy < 2 and cpi_yoy > 4:
        signal.append("🟠 인플레 고조 + 유동성 정체 → **방어적 자산 선호 구간**")
    else:
        signal.append("⚪ 중립 국면 → **추가 확인 필요** (실업률, 금리, PER 등과 종합 고려)")

    return "\n".join(signal)




def get_high_yield_spread():
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'BAMLH0A0HYM2',  # 하이일드 스프레드
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def check_high_yield_spread_warning(df):
    """
    하이일드 스프레드 데이터프레임을 받아
    최신값과 전일 대비 변화율을 체크해 경고를 출력하는 함수
    """
    df = df.dropna(subset=['value'])  # NaN 제거
    df = df.sort_values('date')       # 날짜순 정렬
    
    today_row = df.iloc[-1]
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

    return "\n".join(messages)

def get_dollar_index(period="10y"):
    """
    달러 인덱스 (DXY) 데이터를 yfinance에서 가져와서 DataFrame으로 반환
    period: '1d', '5d', '1mo', '3mo', '6mo', '1y', etc.
    """
    ticker = "DX-Y.NYB"  # yfinance 상 DXY 심볼 (ICE 선물시장용)
    df = yf.download(ticker, period=period, interval="1d", progress=False)
    df = df.reset_index()

    # 컬럼 정리 : 컬럼 이름을 표준화
    df = df[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'dxy'})
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_snp_inedx(period="10y"):
    
    ticker = '^GSPC'
    df = yf.download(ticker, period=period, interval="1d", progress=False )
    df = df.reset_index()
    df = df[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'snp500'})
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_yen_index(period="10y"):
    """
    엔화 인덱스 (FXY) ETF 데이터를 가져오는 함수
    - FXY는 일본 엔화 강세에 투자하는 ETF
    """
    ticker = 'FXY'
    df = yf.download(ticker, period=period, interval='1d', progress=False)
    df = df.reset_index()
    df = df[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'yen_index'})
    df['date'] = pd.to_datetime(df['date'])
    return df

def get_japan_policy_rate(api_key: str = API_KEY, start_date="2015-05-18"):
    """
    일본 기준금리 데이터를 FRED API에서 가져오는 함수
    API Key는 FRED 홈페이지에서 무료 발급 가능
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': 'IRLTLT01JPM156N',  # ← 바뀐 시리즈 ID!
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start_date
    }

    response = requests.get(url, params=params)
    data = response.json()

    # 에러 핸들링링
    if 'observations' not in data:
        raise ValueError(f"API 오류: {data.get('error_message', '알 수 없는 오류입니다.')}")

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['japan_policy_rate'] = pd.to_numeric(df['value'], errors='coerce')
    df = df[['date', 'japan_policy_rate']]
    return df



# as-js
# def get_bull_bear_spread():
#     url = ""

#     options = Options()
#     options.add_argument("--headless")
#     options.add_argument("--disable-gpu")
#     options.add_argument("--no-sandbox")

#     driver = webdriver.Chrome(options=options)
#     driver.get(url)
#     time.sleep(5)  # JS 로딩 대기

#     soup = BeautifulSoup(driver.page_source, "html.parser")
#     driver.quit()

#     # "Last Value" 텍스트가 있는 td 찾기
#     for td in soup.select("td.col-6"):
#         if "Last Value" in td.get_text(strip=True):
#             value_td = td.find_next_sibling("td")
#             if value_td:
#                 return value_td.get_text(strip=True)

#     return None


def get_bull_bear_spread():
    url = "https://ycharts.com/indicators/us_investor_sentiment_bull_bear_spread"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # as-js
    # driver = webdriver.Chrome(
    #     service=Service(ChromeDriverManager().install()),
    #     options=options
    # )

    driver = webdriver.Chrome(service=Service(), options=options)
    # driver = webdriver.Chrome(service=Service())

    driver.get(url)
    time.sleep(5)  # JS 렌더링 대기

    soup = BeautifulSoup(driver.page_source, "html.parser")
    
    for td in soup.select("td.col-6"):
        if "Last Value" in td.get_text(strip=True):
            value_td = td.find_next_sibling("td")
            if value_td:
                return value_td.get_text(strip=True)
            
    return None


def analyze_bull_bear_spread(index):
    '''
    bull-bear 스프레드 분석(역발상 지표)
    -20일 경우 매수 타이밍
    -30이면 적극 매수 타이밍
    '''

    try:
        index = float(index.replace('%', '').strip())
    except ValueError:
        return f"❌ 유효하지 않은 값입니다: {index}"

    messages = []
    messages.append(f"🔎 bull-bear 스프레드 현재값: {index:.2f}%")

    if index <= -30:
        messages.append("✅ 적극 매수 기회: 스프레드가 -30 이하입니다.")
    elif index <= -20:
        messages.append("✅ 매수 기회: 스프레드가 -20 이하입니다.")
    else:
        messages.append("⚠️ 판단 보류: 중립 또는 과열 구간입니다.")

    return "\n".join(messages)
    

def get_equity_put_call_ratio():
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
                return value_td.get_text(strip=True)

    return None

#as-js
def get_index_put_call_ratio():
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
                return value_td.get_text(strip=True)

    return None



def get_equity_put_call_trend(days=20):
    url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # 테이블의 어떤 행이라도 나타날 때까지 기다립니다.
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
    except Exception as e:
        print("❌ 테이블 로딩 실패:", e)
        driver.quit()
        return pd.DataFrame()

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # 모든 테이블의 행을 선택합니다.
    rows = soup.select("table tbody tr")
    print(f"✅ 추출된 row 수: {len(rows)}")

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            date = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            try:
                data.append((pd.to_datetime(date), float(value)))
            except ValueError:
                # 날짜나 값이 유효하지 않은 행은 건너뜁니다.
                continue

    df = pd.DataFrame(data, columns=["date", "value"])
    # 날짜를 기준으로 내림차순 정렬하여 최신 'days'만큼의 데이터를 가져온 후, 다시 날짜 오름차순으로 정렬합니다.
    df = df.sort_values("date", ascending=False).head(days).sort_values("date")
    return df

def get_index_put_call_trend(days=20):
    url = 'https://ycharts.com/indicators/cboe_index_put_call_ratio'

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # 테이블의 어떤 행이라도 나타날 때까지 기다립니다.
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
    except Exception as e:
        print("❌ 테이블 로딩 실패:", e)
        driver.quit()
        return pd.DataFrame()

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # 모든 테이블의 행을 선택합니다.
    rows = soup.select("table tbody tr")
    print(f"✅ 추출된 row 수: {len(rows)}")

    data = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            date = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            try:
                data.append((pd.to_datetime(date), float(value)))
            except ValueError:
                # 날짜나 값이 유효하지 않은 행은 건너뜁니다.
                continue

    df = pd.DataFrame(data, columns=["date", "value"])
    # 날짜를 기준으로 내림차순 정렬하여 최신 'days'만큼의 데이터를 가져온 후, 다시 날짜 오름차순으로 정렬합니다.
    df = df.sort_values("date", ascending=False).head(days).sort_values("date")
    return df


def analyze_put_call_ratio_trend(df):
    if df.empty or len(df) < 2:
        return "데이터 부족 (추세 분석 불가)"

    # 날짜를 숫자로 변환 (예: 1, 2, 3...)
    x = np.arange(len(df))
    y = df['value'].values

    # 선형 회귀 수행
    slope, intercept, r_value, p_value, std_err = linregress(x, y)

    trend_status = ""
    
    if slope > 0.001:  # 양의 기울기가 유의미한 경우
        trend_status = "상승 추세 (Increasing Trend)"
    elif slope < -0.001: # 음의 기울기가 유의미한 경우
        trend_status = "하락 추세 (Decreasing Trend)"
    else: # 기울기가 거의 0인 경우
        trend_status = "횡보 추세 (Sideways Trend)"

    return {
        "기울기 (Slope)": round(slope, 4),
        "추세 상태": trend_status,
        "R-squared": round(r_value**2, 4) # 설명력 (0~1, 1에 가까울수록 선형 모델이 데이터를 잘 설명)
    }


def check_put_call_ratio_warning(data, ratio_type):
    """
    풋콜 레이티오 데이터를 받아와서서
    매수 혹은 매도 시점을 출력하는 함수

    ratio_type : equity, index 둘 중 하나 입력
    """

    put_call_ratio = float(data)

    messages = [f"📊 Equity Put/Call Ratio: {put_call_ratio}"]

    # 간단한 시그널 판단

    if ratio_type == "equity":
    
        if put_call_ratio > 1.0:
            messages.append("📉 Equity: 공포심 과다 → 반등 가능성 (매수 시점 탐색)")
        elif put_call_ratio < 0.7:
            messages.append("🚨 Equity: 과열 탐욕 상태 → 매도 경고 또는 조정 가능성")
        else:
            messages.append("⚖️ Equity: 중립 구간")

    elif ratio_type == "index":

        if put_call_ratio > 1.5:
            messages.append("📉 Index: 헤지 수요 과도 → 반등 가능성 ↑")
        elif put_call_ratio < 0.7:
            messages.append("🚨 Index: 상승 베팅 과다 → 과열 위험 ↑")
        else:
            messages.append("⚖️ Index: 중립 구간")

    else:
        messages.append("❌ 오류: ratio_type은 'equity' 또는 'index'만 가능")
        
    return "\n".join(messages)

def get_fed_funds_rate():
    '''
    미국 기준 금리 계산
    '''
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'FEDFUNDS',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['fed_funds_rate'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def get_vix_index(period='10y'):
    df = yf.download('^VIX', period=period, interval='1d', progress=False)
    df = df.reset_index()
    df = df[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'vix'})
    df['date'] = pd.to_datetime(df['date'])
    return df

def analyze_vix():
    df_vix = get_vix_index()
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
        result.append("🟠 시장 불확실성 증가 → 투자자 주의 필요")
    else:
        result.append("🔴 극단적 공포 상태 → 과매도/저점 반등 가능성 (역발상 매수 고려 구간)")

    return "\n".join(result)

def analyze_real_rate_and_yield_spread():
    # 데이터 불러오기
    df_10y = get_10years_treasury_yeild()
    df_2y = get_2years_treasury_yeild()
    df_cpi_yoy = get_cpi_yoy()
    df_fed = get_fed_funds_rate()

    # 날짜 정렬
    df_10y = df_10y.sort_values("date")
    df_2y = df_2y.sort_values("date")
    df_cpi_yoy = df_cpi_yoy.sort_values("date")
    df_fed = df_fed.sort_values("date")

    # 병합
    merged = pd.merge(df_10y, df_2y, on='date', suffixes=('_10y', '_2y'), how='inner')
    merged = pd.merge(merged, df_cpi_yoy[['date', 'CPI YOY(%)']], on='date', how='inner')
    merged = pd.merge(merged, df_fed[['date', 'fed_funds_rate']], on='date', how='inner')
    merged = merged.dropna()

    # 가장 최근 값 추출
    latest = merged.iloc[-1]
    date = latest['date'].date()
    rate_10y = latest['value_10y']
    rate_2y = latest['value_2y']
    fed_rate = latest['fed_funds_rate']
    cpi_yoy = latest['CPI YOY(%)']

    # 계산
    real_rate_long = rate_10y - cpi_yoy        # 장기 실질금리
    real_rate_short = fed_rate - cpi_yoy       # 단기 실질금리
    yield_spread = rate_10y - rate_2y          # 장단기 금리차

    # 출력 메시지
    result = [f"📅 기준일: {date}",
              f"📈 10년물 국채금리: {rate_10y:.2f}%",
              f"📉 2년물 국채금리: {rate_2y:.2f}%",
              f"🔺 미국 기준금리 (Fed Funds): {fed_rate:.2f}%",
              f"📊 CPI YoY: {cpi_yoy:.2f}%",
              f"💡 장기 실질금리 (10Y - CPI YoY): {real_rate_long:.2f}%",
              f"💡 단기 실질금리 (기준금리 - CPI YoY): {real_rate_short:.2f}%",
              f"🔀 장단기 금리차 (10Y - 2Y): {yield_spread:.2f}%"]

    # 장기 실질금리 해석
    if real_rate_long < 0:
        result.append("🟦 장기 실질금리 < 0 → 유동성 풍부한 환경 → 성장주 우호")
    elif real_rate_long <= 1.5:
        result.append("⚖️ 장기 실질금리 0~1.5% → 균형 잡힌 시장 환경 → 중립 또는 점진적 긴축")
    else:
        result.append("🟥 장기 실질금리 > 1.5% → 할인율 부담 커짐 → 주식시장 역풍 우려")

    # 단기 실질금리 해석
    if real_rate_short < 0:
        result.append("🟩 단기 실질금리 < 0 → 여전히 완화적 통화정책 (유동성 공급)")
    elif real_rate_short <= 1.5:
        result.append("⚖️ 단기 실질금리 0~1.5% → 중립적 정책 환경")
    else:
        result.append("🟥 단기 실질금리 > 1.5% → 명확한 긴축 환경 → 투자자 비용 부담 상승")

    # 금리차 해석
    if yield_spread < 0:
        result.append("🟧 장단기 금리 역전 → 경기 침체 전조 (6~12개월 후 침체 가능성)")
    else:
        result.append("🟩 장단기 금리 정상 구조 → 경기 확장 가능성")

    return "\n".join(result)


def get_ecri_leading_index_with_trend(days=20):
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'USSLIND',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'observations' not in data:
        print("❌ 요청 실패:", data.get('error_message', '알 수 없는 오류'))
        return None, "데이터 수신 실패"

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna().sort_values("date").reset_index(drop=True)

    # 최근 days 주 동안 추세 분석
    if len(df) >= days:
        recent = df.tail(days)
        x = np.arange(len(recent))
        y = recent['value'].values
        slope, intercept, r_value, p_value, std_err = linregress(x, y)

        if slope > 0.05:
            trend = "📈 상승 추세 (회복 조짐)"
        elif slope < -0.05:
            trend = "📉 하락 추세 (경기 둔화)"
        else:
            trend = "➖ 횡보 추세 (불확실성 지속)"
    else:
        trend = "데이터가 부족하여 추세 판단 불가"

    return df.rename(columns={'value': 'ECRI Leading Index'}), trend

def get_unemployment_rate():
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'UNRATE',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['unemployment_rate'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def get_ism_pmi():
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

def get_ECRI():
    '''
    ECRI가 발표하는 지표를 공식적으로 FRED에 제공하는 형태
    상승시 경기회복/확장 의미, 하락시 경기 둔화/침체 의미
    '''
     
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'USSLIND',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['ECRI_index'] = pd.to_numeric(df['value'], errors='coerce')
    return df

def analyze_ecri_trend(df):
    x = np.arange(len(df))
    y = df['ECRI_index'].values
    slope, _, r_value, _, _ = linregress(x, y)

    if slope > 0.05:
        return "📈 상승 추세 (경기 회복 기대)"
    elif slope < -0.05:
        return "📉 하락 추세 (경기 둔화 위험)"
    else:
        return "➖ 횡보 추세 (불확실성 지속)"


def get_fred_series(series_id: str, column_name: str):
    """
    FRED API에서 시계열 데이터를 가져오는 범용 함수
    - series_id: FRED의 시리즈 ID (예: 'NAPM' → ISM PMI)
    - column_name: 결과 DataFrame에서 사용할 컬럼명
    """
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': series_id,
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'observations' not in data:
        raise Exception(f"FRED API 오류: {data.get('error_message', '응답에 데이터 없음')}")

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df[column_name] = pd.to_numeric(df['value'], errors='coerce')
    return df[['date', column_name]]


def get_wti_crude_oil_price():
    """
    FRED API를 통해 WTI 원유 가격(DCOILWTICO) 데이터를 가져오는 함수
    """
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'DCOILWTICO',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'observations' not in data:
        raise Exception(f"API 오류 발생: {data.get('error_message', '응답에 데이터 없음')}")

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['wti_crude_oil_price'] = pd.to_numeric(df['value'], errors='coerce')
    return df[['date', 'wti_crude_oil_price']]

def get_industrial_production_index():
    """
    미국 산업생산지수(INDPRO)를 FRED API에서 불러오는 함수
    """
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'INDPRO',
        'api_key': API_KEY,  # 사용 중인 FRED API 키
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'observations' not in data:
        raise Exception(f"❌ API 오류 발생: {data.get('error_message', '응답에 데이터 없음')}")

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['industrial_production'] = pd.to_numeric(df['value'], errors='coerce')
    return df[['date', 'industrial_production']]

def get_saudi_production():
    """
    FRED API를 통해 사우디 원유 생산량(OPECOPM) 데이터를 가져오는 함수
    """
    url = 'https://api.stlouisfed.org/fred/series/observations'
    params = {
        'series_id': 'SAUNGDPMOMBD',
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }

    response = requests.get(url, params=params)
    data = response.json()

    if 'observations' not in data:
        raise Exception(f"API 오류 발생: {data.get('error_message', '응답에 데이터 없음')}")

    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['saudi_crude_production'] = pd.to_numeric(df['value'], errors='coerce')
    return df[['date', 'saudi_crude_production']]

def get_eia_series_v2(series_id: str, column_name: str):
    url = f'https://api.eia.gov/v2/seriesid/{series_id}'
    params = {'api_key': EIA_API_KEY}
    response = requests.get(url, params=params)
    data = response.json()

    if 'response' in data and 'data' in data['response']:
        records = data['response']['data']
        df = pd.DataFrame(records)
        df['date'] = pd.to_datetime(df['period'])
        df = df[['date', 'value']].rename(columns={'value': column_name})
        return df
    else:
        raise Exception(f"API 오류 발생: {data.get('error', '데이터 없음')}")

# 시리즈 ID 목록
series_ids = {
    'crude_production': 'PET.MCRFPUS2.M',   # 원유 생산량 (월간, 미국)
    'crude_inventory': 'PET.WCESTUS1.W',    # 원유 재고량 (주간, 미국)
    'crude_imports': 'PET.MCRIMUS2.M'       # 원유 수입량 (월간, 미국)
}



def analyze_oil_price_change_causes(
    oil_df, indpro_df,
    saudi_df, us_prod_df, inventory_df, imports_df
): #ism_df
    def to_monthly(df, colname):
        return df.set_index('date').resample('M').mean().rename(columns={colname: f'{colname}_m'})

    dfs = [
        to_monthly(oil_df, 'wti_crude_oil_price'),
        # to_monthly(ism_df, 'ism'),
        to_monthly(indpro_df, 'industrial_production'),
        to_monthly(saudi_df, 'saudi_crude_production'),
        to_monthly(us_prod_df, 'us_crude_production'),
        to_monthly(inventory_df, 'us_crude_inventory'),
        to_monthly(imports_df, 'us_crude_imports')
    ]

    merged = pd.concat(dfs, axis=1).dropna().reset_index()
    recent = merged.tail(2)
    delta = recent.iloc[1, 1:] - recent.iloc[0, 1:]

    analysis = []

    if delta['wti_crude_oil_price_m'] > 0:
        analysis.append(f"📈 유가 상승 감지: +{delta['wti_crude_oil_price_m']:.2f}달러")
        # if delta['ism_m'] > 0:
        #     analysis.append("🔼 ISM PMI 상승 → 제조업 회복 기대")
        if delta['industrial_production_m'] > 0:
            analysis.append("🏭 산업생산 증가 → 에너지 수요 증가 가능성")
        if delta['saudi_crude_production_m'] < 0:
            analysis.append("🇸🇦 사우디 산유량 감소 → 공급 감소")
        if delta['us_crude_production_m'] < 0:
            analysis.append("🇺🇸 미국 산유량 감소 → 공급 감소")
        if delta['us_crude_inventory_m'] < 0:
            analysis.append("📉 원유 재고 감소 → 공급 부족 가능성")
        if delta['us_crude_imports_m'] < 0:
            analysis.append("🛬 수입 감소 → 공급 압박")
    else:
        analysis.append(f"📉 유가 하락 또는 변화 없음: {delta['wti_crude_oil_price_m']:.2f}달러")

    return analysis

def get_UMCSENT_index():
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
        'api_key': API_KEY,
        'file_type': 'json',
        'observation_start': '2000-01-01'
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['observations'])
    df['date'] = pd.to_datetime(df['date'])
    df['umcsent_index'] = pd.to_numeric(df['value'], errors='coerce')
    return df 


def get_forward_pe():
    url = 'https://en.macromicro.me/series/20052/sp500-forward-pe-ratio'

    options = Options()
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)


    try:
        # ✅ 해당 요소가 로드될 때까지 대기 (최대 10초)
        WebDriverWait(driver, 15).until(
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
            "forward_pe": pe_val,
            "df": df
        }
    else:
        raise ValueError("📛 Forward PE 값을 찾을 수 없습니다.")
    

def get_ttm_pe():
    url = "https://ycharts.com/indicators/sp_500_pe_ratio"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)  # JS 로딩 대기

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    # "Last Value" 텍스트가 있는 td 찾기
    for td in soup.select("td.col-6"):
        if "Last Value" in td.get_text(strip=True):
            value_td = td.find_next_sibling("td")
            if value_td:
                return value_td.get_text(strip=True)

    return None


def analyze_pe(forward_pe: float, ttm_pe: float) -> str:
    message = f"📊 S&P 500 Forward PER: {forward_pe:.2f}\n"
    message += f"📊 S&P 500 TTM PER: {ttm_pe:.2f}\n\n"

    # 절대적 고평가/저평가 판단
    if forward_pe > 21:
        message += "⚠️ Forward PER 기준으로 **고평가** 구간입니다.\n"
    elif forward_pe < 17:
        message += "✅ Forward PER 기준으로 **저평가** 구간입니다.\n"
    else:
        message += "⚖️ Forward PER 기준으로 **평균 범위**입니다.\n"

    # TTM 대비 Forward 비교
    if ttm_pe > forward_pe:
        message += "🟢 시장은 **향후 실적 개선**을 기대하는 낙관적인 흐름입니다."
    elif ttm_pe < forward_pe:
        message += "🔴 시장은 **실적 둔화**를 반영하는 보수적인 흐름입니다."
    else:
        message += "⚪ 시장은 현재 실적 수준을 그대로 유지할 것으로 보고 있습니다."

    return message

 


treasury_10years_df = get_10years_treasury_yeild()
treasury_2years_df = get_2years_treasury_yeild()
cpi_df = get_cpi_yoy()
m2_df = get_m2()
m2_yoy = get_m2_yoy()
m2_signal = analyze_m2_investment_signal(m2_df, m2_yoy, cpi_df)
high_yield_spread_df = get_high_yield_spread()
high_yield_warnging = check_high_yield_spread_warning(high_yield_spread_df)
dollar_index = get_dollar_index()
snp_index = get_snp_inedx()
yen_index = get_yen_index()
japan_policy_rate = get_japan_policy_rate()
japan_policy_rate = japan_policy_rate.set_index('date').resample('D').ffill().reset_index()
bull_bear_ratio = get_bull_bear_spread()
bull_bear_warning = analyze_bull_bear_spread(bull_bear_ratio)
equity_put_call_ratio = get_equity_put_call_ratio()
equity_put_call_trend = get_equity_put_call_trend()
equity_put_call_trend_warning = analyze_put_call_ratio_trend(equity_put_call_trend)
equity_put_call_ratio_warning = check_put_call_ratio_warning(equity_put_call_ratio, 'equity')

index_put_call_ratio = get_index_put_call_ratio()
index_put_call_trend = get_index_put_call_trend()
index_put_call_trend_warning = analyze_put_call_ratio_trend(index_put_call_trend)
index_put_call_ratio_warning = check_put_call_ratio_warning(index_put_call_ratio, 'index')

fed_base_interest_rate = get_fed_funds_rate()
vix_index = get_vix_index()
vix_analysis = analyze_vix()
real_rate_and_yield_spread = analyze_real_rate_and_yield_spread()
ecri = get_ECRI()
ecri_trend = analyze_ecri_trend(ecri)
unemployment_rate = get_unemployment_rate()
ism_pmi = get_ism_pmi()

oil_price = get_wti_crude_oil_price()
Indpro_index = get_industrial_production_index()
saudi_oil_production = get_saudi_production()
us_oil_inventory = get_eia_series_v2(series_ids['crude_inventory'], 'us_crude_inventory')
us_oil_production = get_eia_series_v2(series_ids['crude_production'], 'us_crude_production')
us_oil_imports = get_eia_series_v2(series_ids['crude_imports'], 'us_crude_imports')
analyze_oil_price_change = analyze_oil_price_change_causes(oil_price, Indpro_index, saudi_oil_production, us_oil_production, us_oil_inventory, us_oil_imports)
umcsent_index = get_UMCSENT_index()
snp_forward_pe = get_forward_pe()
snp_ttm_pe = float(get_ttm_pe())
evaluate_pe = analyze_pe(snp_forward_pe['forward_pe'], snp_ttm_pe)


## 출력

print("미국 기준 금리")
print(fed_base_interest_rate.tail())

print("미국 10년물 국채금리")
print(treasury_10years_df.tail())

print("미국 2년물 국채금리")
print(treasury_2years_df.tail())

print("미국 CPI 지표")
print(cpi_df.tail())

print("시장 내 유통 통화")
print(m2_df)

print("M2 YoY 증가율")
print(m2_yoy)

print("M2 분석")
print(m2_signal)

print("하이일드 스프레드")
print(high_yield_spread_df)

print("하이일드 경고 및 매수 신호")
print(high_yield_warnging)

print('달러 인덱스')
print(dollar_index)

print('S&P500 지수')
print(snp_index)

print('엔 지수(eft 대체)')
print(yen_index)

print('일본 10년물 국채 금리')
print(japan_policy_rate)

print("bull/bear spread ratio")
print(bull_bear_ratio)

print('bull-bear spread 분석')
print(bull_bear_warning)

print("equity_put/call ratio")
print(equity_put_call_ratio)

print("equity_put/call ratio 추세")
print(equity_put_call_trend)

print("equity_put/call ratio 분석")
print(equity_put_call_trend_warning)

print("index_put/call ratio")
print(index_put_call_ratio)

print("index_put/call ratio 추세")
print(index_put_call_trend)

print("index_put/call ratio 분석")
print(index_put_call_trend_warning)

print("현 시점 index put call ratio 평가")
print(index_put_call_ratio_warning)

print("미국 기준 금리")
print(fed_base_interest_rate)

print("VIX 지수")
print(vix_index)

print("VIX 해석")
print(vix_analysis)

print("실질금리&장단기 금리차로 보는 시장예상")
print(real_rate_and_yield_spread)

print('ECRI 선행지수 및 추세')
print(ecri)

print("실업률")
print(unemployment_rate)

print("ISM 제조업 PMI 지수") # 50 이하일 때 수축 신호 --> 경기 민감 업종 주가에 영향
print(ism_pmi)

print("ECRI 분석")
print(ecri)

print("원유 가격")
print(oil_price)

print("INDPRO 지수")
print(Indpro_index)

print("사우디 산유량")
print(saudi_oil_production)

print("미국 원유 생산량")
print(us_oil_production)

print("유가 변동 분석")
print(analyze_oil_price_change)

print("미시간 소비자 심리지수")
print(umcsent_index)

print("S&P500 포워드 PER")
print(snp_forward_pe)

print("S&P500 현재 PER")
print(snp_ttm_pe)

print("PE 저/고평가 여부")
print(evaluate_pe)


# 시각화 작업
import matplotlib.pyplot as plt

fig, ax1 = plt.subplots()

# 첫 번째 y축: 10년물 국채금리
# color = 'tab:blue'
# ax1.set_xlabel('Date')
# ax1.set_ylabel('10Y Treasury Yield (%)', color=color)
# ax1.plot(treasury_df['date'], treasury_df['value'], color=color, label='10Y Treasury Yield')
# ax1.tick_params(axis='y', labelcolor=color)

# # 두 번째 y축: CPI
# ax2 = ax1.twinx()  # 두 번째 y축 공유
# color = 'tab:orange'
# ax2.set_ylabel('CPI YOY', color=color)
# ax2.plot(cpi_df['date'], cpi_df['CPI YOY(%)'], color=color, label='CPI')
# ax2.tick_params(axis='y', labelcolor=color)

# # 제목과 보여주기
# plt.title('US 10Y Treasury Yield & CPI Trend (Dual Axis)')
# fig.tight_layout()
# plt.show()


