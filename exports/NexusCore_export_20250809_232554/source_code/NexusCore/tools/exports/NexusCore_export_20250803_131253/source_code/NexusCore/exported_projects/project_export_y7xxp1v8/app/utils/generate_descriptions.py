import os
import requests
import csv
import time
import random
from dotenv import load_dotenv
from datetime import datetime

# 環境変数の読み込み
load_dotenv()

class BUYMADescriptionGenerator:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.endpoint = "https://api.perplexity.ai/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BUYMA-Auto-Desc/3.0"
        }
        self.model = "sonar-pro"  # 最新有効モデル名

    def _create_log(self, message, log_type="error"):
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{log_type}_{timestamp}.log"
        with open(os.path.join(log_dir, filename), "w", encoding="utf-8") as f:
            f.write(message)

    def _call_api(self, payload):
        try:
            response = requests.post(
                self.endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e.response.status_code}\n{e.response.text}"
            self._create_log(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"Request Failed: {str(e)}"
            self._create_log(error_msg)
        except Exception as e:
            error_msg = f"Unexpected Error: {str(e)}"
            self._create_log(error_msg)
        return None

    def generate_description(self, product_info):
        prompt = f"""
        あなたはBUYMA専門のプロコピーライターです。
        以下の条件で商品説明文を日本語で作成してください。

        [要件]
        1. 300-500文字
        2. ブランド名とカテゴリを自然に配置
        3. 商品の特徴を3点箇条書き
        4. 感情に訴える表現（例: 「上質なレザーの風合い」）
        5. 急かし表現や「今すぐ」などの強い勧誘は避ける
        6. 重複表現を避け、情報を簡潔に整理
        7. 生活シーンや使用イメージを盛り込む
        8. 読み手に自然に提案する口調で仕上げる

        [商品情報]
        ブランド: {product_info.get('brand', '')}
        商品名: {product_info.get('name', '')}
        カテゴリ: {product_info.get('category', '')}
        特徴: {product_info.get('features', '')}
        素材: {product_info.get('materials', '')}
        サイズ: {product_info.get('size', '')}
        カラー: {product_info.get('color', '')}
        対象層: {product_info.get('target', '')}
        価格帯: {product_info.get('price_range', '')}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "あなたは高級ファッション専門のコピーライターです。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        result = self._call_api(payload)
        return result['choices'][0]['message']['content'].strip() if result else None

    def batch_process(self, products, retry=3):
        results = []
        for idx, product in enumerate(products):
            attempt = 0
            while attempt < retry:
                try:
                    print(f"処理中 ({idx+1}/{len(products)})")
                    desc = self.generate_description(product)
                    if desc:
                        results.append({**product, "description": desc})
                        break
                    else:
                        attempt += 1
                        time.sleep(2 ** attempt)
                except Exception as e:
                    print(f"エラー: {str(e)}")
                    attempt += 1
            time.sleep(random.uniform(1, 3))
        return results

if __name__ == "__main__":
    generator = BUYMADescriptionGenerator()
    sample_products = [
        {
            "brand": "PRADA",
            "name": "シンフォニー トートバッグ",
            "category": "トートバッグ",
            "features": "軽量ナイロン素材、大容量収納",
            "materials": "ナイロン",
            "size": "W35cm x H25cm x D15cm",
            "color": "ブラック",
            "target": "20-30代女性",
            "price_range": "15-20万円"
        }
    ]
    processed_data = generator.batch_process(sample_products)
    if processed_data:
        output_path = os.path.join(os.path.dirname(__file__), 'output.csv')
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=processed_data[0].keys())
            writer.writeheader()
            writer.writerows(processed_data)
        print(f"CSVファイルを正常に出力しました: {output_path}")
    else:
        print("処理に失敗しました。ログを確認してください。")
