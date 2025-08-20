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