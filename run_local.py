# run_local.py

from macro_crawling import MacroCrawler

if __name__ == "__main__":
    crawler = MacroCrawler("미국 CPI")
    result = crawler.crawl()
    print(f"[로컬 테스트 결과] {result}")
