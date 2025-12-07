# CR-FASTAPI-016: Orchestrator の UI（Gradio）依存分離

- **CR-ID**: CR-FASTAPI-016
- **Status**: Completed
- **Date**: 2025-12-08

## 1. 概要

### 目的
FastAPI の API テスト実行時に Gradio / UI 層が import されてしまう問題を解消する。

### ゴール
- `pytest tests/api` 実行時に Gradio / UI 関連モジュールが一切 import されない状態にする
- Orchestrator（core）の import だけで UI が起動しないようにする
- 依存方向を「Core ← UI / API」に統一

## 2. 実装内容

### 変更ファイル

**src/nexuscore/agents/requirement_agent.py**:
- Gradio の import をモジュールレベルから lazy import（関数内 import）に変更
- `launch_gradio_ui()` メソッド内でのみ Gradio を import するように修正

### 変更前
```python
import gradio as gr  # モジュールレベルで import
```

### 変更後
```python
# Gradio は lazy import（launch_gradio_ui() 内でのみ import）で UI 依存を分離

def launch_gradio_ui(self, share: bool = False) -> Dict[str, Any]:
    # Lazy import: Gradio はこのメソッド内でのみ import
    try:
        import gradio as gr
    except ImportError:
        # フォールバック処理
```

## 3. 動作確認

- ✅ `RequirementAgent` を import しても Gradio が読み込まれない
- ✅ `Orchestrator` を import しても Gradio が読み込まれない
- ✅ `FastAPI app` を import しても Gradio が読み込まれない
- ✅ `pytest tests/api` が正常に実行される

## 4. 完了条件

- ✅ `pytest tests/api` が Gradio / UI 非依存で完了する
- ✅ Orchestrator / Core モジュールから Gradio / UI モジュールへの直接 import が存在しない
- ✅ FastAPI API エントリポイントが UI を import していない
- ✅ 既存の FastAPI エンドポイント仕様は変わっていない

