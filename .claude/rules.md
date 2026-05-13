# NexusCore 開発ルール（軽量版）

このルールセットは、開発速度を最大化しつつ品質を維持するための最小限の規約です。

---

## プロジェクト識別

**ルール**: すべてのメッセージは「#project: NexusCore」から開始すること。

---

## ディレクトリ構造

**ルール**: 以下の構造を前提とし、明示的な指示がない限り変更しないこと。

```
src/nexuscore/
├── api/          # FastAPI アプリケーション
├── ui/           # Gradio / UI コンポーネント
├── services/      # ビジネスロジック
├── core/         # オーケストレーター
└── agents/       # AI エージェント実装

tests/             # テストスイート
docs/             # ドキュメント
ガバナンス/        # ガバナンス
```

---

## API アーキテクチャ

**ルール1**: 新規外部APIは FastAPI 必須

- 新規 HTTP API は FastAPI で実装
- Flask ベースの API 追加は禁止
- 既存 Flask API はバグ修正または FastAPI 移行のみ触る

**ルール2**: Public API は /api/v1 プレフィックス

- 公開 API: `/api/v1/projects`, `/api/v1/runs/{run_id}`
- 内部/管理用: `/internal/*` またはルーティングなし

**ルール3**: Pydantic BaseModel 必須

- Request/Response は Pydantic BaseModel を使用
- Public API で `dict` や `Any` を直接返すことは禁止
- スキーマ定義: `src/nexuscore/api/schemas/projects.py`

**ルール4**: OpenAPI が唯一の仕様

- すべての Public API は OpenAPI で表現可能であること
- コメントのみの隠し仕様を導入しないこと

---

## 認証・セキュリティ

**ルール1**: Depends() による認証

- 認証が必要なエンドポイントは `Depends(get_current_user)` または `Depends(get_api_key)` を使用
- 例外: GitHub Webhook は署名検証のみ（API Key 不用）

**ルール2**: 認証方式の一貫性

- `/api/v1/*` で認証方式は一貫させる
- アドホックな認証パターン混在は禁止

**ルール3**: シークレット非ハードコード

- すべての秘密情報は環境変数または設定モジュールから読み込む

---

## UI と API の分離

**ルール**: 責務の分離

- ルートハンドラは薄く（入力パース、サービス呼び出し、レスポンスマッピング）
- ビジネスロジックは `services/` または `core/` に配置
- FastAPI から Gradio/UI を import しない

---

## テスト

**ルール**: 新規 API テストは FastAPI TestClient

- 新規 API テストは `TestClient` を使用
- 既存 Flask テストは移行期間中 skip 可

---

## エラーハンドリング

**ルール**: 標準化されたエラーレスポンス

```json
{
  "error": {
    "code": "SOME_CODE",
    "message": "Human-readable message"
  }
}
```

- 生の例外オブジェクトやスタックトレースをクライアントに返さない
- エラーコードは `docs/api/エラーコードカタログ.md` に定義（Single Source of Truth）

---

## 言語ポリシー

**ルール**: 人間向け出力は日本語優先

- 仕様書、説明、レポートは原則日本語
- ファイルパス、関数名、クラス名は英語のまま

---

## Tier 分類と開発フロー

### Tier 1 タスク（重要）

**定義**: 認証・認可、決済処理、データ移行、公開API設計、セキュリティ関連

**フロー**:
1. 簡易仕様確認（3項目）
2. ユーザー確認
3. 実装開始
4. （必要なら）Decision Recorder で決定記録

### Tier 2 タスク（通常）

**定義**: ビジネスロジック実装、UI実装、バグ修正、リファクタリング

**フロー**:
1. 直接実装開始

---

## 週次レビュー

**ルール**: コードレビューは自動化

- Code Reviewer Agent が週次で自動レビュー
- 重大な指摘→即時修正
- 軽微な指摘→Issue化
- 決定記録が必要なら Decision Recorder

---

## 規約の適用範囲

**適用する**:
- ✅ プロジェクトタグ必須
- ✅ API アーキテクチャ（FastAPI, /api/v1）
- ✅ 認証方式の一貫性
- ✅ エラーコードカタログ

**廃止した規約**:
- ❌ 2セクション構成（人間向け/Cursor向け分離）
- ❌ CR完了レポートの7セクション
- ❌ 小さな修正でのSpec必須
- ❌ unified diffのみ制約
- ❌ SDK生成・TestPyPI公開手順の規約
