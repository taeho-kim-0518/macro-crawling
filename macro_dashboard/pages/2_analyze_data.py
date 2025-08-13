import streamlit as st
import matplotlib.pyplot as plt
import os
import time
from dateutil.relativedelta import relativedelta
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import seaborn as sns
from scipy.stats import linregress
from io import StringIO
import sys

# 🔧 상위 폴더의 macro_crawling 모듈 임포트 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from macro_crawling import MacroCrawler

# ✅ 실행 환경에 따라 MacroCrawler 인스턴스 처리
if __name__ == "__main__":
    crawler = MacroCrawler()
else:
    crawler = st.session_state.crawler

merge_m2_md_df = crawler.merge_m2_margin_sp500_abs()

st.subheader("S&P500 + Margin Debt/M2 + Signals")
m2_md_fig = crawler.plot_sp500_with_signals_and_graph()

st.pyplot(m2_md_fig)
plt.close(m2_md_fig)  # 렌더 후 닫기(옵션)