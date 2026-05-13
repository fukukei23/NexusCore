# CR-FASTAPI-018: Python SDK 商品化（v0.1.0）

## 1. 人間向け仕様書（Implementation Task Overview）

### 1.1 目的（Why）

現状の Python SDK は「OpenAPI からの自動生成アーティファクト」であり、
以下の点で「プロダクトとして利用可能な SDK」になっていない：

- バージョンが未定義／不統一（v0.1.0 としての位置づけが明確でない）
- 外部利用者向け README・導入手順・使用例が不足
- LICENSE が明確でなく、対外利用の前提が不明瞭
- pip install（ローカル or TestPyPI）での導入フローが整理されていない
- Pydantic モデル含め、型情報のドキュメントが乏しい

この CR の目的は、Python SDK を v0.1.0 として「外部に配布可能な製品レベル」に引き上げること。

### 1.2 ゴール（Outcome）

- Python SDK が Semantic Versioning に基づく v0.1.0 として明示されている
- ローカル pip install および TestPyPI への publish ができる状態
- SDK 単体の README（外部開発者向け）が存在し、次が明確になっている：
  - インストール方法（ローカル / TestPyPI）
  - 認証（API Key）設定方法
  - 代表的な API 呼び出し例（Projects / Runs / Execute など）
  - エラーコードカタログとの関係（エラーコードカタログ.md 参照方法）
- LICENSE が SDK ディレクトリ直下に存在し、NexusCore 本体と整合している
- 簡易な SDK 向けテスト（インポート確認、型レベルの smoke test）が存在
- .cursorrules における「SDK 手書き禁止」「OpenAPI からの自動生成」のポリシーを侵さずに商品化が完了している

### 1.3 スコープ（In-Scope）

Python SDK の「パッケージング・バージョニング・ドキュメント・最小テスト」の整備

次の要素を v0.1.0 として定義：
- パッケージ名（例: nexuscore-sdk-python など。既存 generator の出力実態に合わせる）
- バージョン（0.1.0）
- サポートする Python バージョン範囲

SDK ディレクトリ直下に次を追加：
- pyproject.toml または setup.py / setup.cfg
- README.md（SDK 専用）
- LICENSE（必要に応じてコピー or リンク）
- examples/ ディレクトリ（簡単なサンプルコード）
- tests/ ディレクトリ（インポート・基本 API 呼び出しの smoke test）

Makefile または tools/generate_sdk.py に、Python SDK のビルド・publish 手順を追記：
- make sdk-python で SDK 再生成＋バージョン反映
- make sdk-python-build で wheel / sdist 生成
- make sdk-python-publish-test で TestPyPI に publish

### 1.4 非スコープ（Out-of-Scope）

- TypeScript SDK（これは CR-FASTAPI-019 で扱う）
- 公開 PyPI への正式公開（本 CR では TestPyPI まで）
- SDK API の設計そのもの（メソッド名や呼び出しパターンの大幅変更）は行わない
- OpenAPI 自体の変更（必要なら別 CR で行う）

### 1.5 前提・制約

- .cursorrules により：
  - SDK コード（auto-generated 部分）の手書き修正は禁止
  - SDK の変更は原則 tools/generate_sdk.py による自動生成が前提
- 既存の SDK 出力場所は sdk/python/ 以下にあるものとする（実際のディレクトリ名は Cursor 側で探索）
- OpenAPI Generator のツールチェーンは CR-FASTAPI-012A の仕様（openapi-generator-cli）に従う
- プロジェクト全体の LICENSE 方針に従う（新規ライセンス選定は行わない）

### 1.6 実装タスク一覧

1. **現状 SDK 構成のインベントリ**
   - sdk/python/ 以下のディレクトリ構造と generator 出力を調査
   - 生成物とそうでないファイルの境界を明確化

2. **パッケージングファイルの作成**
   - sdk/python/ 直下に pyproject.toml または setup.py / setup.cfg を追加
   - パッケージ名、バージョン（0.1.0）、依存関係、Python 要件を定義

3. **LICENSE の配置**
   - SDK 直下に LICENSE を配置（既存 LICENSE のコピーまたは参照）

4. **SDK 専用 README の作成**
   - 導入方法（pip install / TestPyPI）
   - 認証設定（API Key）
   - 代表的なコード例（Projects 一覧取得など）
   - エラーコードの扱い（ERROR_CODE_CATALOG との対応）

5. **examples ディレクトリの作成**
   - examples/basic_usage.py など、最小限のサンプルを配置

6. **tests ディレクトリの作成**
   - インポート・クライアント生成の smoke test
   - ローカル FastAPI サーバーに対する簡易な HTTP モック／スキップ付きテスト
   - 「SDK が生成済み／インポート可能」であることを確認するテスト

7. **生成スクリプト／Makefile の整備**
   - tools/generate_sdk.py に Python SDK v0.1.0 対応を反映（必要であれば）
   - Makefile に sdk-python / sdk-python-build / sdk-python-publish-test ターゲットを追加

8. **Completion Report の作成**
   - docs/api/CR-FASTAPI-018_完了報告.md を新規作成
   - README / docs/api/README に CR-FASTAPI-018 の完了とリンクを追記

### 1.7 リスク・依存関係

- OpenAPI が不安定な場合、SDK v0.1.0 の互換性がすぐ破壊されるリスク
- 自動生成されたコードへの依存が強いため、将来の "手書きラッパー" 追加には別 CR が必要
- TestPyPI への publish 設定がローカル環境依存になりやすい（環境変数やトークン管理が必要）

### 1.8 Definition of Done（完了条件）

- Python SDK が pip install <path> でローカルインストール可能
- TestPyPI に 0.1.0 として publish 可能な状態（dry-run・設定レベル）である
- SDK 専用 README, LICENSE, examples, tests が sdk/python/ 以下に整備されている
- tools/generate_sdk.py＋Makefile で自動生成〜ビルドまで回せる
- docs/api/CR-FASTAPI-018_完了報告.md が存在し、README からリンクされている
- .cursorrules の「SDK 手書き禁止」ルールに違反していない（auto-generated 部分は未改変）

## 2. Cursor 用実装指示書（Implementation Instruction for Cursor）

### 2.1 変更対象ファイル（Targets）

Cursor MUST operate on (create or modify) the following:

- sdk/python/ 配下（ただし 自動生成コード部分の直接編集は禁止）
- sdk/python/pyproject.toml または sdk/python/setup.py / setup.cfg
- sdk/python/README.md
- sdk/python/LICENSE
- sdk/python/examples/（新規）
- sdk/python/tests/（新規）
- tools/generate_sdk.py
- Makefile
- docs/api/CR-FASTAPI-018_完了報告.md（新規作成）
- docs/api/README.md
- README.md

Cursor MUST NOT:

- sdk/python/ の auto-generated ソースファイル（generator が吐き出すクライアントコード）を直接編集してはならない
- OpenAPI 仕様書（YAML/JSON）をこの CR で変更してはならない（別 CR 前提）

### 2.2 必須実装内容（Required Changes）

Cursor MUST perform the following:

1. **Python SDK パッケージメタデータの定義**
   - sdk/python/pyproject.toml もしくは setup.py / setup.cfg を作成し、
     - パッケージ名
     - バージョン = 0.1.0
     - Python 対応バージョン
     - 依存関係（requests など、既存 SDK が前提とするライブラリ）
   を設定すること。

2. **LICENSE の配置**
   - プロジェクト全体の LICENSE 方針に合わせて、sdk/python/LICENSE を作成すること。
   - 既存 LICENSE ファイルがリポジトリルートにある場合は内容をコピーすること。

3. **SDK 専用 README の作成**
   - sdk/python/README.md を作成し、少なくとも次を含めること：
     - 概要（NexusCore Python SDK とは何か）
     - インストール方法
       - ローカルインストール例: pip install .（sdk/python ディレクトリで実行）
       - TestPyPI からのインストール例（プレースホルダーで可）
     - 認証（API Key）の設定方法
       - 環境変数 / 明示指定 など、現状の SDK が取る方式を明記
     - 代表的な使用例：
       - Projects 一覧取得
       - Runs 取得 or Execute API 呼び出し
     - エラーコードの扱い：
       - エラー内容が エラーコードカタログ.md と対応している旨と、その場所へのリンクを記載

4. **examples ディレクトリの作成**
   - sdk/python/examples/basic_usage.py を作成し、次のような最小コードを含めること：
     - クライアントインスタンスを生成
     - API Key を設定
     - /api/v1/projects を呼び出し、結果を print する
   - 実際のクラス名・モジュールパスは generator 出力を調査した上で正しく利用すること。

5. **tests ディレクトリの作成**
   - sdk/python/tests/test_imports.py のようなテストを作成し、次を確認すること：
     - SDK のトップレベルパッケージが import できること
     - クライアントクラスが存在すること
     - ネットワーク依存のあるテストはスキップまたはモック化すること（E2E は別 CR 範囲）。

6. **生成スクリプト / Makefile の更新**
   - tools/generate_sdk.py において、Python SDK 生成後に必要であれば
     - バージョン番号の埋め込み（0.1.0）
     - 不要ファイル削除や整形
   を行う処理を追加してよい（ただし SDK コード本体は generator に任せること）。
   - Makefile に次のターゲットを追加・更新すること：
     - sdk-python：OpenAPI から Python SDK を生成する（既存のものがあればそれを明確化）
     - sdk-python-build：python -m build または python -m pip install build && python -m build で wheel / sdist を生成
     - sdk-python-publish-test：TestPyPI への publish コマンド（プレースホルダーコマンドと環境変数説明）

7. **Completion Report の作成**
   - docs/api/CR-FASTAPI-018_完了報告.md を新規作成し、以下を含めること：
     - 実装日時
     - 目的・ゴール
     - 実装ステップ
     - 変更ファイル一覧（新規作成・変更）
     - 実行したテストと結果（pip install や pytest sdk/python/tests など）
     - 今後の改善ポイント（例：公式 PyPI 公開、より高度な E2E テスト）

8. **README / docs/api/README の更新**
   - README.md に「CR-FASTAPI-018 完了」と Python SDK 商品化の一行説明を追加すること。
   - docs/api/README.md に CR-FASTAPI-018_完了報告.md へのリンクを追加すること。

### 2.3 禁止事項（Prohibited Changes）

Cursor MUST NOT:

- sdk/python/ 内の auto-generated クライアントコード（OpenAPI generator の出力）を直接編集してはならない。
- OpenAPI 仕様書（YAML/JSON）の変更を本 CR で行ってはならない。
- Python SDK の public メソッド名や API 呼び出し仕様を、明示的指示なしに変更してはならない。
- /api/v1 の FastAPI ルートや Pydantic スキーマを変更してはならない。
- TypeScript SDK（sdk/typescript/ 等）を編集してはならない（CR-FASTAPI-019 の範囲）。
- .cursorrules に反する形で SDK コードを手書き改変してはならない。

### 2.4 テスト要件（Test Requirements）

Cursor MUST ensure that the following pass (or are at least runnable):

```bash
# SDK テスト（最低限）
cd sdk/python
python -m pip install .  # ローカルインストール検証
pytest tests  # 作成したテストが通ること

# プロジェクトルートに戻って
cd ../..
pytest tests/api  # 既存 API テストに悪影響がないこと
```

実行コマンドは Completion Report に明記すること。

### 2.5 出力形式（Cursor 実装フェーズ）

実装時、Cursor MUST:

- すべてのコード変更を unified diff 形式で出力すること。
- diff 提示後に、作成・変更されたファイル一覧をサマライズすること。
- docs/api/CR-FASTAPI-018_完了報告.md の中身を Markdown 全文で出力すること。

