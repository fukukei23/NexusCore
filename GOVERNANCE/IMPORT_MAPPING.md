# GOVERNANCE 移植対象ファイル一覧・配置表

> **注意**: このドキュメントは、テンプレートGit（STIT+IRG registry）から正式版を移植する際の参照用です。

## 移植元（テンプレートGit）

テンプレートGit（STIT+IRG registry）の `GOVERNANCE/` 配下を参照してください。

移植元のファイル一覧を取得するコマンド：
```bash
# テンプレートGit リポジトリで実行
git ls-files GOVERNANCE/
```

## 移植対象ファイル一覧（最低限）

以下のファイルをテンプレートGitから移植する予定です：

| 種別 | テンプレートGit（移植元） | NexusCore（移植先） | 状態 |
|------|------------------------|---------------------|------|
| ガバナンス入口 | `GOVERNANCE/README.md` | `GOVERNANCE/README.md` | ✅ Bootstrap Draft 作成済み |
| マスタープロトコル | `GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md` | `GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md` | ✅ Bootstrap Draft 作成済み |
| レビューパケット | `GOVERNANCE/REVIEW_PACKET_TEMPLATE.md` | `GOVERNANCE/REVIEW_PACKET_TEMPLATE.md` | ✅ Bootstrap Draft 作成済み |
| 実装AI規範 | `GOVERNANCE/AI_INSTRUCTIONS.md` | `GOVERNANCE/AI_INSTRUCTIONS.md` | ✅ Bootstrap Draft 作成済み |
| Spec置き場 | `GOVERNANCE/spec/README.md` | `GOVERNANCE/spec/README.md` | ✅ Bootstrap Draft 作成済み |
| Spec置き場（空dir） | `GOVERNANCE/spec/.gitkeep` | `GOVERNANCE/spec/.gitkeep` | ✅ 作成済み |
| Review成果物 | `GOVERNANCE/review_packets/README.md` | `GOVERNANCE/review_packets/README.md` | ✅ Bootstrap Draft 作成済み |
| Review成果物（空dir） | `GOVERNANCE/review_packets/.gitkeep` | `GOVERNANCE/review_packets/.gitkeep` | ✅ 作成済み |
| CLI置き場 | `GOVERNANCE/cli/README.md` | `GOVERNANCE/cli/README.md` | ✅ Bootstrap Draft 作成済み |
| CLI置き場（空dir） | `GOVERNANCE/cli/.gitkeep` | `GOVERNANCE/cli/.gitkeep` | ✅ 作成済み |

## 配置表（マッピング）

すべてのファイルは、テンプレートGitと同じパス構造で NexusCore に配置します（同居方式）。

```
GOVERNANCE/
├── README.md                          # ✅ Bootstrap Draft
├── MASTER_PROTOCOL_TEMPLATE.md        # ✅ Bootstrap Draft → TODO: 正式版移植
├── REVIEW_PACKET_TEMPLATE.md          # ✅ Bootstrap Draft → TODO: 正式版移植
├── AI_INSTRUCTIONS.md                 # ✅ Bootstrap Draft → TODO: 正式版移植
├── spec/
│   ├── README.md                      # ✅ Bootstrap Draft
│   └── .gitkeep                       # ✅ 作成済み
├── review_packets/
│   ├── README.md                      # ✅ Bootstrap Draft
│   └── .gitkeep                       # ✅ 作成済み
└── cli/
    ├── README.md                      # ✅ Bootstrap Draft
    └── .gitkeep                       # ✅ 作成済み
```

## 衝突時ルール

NexusCore に同名ファイルが既に存在する場合：

1. **上書き禁止**: まず差分比較を実施
2. **統合版作成**: NexusCore側を残すなら、テンプレート側内容を取り込んだ「統合版」を作成（Decision Logに記録）
3. **SSOT明記**: どちらをSSOTにするかを明記し、README導線を統一

## 移植手順（TODO）

1. テンプレートGit リポジトリをクローンまたは参照
2. `git ls-files GOVERNANCE/` で完全なファイル一覧を取得
3. 各ファイルを NexusCore の対応パスにコピー
4. Bootstrap Draft ファイルを正式版で置き換え
5. 差分比較を実施し、衝突があれば統合版を作成
6. Decision Log に移植完了を記録

## 注意事項

- テンプレートGitの SSOT が提供されるまで、Bootstrap Draft のまま運用
- 正式版移植時は、このドキュメントを更新して完了を記録

