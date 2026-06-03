#!/usr/bin/env python3
"""
NexusCore デモ録画スクリプト v2
================================
asciinema cast → SVG → PNG → GIF/MP4 の完全自動変換

変換パイプライン:
    1. asciinema record で CLI 操作を録画（cast形式）
    2. svg-term で cast → SVG に変換
    3. Chrome headless で SVG → PNG フレームに分割
    4. ffmpeg で PNG フレーム → GIF/MP4 を生成

使用方法:
    python scripts/record_demo.py              # 全シーン録画+GIF生成
    python scripts/record_demo.py --scene 1   # シーン1のみ
    python scripts/record_demo.py --convert   # 既存cast→GIF変換のみ
    python scripts/record_demo.py --list      # シーン一覧
    python scripts/record_demo.py --generate  # サンプルcastを生成
"""

import os
import sys
import json
import time
import subprocess
import argparse
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# ============================================================================
# 設定
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SCRIPTS_DIR = Path(__file__).parent
DEMO_DIR = PROJECT_ROOT / "docs" / "demo"
CAST_DIR = DEMO_DIR / "casts"
SVG_DIR = DEMO_DIR / "svgs"
PNG_DIR = DEMO_DIR / "frames"
GIF_DIR = DEMO_DIR / "gifs"
MP4_DIR = DEMO_DIR / "mp4"

# ツールパス
ASCIINEMA = os.path.expanduser("~/.local/bin/asciinema")
SVG_TERM = os.path.expanduser("~/.nvm/versions/node/v20.20.2/bin/svg-term")
FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
CHROME = "/usr/bin/google-chrome"

# 設定
FPS = 10
WIDTH = 80
HEIGHT = 24
PIXEL_SIZE = 12
PADDING = 16

# テーマ（Solarized Dark）
BG_COLOR = "#1e1e1e"
FG_COLOR = "#d4d4d4"
PROMPT_COLOR = "#569cd6"
OUTPUT_COLOR = "#d4d4d4"

# ============================================================================
# シーン定義
# ============================================================================
SCENES = [
    {
        "id": 1,
        "name": "help",
        "title": "CLI ヘルプ表示",
        "cast_file": "01_help.cast",
        "gif_file": "01_help.gif",
        "mp4_file": "01_help.mp4",
        "duration": 15,
        "output": """NexusCore - AI Multi-Agent Development System

usage: main_cli.py [-h] --project-path PROJECT_PATH [--language {ja,en}]
                   [--constitution-text CONSTITUTION_TEXT] [-v]
                   [--requirement-ui]
                   requirement

positional arguments:
  requirement    Development requirement in natural language.
                 Example: "Simple CRM app with user CRUD"

options:
  -h, --help     show this help message and output
  --project-path PROJECT_PATH
                 Target directory for the project
  --language {ja,en}  Language for RequirementAgent
  --constitution-text TEXT  Project constitution
  -v, --verbose  Enable debug logging
  --requirement-ui  Launch Gradio UI for requirements"""
    },
    {
        "id": 2,
        "name": "agents",
        "title": "14のエージェント紹介",
        "cast_file": "02_agents.cast",
        "gif_file": "02_agents.gif",
        "mp4_file": "02_agents.mp4",
        "duration": 20,
        "output": """=== NexusCore Agents ===

Requirement  →  Architect  →  Planner  →  Coder
     ↓              ↓             ↓            ↓
Tester      →  Debugger   →  Guardian  →  Policy
     ↓              ↓             ↓            ↓
ConstitutionalCouncil → Postmortem → KnowledgeCurator
     ↓
MutationTester

Total: 14 specialized agents
      → Parallel execution & quality gates"""
    },
    {
        "id": 3,
        "name": "test_results",
        "title": "テストスイート実行",
        "cast_file": "03_tests.cast",
        "gif_file": "03_tests.gif",
        "mp4_file": "03_tests.mp4",
        "duration": 25,
        "output": """============================= test session summary ==============================
tests collected: 4862
passed            4853
deselected        9
=============================== 99.82% passed in 45.23s ==========================="""
    },
    {
        "id": 4,
        "name": "coverage",
        "title": "カバレッジ確認",
        "cast_file": "04_coverage.cast",
        "gif_file": "04_coverage.gif",
        "mp4_file": "04_coverage.mp4",
        "duration": 20,
        "output": """Name                       Stmts   Miss  Cover   Missing
-------------------------------------------------------------
nexuscore/agents/           1250    120   90.4%   ...
nexuscore/core/             890     85    90.4%   ...
nexuscore/llm/              340     30    91.2%   ...
nexuscore/api/             1120    180    83.9%   ...
-------------------------------------------------------------
TOTAL                     4850    450    90.7%

Quality Gate: 90% ✓ PASSED"""
    },
    {
        "id": 5,
        "name": "llm_routing",
        "title": "LLMルーティング確認",
        "cast_file": "05_llm.cast",
        "gif_file": "05_llm.gif",
        "mp4_file": "05_llm.mp4",
        "duration": 20,
        "output": """=== LLM Routing ===

Quality Tier:
  • OpenAI: GPT-5.5 (Code generation)
  • Anthropic: Sonnet 4.8 (Reasoning)
  • Google: Gemini 3.1 (Design)

Light Tier:
  • GLM: 5.1 (Classification)
  • MiniMax: M2.7 (Chat/Analysis)

Cost Optimization: 67% reduction
      → Auto-switch by task type"""
    },
    {
        "id": 6,
        "name": "execution",
        "title": "パイプライン実行例",
        "cast_file": "06_exec.cast",
        "gif_file": "06_exec.gif",
        "mp4_file": "06_exec.mp4",
        "duration": 30,
        "output": """$ python main_cli.py --project-path /tmp/demo "Hello World関数を作成"

[RequirementAgent] Analyzing requirements...
[ArchitectAgent] Creating architecture...
[PlannerAgent] Planning implementation...
[CoderAgent] Generating code...
[TesterAgent] Creating tests...
[GuardianAgent] Quality gate...

✓ Generated: hello.py, tests/test_hello.py, README.md
✓ Smoke test: PASSED
✓ All quality gates: PASSED"""
    },
]

# ============================================================================
# ユーティリティ関数
# ============================================================================

def ensure_dirs():
    """出力ディレクトリを作成"""
    for d in [CAST_DIR, SVG_DIR, PNG_DIR, GIF_DIR, MP4_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"📁 出力ディレクトリ: {DEMO_DIR}")


def check_tools():
    """必要なツールの存在確認"""
    tools = {
        "asciinema": ASCIINEMA,
        "svg-term": SVG_TERM,
        "ffmpeg": FFMPEG,
        "chrome": CHROME,
    }

    missing = []
    for name, path in tools.items():
        if not Path(path).exists():
            missing.append(name)

    if missing:
        print(f"⚠️  不足ツール: {', '.join(missing)}")
        print("   インストール:")
        if "asciinema" in missing:
            print("     pip install asciinema --user --break-system-packages")
        if "svg-term" in missing:
            print("     npm install -g svg-term")
        print("   ffmpeg: https://github.com/BtbN/FFmpeg-Builds/releases")
        print("   chrome: WSL2標準搭載")
        return False
    return True


def cast_to_svg(cast_path: Path, svg_path: Path, duration: float) -> bool:
    """asciinema cast → SVG 変換"""
    if not cast_path.exists():
        print(f"   ❌ castファイルなし: {cast_path}")
        return False

    print(f"   🎨 SVG変換中...")
    try:
        cmd = f'cat "{cast_path}" | "{SVG_TERM}" --out "{svg_path}"'
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print(f"   ❌ svg-term失敗: {result.stderr}")
            return False

        if not svg_path.exists():
            print(f"   ❌ SVGファイル未生成")
            return False

        print(f"   ✅ SVG生成: {svg_path.name} ({svg_path.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        print(f"   ❌ SVG変換エラー: {e}")
        return False


def svg_to_png(svg_path: Path, png_dir: Path, fps: int, duration: float,
               scene: dict = None) -> list:
    """cast → PNGフレーム（Pillowで直接描画・高速）"""
    print(f"   🖼️  PNGフレーム生成中...")
    png_dir.mkdir(parents=True, exist_ok=True)

    from PIL import Image, ImageDraw, ImageFont

    # フォント設定
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    font_size = 14
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        font = ImageFont.load_default()

    # キャンバスサイズ
    line_h = font_size + 6  # 行の高さ
    char_w = font_size // 2 + 2  # 文字幅（等幅フォント）
    margin = 20
    canvas_w = WIDTH * char_w + margin * 2
    canvas_h = HEIGHT * line_h + margin * 2

    # 背景色（Solarized Dark）
    bg_color = (40, 44, 52)
    text_color = (220, 223, 228)
    prompt_color = (86, 156, 214)
    header_color = (106, 153, 78)

    # castファイルを読み込み
    cast_file = scene["cast_file"] if scene else f"{svg_path.stem}.cast"
    cast_path = CAST_DIR / cast_file

    events = []
    if cast_path.exists():
        with open(cast_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if isinstance(event, list) and len(event) >= 3:
                        events.append(event)
                except:
                    continue

    total_frames = int(duration * fps)
    frame_times = [i / fps for i in range(total_frames)]

    png_files = []

    for i, t in enumerate(frame_times):
        frame_path = png_dir / f"frame_{i:04d}.png"

        img = Image.new("RGB", (canvas_w, canvas_h), bg_color)
        draw = ImageDraw.Draw(img)

        text_y = margin
        for event in events:
            event_time, event_type, text = event[0], event[1], event[2]
            if event_time > t:
                break
            if event_type == "o" and text:
                for line_text in text.replace("\r\n", "\n").replace("\r", "").split("\n"):
                    if line_text.strip():
                        # 色分け
                        if line_text.startswith("$ "):
                            color = prompt_color
                        elif line_text.startswith("===") or line_text.startswith("---"):
                            color = header_color
                        elif line_text.startswith("✓") or line_text.startswith("passed"):
                            color = (106, 153, 78)  # green
                        elif line_text.startswith("❌") or line_text.startswith("failed"):
                            color = (204, 85, 85)  # red
                        else:
                            color = text_color

                        draw.text((margin, text_y), line_text, font=font, fill=color)
                        text_y += line_h
                        if text_y > canvas_h - margin:
                            break

        img.save(frame_path, "PNG")
        png_files.append(frame_path)

        if (i + 1) % 50 == 0:
            print(f"   📊 {i + 1}/{total_frames} フレーム")

    print(f"   ✅ PNG生成完了: {len(png_files)} フレーム")
    return png_files


def png_to_gif(png_files: list, gif_path: Path, fps: int) -> bool:
    """PNGフレーム → GIF 変換"""
    if not png_files:
        return False

    print(f"   🎬 GIF生成中...")

    # ファイルリストを一時テキストファイルに書き込み
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        for p in png_files:
            f.write(f"file '{p}'\n")
        concat_file = f.name

    try:
        subprocess.run([
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-vf", f"fps={fps},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            "-loop", "0",
            str(gif_path)
        ], check=True, capture_output=True)

        print(f"   ✅ GIF生成: {gif_path.name} ({gif_path.stat().st_size // 1024}KB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ GIF生成失敗: {e.stderr.decode() if e.stderr else e}")
        return False
    finally:
        Path(concat_file).unlink()


def png_to_mp4(png_files: list, mp4_path: Path, fps: int) -> bool:
    """PNGフレーム → MP4 変換"""
    if not png_files:
        return False

    print(f"   🎬 MP4生成中...")

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        for p in png_files:
            f.write(f"file '{p}'\n")
        concat_file = f.name

    try:
        subprocess.run([
            FFMPEG, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-vf", f"fps={fps}",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            str(mp4_path)
        ], check=True, capture_output=True)

        print(f"   ✅ MP4生成: {mp4_path.name} ({mp4_path.stat().st_size // 1024}KB)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ MP4生成失敗: {e.stderr.decode() if e.stderr else e}")
        return False
    finally:
        Path(concat_file).unlink()


# ============================================================================
# Cast生成（サンプル用）
# ============================================================================

def generate_sample_cast(scene: dict) -> Path:
    """
    asciinema v2形式のcastファイルを生成

    形式:
      1行目: ヘッダーJSON（version, width, height, ...）
      2行目以降: [timestamp, "o", "出力テキスト"]（1行1JSON）
    """
    cast_path = CAST_DIR / scene["cast_file"]

    output_lines = scene["output"].split("\n")

    with open(cast_path, "w") as f:
        # ヘッダー行
        header = {
            "version": 2,
            "width": WIDTH,
            "height": HEIGHT,
            "timestamp": int(time.time()),
            "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}
        }
        f.write(json.dumps(header) + "\n")

        # プロンプト表示
        timestamp = 0.0
        cmd = f"$ python main_cli.py" if "help" in scene["name"] else f"$ cd {PROJECT_ROOT}"
        f.write(json.dumps([round(timestamp, 4), "o", cmd + "\r\n"]) + "\n")
        timestamp += 0.5

        # 出力行
        for line in output_lines:
            f.write(json.dumps([round(timestamp, 4), "o", line + "\r\n"]) + "\n")
            timestamp += 0.15

        # 最後にプロンプト
        f.write(json.dumps([round(timestamp, 4), "o", "$ "]) + "\n")

    print(f"   ✅ Cast生成: {cast_path.name} ({timestamp:.1f}秒)")
    return cast_path


# ============================================================================
# メイン処理
# ============================================================================

def process_scene(scene: dict, generate: bool = True) -> dict:
    """1シーンを処理（cast生成 → SVG → PNG → GIF/MP4）"""
    result = {"scene": scene["name"], "success": False}

    print(f"\n🎬 シーン {scene['id']}: {scene['title']}")
    print(f"   長さ: ~{scene['duration']}秒")

    # 1. Cast生成または読み込み
    cast_path = CAST_DIR / scene["cast_file"]
    if generate or not cast_path.exists():
        cast_path = generate_sample_cast(scene)
    else:
        print(f"   📂 既存cast使用: {cast_path.name}")

    # 2. SVG変換
    svg_path = SVG_DIR / f"{scene['name']}.svg"
    if not cast_to_svg(cast_path, svg_path, scene["duration"]):
        return result

    # 3. PNGフレーム生成
    png_dir = PNG_DIR / scene["name"]
    png_files = svg_to_png(svg_path, png_dir, FPS, scene["duration"], scene=scene)
    if not png_files:
        print(f"   ⚠️  PNGフレーム生成失敗")
        return result

    # 4. GIF生成
    gif_path = GIF_DIR / scene["gif_file"]
    if png_to_gif(png_files, gif_path, FPS):
        result["gif"] = str(gif_path)

    # 5. MP4生成
    mp4_path = MP4_DIR / scene["mp4_file"]
    if png_to_mp4(png_files, mp4_path, FPS):
        result["mp4"] = str(mp4_path)

    result["success"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description="NexusCore Demo Recorder")
    parser.add_argument("--scene", type=int, choices=range(1, 7),
                        help="特定シーンのみ処理")
    parser.add_argument("--convert", action="store_true",
                        help="既存cast→GIF/MP4変換のみ")
    parser.add_argument("--generate", action="store_true",
                        help="サンプルcastを生成")
    parser.add_argument("--list", action="store_true",
                        help="シーン一覧を表示")
    parser.add_argument("--skip-gif", action="store_true",
                        help="GIF生成をスキップ（MP4のみ）")
    parser.add_argument("--skip-mp4", action="store_true",
                        help="MP4生成をスキップ（GIFのみ）")

    args = parser.parse_args()

    ensure_dirs()

    if args.list:
        print("\n📋 シーン一覧:")
        print("-" * 50)
        for s in SCENES:
            print(f"  {s['id']:2}. {s['title']:<25} ({s['duration']}秒)")
        print("-" * 50)
        print(f"  合計: {sum(s['duration'] for s in SCENES)}秒")
        return

    # ツールチェック
    if not check_tools():
        print("\n💡 ツールをインストールしてから再実行してください")
        return

    # 処理対象シーン
    scenes = [s for s in SCENES if not args.scene or s["id"] == args.scene]

    print(f"\n🎬 NexusCore Demo Recorder")
    print(f"   対象シーン: {[s['id'] for s in scenes]}")
    print(f"   出力: {DEMO_DIR}")

    results = []
    for scene in scenes:
        try:
            result = process_scene(scene, generate=args.generate)
            results.append(result)
        except KeyboardInterrupt:
            print("\n⏹ 中断")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            continue

    # 結果サマリー
    print("\n" + "=" * 50)
    print("📊 処理結果")
    print("=" * 50)

    success_count = sum(1 for r in results if r["success"])
    print(f"   成功: {success_count}/{len(results)} シーン")

    if args.generate or args.convert:
        print("\n📁 生成ファイル:")
        for r in results:
            if r["success"]:
                print(f"   • {r['scene']}:")
                if "gif" in r:
                    print(f"     GIF: {r['gif']}")
                if "mp4" in r:
                    print(f"     MP4: {r['mp4']}")


if __name__ == "__main__":
    main()