from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import csv
import time
import random
import os
import re
from urllib.parse import urljoin

# ====================
# 設定部分（必要に応じて変更）
# ====================
BASE_URL = "https://www.buyma.com/r/_%s/"  # ブランド名を%sに挿入
BRANDS = ["GUCCI", "PRADA"]                # 対象ブランドリスト
MAX_PAGES = 2                              # 最大取得ページ数
DELAY_RANGE = (10, 30)                     # ランダム待機時間（秒）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)..."
]
PROXIES = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080"
]

# ====================
# Chrome設定
# ====================
def setup_driver():
    chrome_options = Options()
    
    # Headlessモード
    chrome_options.add_argument("--headless=new")
    
    # プロキシ設定
    chrome_options.add_argument(f"--proxy-server={random.choice(PROXIES)}")
    
    # ユーザーエージェントローテーション
    chrome_options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
    
    # 基本設定
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    return webdriver.Chrome(options=chrome_options)

# ====================
# 商品詳細取得関数
# ====================
def get_product_details(driver, product_url):
    """商品詳細ページから追加情報を取得"""
    try:
        driver.get(product_url)
        time.sleep(random.uniform(*DELAY_RANGE))
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_detail"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 追加情報取得例
        description = soup.select_one('div.product_description').text.strip()[:200] + "..." if soup.select_one('div.product_description') else ""
        seller_info = soup.select_one('div.seller_profile').text.strip()[:100] + "..." if soup.select_one('div.seller_profile') else ""
        
        return {
            'description': description,
            'seller_info': seller_info
        }
        
    except Exception as e:
        print(f"詳細ページエラー: {str(e)}")
        return {}

# ====================
# メインスクレイピング関数
# ====================
def scrape_brand(driver, brand):
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools', f'buyma_{brand.lower()}_products.csv')
    products = []
    
    for page in range(1, MAX_PAGES + 1):
        try:
            # ページアクセス
            url = BASE_URL % brand + f"?pageno={page}"
            driver.get(url)
            time.sleep(random.uniform(*DELAY_RANGE))
            
            # 商品コンテナ待機
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.product_body"))
            )
            
            # ページネーション確認
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            next_page = soup.select_one('a.pagination_next:not(.disabled)')
            if not next_page and page != 1:
                break
                
            # 商品情報取得
            for item in soup.select('div.product_body'):
                # 基本情報
                name_elem = item.select_one('div.product_name')
                name = name_elem.text.strip()[:50] + "..." if name_elem else "商品名不明"
                name = re.sub(r'★|即発送|SALE\!|即納|新品', '', name).strip()

                # 価格
                price_elem = item.select_one('span.Price_Txt') or \
                            item.select_one('div.product_price span') or \
                            item.select_one('.price')
                price = re.sub(r'[^\d,]', '', price_elem.text.strip()).replace(',', '') if price_elem else "0"

                # 画像URL
                image_elem = item.select_one('img[loading="lazy"]')
                image_url = ""
                if image_elem:
                    image_url = image_elem.get('data-src') or image_elem.get('src')
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = urljoin(url, image_url)

                # 詳細情報（確率制限）
                details = {}
                if random.random() < 0.3:
                    detail_link = item.select_one('a.product_name')['href']
                    details = get_product_details(driver, urljoin(url, detail_link)) if detail_link else {}
                
                products.append({
                    'brand': brand,
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    **details
                })

        except Exception as e:
            print(f"ページ{page}処理中にエラー: {str(e)}")
            continue

    # CSV保存
    if products:
        with open(csv_path, 'w', newline='', encoding='cp932', errors='replace') as f:
            writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'image_url', 'description', 'seller_info'])
            writer.writeheader()
            writer.writerows(products)
        print(f"{brand} - {len(products)}件の商品を保存しました")
    else:
        print(f"{brand} - 商品データが0件のため保存をスキップしました")

# ====================
# メイン実行
# ====================
def main():
    driver = setup_driver()
    try:
        for brand in BRANDS:
            start_time = time.time()
            scrape_brand(driver, brand)
            elapsed_time = time.time() - start_time
            sleep_time = max(random.randint(*DELAY_RANGE) - elapsed_time, 5)
            time.sleep(sleep_time)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
