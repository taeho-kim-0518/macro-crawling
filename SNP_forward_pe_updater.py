import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class forwardpe_updater:

    def __init__(self, csv_path="forward_pe_data.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["date"], encoding='CP949')
            print("✅ Forward PE CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "date",
                "forward_pe"
            ])

    def get_forward_pe(self):
            url = 'https://en.macromicro.me/series/20052/sp500-forward-pe-ratio'

            options = Options()
            # options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
 

            driver = webdriver.Chrome(options=options)
            driver.get(url)


            try:
                # ✅ 해당 요소가 로드될 때까지 대기 (최대 10초)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.sidebar-sec.chart-stat-lastrows span.val"))
                )
            except:
                driver.quit()
                raise RuntimeError("📛 페이지 로딩 중 Forward PE 데이터를 찾지 못했습니다.")

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()

            latest_val = soup.select_one("div.sidebar-sec.chart-stat-lastrows span.val")
            date = soup.select_one("div.sidebar-sec.chart-stat-lastrows .date-label")

            if latest_val and date:
                date_text = date.text.strip()
                pe_val = float(latest_val.text.strip())
                df = pd.DataFrame([{"date": date_text, "forward_pe": pe_val}])
                return {
                    "date": date_text,
                    "forward_pe": pe_val
                }
            else:
                raise ValueError("📛 Forward PE 값을 찾을 수 없습니다.")

    def update_forward_pe_csv(self):
        new_df = self.get_forward_pe()
        
        if new_df is None:
            return 
        
        # ✅ dict → DataFrame 변환
        new_df = pd.DataFrame([new_df])
        new_df["date"] = pd.to_datetime(new_df["date"], errors="coerce")
        self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")

        # 기존에 없는 날짜만 필터링
        new_rows = new_df[~new_df["date"].isin(self.df["date"])]

        if not new_rows.empty:
            print(f"🆕 {len(new_rows)}개의 새 행이 추가됩니다.")

            updated = pd.concat([self.df, new_rows], ignore_index=True).dropna(subset=["date"])
            updated = updated.sort_values("date")

            # ✅ 저장 전 날짜를 문자열로 포맷 (일관성 유지)
            updated["date"] = updated["date"].dt.strftime("%Y-%m-%d")
            updated.to_csv(self.csv_path, index=False)

            # ✅ self.df도 업데이트 후 datetime 재변환
            updated["date"] = pd.to_datetime(updated["date"])
            self.df = updated
        else:
            print("📭 새로운 데이터 없음. CSV 업데이트 건너뜀.")

        return self.df

if __name__ == "__main__":
    update = forwardpe_updater()

    update.update_forward_pe_csv()