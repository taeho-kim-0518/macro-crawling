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
from webdriver_manager.chrome import ChromeDriverManager
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
                "spread"
            ])

    def get_bull_bear_spread(self):

        url = "https://ycharts.com/indicators/us_investor_sentiment_bull_bear_spread"

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
 

        # 수정: webdriver-manager를 사용해 자동으로 드라이버 관리
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        try:
            # ✅ time.sleep(5) 대신 WebDriverWait를 사용하여 요소가 나타날 때까지 대기
            WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.panel-data"))
                )
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # 'Stats' 제목을 가진 패널을 찾기
            stats_panel = None
            for panel in soup.find_all('div', class_='panel-data'):
                title = panel.find('h3', class_='panel-title')
                if title and title.get_text(strip=True) == 'Stats':
                    stats_panel = panel
                    break
            
            if not stats_panel:
                raise ValueError("❌ 'Stats' 패널을 찾을 수 없습니다. 웹사이트 구조가 변경되었을 수 있습니다.")

            # 선택된 'Stats' 패널 내에서 'Last Value'와 'Latest Period'를 찾음
            last_value_td = stats_panel.find('td', string='Last Value')
            latest_period_td = stats_panel.find('td', string='Latest Period')

            if last_value_td and last_value_td.find_next_sibling('td'):
                bull_bear_spread = last_value_td.find_next_sibling('td').get_text(strip=True)
            
            if latest_period_td and latest_period_td.find_next_sibling('td'):
                date = latest_period_td.find_next_sibling('td').get_text(strip=True)

            if bull_bear_spread and date:
                return {
                    "date": date,
                    "spread": bull_bear_spread
                }
            else:
                raise ValueError("❌ 'Last Value' 또는 'Latest Period'를 찾을 수 없습니다.")
                
        finally:
            driver.quit()



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