import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import sys
import os

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
def draw_abs_chart(df, value_col: str, title: str, color: str, ylabel: str):
    fig, ax = plt.subplots(figsize=(4, 3))

    # 시계열 데이터 그리기
    ax.plot(df['date'], df[value_col], color=color)

    # 마지막 값 구하기
    last_date = df['date'].iloc[-1]
    last_value = df[value_col].iloc[-1]

    # 마지막 값에 숫자 표기
    ax.text(
        last_date, last_value,
        f"{last_value:,.0f}",  # 천 단위 콤마, 소수점 없이
        fontsize=13,
        color=color,
        ha='left',
        va='bottom'
    )

    ax.set_title(title)
    ax.set_ylabel(ylabel)  # ← y축 단위 받아서 표시
    ax.grid(True)
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
    st.write("월별 데이터, 1개월 지연 발표")

with col2:
    st.subheader("🟧 2년물 금리")
    st.pyplot(draw_yield_chart(df_2y, 'value', '2Y Yield', 'orange'))
    st.write("월별 데이터, 1개월 지연 발표")

with col3:
    st.subheader("🟥 기준금리")
    st.pyplot(draw_yield_chart(df_fed, 'fed_funds_rate', 'Fed Funds Rate', 'red'))

# 🔳 시각화 (2행 2열)
col1, col2 = st.columns(2)
with col1:
    st.subheader("🟩 실질 금리")
    st.pyplot(draw_yield_chart(real_rate, 'value', 'Real Yield', 'green'))

with col2:
    st.subheader("🟨 CPI Index")
    st.pyplot(draw_yield_chart(df_cpi, 'CPI YOY(%)', 'CPI Index', 'yellow'))

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

with col2:
    st.subheader("🟪 Margin Debt")
    st.pyplot(draw_abs_chart(
        md_df, 'margin_debt', 'Margin Debt', 'purple', '단위: USD (Million)'
    ))


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

with col2:
    st.subheader("💴 Yen Index")
    st.pyplot(draw_abs_chart(
        yen_index, 'value', 'Yen Index', 'orange', 'Index'
    ))

with col3:
    st.subheader("💶 Euro Index")
    st.pyplot(draw_abs_chart(
        euro_index, 'value', 'Euro Index', 'blue', 'Index'
    ))


col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🟠 Copper Price")
    st.pyplot(draw_abs_chart(
        copper_price, 'value', 'Copper Price', 'orange', 'Price'
    ))

with col2:
    st.subheader("🪙 Gold Price")
    st.pyplot(draw_abs_chart(
        gold_price, 'value', 'Gold Price', 'yellow', 'Price'
    ))

with col3:
    st.subheader("🛢️ Oil Price")
    st.pyplot(draw_abs_chart(
        oil_price, 'value', 'Gold Price', 'black', 'Price'
    ))