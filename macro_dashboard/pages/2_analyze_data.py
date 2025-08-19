import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
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

# Streamlit Cloud 환경에 맞게 절대 경로 설정
# 현재 프로젝트의 루트 디렉토리는 /mount/src/macro-crawling 입니다.
# 따라서 폰트 폴더는 /mount/src/macro-crawling/fonts 에 위치합니다.
font_folder = '/mount/src/macro-crawling/fonts'

# 폰트 파일이 있는지 확인하고 설정
font_path = None
for filename in os.listdir(font_folder):
    if filename.endswith('.ttf') or filename.endswith('.otf'):
        font_path = os.path.join(font_folder, filename)
        break

if font_path and os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    plt.rc('font', family=font_name)
    
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

merge_m2_md_df = crawler.merge_m2_margin_sp500_abs()

st.subheader("S&P500 + Margin Debt/M2 + Signals")
m2_md_fig = crawler.plot_sp500_with_signals_and_graph()

st.pyplot(m2_md_fig)
plt.close(m2_md_fig)  # 렌더 후 닫기(옵션)