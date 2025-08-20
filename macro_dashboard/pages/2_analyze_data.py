import streamlit as st
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
import platform

# Streamlit Cloud 환경에 맞게 절대 경로 설정
# 현재 프로젝트의 루트 디렉토리는 /mount/src/macro-crawling 입니다.
# 따라서 폰트 폴더는 /mount/src/macro-crawling/fonts 에 위치합니다.
# font_folder = '/mount/src/macro-crawling/fonts'

# # 폰트 파일이 있는지 확인하고 설정
# font_path = None
# for filename in os.listdir(font_folder):
#     if filename.endswith('.ttf') or filename.endswith('.otf'):
#         font_path = os.path.join(font_folder, filename)
#         break

# if font_path and os.path.exists(font_path):
#     fm.fontManager.addfont(font_path)
#     font_name = fm.FontProperties(fname=font_path).get_name()
#     plt.rc('font', family=font_name)
    
# # Matplotlib에서 '-' 기호 깨짐 방지
# plt.rcParams['axes.unicode_minus'] = False
# =========================
# 폰트 설정 (로컬/배포 겸용)
# =========================
def setup_font():
    candidate_dirs = []

    # 1) 환경변수 우선
    env_dir = os.environ.get("FONT_DIR")
    if env_dir:
        candidate_dirs.append(Path(env_dir))

    # 2) 리포 루트 기준 폴더 탐색 (현재 파일: mcp/macro_dashboard/pages/1_raw_data.py)
    here = Path(__file__).resolve()
    repo_root = here.parents[2]  # mcp
    macro_dashboard = here.parents[1]  # mcp/macro_dashboard
    candidate_dirs += [
        repo_root / "fonts",              # mcp/fonts
        macro_dashboard / "fonts",        # mcp/macro_dashboard/fonts (있다면)
    ]

    # 3) 배포 절대 경로(있을 때만)
    candidate_dirs.append(Path("/mount/src/macro-crawling/fonts"))

    # 실제 존재하는 폴더만
    valid_dirs = [p for p in candidate_dirs if p.exists()]

    # 폰트 등록
    chosen = None
    registered = []
    for d in valid_dirs:
        files = []
        files += list(d.glob("*.ttf"))
        files += list(d.glob("*.otf"))
        for f in files:
            fm.fontManager.addfont(str(f))
            registered.append(f)

    if registered:
        # 선호 순위: 나눔/노토/맑은고딕 계열 → 첫 번째
        preferred_keywords = ["Nanum", "Noto Sans CJK KR", "Noto Sans KR", "Malgun", "Apple SD Gothic"]
        names = []
        for f in registered:
            try:
                n = fm.FontProperties(fname=str(f)).get_name()
                if n:
                    names.append((n, f))
            except Exception:
                pass

        # 키워드 우선 선택
        for kw in preferred_keywords:
            for n, f in names:
                if kw.lower() in n.lower():
                    chosen = n
                    break
            if chosen:
                break

        # 없으면 첫 번째
        if not chosen and names:
            chosen = names[0][0]

    # 폰트 하나도 못 찾으면 시스템 기본 폴백
    if not chosen:
        sysname = platform.system()
        if sysname == "Windows":
            chosen = "Malgun Gothic"
        elif sysname == "Darwin":
            chosen = "Apple SD Gothic Neo"
        else:
            chosen = "Noto Sans CJK KR"  # 설치돼 있으면 적용됨

    mpl.rcParams["font.family"] = chosen
    mpl.rcParams["axes.unicode_minus"] = False  # '-' 깨짐 방지
    return chosen

selected_font = setup_font()
# st.write(f"Using font: {selected_font}")  # 디버깅시 켜기

# 🔧 상위 폴더의 macro_crawling 모듈 임포트 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from macro_crawling import MacroCrawler

# ✅ 실행 환경에 따라 MacroCrawler 인스턴스 처리 (세션에 없으면 생성)
if "crawler" not in st.session_state or st.session_state.crawler is None:
    try:
        st.session_state.crawler = MacroCrawler()
    except Exception as e:
        st.error(f"MacroCrawler 초기화 실패: {e}")
        st.stop()
crawler = st.session_state.crawler


# 🔧 상위 폴더의 macro_crawling 모듈 임포트 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from macro_crawling import MacroCrawler

# ✅ 실행 환경에 따라 MacroCrawler 인스턴스 처리
if __name__ == "__main__":
    crawler = MacroCrawler()
else:
    crawler = st.session_state.crawler


# =========================
# 화면 구성 시작
# =========================

merge_m2_md_df = crawler.merge_m2_margin_sp500_abs()

st.subheader("S&P500 + Margin Debt/M2 + Signals")
fig, ax, signals = crawler.plot_sp500_with_signals_and_graph()

# 그래프 렌더
st.pyplot(fig, use_container_width=True)

st.write("유통 통화량 중 부채비율에 따른 주식 매수/매도 시그널")
st.write("Z-score의 값이 -1.2 미만이고, 전월 대비 상승률이 0% 초과일 경우 매수")
st.write("전월 대비 하락률이 7% 초과일 경우 매도")

# 시그널 테이블 표시
st.dataframe(signals)

# 렌더 후 닫기 (원하면)
plt.close(fig)