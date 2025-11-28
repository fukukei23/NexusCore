"""
UI キーワード表

UI が壊れたときすぐ気づけるよう、全ページ共通で UI キーワードを一元管理するモジュール。

各ページの重要な文字列（日本語含む）をここに集約し、
UI ラベル変更時はこのファイルを修正するだけで対応可能にする。
"""

# プロジェクト一覧ページ（/projects/）のキーワード
PROJECTS_PAGE_KEYWORDS = [
    "Projects",  # タイトル
    "Success Rate",  # メトリクス
    "Test Project",  # プロジェクト名（テスト用）
    "Latest Status",  # ステータス表示
    "Exec Time",  # 実行時間
    "Retry",  # リトライ回数
]

# プロジェクト詳細ページ（/projects/<id>）のキーワード
PROJECT_DETAIL_KEYWORDS = [
    "Test Project",  # プロジェクト名
    "Recent Runs",  # Run 一覧
    "Success Rate",  # メトリクス
    "Metrics",  # メトリクスセクション
    "Metrics (Last 30 Runs)",  # メトリクスセクションタイトル
]

# Run 詳細ページ（/logs/runs/<run_id>）のキーワード
RUN_DETAIL_KEYWORDS = [
    "Self-Healing Metrics",  # メトリクスセクション
    "Guardian Review",  # Guardian Review セクション
    "AI Diff Summary",  # AI Diff Summary セクション
    "Observability",  # Observability セクション
    "Retry",  # リトライ回数
    "Model",  # モデル名
    "Exec Time",  # 実行時間
    "Files Changed",  # 変更ファイル数
]

# External API テスト UI（/api-test/）のキーワード
API_TEST_PAGE_KEYWORDS = [
    "API Test",  # タイトル
    "/api/v1/projects",  # API エンドポイント
    "Project ID",  # プロジェクト選択
    "Requirement",  # 要件入力
    "Test Project",  # プロジェクト名（テスト用）
]

