# pages/3_today_signal.py
import streamlit as st
import pandas as pd
import os, sys, importlib
from pathlib import Path

st.set_page_config(page_title="Today's Signal", page_icon="📅", layout="wide")

# repo 루트(mcp) 경로 등록
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# repo 루트(mcp) 경로 등록
sys.path.append(str(Path(__file__).parents[2]))

from macro_crawling import MacroCrawler

# 모듈 강제 리로드 → 최신 코드 반영
# import macro_crawling as mc
# mc = importlib.reload(mc)
# MacroCrawler = mc.MacroCrawler

st.title("📅 Today’s Trading Signal")

# 세션 크롤러 준비 (메서드 없으면 재생성)
if "crawler" not in st.session_state:
    st.session_state.crawler = MacroCrawler()
elif not hasattr(st.session_state.crawler, "get_today_signal_with_m2_and_margin_debt"):
    # 예전 인스턴스(메서드 없음) → 새로 만듦
    st.session_state.crawler = MacroCrawler()

crawler = st.session_state.crawler

# (선택) 디버그: 실제 로드된 파일 경로 확인
# st.caption(f"macro_crawling: {mc.__file__}")

res = crawler.get_today_signal_with_m2_and_margin_debt()

st.subheader("M2/Margin_Debt에 따른 매수/매도 판단")
if res["action"] == "BUY":
    st.success("✅ 오늘 매수")
elif res["action"] == "SELL":
    st.error("⛔ 오늘 매도")
else:
    st.warning("⏸️ 대기")

st.subheader("컨텍스트(오늘 신호가 없으면 최근 발표분)")
st.dataframe(res["details"], use_container_width=True)
st.caption("임계치: z-score : -1.2 미만 + 전월 대비 상승률이 0% 초과일 때 매수 / 전월 대비 하락률이 7% 초과일 때 매도")
nr = res.get("next_release")
if nr:
    st.caption(f"다음 발표: {nr['release_date'].date()} → 주문일: {nr['effective_date'].date()} (예정)")

#--------------

st.subheader("오늘의 Bull-Bear 스프레드 시그널")

sig = crawler.generate_bull_bear_signals()

col1, col2, col3 = st.columns(3)
col1.metric("시그널", f"{sig['icon']} {sig['signal']}")
col2.metric("최근 데이터 수집일", sig["date"])
col3.metric("최근 Spread", f"{sig['spread']:.3f}")

st.write(sig["comment"])
st.caption(f"임계치: Buy<{sig['thresholds']['buy_th']:.2f} / Sell>{sig['thresholds']['sell_th']:.2f}")

#---------------

st.subheader("오늘의 Put-Call Ratio 시그널")

pcr = crawler.decide_equity_pcr_today()

col1, col2, col3 = st.columns(3)
col1.metric("시그널", pcr['signal'][0])
col2.metric("최근 데이터 수집일", pcr['date'][0].strftime('%Y-%m-%d'))
col3.metric("최근 Put-Call Ratio", f"{pcr['equity_value'][0]:.2f}")

st.caption("임계치: 1.5 초과이면 매수 / 0.4 미만이면 매도")

#--------------

st.subheader("이평선 상/하위 비중 분석")

ma_above = crawler.interpret_ma_above_ratio()

# col1, col2, col3, col4 = st.columns(4)
# col1.metric("날짜", ma_above['date'][0])
# col2.metric("시그널", ma_above['signal_50'][0])
# col3.metric("50일 이평선 상위비율", ma_above['50_ma'][0])
# col4.metric("설명", ma_above['comment_50'][0])

# col5, col6, col7, col8 = st.columns(4)
# col5.metric("날짜", ma_above['date'][0])
# col6.metric("시그널", ma_above['signal_200'][0])
# col7.metric("200일 이평선 상위비율", ma_above['200_ma'][0])
# col8.metric("설명", ma_above['comment_200'][0])

# 50일 이평선
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("**날짜**")
    st.write(ma_above['date'][0])
with col2:
    st.markdown("**50일 시그널**")
    st.write(ma_above['signal_50'][0])
with col3:
    st.markdown("**50일 이평선 상위비율**")
    st.write(f"{ma_above['50_ma'][0]:.2f}%")
with col4:
    st.markdown("**설명**")
    st.write(ma_above['comment_50'][0]) # st.write는 글자를 잘라내지 않습니다.

st.markdown("---") # 시각적 구분선 추가

# 200일 이평선
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.markdown("**날짜**")
    st.write(ma_above['date'][0])
with col6:
    st.markdown("**200일 시그널**")
    st.write(ma_above['signal_200'][0])
with col7:
    st.markdown("**200일 이평선 상위비율**")
    st.write(f"{ma_above['200_ma'][0]:.2f}%")
with col8:
    st.markdown("**설명**")
    st.write(ma_above['comment_200'][0]) # st.write는 글자를 잘라내지 않습니다.

#--------------
st.subheader("이평선 이격도 분석")

ma_disparity = crawler.analyze_disparity_with_ma()

# 일자 및 기준 지표
col1, col2 = st.columns(2)
with col1:
    st.markdown("**날짜**")
    st.write(ma_disparity['date'][0])
with col2:
    st.markdown("**S&P500 수치**")
    st.write(ma_disparity['sp500'][0])

# 50일선
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**50일 기준 지수**")
    st.write(ma_disparity['50-day MA'][0])
with col2:
    st.markdown("**50일 이격도**")
    st.write(ma_disparity['50-day disparity (%)'][0])
with col3:
    st.markdown("**설명**")
    st.write(ma_disparity['comment_50'][0]) # st.write는 글자를 잘라내지 않습니다.

st.caption("임계치 : -10% 미만: 매수 / 20% 이상: 매도")

# 200일선
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**200일 기준 지수**")
    st.write(ma_disparity['200-day MA'][0])
with col2:
    st.markdown("**200일 이격도**")
    st.write(ma_disparity['200-day disparity (%)'][0])
with col3:
    st.markdown("**설명**")
    st.write(ma_disparity['comment_200'][0]) # st.write는 글자를 잘라내지 않습니다.

st.caption("임계치 : -10% 미만: 매수 / 20% 이상: 매도")

#--------------
st.subheader("미국선행경기지수 + PMI")

lei_pmi_signal = crawler.decide_today_lei_signal_min()
buy_delta_pp = 0.25

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**오늘 날짜**")
    st.write(lei_pmi_signal["오늘 날짜"])
with c2:
    st.markdown("**시그널**")
    sig = lei_pmi_signal["시그널"]
    st.markdown(":red[**BUY**]" if sig == "BUY" else ":gray[HOLD]")
with c3:
    st.markdown("**데이터 기준일**")
    st.write(lei_pmi_signal["데이터 기준일"])

# 2행
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**미국선행경기지수(LEI)**")
    st.write(lei_pmi_signal["LEI"])
with c2:
    st.markdown("**ISM PMI**")
    st.write(lei_pmi_signal["PMI"])
with c3:
    st.markdown("**6개월간 금리 변동**")
    st.write(lei_pmi_signal["Change_rate"])

st.write(f"임계치 : pmi > 50 + lei > 100 + change_rate : {buy_delta_pp}")


#--------------
ape = crawler.analyze_pe()  # 임계치 바꾸려면 analyze_pe(fwd_buy_lt=16.5, ...) 처럼

c1, c2, c3 = st.columns(3)
with c1:
    st.metric("📅 기준일", ape["date"])
with c2:
    st.metric("TTM P/E", f'{ape["ttm_pe"]:.2f}')
with c3:
    st.metric("Forward P/E", f'{ape["forward_pe"]:.2f}')

st.markdown("---")
st.subheader("🚦 자동 시그널")
st.markdown(f"**{ape['signal']}**")

#with st.expander("규칙과 해석 보기"):
st.markdown(ape["signal_md"])