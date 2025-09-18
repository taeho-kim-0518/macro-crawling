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

class PutCallRatioUpdater:

    def __init__(self, csv_path="put_call_ratio.csv"):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(self.csv_path, parse_dates=["date"], encoding='CP949')
            print("✅ PUT CALL RATIO CSV 불러오기 성공")
        
        except FileNotFoundError:
            print("⚠️ CSV 파일이 없어 새로 생성합니다.")
            self.df = pd.DataFrame(columns=[
                "date",
                "equity_value",
                "index_value"
            ])

    def get_equity_put_call_ratio(self):
        url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        # 수정: webdriver-manager를 사용해 자동으로 드라이버 관리
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        time.sleep(5)  # JS 로딩 대기

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    equity_value = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if equity_value and date:
            return {
                "date": date,
                "equity_value": equity_value
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")


    def get_index_put_call_ratio(self):
        url = 'https://ycharts.com/indicators/cboe_index_put_call_ratio'

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
   

        # 수정: webdriver-manager를 사용해 자동으로 드라이버 관리
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        # ✅ time.sleep(5) 대신 WebDriverWait를 사용하여 요소가 나타날 때까지 대기
        WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.stats-card-section > span.text-2xl"))
            )

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        # "Last Value" 텍스트가 있는 td 찾기
        for td in soup.select("td.col-6"):
            if "Last Value" in td.get_text(strip=True):
                value_td = td.find_next_sibling("td")
                if value_td:
                    index_value = value_td.get_text(strip=True)
                    break

        # ✅ Last Period (날짜) 추출 - tr 기반으로 따로 탐색
        for row in soup.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) == 2 and "Latest Period" in tds[0].get_text(strip=True):
                date = tds[1].get_text(strip=True)
                break

        if index_value and date:
            return {
                "date": date,
                "index_value": index_value
            }
        else:
            raise ValueError("❌ Last Value 또는 Last Period를 찾을 수 없습니다.")

    def update_csv(self):
        equity_df = self.get_equity_put_call_ratio()
        index_df = self.get_index_put_call_ratio()
    
        # 날짜 포맷 정제 (공통 적용)
        date_str_eq = equity_df["date"]
        date_str_idx = index_df["date"]

        parsed_date_eq = pd.to_datetime(date_str_eq, format="%b %d %Y", errors="coerce")
        parsed_date_idx = pd.to_datetime(date_str_idx, format="%b %d %Y", errors="coerce")

        # 날짜가 다르면 예외 처리 (예외적으로 발생할 수 있음)
        if parsed_date_eq != parsed_date_idx:
            raise ValueError(f"❌ 날짜 불일치: equity={parsed_date_eq}, index={parsed_date_idx}")

        
        parsed_date = parsed_date_eq

        # 이미 존재하는 날짜인지 확인
        if parsed_date in self.df["date"].values:
            print("📭 이미 존재하는 날짜입니다. 업데이트 건너뜀.")
            return self.df

        # 새 행 추가
        new_row = pd.DataFrame([{
            "date": parsed_date,
            "equity_value": float(equity_df["equity_value"]),
            "index_value": float(index_df["index_value"])
        }])

        updated_df = pd.concat([self.df, new_row], ignore_index=True)
        updated_df = updated_df.sort_values("date")
        updated_df.to_csv(self.csv_path, index=False)
        self.df = updated_df
        print("✅ 새로운 데이터가 추가되었습니다.")
        return self.df
    
if __name__ == "__main__":
    update = PutCallRatioUpdater()

    result = update.update_csv()
    print(result)