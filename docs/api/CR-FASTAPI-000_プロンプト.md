# CR-FASTAPI-000: API Inventory (Flask → FastAPI Migration Baseline)

> これは Cursor のチャットにそのまま貼る「タスク指示」です。

```text
#project: NexusCore

CR-FASTAPI-000: API inventory (Flask → FastAPI migration baseline)

目的:
NexusCore リポジトリ内の既存 HTTP API (主に Flask ベース) を全て棚卸しし、
- public / internal / 廃止候補
- FastAPI 移行優先順位
を一覧化する。

やりたいこと:

1. リポジトリ全体から Flask ベースのルーティング定義を探索する。
   - 例: @app.route, @blueprint.route, flask.Blueprint(...).route など
   - 個別に実装されたルート関数でもかまわないので漏らさないこと。

2. 各ルートについて、以下の情報を抽出し、Markdown テーブルにまとめる:
   - HTTP method (GET/POST/PUT/DELETE/...)
   - path (例: "/api/execute", "/api/projects", "/health", など)
   - module / file path (例: "src/nexuscore/api/server.py")
   - handler function 名 (例: "execute_task")
   - 認証の有無・方式 (ざっくりでよい: "no auth", "API key", "session", など)
   - 用途分類:
     - "public" (外部公開想定: SaaS API, Webhook など)
     - "internal" (UI や内部マイクロサービスからのみ利用)
     - "deprecated" or "candidate_for_removal" (現在ほぼ使われていない／今後廃止してよい)
   - 備考:
     - Gradio/UI からのみ呼ばれている、Webhook 入口、など

3. 上記一覧を `docs/api/APIインベントリ.md` に Markdown として新規作成する:
   - 見出し構成イメージ:
     - # API Inventory (Flask baseline)
       - ## Public endpoints
       - ## Internal endpoints
       - ## Deprecated / removal candidates

4. 重要:
   - 差分は unified diff のみで提示すること。
   - 既存コードの挙動は変えないこと。今回は「棚卸しとドキュメント追加」に留める。
   - 分類に迷う場合は "internal" とし、備考に迷いの理由を書く。

出力フォーマット:
1. `docs/api/APIインベントリ.md` の unified diff
2. コンソールにも、public / internal / deprecated ごとのサマリ件数を簡単に表示
   - 例: "Public: 5, Internal: 12, Deprecated: 3"

このタスクでは FastAPI 移行は行わず、「現状の API の見える化」だけを行う。
```

