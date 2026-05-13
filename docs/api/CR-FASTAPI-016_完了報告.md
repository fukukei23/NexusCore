# CR-FASTAPI-016: Orchestrator の UI（Gradio）依存分離 - 完了レポート

## 実装日時
2025年12月8日

## 概要

### 目的
FastAPI の API テスト実行時に Gradio / UI 層が import されてしまう問題を解消する。

### ゴール
- `pytest tests/api` 実行時に Gradio / UI 関連モジュールが一切 import されない状態にする
- Orchestrator（core）の import だけで UI が起動しないようにする
- 依存方向を「Core ← UI / API」に統一

## 実装ステップ

### Step 1: 依存関係の実態把握
- Gradio / UI を import している箇所を洗い出し
- `RequirementAgent` がモジュールレベルで `import gradio as gr` していることを確認

### Step 2: Core と UI の切り離し
- `RequirementAgent` の Gradio import を lazy import（関数内 import）に変更
- `launch_gradio_ui()` メソッド内でのみ Gradio を import するように修正

## 変更ファイル一覧

### 変更ファイル
- `src/nexuscore/agents/requirement_agent.py` - Gradio import を lazy import に変更

## 動作確認結果

### テスト実行
```bash
python3 -c "from nexuscore.agents.requirement_agent import RequirementAgent; print('Gradio imported:', 'gradio' in sys.modules)"
# 結果: Gradio imported: False ✅

python3 -c "from nexuscore.core.orchestrator import Orchestrator; print('Gradio imported:', 'gradio' in sys.modules)"
# 結果: Gradio imported: False ✅

python3 -c "from nexuscore.api.fastapi_app import app; print('Gradio imported:', 'gradio' in sys.modules)"
# 結果: Gradio imported: False ✅
```

### API テスト実行
```bash
pytest tests/api/test_fastapi_auth.py::test_auth_missing_header_returns_401 -v
# 結果: PASSED ✅
```

## 設計上の改善点

- **依存方向の明確化**: Core → UI の逆依存を排除し、UI → Core の一方向依存に統一
- **Lazy Import パターン**: UI 関連の import を必要時のみに遅延させることで、テスト時の不要な読み込みを防止

## 既知の制約・注意事項

- `RequirementAgent.launch_gradio_ui()` を呼び出す場合は Gradio が必要
- UI 機能を使用しない場合は Gradio がインストールされていなくても動作する

## 次のステップ

- 他の UI 関連モジュール（Streamlit など）も同様に lazy import 化を検討
- UI 起動用スクリプトと API サーバー起動用スクリプトの明確な分離

