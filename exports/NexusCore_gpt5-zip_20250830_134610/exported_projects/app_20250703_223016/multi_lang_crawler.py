from googletrans import Translator
from icrawler.builtin import BingImageCrawler, BaiduImageCrawler
import os

translator = Translator()

product_list = [
    "アディダス ショルダーバッグ",
    "ナイキ シューズ"
]

base_dir = './images'

for product in product_list:
    # 多言語変換
    jp = product
    en = translator.translate(product, src='ja', dest='en').text
    zh = translator.translate(product, src='ja', dest='zh-cn').text

    print(f"日本語: {jp}, 英語: {en}, 中国語: {zh}")

    # Bing（日本語・英語）
    for keyword in [jp, en]:
        folder = os.path.join(base_dir, 'bing', keyword.replace(' ', '_'))
        os.makedirs(folder, exist_ok=True)
        crawler = BingImageCrawler(storage={'root_dir': folder}, downloader_threads=8)
        crawler.crawl(keyword=keyword, max_num=10)

    # Baidu（中国語推奨）
    folder = os.path.join(base_dir, 'baidu', zh.replace(' ', '_'))
    os.makedirs(folder, exist_ok=True)
    crawler = BaiduImageCrawler(storage={'root_dir': folder}, downloader_threads=8)
    crawler.crawl(keyword=zh, max_num=10)
