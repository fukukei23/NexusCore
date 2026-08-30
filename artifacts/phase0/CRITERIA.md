# Phase 0 撤退判定基準（凍結・5ラウンドレビュー合意）

## 「既存メソッド上書き」の定義
子クラスでのインスタンスメソッド新規定義のみを「上書き」とカウントする。
以下は「上書き」とは見なさない（許容される）:
- `__init_subclass__` 経由の注入
- classmethod 追加
- Mixin 自体による新メソッド（`complete_with_tools` 等）の追加

（実装補足 2026-08-31: 判定は ToolCallingMixin 追加予定メソッド4種と
provider 自クラス定義の衝突有無で行う。`override_check` の
`mixin_overlap: []` = OK。継承により得たメソッドは数えない）

## 「リトライ実装差」の定義
以下のいずれか1つ以上の実装がプロバイダ間で欠落している状態を「差分あり」とカウントする:
- バックオフ戦略（指数・full jitter 等）
- Retry-After 解析（429応答ヘッダ読み取り）
- 最大試行回数の実装（`max_retries` 等）

（実装補足 2026-08-31: 共通HTTP層 `nexuscore/llm/http_client.py` の
urllib3 Retry〔backoff_factor=1・429/5xx・3回〕で担保された項目は
「実効値あり」としてカウントする。provider クラス自前の実装のみを
数えると共有層カバーを見落とし誤判定するため）

差分が3プロバイダ以上で検出された場合は Phase 1 着手不可（A案フォールバック）。

## 凍結日時
2026-08-30（spec round1〜6 レビュー合意）
