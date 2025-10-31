import os
import csv
import time
import random
import requests
import hashlib
import zipfile
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# --- 設定（SDカードD:ドライブ・スプレッドシートID設定済み）---
CONFIG = {
    'profile_path': r"C:/Users/USER/AppData/Local/Google/Chrome/SeleniumProfile",
    'base_dir': 'D:/catalog_images',
    'screenshot_dir': 'D:/screenshots',
    'csv_path': 'D:/catalog_data.csv',
    'extracted_images_dir': 'D:/extracted_images',
    'google_credentials': 'D:/credentials.json',
    'spreadsheet_id': '1z9_lczAbnbsMYpAEslamfekEMrPQVIM1rfHqNbzze_Y',
    'worksheet_name': 'catalog_data',
    'safety': {
        'max_daily_requests': 500,
        'request_interval': (5, 10),
        'error_threshold': 10,
        'response_time_threshold': 8.0
    }
}

class BUYMACatalogManager:
    def __init__(self):
        self.driver = self._init_driver()
        self.request_count = 0
        self.error_count = 0
        self.downloaded_hashes = set()
        self.downloaded_catalog_ids = set()
        self.csv_records = []
        self._setup_directories()
        self._init_google_sheets()
        self.stop_flag = False

    def _setup_directories(self):
        directories = [
            CONFIG['screenshot_dir'],
            CONFIG['base_dir'],
            CONFIG['extracted_images_dir']
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"ディレクトリ作成: {directory}")

    def _init_google_sheets(self):
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(
                CONFIG['google_credentials'], scopes=scope
            )
            self.gc = gspread.authorize(creds)
            self.worksheet = self.gc.open_by_key(CONFIG['spreadsheet_id']).worksheet(CONFIG['worksheet_name'])
            print("Googleスプレッドシート接続成功")
        except Exception as e:
            print(f"Googleスプレッドシート接続エラー: {e}")
            self.gc = None
            self.worksheet = None

    def _init_driver(self):
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={CONFIG['profile_path']}")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--lang=ja")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        stealth(driver,
            languages=["ja-JP", "ja"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver

    def _human_like_delay(self):
        if self._check_response_time():
            delay = random.uniform(*CONFIG['safety']['request_interval']) * 1.5
        else:
            delay = random.uniform(*CONFIG['safety']['request_interval'])
        time.sleep(delay)

    def _check_response_time(self):
        try:
            navigation_start = self.driver.execute_script("return window.performance.timing.navigationStart")
            response_start = self.driver.execute_script("return window.performance.timing.responseStart")
            return (response_start - navigation_start) / 1000 > CONFIG['safety']['response_time_threshold']
        except Exception:
            return False

    def _force_close_modals(self):
        try:
            close_selectors = [
                ".catalogs-modal__close",
                ".modal-close",
                "//button[contains(text(), '閉じる')]",
                "//button[contains(text(), 'キャンセル')]"
            ]
            for selector in close_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            element.click()
                            self._human_like_delay()
                            return True
                except Exception:
                    continue
            self.driver.execute_script("""
                document.querySelectorAll('.catalogs-modal-table, .modal, .modal-backdrop').forEach(e => e.remove());
            """)
            return True
        except Exception as e:
            print(f"モーダル閉じエラー: {str(e)[:30]}")
            return False

    def _extract_images_from_zip(self, zip_path, brand_name, catalog_id):
        try:
            extract_dir = os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id)
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            image_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        old_path = os.path.join(root, file)
                        new_filename = f"{brand_name}_{catalog_id}_{len(image_files)+1}_{file}"
                        new_path = os.path.join(extract_dir, new_filename)
                        os.rename(old_path, new_path)
                        image_files.append(new_path)
            
            return len(image_files), image_files
        except Exception as e:
            print(f"ZIP解凍エラー: {e}")
            return 0, []

    def _download_file(self, url, brand_name, catalog_id):
        session = requests.Session()
        for c in self.driver.get_cookies():
            session.cookies.set(c['name'], c['value'])
        headers = {
            'Referer': self.driver.current_url,
            'User-Agent': self.driver.execute_script("return navigator.userAgent;")
        }
        
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            file_hash = hashlib.md5(response.content).hexdigest()
            if catalog_id in self.downloaded_catalog_ids or file_hash in self.downloaded_hashes:
                return False, None
            
            save_dir = os.path.join(CONFIG['base_dir'], brand_name, catalog_id)
            os.makedirs(save_dir, exist_ok=True)
            zip_path = os.path.join(save_dir, f'catalog_{catalog_id}.zip')
            
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            image_count, image_files = self._extract_images_from_zip(zip_path, brand_name, catalog_id)
            
            record = {
                'brand': brand_name,
                'catalog_id': catalog_id,
                'zip_path': zip_path,
                'extracted_dir': os.path.join(CONFIG['extracted_images_dir'], brand_name, catalog_id),
                'download_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_count': image_count,
                'file_size': os.path.getsize(zip_path),
                'first_image_path': image_files[0] if image_files else '',
                'all_image_paths': '|'.join(image_files),
                'status': 'success'
            }
            
            self.csv_records.append(record)
            self.downloaded_hashes.add(file_hash)
            self.downloaded_catalog_ids.add(catalog_id)
            
            self._add_to_google_sheet(record)
            
            return True, record
        return False, None

    def _add_to_google_sheet(self, record):
        if self.worksheet:
            try:
                row_data = [
                    record['brand'],
                    record['catalog_id'],
                    record['zip_path'],
                    record['extracted_dir'],
                    record['download_date'],
                    record['image_count'],
                    record['file_size'],
                    record['first_image_path'],
                    record['all_image_paths'],
                    record['status']
                ]
                self.worksheet.append_row(row_data)
                print(f"Googleスプレッドシートに追加: {record['brand']} {record['catalog_id']}")
            except Exception as e:
                print(f"Googleスプレッドシート追加エラー: {e}")

    def get_popular_brands(self, limit=50):
        return {
            203: "GUCCI",
            290: "PRADA", 
            142: "CHANEL",
            180: "HERMES",
            195: "LOUIS VUITTON",
            215: "BOTTEGA VENETA",
            183: "CELINE",
            186: "BALENCIAGA",
            164: "SAINT LAURENT",
            202: "DIOR",
            147: "FENDI",
            167: "VALENTINO",
            144: "COACH",
            155: "BURBERRY",
            172: "MONCLER",
            149: "MARC JACOBS",
            222: "MARNI",
            146: "CHLOE",
            209: "TORY BURCH",
            176: "JIMMY CHOO",
            191: "MICHAEL KORS",
            214: "VERSACE",
            141: "BVLGARI",
            227: "ROBINMAY",
            204: "LONGCHAMP",
            225: "GIANNI CHIARINI",
            228: "MM6 MAISON MARGIELA",
            148: "MAISON MARGIELA",
            150: "HAY",
            299: "NIKE",
            300: "adidas",
            301: "PUMA",
        }

    def process_catalog(self, row, brand_name):
        try:
            self._force_close_modals()
            catalog_id = row.find_element(By.CSS_SELECTOR, 'span.catalogs-table__contents-id').text.strip()
            
            image_cell = WebDriverWait(row, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.catalogs-table__image-item > .catalogs-table__image'))
            )
            ActionChains(self.driver).move_to_element(image_cell).pause(0.5).click().perform()
            
            WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".catalogs-modal-table"))
            )
            
            download_link = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.catalogs-modal-table__link"))
            )
            download_url = download_link.get_attribute('href')
            
            success, record = self._download_file(download_url, brand_name, catalog_id)
            if success:
                print(f"成功: {brand_name} {catalog_id} (画像{record['image_count']}枚)")
            else:
                print(f"スキップ: {brand_name} {catalog_id}")
            
            self._force_close_modals()
            return True
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.png'))
            with open(os.path.join(CONFIG['screenshot_dir'], f'error_{timestamp}.html'), 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print(f"エラー発生: {str(e)[:100]}")
            return False

    def process_pagination(self, base_url, brand_name):
        page_num = 1
        while not self.stop_flag:
            try:
                self.driver.get(f"{base_url}&page={page_num}" if "?brand_id=" in base_url else f"{base_url}?page={page_num}")
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'tr.catalogs-table__row'))
                )
                
                rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr.catalogs-table__row')
                if not rows:
                    break
                    
                for row in rows:
                    if self.stop_flag:
                        return
                    self.process_catalog(row, brand_name)
                    self._human_like_delay()
                
                try:
                    next_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.pagination__next:not([disabled])'))
                    )
                    page_num += 1
                    self._human_like_delay()
                except (NoSuchElementException, TimeoutException):
                    print(f"{brand_name} の最終ページに到達")
                    break
            except Exception as e:
                print(f"ページ処理エラー（{brand_name}）: {str(e)}")
                self.driver.save_screenshot(os.path.join(CONFIG['screenshot_dir'], f'pagination_error_{brand_name}.png'))
                break

    def _save_csv_summary(self):
        if not self.csv_records:
            return
        
        fieldnames = [
            'brand', 'catalog_id', 'zip_path', 'extracted_dir',
            'download_date', 'image_count', 'file_size',
            'first_image_path', 'all_image_paths', 'status'  # ← ここに'all_image_paths'を追加
        ]
        
        with open(CONFIG['csv_path'], 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.csv_records)
        
        print(f"詳細レポート保存: {CONFIG['csv_path']}")
        
        total_downloads = len(self.csv_records)
        total_images = sum(record['image_count'] for record in self.csv_records)
        total_size_mb = sum(record['file_size'] for record in self.csv_records) / (1024 * 1024)
        
        summary = f"""
=== ダウンロード完了サマリー ===
総ダウンロード数: {total_downloads}件
総画像数: {total_images}枚
総ファイルサイズ: {total_size_mb:.2f}MB
保存先: {CONFIG['base_dir']}
解凍画像: {CONFIG['extracted_images_dir']}
CSV詳細: {CONFIG['csv_path']}
Googleスプレッドシート: {'連携済み' if self.worksheet else '未接続'}
        """
        print(summary)

    def main_flow(self):
        try:
            if self.worksheet:
                try:
                    headers = ['Brand', 'Catalog_ID', 'ZIP_Path', 'Extracted_Dir', 
                             'Download_Date', 'Image_Count', 'File_Size_Bytes', 
                             'First_Image_Path', 'All_Image_Paths', 'Status']
                    self.worksheet.clear()
                    self.worksheet.append_row(headers)
                    print("Googleスプレッドシートヘッダー設定完了")
                except Exception as e:
                    print(f"ヘッダー設定エラー: {e}")
            
            self.driver.get('https://www.buyma.com/login/')
            input("手動ログイン後、Enterを押してください...\n（途中で止めたい場合はCtrl+C）")

            popular_brands = self.get_popular_brands(30)
            print(f"処理対象ブランド: {list(popular_brands.values())}")
            
            for brand_id, brand_name in popular_brands.items():
                if self._safety_check():
                    break
                
                print(f"\n{brand_name}の処理を開始します...")
                catalog_url = f'https://www.buyma.com/my/sell/catalogs?brand_id={brand_id}'
                self.process_pagination(catalog_url, brand_name)

        except KeyboardInterrupt:
            print("\nユーザー要求により停止しました")
            self.stop_flag = True
        except Exception as e:
            print(f"致命的エラー: {str(e)}")
        finally:
            self.cleanup()

    def _safety_check(self):
        self.request_count += 1
        if self.request_count >= CONFIG['safety']['max_daily_requests']:
            print("1日のリクエスト上限に達しました")
            return True
        if self.error_count >= CONFIG['safety']['error_threshold']:
            print("エラーが多発したため停止します")
            return True
        return False

    def cleanup(self):
        self._save_csv_summary()
        self.driver.quit()
        print("リソースを解放しました")

# --- 実行部分 ---
if __name__ == "__main__":
    print("BUYMA画像自動収集ツール（SDカードD:ドライブ対応版）")
    print("必要な設定:")
    print("1. SDカードがD:ドライブとして認識されていること")
    print("2. credentials.jsonがD:ルートにあること")
    print("3. スプレッドシートの共有設定（サービスアカウント追加）")
    print("-" * 50)
    
    manager = BUYMACatalogManager()
    manager.main_flow()
