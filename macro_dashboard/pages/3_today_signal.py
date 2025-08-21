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



st.subheader("오늘의 Bull-Bear 스프레드 시그널")

sig = crawler.generate_bull_bear_signals()

col1, col2, col3 = st.columns(3)
col1.metric("시그널", f"{sig['icon']} {sig['signal']}")
col2.metric("최근 날짜", sig["date"])
col3.metric("최근 Spread", f"{sig['spread']:.3f}")

st.write(sig["comment"])
st.caption(f"임계치: Buy<{sig['thresholds']['buy_th']:.2f} / Sell>{sig['thresholds']['sell_th']:.2f}")