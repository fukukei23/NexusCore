"""
GitHub Webhook API リクエスト・レスポンススキーマ

FastAPI の GitHub Webhook エンドポイント用の Pydantic モデル定義。
既存の Flask API (`src/nexuscore/api/github_webhook_handler.py`) の仕様に準拠。
"""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GitHubRepository(BaseModel):
    """
    GitHub リポジトリ情報モデル

    Attributes:
        full_name: リポジトリのフルネーム（例: "owner/repo"）
    """
    full_name: str = Field(..., description="リポジトリのフルネーム")


class GitHubPullRequestLabel(BaseModel):
    """
    GitHub PR ラベルモデル

    Attributes:
        name: ラベル名
    """
    name: str = Field(..., description="ラベル名")


class GitHubPullRequestHead(BaseModel):
    """
    GitHub PR の head ブランチ情報モデル

    Attributes:
        sha: コミットSHA
    """
    sha: str = Field(..., description="コミットSHA")


class GitHubPullRequestBase(BaseModel):
    """
    GitHub PR の base ブランチ情報モデル

    Attributes:
        ref: ブランチ名
    """
    ref: str = Field(..., description="ブランチ名")


class GitHubPullRequest(BaseModel):
    """
    GitHub Pull Request 情報モデル

    既存の実装で実際に使用されているフィールドのみを定義。

    Attributes:
        number: PR番号
        draft: ドラフトPRかどうか
        labels: ラベル一覧
        head: head ブランチ情報
        base: base ブランチ情報
    """
    number: int = Field(..., description="PR番号")
    draft: bool = Field(default=False, description="ドラフトPRかどうか")
    labels: List[GitHubPullRequestLabel] = Field(default_factory=list, description="ラベル一覧")
    head: GitHubPullRequestHead = Field(..., description="head ブランチ情報")
    base: GitHubPullRequestBase = Field(..., description="base ブランチ情報")


class GitHubWebhookPayload(BaseModel):
    """
    GitHub Webhook ペイロードモデル

    既存の実装で実際に使用されているフィールドのみを定義。

    Attributes:
        action: イベントアクション（"opened", "synchronize", "reopened", "ready_for_review" など）
        repository: リポジトリ情報
        pull_request: Pull Request情報
    """
    action: str = Field(..., description="イベントアクション")
    repository: GitHubRepository = Field(..., description="リポジトリ情報")
    pull_request: GitHubPullRequest = Field(..., description="Pull Request情報")

    class Config:
        extra = "allow"  # GitHub Webhook には追加フィールドが存在する可能性があるため


class GitHubWebhookResponse(BaseModel):
    """
    GitHub Webhook レスポンスモデル

    既存のFlask実装のレスポンス形式に準拠。

    Attributes:
        accepted: Webhookが受け入れられたかどうか
        result: 実行結果（accepted=Trueの場合）
        reason: 拒否理由（accepted=Falseの場合）
        error: エラーメッセージ（エラー時）
        status: ステータス（"skipped", "fixed", "not_fixed", "no_issues", "error" など）
        summary: サマリー
    """
    accepted: bool = Field(..., description="Webhookが受け入れられたかどうか")
    result: Optional[Dict[str, Any]] = Field(None, description="実行結果")
    reason: Optional[str] = Field(None, description="拒否理由")
    error: Optional[str] = Field(None, description="エラーメッセージ")
    status: Optional[Literal["skipped", "fixed", "not_fixed", "no_issues", "error"]] = Field(
        None, description="ステータス"
    )
    summary: Optional[str] = Field(None, description="サマリー")

    class Config:
        json_schema_extra = {
            "example": {
                "accepted": True,
                "result": {
                    "status": "fixed",
                    "summary": "Tests are now passing",
                    "run_id": "sh-123",
                },
            }
        }

