# CR-NEXUS-050: SSoT(cr_spec) 変更検知の強制ゲート（CI FAIL → 更新ツールで解除） - 完了レポート

## 実装日時

2025年12月25日

## 概要

### 目的

`src/nexuscore/governance/cr_spec.py`（SSoT）が変更されたら必ず pytest を FAIL させる。開発者が影響確認した上で、専用更新ツールを実行した場合のみ PASS する状態にする。「気づかないまま SSoT を変更して運用が壊れる事故」を防止する。

### ゴール

- cr_spec.py が変更されたら CI/pytest は必ず FAIL
- 解除は人間の意図的操作（更新ツール実行）でのみ行う
- CI が勝手に fingerprint を更新して通す挙動は禁止

### 原則

- 既存仕様変更は禁止。追加は「変更検知ゲート」だけ。
- フィンガープリント計算は sha256（ファイルbytesそのまま）でよい。過度な正規化は禁止。

## 実装ステップ

### Step 1: Fingerprint ファイルの作成

**実施内容**:
- `docs/governance/CR_SPEC_FINGERPRINT.txt` を新規作成
- 現在の cr_spec.py の sha256 値を保存

**実装詳細**:
- 1行だけ。cr_spec.py の sha256 値。

### Step 2: 更新ツールの実装

**実施内容**:
- `tools/update_cr_spec_fingerprint.py` を新規作成
- cr_spec.py を読み、sha256 を計算し、CR_SPEC_FINGERPRINT.txt を更新する

**実装詳細**:
- 実行時に更新前後の値を標準出力に出す（簡潔でよい）
- 失敗時は非ゼロ終了

### Step 3: 変更検知テストの実装

**実施内容**:
- `tests/governance/test_cr_spec_change_guard.py` を新規作成
- `tests/governance/__init__.py` を新規作成

**実装詳細**:
- 現在の cr_spec.py の sha256 と、CR_SPEC_FINGERPRINT.txt の値が一致することを検証
- 不一致なら FAIL
- FAIL メッセージには以下を含める：
  - 「cr_spec.py が変更された」
  - 影響範囲チェックリスト（scaffold、品質ゲート、README整合）
  - 解除方法：python tools/update_cr_spec_fingerprint.py

### Step 4: 動作確認

**実施内容**:
- cr_spec.py を変更すると test_cr_spec_change_guard が FAIL することを確認
- update_cr_spec_fingerprint.py を実行し、fingerprint を更新すると PASS することを確認

## 変更ファイル一覧

### 新規作成ファイル
- `docs/governance/CR_SPEC_FINGERPRINT.txt` - cr_spec.py の sha256 fingerprint
- `tools/update_cr_spec_fingerprint.py` - fingerprint 更新ツール
- `tests/governance/__init__.py` - governance テストモジュールの初期化
- `tests/governance/test_cr_spec_change_guard.py` - 変更検知テスト

### 変更ファイル
- `docs/api/README.md` - CR-NEXUS-050 のエントリ追加（後で実施）

## 動作確認結果

### テスト結果

**実行コマンド**:
```bash
python -m pytest tests/governance/test_cr_spec_change_guard.py -q
python -m pytest tests/api/test_completion_reports_exist.py tests/api/test_completion_reports_for_completed_crs.py tests/api/test_completion_report_quality_gate.py tests/api/test_completion_report_content_quality_gate.py tests/api/test_readme_cr_status_quality_gate.py tests/api/test_readme_cr_entry_quality_gate.py tests/api/test_scaffold_cr.py tests/api/test_cr_spec_single_source_of_truth.py tests/governance/test_cr_spec_change_guard.py -q
```

**結果**:
- ✅ `test_cr_spec_change_guard.py`: 1 passed
- ✅ 全テスト: 24 passed

**確認項目**:
- ✅ cr_spec.py を変更すると test_cr_spec_change_guard が FAIL する
- ✅ update_cr_spec_fingerprint.py を実行し、fingerprint を更新すると PASS する
- ✅ 既存テストに影響がない

### 動作確認の詳細

1. **変更検知の確認**:
   - cr_spec.py に変更を加えると、test_cr_spec_change_guard が FAIL することを確認
   - FAIL メッセージに影響範囲チェックリストと解除方法が含まれることを確認

2. **更新ツールの確認**:
   - update_cr_spec_fingerprint.py を実行すると、fingerprint が更新されることを確認
   - 更新後、test_cr_spec_change_guard が PASS することを確認

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

## 設計上の改善点

### 安全性の向上
1. **変更検知の強制**
   - cr_spec.py が変更された場合、必ず pytest が FAIL する
   - 開発者が意図せず変更しても、影響確認を強制できる

2. **意図的操作の明確化**
   - fingerprint 更新は専用ツールでのみ可能
   - CI が勝手に fingerprint を更新して通す挙動は禁止

3. **影響範囲の明確化**
   - FAIL メッセージに影響範囲チェックリストを含めることで、開発者が確認すべき項目を明確化

### 運用性の向上
1. **自動化の容易さ**
   - fingerprint 更新ツールがシンプルで実行しやすい
   - 更新前後の値を表示することで、変更内容を確認可能

2. **保守性の向上**
   - テストが独立しており、他のテストに影響を与えない
   - 新しいテストモジュール（tests/governance/）を追加することで、組織が明確

## 既知の制約・注意事項

### 制約
- フィンガープリント計算は sha256（ファイルbytesそのまま）でよい。過度な正規化は禁止
- CI が勝手に fingerprint を更新して通す挙動は禁止

### 注意事項
- cr_spec.py を変更した場合は、必ず影響範囲を確認してから fingerprint を更新すること
- fingerprint 更新ツールを実行する前に、影響範囲チェックリストを確認すること

## 次のステップ

### 推奨アクション
1. **CI 統合**
   - CI に test_cr_spec_change_guard を追加し、cr_spec.py の変更を検知する

2. **ドキュメント更新**
   - cr_spec.py を変更する際の手順をドキュメント化

## まとめ

CR-NEXUS-050 の実装により、cr_spec.py（SSoT）の変更検知を強制するゲートが追加されました。これにより、開発者が意図せず SSoT を変更しても、影響確認を強制できるようになりました。すべてのテストが PASS し、変更検知機能が正常に動作することを確認しました。

