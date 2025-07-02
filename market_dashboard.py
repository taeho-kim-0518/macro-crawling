import streamlit as st
import pandas as pd
import altair as alt

# 배포 url : https://macro-dashboard001.streamlit.app/

# 👉 data_collect.py에 있는 함수와 결과값 import
from create_API_file import (
    get_10years_treasury_yeild,
    get_2years_treasury_yeild,
    get_cpi_yoy,
    get_m2,
    get_m2_yoy,
    analyze_m2_investment_signal,
    get_high_yield_spread,
    check_high_yield_spread_warning,
    get_dollar_index,
    get_snp_inedx,
    get_yen_index,
    get_japan_policy_rate,
    get_bull_bear_spread,
    analyze_bull_bear_spread,
    get_equity_put_call_ratio,
    get_equity_put_call_trend,
    get_index_put_call_ratio,
    get_index_put_call_trend,
    analyze_put_call_ratio_trend,
    check_put_call_ratio_warning,
    get_fed_funds_rate,
    get_vix_index,
    analyze_vix,
    analyze_real_rate_and_yield_spread,
    get_ECRI,
    analyze_ecri_trend,
    get_unemployment_rate,
    get_ism_pmi,
    get_wti_crude_oil_price,
    get_industrial_production_index,
    get_saudi_production,
    get_eia_series_v2,
    analyze_oil_price_change_causes,
    get_UMCSENT_index,
    get_forward_pe,
    get_ttm_pe,
    analyze_pe
)

st.set_page_config(page_title="📊 Macro Dashboard", layout="wide")

st.title("📊 미국 거시경제 지표 대시보드")
st.markdown("자동 수집된 최신 데이터 기반 분석")

# -------- 금리 관련 시각화 --------
st.header("📌 금리 관련")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🔹 10년물 국채 금리")
    df_10y = get_10years_treasury_yeild()
    st.line_chart(df_10y.set_index("date")["value"])

with col2:
    st.subheader("🔹 2년물 국채 금리")
    df_2y = get_2years_treasury_yeild()
    st.line_chart(df_2y.set_index("date")["value"])

with col3:
    st.subheader("🔹 FED 기준 금리")
    df_fy = get_fed_funds_rate()
    df_fy = df_fy.set_index("date").reset_index()

    chart = alt.Chart(df_fy).mark_line().encode(
        x='date:T',
        y=alt.Y('value:Q', scale=alt.Scale(domain=[0, 7]))
    ).properties(
        width='container',
        height=400
    )

    st.altair_chart(chart, use_container_width=True)


st.subheader("🔍 실질금리 & 장단기 금리차 분석")
st.code(analyze_real_rate_and_yield_spread())

# -------- CPI --------
st.header("📌 인플레이션 (CPI YoY)")
df_cpi = get_cpi_yoy()
st.line_chart(df_cpi.set_index("date")["CPI YOY(%)"])

# -------- M2 ---------
st.header("통화량 지표")
m2 = get_m2()
m2_trend = get_m2_yoy()
m2_signal = analyze_m2_investment_signal(m2, m2_trend, df_cpi)
st.code(m2_signal)
st.markdown("m2_yoy > 5'%' and cpi_yoy < 3% : 🟢 유동성 풍부 + 인플레 안정")
st.markdown("m2_yoy < 2'%' and cpi_yoy > 4% < : 🟠 인플레 고조 + 유동성 정체")
st.markdown('m2_yoy < 0 : 🔴 유동성 축소 (QT) 경고 / 그 외 : ⚪ 중립 국면 → **추가 확인 필요** (실업률, 금리, PER 등과 종합 고려)')

# ✅ 최신 값과 변화율 시각화 카드로 추가 표시
latest_m2 = m2.iloc[-1]
prev_m2 = m2.iloc[-8]

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📅 최근 M2 날짜", latest_m2["date"].strftime("%Y-%m-%d"))

with col2:
    st.metric("💵 최근 M2", f"{latest_m2['value']:,.2f}")

with col3:
    m2_change = latest_m2['value'] - prev_m2['value']
    m2_change_pct = (m2_change / prev_m2['value']) * 100
    st.metric("📊 8주 대비 M2 증감률", f"{m2_change_pct:.2f}%", delta=f"{m2_change:+,.2f}")

# ---- High Yield Spread ----
st.header("하이일드 스프레드 지표")
hy_spread = get_high_yield_spread()
hy_signal = check_high_yield_spread_warning(hy_spread)
st.code(hy_signal)

st.markdown("### 📊 하이일드 스프레드 투자 해석 기준")

st.markdown("""
| 스프레드 수준 | 해석 | 투자 판단 |
|---------------|------|------------|
| **7% 이상** | 극심한 공포, 유동성 경색 가능성 | 🚨 **위기 가능성 (현금 비중↑)**<br>🟢 **단, 역발상 매수 진입 고려 가능** |
| **5~7%** | 위험 회피 구간, 조정 가능성 | ⚠️ **방어적 포트폴리오 유지**<br>🔍 **추가 하락 여부 관찰** |
| **3~5%** | 중립~낙관 혼재 | ⚪ **시장 안정화 구간, 방향 모호** |
| **3% 이하** | 시장 낙관 극대화 | 🔴 **과열 구간, 일부 이익 실현 고려** |
""", unsafe_allow_html=True)

# ---- Bull Bear Spread ----
st.header("bull-bear 스프레드")
bull_bear_spread = get_bull_bear_spread()
bull_bear_signal = analyze_bull_bear_spread(bull_bear_spread)
st.code(bull_bear_signal)
st.markdown('🟢 -20% 미만일 시 매수 타이밍. 그 외 중립 국면 → **추가 확인 필요**')


# ---- Put Call Ratio 분석 ----
st.header("Pull-Call Ratio 분석")
# 📊 지표 값 불러오기
equity_ratio_raw = get_equity_put_call_ratio()
index_ratio_raw = get_index_put_call_ratio()

# ⚠️ 문자열 처리 (% 제거 등은 필요 없음 – 이미 float 값으로 오는 것으로 가정)
equity_ratio = float(equity_ratio_raw)
index_ratio = float(index_ratio_raw)

# 📈 추이 데이터
equity_trend_df = get_equity_put_call_trend()
index_trend_df = get_index_put_call_trend()

# 🔍 추세 분석
equity_trend_analysis = analyze_put_call_ratio_trend(equity_trend_df)
index_trend_analysis = analyze_put_call_ratio_trend(index_trend_df)

# 📌 시그널 해석
equity_signal = check_put_call_ratio_warning(equity_ratio, "equity")
index_signal = check_put_call_ratio_warning(index_ratio, "index")

st.subheader("🟩 Equity Put/Call Ratio")
col1, col2 = st.columns(2)

with col1:
    st.metric("현재값", f"{equity_ratio:.2f}")
    st.code(check_put_call_ratio_warning(equity_ratio, "equity"))
    st.code(equity_trend_analysis)
    st.markdown("ℹ️ **해석 기준**: `1 이상`이면 공포 심리 과도 → 매수 시점, `0.7 미만`이면 과열 상태 → 주의 필요")

with col2:
    st.markdown("📈 **최근 20일 추이**")
    st.line_chart(equity_trend_df.set_index("date")["value"])

st.divider()

# === Index Put/Call Ratio ===
st.subheader("🟦 Index Put/Call Ratio")

col3, col4 = st.columns(2)

with col3:
    st.metric("현재값", f"{index_ratio:.2f}")
    st.code(check_put_call_ratio_warning(index_ratio, "index"))
    st.code(index_trend_analysis)
    st.markdown("ℹ️ **해석 기준**: `1.5 이상`이면 공포 심리 과도 → 매수 시점, `0.7 미만`이면 과열 상태 → 주의 필요")

with col4:
    st.markdown("📈 **최근 20일 추이**")
    st.line_chart(index_trend_df.set_index("date")["value"])

# ------- VIX --------
st.header("📌 VIX 분석")
vix_index = get_vix_index()
vix_analysis = analyze_vix()
st.code(vix_analysis)

# -------- PER --------
st.header("📌 S&P 500 PER 분석")
forward_pe = get_forward_pe()
ttm_pe = float(get_ttm_pe())
st.code(analyze_pe(forward_pe["forward_pe"], ttm_pe))

# Footer
st.markdown("---")
st.caption("Made with ❤️ by Streamlit. Data from FRED, YCharts, MacroMicro, and more.")
