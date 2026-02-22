# docs/srs/ README

## SRS 運用ルール（簡潔版）

- SRS（Software Requirements Specification）は **CR（実装仕様）より上位**の文書である。
- 新規 CR（`docs/spec/CR-*.md`）は、必ず本 SRS の **FR/NFR を参照**し、満たす要求を明示する。
- CR 冒頭の SRS Traceability ブロックは、**機械処理可能な固定フォーマット（3行引用）**とする。
- SRS は、破壊的変更を伴わない限り **追記更新**を基本とする（互換性と履歴性を重視）。
- 将来（例: CR-NEXUS-020 以降）で、必要に応じて SDD（詳細設計）に拡張する。


