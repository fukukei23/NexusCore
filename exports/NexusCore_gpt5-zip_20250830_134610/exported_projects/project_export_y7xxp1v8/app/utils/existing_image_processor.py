# ──────────────────────────────────────────────────────────────
#  existing_image_processor.py  ― 色ズレ・失敗検知・自動停止付き完全版
# ----------------------------------------------------------------
#  必要ライブラリ
#     pip install rembg pillow opencv-python numpy pyoxipng
# ----------------------------------------------------------------
import io, sys, zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import remove, new_session

try:
    import pyoxipng           # Rust 圧縮ライブラリ
except ImportError:
    pyoxipng = None           # 無くても動く（Pillow 圧縮のみ）

# ── 設定 ────────────────────────────────────────────────────
BASE_DIR        = r"D:\catalog_images"   # 画像&ZIP ルート
MAX_W           = 1200                  # 横幅リサイズ上限
MAX_BYTES       = 5_000_000             # 5 MB 超は JPEG にフォールバック
JPEG_QUAL       = 90                    # JPEG 品質

MAX_CONSEC_FAIL = 5                     # 連続失敗で停止
MAX_TOTAL_FAIL  = 50                    # 累計失敗で停止
FAIL_SIZE_KB    = 15                    # 15 KB 未満を失敗とみなす
# ──────────────────────────────────────────────────────────


def cleanup_previous_results(base: Path):
    """旧 *_bg.* を全削除して再処理"""
    targets = [*base.rglob("*_bg.png"), *base.rglob("*_bg.jpg")]
    if targets:
        print(f"[CLEANUP] 旧結果 {len(targets)} ファイル削除")
        for f in targets:
            f.unlink(missing_ok=True)


def unzip_all(base: Path):
    """ZIP 自動展開"""
    for z in base.rglob("*.zip"):
        dst = z.with_suffix("")
        if dst.exists():
            continue
        try:
            print(f"[UNZIP] {z.relative_to(base)}")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(dst)
        except zipfile.BadZipFile:
            print(f"[WARN] 壊れた ZIP: {z}")


def optimize_png(rgba: np.ndarray, out_path: Path):
    """RGBA numpy → PNG-8 → (任意) oxipng 圧縮"""
    img = Image.fromarray(rgba, mode="RGBA")

    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h), Image.LANCZOS)

    img8 = img.quantize(method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE)

    buf = io.BytesIO()
    img8.save(buf, format="PNG", optimize=True)
    data = buf.getvalue()

    if pyoxipng:
        data = pyoxipng.optimize(data, level=4, strip=True)

    out_path.write_bytes(data)

    if out_path.stat().st_size > MAX_BYTES:
        raise ValueError("PNG > 5 MB")


def save_white_jpeg(rgba: np.ndarray, out_path: Path):
    """白背景 JPEG 保存（RGB → BGR 変換込み）"""
    rgb   = rgba[:, :, :3]
    alpha = rgba[:, :, 3:] / 255.0
    white = np.full_like(rgb, 255)
    merged = (alpha * rgb + (1 - alpha) * white).astype(np.uint8)
    bgr = cv2.cvtColor(merged, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(out_path), bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUAL])


def is_failure(file: Path, rgba: np.ndarray) -> bool:
    """極端に小さい or アルファ全同値なら失敗"""
    if file.stat().st_size <= FAIL_SIZE_KB * 1024:
        return True
    a = rgba[:, :, 3]
    return a.min() == a.max()


def process_single(bgr: np.ndarray, png_out: Path, jpg_out: Path):
    """色空間を統一して 1 枚処理"""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    rgba = np.array(remove(Image.fromarray(rgb)))  # RGB→RGBA
    try:
        optimize_png(rgba, png_out)
        return png_out, "PNG", rgba
    except Exception as e:
        print(f"[WARN] {e} → JPEG 保存")
        save_white_jpeg(rgba, jpg_out)
        return jpg_out, "JPG", rgba


def process_images(base_dir: str = BASE_DIR):
    base = Path(base_dir)

    print("[WARMUP] rembg モデル初期化（初回のみ数十秒）")
    new_session("u2net")
    print("[WARMUP] OK\n")

    cleanup_previous_results(base)
    unzip_all(base)

    files = [*base.rglob("*.jpg"), *base.rglob("*.jpeg")]
    print(f"[INFO] 処理対象 JPEG: {len(files)} 枚")

    consec_fail = total_fail = 0

    for idx, p in enumerate(files, 1):
        png_out = p.parent / f"{p.stem}_bg.png"
        jpg_out = p.parent / f"{p.stem}_bg.jpg"

        bgr = cv2.imread(str(p))
        if bgr is None:
            print(f"[SKIP] 読込失敗: {p}")
            continue

        try:
            out_file, kind, rgba = process_single(bgr, png_out, jpg_out)
        except Exception as e:
            print(f"[ERR] {p.name} → {e}")
            consec_fail += 1; total_fail += 1
            continue

        kb = out_file.stat().st_size // 1024
        print(f"[{idx}] {kind} {out_file.name} {kb} KB")

        if is_failure(out_file, rgba):
            print(f"[FAIL] {out_file.name} を異常検知")
            consec_fail += 1; total_fail += 1
        else:
            consec_fail = 0

        if consec_fail >= MAX_CONSEC_FAIL:
            print(f"[ABORT] 連続 {consec_fail} 回失敗 → 停止")
            sys.exit(1)
        if total_fail >= MAX_TOTAL_FAIL:
            print(f"[ABORT] 累計 {total_fail} 件失敗 → 停止")
            sys.exit(1)


if __name__ == "__main__":
    process_images()
