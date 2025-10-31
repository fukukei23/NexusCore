# ==============================================================================
# ファイル名: knowledge_base.py
# 配置場所: src/nexuscore/database/
# 目的: PostgreSQLを使い、FKB(Failure Knowledge Base)を永続化する（UPSERT対応）
# バージョン: 3.0 (Production Ready, Backward Compatible)
# 互換: add_knowledge/find_solution のシグネチャ維持
# 返却: add_knowledge は "created" | "updated" | "exists" | "failed" | "not_ready"
#       （従来 "created" | "exists" | "failed" を上位互換）
# ==============================================================================
# -*- coding: utf-8 -*-
import os
import json
import logging
import re
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, Column, String, JSON, Integer, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
Base = declarative_base()


class KnowledgeEntry(Base):
    __tablename__ = 'knowledge_entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    error_signature = Column(String, nullable=False, unique=True, index=True)
    cause = Column(String)
    target = Column(String)          # 例: 'source_file' | 'test_file' | 'both'
    solution_pattern = Column(JSON)  # 例: {"action": "edit", "file": "...", ...}
    description = Column(String)


class KnowledgeBase:
    def __init__(self, db_url: Optional[str] = None):
        url = db_url or os.getenv("DATABASE_URL")
        if not url:
            logger.error("Database URL not found.")
            self._engine = None
            self._Session = None
            return

        try:
            self._engine = create_engine(
                url,
                pool_pre_ping=True,
                future=True,
            )
            self._Session = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)

            # 既存スキーマを維持して作成
            Base.metadata.create_all(self._engine)
            logger.info("✅ Successfully connected to PostgreSQL Knowledge Base.")
        except Exception as e:
            logger.error(f"❌ Could not connect to PostgreSQL: {e}", exc_info=True)
            self._engine = None
            self._Session = None

    # ---- ユーティリティ ---------------------------------------------------------
    @staticmethod
    def _sanitize_entry(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        余計なキーが来ても弾き、モデルに適合するdictだけに整える。
        """
        allowed = {"error_signature", "cause", "target", "solution_pattern", "description"}
        clean = {k: v for k, v in (data or {}).items() if k in allowed}
        if not clean.get("error_signature"):
            raise ValueError("`error_signature` is required.")
        return clean

    @staticmethod
    def _equal_json(a: Any, b: Any) -> bool:
        """
        JSON相当の比較（辞書/配列の順不同対策としてダンプ比較）。
        """
        try:
            return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)
        except Exception:
            return a == b

    # ---- 互換API: 追加/更新（UPSERT） -------------------------------------------
    def add_knowledge(self, entry_data: Dict[str, Any]) -> str:
        """
        互換API: 旧 "INSERT-only" を「UPSERT」に拡張。
        戻り値:
          - "created": 新規作成
          - "updated": 既存レコードを更新
          - "exists" : 既存と同一内容のため変更なし（互換のため維持）
          - "failed"  : 例外
          - "not_ready": DB未初期化
        """
        if not self._engine or not self._Session:
            return "not_ready"

        try:
            payload = self._sanitize_entry(entry_data)
        except Exception as e:
            logger.error(f"Invalid entry_data: {e}")
            return "failed"

        session = self._Session()
        try:
            # 1) 既存を探索（unique: error_signature）
            stmt = select(KnowledgeEntry).where(KnowledgeEntry.error_signature == payload["error_signature"])
            existing = session.execute(stmt).scalars().first()

            if existing is None:
                # 2) 新規作成（従来互換）
                new_entry = KnowledgeEntry(**payload)
                session.add(new_entry)
                session.commit()
                logger.info(f"[KB] created: {payload['error_signature']}")
                return "created"

            # 3) 差分判定（全フィールド）
            changed = False
            if payload.get("cause") is not None and existing.cause != payload.get("cause"):
                existing.cause = payload.get("cause")
                changed = True
            if payload.get("target") is not None and existing.target != payload.get("target"):
                existing.target = payload.get("target")
                changed = True
            if "solution_pattern" in payload and not self._equal_json(existing.solution_pattern, payload.get("solution_pattern")):
                existing.solution_pattern = payload.get("solution_pattern")
                changed = True
            if payload.get("description") is not None and existing.description != payload.get("description"):
                existing.description = payload.get("description")
                changed = True

            if changed:
                session.commit()
                logger.info(f"[KB] updated: {payload['error_signature']}")
                return "updated"
            else:
                logger.info(f"[KB] exists (no change): {payload['error_signature']}")
                return "exists"

        except IntegrityError:
            # 競合時は exists とみなす（INSERT race等）
            session.rollback()
            logger.info(f"[KB] exists (integrity): {payload.get('error_signature')}")
            return "exists"
        except Exception:
            session.rollback()
            logger.error("Failed to upsert knowledge", exc_info=True)
            return "failed"
        finally:
            session.close()

    # ---- 検索API（既存互換） ----------------------------------------------------
    def find_solution(self, error_log: str) -> Optional[Dict[str, Any]]:
        """
        互換API: error_log に対して、登録済み error_signature (regex可) を順次マッチ。
        件数が増える場合は別途 index/キャッシュ/前方一致の導入を推奨。
        """
        if not self._engine or not self._Session:
            return None

        session = self._Session()
        try:
            entries = session.query(KnowledgeEntry).all()
            for entry in entries:
                pattern = entry.error_signature
                try:
                    if re.search(pattern, error_log):
                        return {
                            "error_signature": entry.error_signature,
                            "cause": entry.cause,
                            "solution_pattern": entry.solution_pattern,
                            "description": entry.description,
                            "target": entry.target,
                        }
                except re.error as re_err:
                    logger.warning(f"Invalid regex in error_signature: {pattern} ({re_err})")
                    continue
            return None
        finally:
            session.close()


# モジュールスコープの既定インスタンス（互換維持）
knowledge_base = KnowledgeBase()