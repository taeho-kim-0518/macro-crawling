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

    def get_put_call_ratio(self, url):
        """주어진 URL에서 Put-Call Ratio 값을 추출합니다."""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        
        try:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Stats')]"))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            stats_panel = None
            for panel in soup.find_all('div', class_='panel-data'):
                title = panel.find('h3', class_='panel-title')
                if title and title.get_text(strip=True) == 'Stats':
                    stats_panel = panel
                    break
            
            if not stats_panel:
                raise ValueError(f"❌ '{url}'에서 'Stats' 패널을 찾을 수 없습니다.")

            last_value_td = stats_panel.find('td', string='Last Value')
            latest_period_td = stats_panel.find('td', string='Latest Period')

            if last_value_td and last_value_td.find_next_sibling('td'):
                ratio_value = last_value_td.find_next_sibling('td').get_text(strip=True)
            else:
                ratio_value = None

            if latest_period_td and latest_period_td.find_next_sibling('td'):
                date_value = latest_period_td.find_next_sibling('td').get_text(strip=True)
            else:
                date_value = None

            if ratio_value and date_value:
                return {
                    "date": date_value,
                    "value": float(ratio_value)
                }
            else:
                raise ValueError(f"❌ '{url}'에서 'Last Value' 또는 'Latest Period'를 찾을 수 없습니다.")
                
        finally:
            driver.quit()

    def update_csv(self):
        equity_url = 'https://ycharts.com/indicators/cboe_equity_put_call_ratio'
        index_url = 'https://ycharts.com/indicators/cboe_index_put_call_ratio'

        try:
            equity_data = self.get_put_call_ratio(equity_url)
            index_data = self.get_put_call_ratio(index_url)
        except ValueError as e:
            print(e)
            return self.df
    
        if equity_data['date'] != index_data['date']:
            raise ValueError(f"❌ 날짜 불일치: equity={equity_data['date']}, index={index_data['date']}")
        
        parsed_date = pd.to_datetime(equity_data['date'], format="%b %d %Y", errors="coerce")
        if pd.isna(parsed_date):
            print(f"❌ 날짜 포맷 오류: {equity_data['date']}")
            return self.df

        if self.df["date"].isin([parsed_date]).any():
            print("📭 이미 존재하는 날짜입니다. 업데이트 건너뜀.")
            return self.df
        
        new_row = pd.DataFrame([{
            "date": parsed_date,
            "equity_value": equity_data['value'],
            "index_value": index_data['value']
        }])

        updated_df = pd.concat([self.df, new_row], ignore_index=True)
        updated_df = updated_df.sort_values("date")
        updated_df.to_csv(self.csv_path, index=False, encoding='CP949')
        self.df = updated_df
        print("✅ 새로운 데이터가 추가되었습니다.")
        return self.df

if __name__ == "__main__":
    updater = PutCallRatioUpdater()
    result = updater.update_csv()
    print(result)