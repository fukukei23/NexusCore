#!/usr/bin/env python3
"""
SDK 自動生成スクリプト

FastAPI の OpenAPI 仕様書を元に、Python / TypeScript 向け SDK を自動生成する。

使用方法:
    python tools/generate_sdk.py [--python|--typescript|--all]
    make sdk
    make sdk-python
    make sdk-ts
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent
SDK_PYTHON_DIR = PROJECT_ROOT / "sdk" / "python"
SDK_TYPESCRIPT_DIR = PROJECT_ROOT / "sdk" / "typescript"
OPENAPI_URL = "http://localhost:8000/api/openapi.json"


def check_openapi_generator() -> tuple[bool, Optional[str]]:
    """
    openapi-generator-cli が利用可能か確認する。

    Returns:
        (is_available, command): 利用可能な場合 (True, コマンド), そうでない場合 (False, None)
    """
    # プロジェクトローカルの node_modules を優先チェック
    local_cli = PROJECT_ROOT / "node_modules" / ".bin" / "openapi-generator-cli"
    if local_cli.exists() and local_cli.is_file():
        return True, str(local_cli)

    # npx が利用可能か確認
    npx_path = shutil.which("npx")
    if npx_path:
        # npx 経由で openapi-generator-cli を試す
        try:
            result = subprocess.run(
                ["npx", "--yes", "openapi-generator-cli", "version"],
                capture_output=True,
                text=True,
                timeout=30,  # タイムアウトを延長（初回ダウンロードに時間がかかる場合がある）
            )
            if result.returncode == 0:
                return True, "npx --yes openapi-generator-cli"
        except subprocess.TimeoutExpired:
            # タイムアウトは無視（ネットワークが遅い場合など）
            pass
        except FileNotFoundError:
            # npx が見つからない場合は次へ
            pass
        except Exception as e:
            # その他のエラーは無視（デバッグ時はコメントアウトして確認可能）
            pass

    # グローバルにインストールされた openapi-generator-cli を確認
    global_cli = shutil.which("openapi-generator-cli")
    if global_cli:
        try:
            result = subprocess.run(
                [global_cli, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, global_cli
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Java 版の openapi-generator を試す
    java_generator = shutil.which("openapi-generator")
    if java_generator:
        try:
            result = subprocess.run(
                [java_generator, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return True, java_generator
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return False, None


def fetch_openapi_spec(url: str) -> dict:
    """
    OpenAPI 仕様書を取得する。

    Args:
        url: OpenAPI JSON の URL

    Returns:
        OpenAPI 仕様書（dict）

    Raises:
        RuntimeError: 取得に失敗した場合
    """
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to fetch OpenAPI spec from {url}: {e}")


def generate_python_sdk(openapi_spec_path: Path, output_dir: Path, generator_cmd: str) -> bool:
    """
    Python SDK を生成する。

    Args:
        openapi_spec_path: OpenAPI 仕様書のパス
        output_dir: 出力先ディレクトリ
        generator_cmd: openapi-generator コマンド

    Returns:
        成功した場合 True
    """
    print(f"Generating Python SDK to {output_dir}...")

    # 出力ディレクトリを作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # openapi-generator コマンドを実行
    cmd = [
        *generator_cmd.split(),
        "generate",
        "-i", str(openapi_spec_path),
        "-g", "python",
        "-o", str(output_dir),
        "--additional-properties=packageName=nexuscore_sdk,packageVersion=1.0.0",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Python SDK generated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate Python SDK: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def generate_typescript_sdk(openapi_spec_path: Path, output_dir: Path, generator_cmd: str) -> bool:
    """
    TypeScript SDK を生成する。

    Args:
        openapi_spec_path: OpenAPI 仕様書のパス
        output_dir: 出力先ディレクトリ
        generator_cmd: openapi-generator コマンド

    Returns:
        成功した場合 True
    """
    print(f"Generating TypeScript SDK to {output_dir}...")

    # 出力ディレクトリを作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # openapi-generator コマンドを実行
    cmd = [
        *generator_cmd.split(),
        "generate",
        "-i", str(openapi_spec_path),
        "-g", "typescript-axios",
        "-o", str(output_dir),
        "--additional-properties=npmName=nexuscore-sdk,npmVersion=1.0.0",
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ TypeScript SDK generated successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate TypeScript SDK: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def verify_generated_sdk(output_dir: Path, sdk_type: str) -> bool:
    """
    生成された SDK を検証する。

    Args:
        output_dir: SDK の出力先ディレクトリ
        sdk_type: SDK の種類（"python" または "typescript"）

    Returns:
        検証に成功した場合 True
    """
    if not output_dir.exists():
        print(f"❌ SDK output directory does not exist: {output_dir}")
        return False

    if sdk_type == "python":
        # Python SDK の主要ファイルを確認
        expected_files = [
            "setup.py",
            "README.md",
        ]
    elif sdk_type == "typescript":
        # TypeScript SDK の主要ファイルを確認
        expected_files = [
            "package.json",
            "README.md",
        ]
    else:
        print(f"❌ Unknown SDK type: {sdk_type}")
        return False

    missing_files = []
    for file_name in expected_files:
        file_path = output_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)

    if missing_files:
        print(f"❌ Missing required files in {sdk_type} SDK: {missing_files}")
        return False

    print(f"✅ {sdk_type} SDK verification passed")
    return True


def main() -> int:
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Generate SDK from OpenAPI spec")
    parser.add_argument(
        "--python",
        action="store_true",
        help="Generate Python SDK only",
    )
    parser.add_argument(
        "--typescript",
        action="store_true",
        help="Generate TypeScript SDK only",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate all SDKs (default)",
    )
    parser.add_argument(
        "--openapi-url",
        default=OPENAPI_URL,
        help=f"OpenAPI JSON URL (default: {OPENAPI_URL})",
    )
    parser.add_argument(
        "--openapi-file",
        help="OpenAPI JSON file path (alternative to --openapi-url)",
    )

    args = parser.parse_args()

    # 生成対象を決定
    generate_python = args.python or (not args.typescript and (args.all or not args.python))
    generate_typescript = args.typescript or (not args.python and (args.all or not args.typescript))

    # openapi-generator が利用可能か確認
    is_available, generator_cmd = check_openapi_generator()
    if not is_available or generator_cmd is None:
        print("❌ openapi-generator-cli is not available.")
        print("Please install it using one of the following methods:")
        print("  1. npm install -g @openapitools/openapi-generator-cli")
        print("  2. Install Java and openapi-generator-cli")
        print("  3. Use npx: npx --yes openapi-generator-cli")
        print("  4. Install locally: npm install --save-dev @openapitools/openapi-generator-cli")
        return 1

    print(f"✅ Using openapi-generator: {generator_cmd}")

    # OpenAPI 仕様書を取得
    if args.openapi_file:
        openapi_spec_path = Path(args.openapi_file)
        if not openapi_spec_path.exists():
            print(f"❌ OpenAPI file not found: {openapi_spec_path}")
            return 1
    else:
        # URL から取得して一時ファイルに保存
        try:
            spec = fetch_openapi_spec(args.openapi_url)
            openapi_spec_path = PROJECT_ROOT / "tmp" / "openapi.json"
            openapi_spec_path.parent.mkdir(parents=True, exist_ok=True)
            with open(openapi_spec_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, indent=2, ensure_ascii=False)
            print(f"✅ Fetched OpenAPI spec from {args.openapi_url}")
        except Exception as e:
            print(f"❌ Failed to fetch OpenAPI spec: {e}")
            print(f"Hint: Make sure FastAPI app is running on {args.openapi_url}")
            print(f"     Or use --openapi-file to specify a local OpenAPI JSON file")
            return 1

    # SDK を生成（generator_cmd は None でないことが確認済み）
    assert generator_cmd is not None  # 型チェッカーのためのアサーション
    success = True

    if generate_python:
        if not generate_python_sdk(openapi_spec_path, SDK_PYTHON_DIR, generator_cmd):
            success = False
        else:
            if not verify_generated_sdk(SDK_PYTHON_DIR, "python"):
                success = False

    if generate_typescript:
        if not generate_typescript_sdk(openapi_spec_path, SDK_TYPESCRIPT_DIR, generator_cmd):
            success = False
        else:
            if not verify_generated_sdk(SDK_TYPESCRIPT_DIR, "typescript"):
                success = False

    if success:
        print("\n✅ SDK generation completed successfully!")
        return 0
    else:
        print("\n❌ SDK generation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

