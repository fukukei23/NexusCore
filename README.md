# NexusCore

**NexusCore** は自律型 AI エージェント群を組み合わせてソフトウェア開発支援を行うフレームワークです。  
道具立て（エージェント／Orchestrator／LLM ルーター）を分離しつつ、必要なツール・UI・テストを同一リポジトリ内で管理する設計になっています。

- 🧠 **AIコード修復／開発支援**：Requirement→Planning→Coding→Testing まで各フェーズを担当するエージェント。
- ☁️ **SaaS展開を意識した分離設計**：LLM/エージェント/オーケストレータを独立レイヤーで構築。

---

## 📂 プロジェクト構成


主要な構成を踏まえ、以下のディレクトリ構成と設定ファイルが重要です。

### 主要ディレクトリ構成

```
NexusCore/
├── src/nexuscore/
│   ├── agents/           # 構成エージェント（planner, coder, debugger, guardian, policy 等）
│   ├── core/             # Orchestrator、NPE インテグレーション、主要フロー制御
│   ├── llm/              # LLMRouter、Provider 統合、プロンプト管理
│   ├── modules/          # エージェントから呼ばれるコード生成・テスト・差分表示ツール
│   ├── npe/              # 予算・ポリシー・ログ・ガード機能の集合
│   └── gradio_app/       # UI/ダッシュボード/修復タイムライン（必要に応じて Streamlit 構成も）
├── dev_tools/             # Fast Lane チェックや開発支援スクリプト
├── tools/                 # ファイル一覧取得・エクスポート・ダッシュボードなどの補助ユーティリティ
├── tests/                 # pytest ベースのユニット / 統合テスト群
├── output/                # 実行ログ / 集計 / 一時ファイル（gitignore 対象）
└── .venv/                 # 仮想環境（WSL 操作時に生成・使用）
```

### 重要な設定ファイル

- `.env` / `.env.template` … OpenAI や Gemini など LLM API キー、予算、動作モードなど環境変数をまとめたファイル。`.env` は `.env.template` をコピーして内容を埋めたもの。
- `requirements.txt` / `requirements.lock.txt` / `pyproject.toml` … Python 依存の宣言とロック。依存追加時は `pip freeze > requirements.lock.txt` などで整合を取るのが重要です。
- `dev_tools/fast_lane_check.py` … 差分解析と Fast Lane 判定用。CI に組み込む場合は `python -m dev_tools.fast_lane_check --json` をコマンド化します。
- `.gitignore` / `output/` 以下 / `.venv/` … ログや生成ファイル、仮想環境などの除外を定義。`output/core_files.txt` などの共有リストを活用する際も位置を参考に。
- `src/nexuscore/config/config.py` & `src/nexuscore/config/generate_secrets.py` … プロジェクト固有の設定ロードと秘密情報生成を担うモジュール。README 内の環境変数手順と合わせて使います。

---

## 🚀 Quick Start

### 1. WSL (Ubuntu) 環境での基本手順

1. `\\wsl.localhost\Ubuntu\home\yn441611\NexusCore`（Linux シェルでは `/home/yn441611/NexusCore`）に移動し、これを作業ルートにします。  
2. システム Python には `pip` が入っていないため、`python -m venv .venv` で仮想環境を作成します。  
3. `.venv/bin/python -m pip install -r requirements.txt` で依存をインストール。  
4. 実行時は `.venv/bin/python main_cli.py …` や `PYTHONPATH=src .venv/bin/pytest …` を使う、または `.venv/bin/activate` してから `python` / `pip` を呼び出してください。  
5. ネイティブなログ・出力先は `/home/yn441611/NexusCore/...` に向け、権限エラーを回避します。  
6. 依存を追加したら `pip freeze > requirements.lock.txt` などでロックファイルを更新して共有してください。

### 2. 依存要件

- Python **3.11+**
- Git
- Docker（任意：サービス連携 / デプロイ用）
- `pip-tools`：`pip install pip-tools`

### 3. ローカルで試すコマンド

- **Fast lane regression gate**  
  リポジトリの差分検査には `dev_tools.fast_lane_check` を使います。

  ```bash
  .venv/bin/python -m dev_tools.fast_lane_check --json
  ```

  - `--base` … 比較対象ブランチ（既定 `origin/main`）
  - `--max-files` / `--max-lines-total` / `--max-lines-per-file` … 切り分けパラメータ
  - `FAST_LANE_FORCE=1` を使うとしきい値を無視

- **重要ファイル一覧の取得**  

  ```bash
  .venv/bin/python -m tools.list_core_files --format text
  ```

  `--include` / `--exclude` でパターンを追加したり、`--format json` / `--output` で整形できます。

## 💬 Codex / AI への指示

- 対話の最初に Codex や他の AI に渡すプロンプトの冒頭で `「日本語でお願いします」` のテンプレート文を使うようにしてください。この README にそのテンプレートを残しておくと、各チャットが新しくなっても同じ日本語指定を繰り返し注入でき、記述忘れも防げます。

### 4. CLI 起動例

```bash
.venv/bin/python main_cli.py --project-path /tmp/nxcore --language ja "ChatOps ダッシュボードを作る"
```

引数例：`--constitution-text` でプロジェクト方針、`--requirement-ui` で RequirementAgent UI モード、`-v` で詳細ログ出力。

---

## 🧪 テストと検証

- `PYTHONPATH=src .venv/bin/pytest tests/core/test_orchestrator.py`
- `PYTHONPATH=src .venv/bin/pytest tests/agents/test_policy_agent.py`
- `PYTHONPATH=src .venv/bin/pytest tests/gradio_app/test_app_ui.py`

全体のテスト・CI は `PYTHONPATH=src` を忘れずに設定してください。

---

## 🧰 補足メモ

- `.env.template` をコピーして `.env` を作成し、API キーや最大予算などを記入してください。  
- `output/` 以下にログや自動テスト結果がたまりますので、コミット不要のものは `.gitignore` に入れています。  
- 大型変更を加えるときは `python -m tools.list_core_files --format json` などで影響範囲を確認しつつ、`tests/` の適切なユニットを更新してください。  
- 新しい LLM プロバイダ追加時は `src/nexuscore/llm/llm_router.py` に設定を追加し、`src/nexuscore/npe` のポリシーや予算にも反映してください。
