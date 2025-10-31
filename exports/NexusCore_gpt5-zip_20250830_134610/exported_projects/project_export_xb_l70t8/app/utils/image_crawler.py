# image_crawler.py ─ DeepLab v3 (MobileNetV3-ONNX 版)
# 依存: torch torchvision onnx opencv-python numpy icrawler requests
# ------------------------------------------------------------
from __future__ import annotations
import cv2, numpy as np, requests
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
from pathlib import Path
from typing import List

# 1. モデルファイル
MODEL_DIR  = Path(__file__).parent / "models"
ONNX_FILE  = MODEL_DIR / "deeplabv3_mnv3.onnx"

# 2. ダウンロード処理は廃止（ローカルに無ければ明示エラー）
def ensure_model() -> None:
    if ONNX_FILE.exists():
        print("✓ DeepLab ONNX モデルは既に存在します")
        return
    raise FileNotFoundError(
        f"{ONNX_FILE.name} がありません。\n"
        "1) app/utils/models で make_deeplab_onnx.py を実行して生成する\n"
        "2) 生成した deeplabv3_mnv3.onnx を models フォルダに置いて再実行してください"
    )

# 3. 深度学習セグメンテーション
class DeepLabSeg:
    def __init__(self, onnx: Path, use_cuda=False):
        self.net = cv2.dnn.readNetFromONNX(str(onnx))
        backend = cv2.dnn.DNN_BACKEND_CUDA if use_cuda else cv2.dnn.DNN_BACKEND_OPENCV
        target  = cv2.dnn.DNN_TARGET_CUDA  if use_cuda else cv2.dnn.DNN_TARGET_CPU
        self.net.setPreferableBackend(backend)
        self.net.setPreferableTarget(target)

    def remove_bg(self, img: np.ndarray, blur=5) -> np.ndarray:
        h, w = img.shape[:2]
        blob = cv2.dnn.blobFromImage(img, 1/127.5, (513, 513), (127.5,)*3, swapRB=True)
        self.net.setInput(blob)
        mask = self.net.forward()[0].argmax(0).astype(np.uint8)
        mask = cv2.resize(mask, (w, h), cv2.INTER_NEAREST)
        fg_mask = cv2.medianBlur(mask*255, blur) if blur else mask*255
        fg = cv2.bitwise_and(img, img, mask=fg_mask)
        return np.where(fg_mask[..., None] == 255, fg, 255)

# 4. 画像検索＋背景除去
def crawl_and_remove_bg(keyword: str, max_num=30,
                        engines: List[str] | None = None,
                        use_cuda=False) -> Path:
    engines = engines or ["bing", "google"]
    out_dir = Path(__file__).parent / "images" / keyword.replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)

    if "bing" in engines:
        BingImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)
    if "google" in engines:
        GoogleImageCrawler(storage={"root_dir": str(out_dir)}).crawl(keyword, max_num)

    ensure_model()
    seg = DeepLabSeg(ONNX_FILE, use_cuda)

    for p in out_dir.glob("*.jpg"):
        try:
            img = cv2.imread(str(p))
            out_path = p.with_stem(p.stem + "_bg").with_suffix(".png")
            cv2.imwrite(str(out_path), seg.remove_bg(img))
            print("✓", p.name)
        except Exception as e:
            print("×", p.name, e)
    return out_dir

def crawl_images(keyword, max_num=50, engines=None):
    return crawl_and_remove_bg(keyword, max_num, engines or ["bing", "google"])

# 5. CLI
if __name__ == "__main__":
    kw = input("検索キーワードを入力してください：")
    print("完了→", crawl_and_remove_bg(kw, 50, ["bing"]).resolve())
