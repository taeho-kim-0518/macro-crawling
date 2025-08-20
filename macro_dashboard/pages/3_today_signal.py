# pages/3_today_signal.py
import streamlit as st
import pandas as pd
import os, sys
from datetime import datetime

# 상위 폴더의 macro_crawling 모듈 경로 추가 (repo 구조: mcp/macro_dashboard/pages/this_file.py)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from macro_crawling import MacroCrawler

# Streamlit 앱 시작
st.set_page_config(page_title="Today's Signal", page_icon="📅", layout="wide")

# 세션 크롤러 준비
if "crawler" not in st.session_state or st.session_state.crawler is None:
    st.session_state.crawler = MacroCrawler()
crawler = st.session_state.crawler

st.title("📅 Today’s Trading Signal")

res = crawler.get_today_signal_with_m2_and_margin_debt()

st.subheader("오늘 주문 판단")
if res["action"] == "BUY":
    st.success("✅ 오늘 매수")
elif res["action"] == "SELL":
    st.error("⛔ 오늘 매도")
else:
    st.warning("⏸️ 대기")

st.subheader("컨텍스트(오늘 신호가 없으면 최근 발표분)")
st.dataframe(res["details"], use_container_width=True)

nr = res.get("next_release")
if nr:
    st.caption(f"다음 발표: {nr['release_date'].date()} → 주문일: {nr['effective_date'].date()} (예정)")