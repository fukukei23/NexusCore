# GOVERNANCE

> STIT+IRG (Spec & Test Driven Iteration + Independent Review Gate) 運用のためのガバナンス資産

## 概要

このディレクトリには、NexusCore プロジェクトのガバナンス運用に必要なテンプレートとプロトコルを格納します。

**STIT 正本（SSOT）**: 本リポジトリにおける STIT（Spec & Test Driven Iteration）の正本は **GOVERNANCE/SPEC_TEST_DRIVEN_ITERATION.md（v1.2）** である。開発タスク開始前に必ず参照すること。

**注意**: 現在のファイルは Bootstrap Draft（初期ドラフト）です。テンプレートGit（STIT+IRG registry）から正式版を移植する予定です。

## ディレクトリ構成

```
GOVERNANCE/
├── README.md                          # このファイル
├── MASTER_PROTOCOL_TEMPLATE.md        # マスタープロトコル（TODO: 正式版を移植）
├── REVIEW_PACKET_TEMPLATE.md          # レビューパケットテンプレート（TODO: 正式版を移植）
├── AI_INSTRUCTIONS.md                 # 実装AI向け指示書（TODO: 正式版を移植）
├── spec/                              # Spec 置き場
│   ├── README.md
│   └── .gitkeep
├── review_packets/                    # Review 成果物置き場
│   ├── README.md
│   └── .gitkeep
└── cli/                               # CLI ツール置き場
    ├── README.md
    └── .gitkeep
```

## 関連ドキュメント

- [Project Profile](../PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Decision Logs](../DECISION_LOGS/DECISION_LOG.md)

