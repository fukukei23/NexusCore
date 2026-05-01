# Unified Gradio UI LLM連携 完了レポート

**日時**: 2026-05-01
**対象ファイル**: `src/nexuscore/ui/unified_gradio_ui.py`

## 変更概要

統合Gradio UIのプレースホルダー実装を実際のLLM呼び出し（GLM-5.1）に置き換え、Test Runnerのバグを修正した。

## 変更内容

### LLM連携
- `dotenv` で `~/.secrets.env` からAPIキー自動読み込み
- `LLMRouter` 初期化、`model="glm:glm-5.1"` でルーティング
- Code/Promptタブ: プロンプト→LLM→コード生成
- AI Revisionタブ: コード+修正指示→LLM→修正コード生成
- マークダウンコードブロック自動除去

### Test Runner修正
- `subprocess.run(["pytest -q"])` → `shlex.split()` でコマンド分割
- `pytest` 未検出 → `sys.executable -m pytest` に変更
- ファイル選択: フラット一覧 → フォルダ→ファイルの2段階ドロップダウン

### 起動方法
```bash
.venv/bin/python src/nexuscore/ui/unified_gradio_ui.py
# http://127.0.0.1:7860
```

## 動作確認

| タブ | 結果 |
|---|---|
| Code / Prompt | ✅ GLM-5.1でコード生成 |
| AI Revision | ✅ GLM-5.1で修正コード生成 |
| Test Runner | ✅ pytest実行・結果表示 |
| History & Diff | ✅ Run レポート読み込み |

## 既知の制限
- Gemini SDK未インストール警告（機能影響なし）
- OpenAI 429レート制限 → GLM固定で回避中
- Gradio 6.0 theme引数非推奨警告（機能影響なし）
