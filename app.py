import streamlit as st
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import random
from bs4 import BeautifulSoup

# --------- 셀레니움 드라이버 초기화 ---------
def init_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")  # 디버깅 시 주석
    driver = webdriver.Chrome(options=options)
    return driver

# --------- 쇼핑 검색 결과 분석 함수 ---------
def analyze_shopping_ranking(driver, keyword, store_name):
    url = f"https://search.shopping.naver.com/search/all?query={keyword}"
    driver.get(url)
    time.sleep(random.uniform(2, 4))

    # ✅ 스크롤 다운을 통해 추가 상품 로딩 유도
    SCROLL_PAUSE_TIME = 1.0
    last_height = driver.execute_script("return document.body.scrollHeight")
    for _ in range(6):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    soup = BeautifulSoup(driver.page_source, "html.parser")

    all_elements = soup.select("div.adProduct_item__T7utB, div.superSavingProduct_item__6mR7_, div.product_item__KQayS")

    top_ads, mid_ads, products = [], [], []
    encountered_product = False
    ad_classnames = ["adProduct_item__T7utB", "superSavingProduct_item__6mR7_"]

    for el in all_elements:
        class_list = el.get("class", [])
        if any(cls in ad_classnames for cls in class_list):
            if not encountered_product:
                top_ads.append(el)
            else:
                mid_ads.append(el)
        elif "product_item__KQayS" in class_list:
            products.append(el)
            encountered_product = True

    def extract_store_name_from_ad(container):
        try:
            mall_divs = container.find_all("div")
            for div in mall_divs:
                cls_list = div.get("class", [])
                for cls in cls_list:
                    if cls.startswith("adProduct_mall_title__") or cls.startswith("superSavingProduct_mall_title__"):
                        a_tag = div.find("a")
                        if a_tag:
                            return a_tag.text.strip()
        except:
            return None
        return None

    def extract_store_name(container):
        for div in container.find_all("div"):
            if "product_mall_title__" in div.get("class", [""])[0]:
                a_tag = div.find("a")
                if a_tag:
                    return a_tag.text.strip()
        return None

    my_ad_index = None
    all_ads = top_ads + mid_ads
    for idx, ad in enumerate(all_ads, 1):
        name = extract_store_name_from_ad(ad)
        if name and store_name in name:
            my_ad_index = idx
            break

    my_product_index = None
    for idx, item in enumerate(products, 1):
        name = extract_store_name(item)
        if name and store_name in name:
            my_product_index = idx
            break

    return {
        "keyword": keyword,
        "상단_광고_개수": len(top_ads),
        "중단_광고_개수": len(mid_ads),
        "광고_상품_개수": len(all_ads),
        "일반_상품_개수": len(products),
        "광고_노출": "노출됨" if my_ad_index else "미노출",
        "광고_순위": my_ad_index if my_ad_index else "-",
        "일반_노출": "노출됨" if my_product_index else "미노출",
        "일반_순위": my_product_index if my_product_index else "-"
    }

# --------- Streamlit UI ---------
st.set_page_config(page_title="네이버 쇼핑 순위 분석기", layout="wide")
st.title("🛍️ 네이버 쇼핑 순위 분석기")

store_name = st.text_input("✅ 내 쇼핑몰 이름", placeholder="예: 하이그린웰")
mode = st.radio("키워드 입력 방식 선택", ["직접 입력", "CSV 업로드"])

keywords = []
if mode == "직접 입력":
    keywords_input = st.text_area("📝 키워드를 쉼표로 구분해서 입력해주세요", placeholder="예: 여자 원피스, 강아지 사료")
    if keywords_input:
        keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
elif mode == "CSV 업로드":
    uploaded_file = st.file_uploader("📂 키워드가 담긴 CSV 파일을 업로드해주세요 (컬럼명: keyword)", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, encoding="cp949")
            if "keyword" in df.columns:
                keywords = df["keyword"].dropna().tolist()
                st.success(f"{len(keywords)}개의 키워드가 로드되었습니다.")
            else:
                st.error("CSV 파일에 'keyword' 컬럼이 존재하지 않습니다.")
        except Exception as e:
            st.error(f"파일을 불러오는 중 오류가 발생했습니다: {e}")

if st.button("🚀 분석 시작"):
    if not store_name:
        st.warning("❗ 쇼핑몰 이름을 입력해주세요.")
    elif not keywords:
        st.warning("❗ 키워드를 입력하거나 CSV 파일을 업로드해주세요.")
    else:
        st.info("브라우저를 열고 분석을 시작합니다. 잠시만 기다려주세요...")
        driver = init_driver()
        results = []
        progress = st.progress(0)
        for idx, kw in enumerate(keywords):
            st.write(f"🔍 {kw} 분석 중...")
            try:
                result = analyze_shopping_ranking(driver, kw, store_name)
                results.append(result)
            except Exception as e:
                results.append({"keyword": kw, "에러": str(e)})
            progress.progress((idx + 1) / len(keywords))
        driver.quit()
        df_result = pd.DataFrame(results)
        st.success("✅ 분석 완료!")
        st.dataframe(df_result)
        csv_data = df_result.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 결과 다운로드 (CSV)", csv_data, file_name="shopping_ranking_result.csv", mime="text/csv")