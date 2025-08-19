import streamlit as st
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
import sys
import os

# 폰트 설정 (기존 코드)
plt.rc('font', family='NanumGothic') # 또는 'NanumGothic', 'AppleGothic' (Mac)

# 폰트 설정 (수정 코드)
# 폰트 폴더 경로 설정 (프로젝트 루트의 'fonts' 폴더)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
font_folder = os.path.join(PROJECT_ROOT, 'fonts')

# 폰트 폴더에서 .ttf 파일 찾기
font_path = None
for filename in os.listdir(font_folder):
    if filename.endswith('.ttf') or filename.endswith('.otf'):
        font_path = os.path.join(font_folder, filename)
        break

if font_path and os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    plt.rc('font', family=fm.FontProperties(fname=font_path).get_name())
    
# Matplotlib에서 '-' 기호 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False


# 🔧 상위 폴더의 macro_crawling 모듈 임포트 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from macro_crawling import MacroCrawler

# ✅ 실행 환경에 따라 MacroCrawler 인스턴스 처리
if __name__ == "__main__":
    crawler = MacroCrawler()
else:
    crawler = st.session_state.crawler

# 📌 시각화 함수 정의
def draw_yield_chart(df, value_col: str, title: str, color: str):
    fig, ax = plt.subplots(figsize=(4, 3))

    # 시계열 데이터 그리기
    ax.plot(df['date'], df[value_col], color=color)

    # 마지막 값 구하기
    last_date = df['date'].iloc[-1]
    last_value = df[value_col].iloc[-1]

    # 마지막 값에 숫자 표기
    ax.text(
        last_date, last_value,
        f"{last_value:.2f}%",  # 소수점 2자리
        fontsize=13,
        color=color,
        ha='left',
        va='bottom'
    )

    ax.set_title(title)
    ax.set_ylabel('%')
    ax.grid(True)
    return fig

# 📌 시각화 함수 정의
def draw_abs_chart(
    df, value_col: str, title: str, color: str, ylabel: str,
    y_pad_ratio: float = 0.08,        # y축 위/아래 여유 비율(8%)
    y_clamp: tuple | None = None      # (ymin, ymax) 강제 범위가 필요할 때만 사용
):
    # 원본 변형 방지
    df_local = df.copy()

     # 날짜 컬럼 자동 탐지
    candidates = ['date', 'Date', 'Month/Year', 'month_year', 'MonthYear']
    date_col = next((c for c in candidates if c in df_local.columns), None)
    if date_col is None:
        # datetime/period 타입 자동 감지
        for c in df_local.columns:
            if pd.api.types.is_datetime64_any_dtype(df_local[c]) or pd.api.types.is_period_dtype(df_local[c]):
                date_col = c
                break
    if date_col is None:
        # 이름에 date/month/year 포함된 컬럼 탐색(최후)
        for c in df_local.columns:
            lc = c.lower()
            if 'date' in lc or ('month' in lc and 'year' in lc):
                date_col = c
                break
    if date_col is None:
        raise KeyError(f"날짜 컬럼을 찾을 수 없습니다. ('date' 또는 'Month/Year' 필요). 현재 컬럼: {list(df_local.columns)}")
    
    # 날짜 형 변환
    if pd.api.types.is_period_dtype(df_local[date_col]):
        df_local[date_col] = df_local[date_col].dt.to_timestamp()
    elif not pd.api.types.is_datetime64_any_dtype(df_local[date_col]):
        df_local[date_col] = pd.to_datetime(df_local[date_col], errors='coerce')

    fig, ax = plt.subplots(figsize=(4, 3))

    # 시계열 라인
    ax.plot(df_local[date_col], df_local[value_col], color=color)

    # 마지막 값 라벨(검정)
    last_date = df_local[date_col].iloc[-1]
    last_value = df_local[value_col].iloc[-1]
    ax.text(
        last_date, last_value,
        f"{last_value:,.0f}",
        fontsize=20,
        color='black',
        ha='left',
        va='bottom'
    )

    # === y축 자동 범위 (변화 보이도록) ===
    series = pd.to_numeric(df[value_col], errors='coerce').dropna()
    if len(series) > 0:
        ymin, ymax = float(series.min()), float(series.max())

        # 값이 모두 같은 경우 대비
        if np.isclose(ymax, ymin):
            bump = max(1.0, abs(ymax) * 0.02)  # 최소 1, 값의 2%
            ymin, ymax = ymin - bump, ymax + bump

        pad = (ymax - ymin) * y_pad_ratio
        auto_ymin, auto_ymax = ymin - pad, ymax + pad

        if y_clamp is not None and all(v is not None for v in y_clamp):
            ax.set_ylim(y_clamp[0], y_clamp[1])
        else:
            ax.set_ylim(auto_ymin, auto_ymax)

    # 타이틀/라벨
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True)
    fig.tight_layout()
    return fig

# ✅ Streamlit 제목
st.title("📂 원시 데이터 보기")
st.header("📊 미국 금리 시각화 대시보드")

# ⬇️ 금리 관련 데이터 로딩
df_10y = crawler.get_10years_treasury_yeild()
df_10y['date'] = df_10y['date'].dt.to_period('M').dt.to_timestamp()

df_2y = crawler.get_2years_treasury_yeild()
df_2y['date'] = df_2y['date'].dt.to_period('M').dt.to_timestamp()

df_fed = crawler.get_fed_funds_rate()
df_fed['date'] = df_fed['date'].dt.to_period('M').dt.to_timestamp()

# ⬇️ 실질 금리 계산 및 출력 (Series → DataFrame)
real_rate = pd.DataFrame({
    "date": df_10y["date"],
    "value": df_10y["value"] - df_2y["value"]
})


# ⬇️ CPI YoY
df_cpi = crawler.get_cpi_yoy()
df_cpi['date'] = df_cpi['date'].dt.to_period('M').dt.to_timestamp()


# 🔳 시각화 (1행 3열)
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("🟦 10년물 금리")
    st.pyplot(draw_yield_chart(df_10y, 'value', '10Y Yield', 'blue'))
    st.write("월별 데이터, 1개월 지연 데이터")

with col2:
    st.subheader("🟧 2년물 금리")
    st.pyplot(draw_yield_chart(df_2y, 'value', '2Y Yield', 'orange'))
    st.write("월별 데이터, 1개월 지연 데이터")

with col3:
    st.subheader("🟥 기준금리")
    st.pyplot(draw_yield_chart(df_fed, 'fed_funds_rate', 'Fed Funds Rate', 'red'))
    st.write("월별 데이터, 1개월 지연 데이터")

# 🔳 시각화 (2행 2열)
col1, col2 = st.columns(2)
with col1:
    st.subheader("🟩 실질 금리")
    st.pyplot(draw_yield_chart(real_rate, 'value', 'Real Yield', 'green'))
    st.write("월별 데이터, 1개월 지연 데이터")

with col2:
    st.subheader("🟨 CPI Index")
    st.pyplot(draw_yield_chart(df_cpi, 'CPI YOY(%)', 'CPI Index', 'yellow'))
    st.write("월별 데이터, 1개월 지연 데이터")

# ────────────────────────────────
st.markdown("---")
st.header("💵 유동성 지표 (M2, Margin Debt)")

# ⬇️ M2
m2_df = crawler.get_m2()
m2_df['date'] = pd.to_datetime(m2_df['date'])
m2_df['value'] = pd.to_numeric(m2_df['value'], errors='coerce')

# ⬇️ Margin Debt
md_df = pd.read_csv("md_df.csv")
md_df['date'] = pd.to_datetime(md_df['Month/Year'], format='mixed', errors='coerce')
md_df['margin_debt'] = (
    md_df["Debit Balances in Customers' Securities Margin Accounts"]
    .astype(str)
    .str.replace(",", "", regex=False)
    .astype(float)
)

# 🔳 시각화 (1행 2열)
col1, col2 = st.columns(2)

with col1:
    st.subheader("🟩 M2 Index")
    st.pyplot(draw_abs_chart(
        m2_df, 'value', 'M2 Index', 'green', '단위: USD (Billion)'
    ))
    st.write("매월 25일 발표 데이터, 1개월 지연 데이터")

with col2:
    st.subheader("🟪 Margin Debt")
    st.pyplot(draw_abs_chart(
        md_df, 'margin_debt', 'Margin Debt', 'purple', '단위: USD (Million)'
    ))
    st.write("매월 25일 발표 데이터, 1개월 지연 데이터")


# ────────────────────────────────
st.markdown("---")
st.header("💰 통화 및 가격 지표")

dollar_index = crawler.get_dollar_index()
yen_index = crawler.get_yen_index()
euro_index = crawler.get_euro_index()
copper_price = crawler.get_copper_price_F()
gold_price = crawler.get_gold_price_F()
oil_price = crawler.get_oil_price_F()


# if __name__ == "__main__" :
#     print("Copper DF", copper_price)

dollar_index['date'] = pd.to_datetime(dollar_index['date'])
dollar_index['value'] = pd.to_numeric(dollar_index['value'], errors='coerce')

yen_index['date'] = pd.to_datetime(yen_index['date'])
yen_index['value'] = pd.to_numeric(yen_index['value'], errors= 'coerce')

euro_index['date'] = pd.to_datetime(euro_index['date'])
euro_index['value'] = pd.to_numeric(euro_index['value'])

copper_price['date'] = pd.to_datetime(copper_price['Date'])
copper_price['value'] = pd.to_numeric(copper_price['Close'], errors='coerce')

gold_price['date'] = pd.to_datetime(gold_price['Date'])
gold_price['value'] = pd.to_numeric(gold_price['Close'], errors='coerce')

oil_price['date'] = pd.to_datetime(oil_price['Date'])
oil_price['value'] = pd.to_numeric(oil_price['Close'], errors='coerce')

# 🔳 시각화 (1행 3열)
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("💵 Dollar Index")
    st.pyplot(draw_abs_chart(
        dollar_index, 'value', 'Dollar Index', 'green', 'Index'
    ))
    st.write("실시간 일별데이터")


with col2:
    st.subheader("💴 Yen Index")
    st.pyplot(draw_abs_chart(
        yen_index, 'value', 'Yen Index', 'orange', 'Index'
    ))
    st.write("실시간 일별데이터")

with col3:
    st.subheader("💶 Euro Index")
    st.pyplot(draw_abs_chart(
        euro_index, 'value', 'Euro Index', 'blue', 'Index'
    ))
    st.write("실시간 일별데이터")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🟠 Copper_F")
    st.pyplot(draw_abs_chart(
        copper_price, 'value', 'Copper Price', 'orange', 'Price'
    ))
    st.write("구리 선물 가격")
    st.write("실시간 일별데이터")
    

with col2:
    st.subheader("🪙 Gold_F")
    st.pyplot(draw_abs_chart(
        gold_price, 'value', 'Gold Price', 'yellow', 'Price'
    ))
    st.write("금 선물 가격")
    st.write("실시간 일별데이터")

with col3:
    st.subheader("🛢️ Oil_F")
    st.pyplot(draw_abs_chart(
        oil_price, 'value', 'Gold Price', 'black', 'Price'
    ))
    st.write("원유 선물 가격")
    st.write("실시간 일별데이터")

    # ────────────────────────────────
st.markdown("---")
st.header("📈 기타 경제 지표")

unemployment_rate = crawler.get_unemployment_rate() # date, unemployment_rate
pmi_index = pd.read_csv("pmi_data.csv") # date, PMI
UMCSENT_index = crawler.get_UMCSENT_index() # date umcsent_index

vix_index = crawler.get_vix_index() # date, vix_index
put_call_ratio = pd.read_csv("put_call_ratio.csv") # date, equity_value, index_value 
ncfi_data = crawler.get_nfci() # date, NFCI_index

high_yeild_spread = crawler.get_high_yield_spread() # date, value
bull_bear_spread = pd.read_csv("bull_bear_spread.csv") # date, spread

if __name__ == "__main__" :
    print("Copper DF", pmi_index)


# 🔳 시각화 (1행 3열)
col1, col2 = st.columns(2)
with col1:
    st.subheader("🚨 VIX")
    st.pyplot(draw_abs_chart(
        vix_index, 'vix_index', 'VIX', 'green', 'Index'
    ))
    st.write("실시간 일별데이터")

with col2:
    st.subheader("🧾 PMI Index")
    st.pyplot(draw_abs_chart(
        pmi_index, 'PMI', 'PMI Index', 'orange', 'Index'
    ))
    st.write("월별 데이터, 1개월 지연 데이터")

# 🔳 시각화 (1행 3열)
col1, col2 = st.columns(2)
with col1:
    st.subheader("🧑‍💻 소비자심리")
    st.pyplot(draw_abs_chart(
        UMCSENT_index, 'umcsent_index', 'UMCSENT Index', 'blue', 'Index'
    ))
    st.write("매월 25일 발표 데이터, 1개월 지연 데이터")

with col2:
    st.subheader("🧑‍💻 국제금융지수")
    st.pyplot(draw_abs_chart(
        ncfi_data, 'NFCI_index', 'NFCI Index', 'orange', 'Index'
    ))
    st.write("주별 데이터")


# 🔳 시각화 (1행 3열)
col1, col2 = st.columns(2)

with col1:
    st.subheader("✂️ 실업률")
    st.pyplot(draw_yield_chart(
        unemployment_rate, 'unemployment_rate', '실업률', 'green'
    ))
    st.write("월별 데이터, 1개월 지연 데이터")

with col2:
    st.subheader("🧾 PutCall R")
    st.pyplot(draw_yield_chart(
        put_call_ratio, 'equity_value', 'PutCall Ratio', 'blue'
    ))
    st.write("실시간 일별데이터")




    # 🔳 시각화 (1행 3열)
col1, col2 = st.columns(2)
with col1:
    st.subheader("📉 하이일드 SP")
    st.pyplot(draw_yield_chart(
        high_yeild_spread, 'value', '하이일드 스프레드', 'blue'
    ))
    st.write("실시간 일별데이터")

with col2:
    st.subheader("⏳ Bull-Bear")
    st.pyplot(draw_yield_chart(
        bull_bear_spread, 'spread', 'Bull_Bear 스프레드', 'purple'
    ))
    st.write("주별 데이터")