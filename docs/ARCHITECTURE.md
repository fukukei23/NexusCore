# NexusCore Architecture

> **Gate / SSOT Entrypoint**: This file is the **Single Source of Truth (SSOT) entry point** for NexusCore architecture. Development tasks must reference this file before starting.

## Purpose

This document serves as the **Gate** for architectural information. It provides:
- High-level overview of NexusCore
- Links to canonical architecture design
- References to STIT+IRG governance documents

For detailed architectural design, see the [Canonical Architecture Document](architecture/ARCHITECTURE_CORE.md).

## System Overview

NexusCore is a multi-agent AI development framework with integrated quality gates, LLM routing, and constitutional governance.

The system orchestrates multiple specialized AI agents to support the complete software development lifecycle: requirement analysis, architecture design, code generation, testing, quality assurance, and governance.

## Gate（参照強制）

開発タスク開始前に必ず参照する：
- このドキュメント（`docs/ARCHITECTURE.md`）
- [Canonical Architecture Design](architecture/ARCHITECTURE_CORE.md) - 詳細なアーキテクチャ設計
- [Project Profile](../../PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md) - 制約宣言
- [Governance](../../GOVERNANCE/README.md) - ガバナンス資産
- [Master Protocol](../../GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md) - プロトコル
- 変更対象に関連する Spec（`docs/spec/` または `GOVERNANCE/spec/`）

## Architecture Documents

### Canonical Design
- **[ARCHITECTURE_CORE.md](architecture/ARCHITECTURE_CORE.md)**: Complete detailed architectural design
  - Component details
  - Data flow diagrams
  - Design patterns
  - Technology stack
  - Extension points

### Related Documents
- `docs/archive/ARCHITECTURE_PHASE3.md` - Historical phase 3 architecture
- `docs/archive/ARCHITECTURE_PHASE4.md` - Historical phase 4 architecture

## STIT+IRG Governance

NexusCore follows **STIT+IRG** (Spec & Test Driven Iteration + Independent Review Gate) governance:

- **Spec-driven development**: Specifications are written before implementation
- **Independent review**: Reviews are conducted in separate contexts (Phase 2.5)
- **Decision logging**: Important decisions are recorded in [Decision Log](../../DECISION_LOGS/DECISION_LOG.md)

For governance details, see:
- [Project Profile](../../PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md)
- [Governance README](../../GOVERNANCE/README.md)
- [Master Protocol Template](../../GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md)

## Quick Reference

**Key Components:**
- **Agent Layer**: Specialized AI agents (Architect, Coder, Debugger, Tester, Guardian, etc.)
- **LLM Router**: Task-based model routing with budget management
- **Quality Gates**: Multi-tier validation (Tier 1: Static, Tier 2: Mutation Testing)
- **Policy & Governance**: Constitutional AI with amendment system

**For detailed information**, see [ARCHITECTURE_CORE.md](architecture/ARCHITECTURE_CORE.md).
