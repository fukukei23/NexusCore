"""
NexusCore SaaS基盤 - データベースモデル

SQLAlchemy ORM モデル定義。
既存の Orchestrator / NPE とは独立して動作する。
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

# db は __init__.py からインポート
from nexuscore.webapp import db


class User(db.Model):
    """
    ユーザーモデル（GitHub OAuth で認証）
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    github_id = Column(String(255), unique=True, nullable=False, index=True)
    github_login = Column(String(255), nullable=False)
    name = Column(String(255))
    avatar_url = Column(String(512))
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # リレーション
    projects = relationship("Project", back_populates="owner", lazy="dynamic")
    runs = relationship("Run", back_populates="triggered_by_user", lazy="dynamic")
    api_keys = relationship(
        "ApiKey", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, github_login='{self.github_login}')>"


class Project(db.Model):
    """
    プロジェクトモデル（対象リポジトリ）
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    repo_url = Column(String(512))
    local_path = Column(String(512), nullable=False)  # Orchestrator / NPE が動くローカルパス
    context_bundle_path = Column(String(512), nullable=True)  # context_bundles/latest.json など
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # リレーション
    owner = relationship("User", back_populates="projects")
    runs = relationship(
        "Run", back_populates="project", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"


class Run(db.Model):
    """
    実行記録（1回のオーケストレーション実行を表現）
    """

    __tablename__ = "runs"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    run_id = Column(String(64), unique=True, nullable=False, index=True)  # uuid.uuid4().hex
    triggered_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(
        String(32), nullable=False, default="PENDING", index=True
    )  # PENDING, RUNNING, SUCCESS, FAILED
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    autonomy_level = Column(Integer, nullable=True)  # 実行時の設定
    llm_model_summary = Column(String(512), nullable=True)  # 使用されたモデルの概要文字列
    requirement = Column(Text, nullable=True)  # ユーザー要件（実行時に指定）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    project = relationship("Project", back_populates="runs")
    triggered_by_user = relationship("User", back_populates="runs")
    patch_records = relationship(
        "PatchRecord", back_populates="run", lazy="dynamic", cascade="all, delete-orphan"
    )
    execution_logs = relationship(
        "ExecutionLog", back_populates="run", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"


class PatchRecord(db.Model):
    """
    パッチ適用記録
    """

    __tablename__ = "patch_records"

    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    file_path = Column(String(512), nullable=False)
    diff_text = Column(Text, nullable=False)  # unified diff
    applied = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    run = relationship("Run", back_populates="patch_records")

    def __repr__(self) -> str:
        return f"<PatchRecord(id={self.id}, file_path='{self.file_path}', applied={self.applied})>"


class ExecutionLog(db.Model):
    """
    実行ログ（NPE / Orchestrator / Agent からの構造化ログ）
    """

    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True)
    run_id = Column(
        Integer, ForeignKey("runs.id"), nullable=True, index=True
    )  # 紐付かない場合もある
    source = Column(String(64), nullable=False, index=True)  # NPE, ORCHESTRATOR, AGENT, SANDBOX 等
    level = Column(String(16), nullable=False, index=True)  # INFO, WARNING, ERROR
    message = Column(String(512), nullable=False)
    payload_json = Column(JSON, nullable=True)  # 任意の詳細情報
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # リレーション
    run = relationship("Run", back_populates="execution_logs")

    def __repr__(self) -> str:
        return f"<ExecutionLog(id={self.id}, source='{self.source}', level='{self.level}')>"


class ApiKey(db.Model):
    """
    APIキー（読み取り専用、ユーザーが自身のラン履歴やログを読むため）
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), nullable=False, unique=True, index=True)  # ハッシュ化したキー
    name = Column(String(255), nullable=False)  # 用途メモ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    user = relationship("User", back_populates="api_keys")

    @staticmethod
    def hash_token(token: str) -> str:
        """
        APIキーをハッシュ化（SHA-256）
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_token() -> str:
        """
        新しいAPIキーを生成（平文、発行時のみ表示）
        """
        return f"nexus_{secrets.token_urlsafe(32)}"

    def verify_token(self, token: str) -> bool:
        """
        トークンが一致するか検証
        """
        return self.token_hash == self.hash_token(token)

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, name='{self.name}')>"
