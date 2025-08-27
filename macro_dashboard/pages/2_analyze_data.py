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

# =========================
# Bull Bear Spread
# =========================

st.subheader("Bull-Bear Spread")

fig, ax, events_df = crawler.plot_snp_with_bull_bear_signals_from_crawler(
    buy_th=-0.2,
    sell_th=0.4,
)

st.pyplot(fig, use_container_width=True)

# ➜ 이벤트 표 렌더 (이 줄이 없어서 안 보였던 것)
if events_df is not None and not events_df.empty:
    st.dataframe(events_df, use_container_width=True)
else:
    st.info("표시할 이벤트가 없습니다. 임계치/기간을 조정해 보세요.")

st.write("Bull-Bear Spread에 따른 주식 매수/매도 시그널")
st.write("데이터가 2024년 9월부터 존재")
st.write("지표가 -0.2 미만일 경우 매수")
st.write("지표가 0.4 초과일 경우 매도")

# =========================
# Put Call Ratio
# =========================

st.subheader("Put-Call Ratio")

fig, signals_df = crawler.plot_sp500_with_pcr_signals()

st.pyplot(fig, use_container_width=True)

# ➜ 이벤트 표 렌더 (이 줄이 없어서 안 보였던 것)
if signals_df is not None and not events_df.empty:
    st.dataframe(signals_df, use_container_width=True)
else:
    st.info("표시할 이벤트가 없습니다. 임계치/기간을 조정해 보세요.")

st.write("Put-Call Ratio에 따른 주식 매수/매도 시그널")
st.write("데이터가 2025-05-15부터 존재")
st.write("지표가 1.5 초과일 경우 매수")
st.write("지표가 0.4 미만일 경우 매도")

# =========================
# LEI & PMI
# =========================
st.subheader("LEI & PMI 지표(매수신호)")

fig, signals = crawler.plot_sp500_with_lei_signals()

st.pyplot(fig, use_container_width=True)

# ➜ 이벤트 표 렌더 (이 줄이 없어서 안 보였던 것)
if signals is not None and not events_df.empty:
    st.dataframe(signals, use_container_width=True)
else:
    st.info("표시할 이벤트가 없습니다. 임계치/기간을 조정해 보세요.")

st.write("REI & PMI에 따른 주식 매수 시그널")
st.write("6개월 금리 변화 임계값 (매수) : ≥ +0.25%p + PMI > 50 + 미국선행경기지수 > 100")
st.write("2015-08-01 부터 데이터 존재")