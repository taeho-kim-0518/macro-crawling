# streamlit_app.py 상단에 추가
import streamlit as st
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from macro_crawling import MacroCrawler

# ✅ 한 번만 인스턴스 생성
if "crawler" not in st.session_state:
    st.session_state.crawler = MacroCrawler()

st.title("📊 메인 대시보드")
st.write("왼쪽 메뉴에서 원하는 페이지를 선택하세요.")