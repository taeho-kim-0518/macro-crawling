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
import time

class BullBearSpreadUpdater:

    def __init__(self, csv_path="bull_bear_spread.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["date"], encoding='CP949')
            print("✅ Bull-Bear Spread CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "date",
                "forward_pe"
            ])

    def get_bull_bear_spread(self):

        url = "https://ycharts.com/indicators/us_investor_sentiment_bull_bear_spread"

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    bull_bear_spread = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if bull_bear_spread and date:
            return {
                "date": date,
                "spread": bull_bear_spread
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")



    def update_csv(self):
        bb_spread = self.get_bull_bear_spread()

    
        # 날짜 포맷 정제 (공통 적용)
        date_str = bb_spread["date"]
        parsed_date = pd.to_datetime(date_str, format="%b %d %Y", errors="coerce")


        # 이미 존재하는 날짜인지 확인
        if parsed_date in self.df["date"].values:
            print("📭 이미 존재하는 날짜입니다. 업데이트 건너뜀.")
            return self.df
        
        # 불러온 값 정제
        spread_str  = bb_spread['spread']
        spread_float = float(spread_str.replace('%', '').strip())

        # 새 행 추가
        new_row = pd.DataFrame([{
            "date": parsed_date,
            "spread": spread_float*0.01
        }])

        updated_df = pd.concat([self.df, new_row], ignore_index=True)
        updated_df = updated_df.sort_values("date")
        updated_df.to_csv(self.csv_path, index=False)
        self.df = updated_df
        print("✅ 새로운 데이터가 추가되었습니다.")
        return self.df
    
if __name__ == "__main__":
    update = BullBearSpreadUpdater()

    result = update.update_csv()
    print(result)