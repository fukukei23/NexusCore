import os
from PIL import Image
import imagehash

def remove_duplicate_images(folder):
    hashes = {}
    removed = 0
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.avif')):
                path = os.path.join(root, file)
                try:
                    img = Image.open(path)
                    hash = imagehash.phash(img)
                    if hash in hashes:
                        print(f"重複画像を削除: {path}")
                        os.remove(path)
                        removed += 1
                    else:
                        hashes[hash] = path
                except Exception as e:
                    print(f"エラー: {path} ({e})")
    print(f"重複削除数: {removed}")

# 例：imagesフォルダ配下すべてで重複除去
remove_duplicate_images('./images')
