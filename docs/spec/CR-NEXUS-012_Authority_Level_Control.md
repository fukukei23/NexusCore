# CR-NEXUS-012: Orchestrator 権限レベル（AuthorityLevel）導入（最小実装）

> **SRS Traceability**
> - Related SRS: docs/srs/NEXUSCORE_SRS.md
> - This CR satisfies: FR-1, FR-2, FR-4; NFR-3

## 1. Implementation Task Overview（人間向け仕様書）

### 1.1 目的（Why）

NexusCore において AI エージェントの自律性を「権限レベル」として明示し、実行の停止点・人間介入の境界を揃える。外部提供（SaaS/API）を見据え、説明責任と再現性（いつ・どこで・なぜ止まるか）を高める。

### 1.2 背景（Context）

- `src/nexuscore/core/orchestrator.py` は中核ファイル（Freeze 対象）であり、無制限な変更は許容されない。
- 既存実装には `constitution["automation_policy"]["autonomy_level"]` と、セッション制御（`SessionController`）が存在する。
- ただし「権限レベル」を定数として統一して参照できる場所がなく、またオーケストレータ実行を権限レベルで段階的に制御するための“外側の薄い制御層”が不足している。

### 1.3 ゴール（Outcome / Goal）

- `AuthorityLevel` を **定数として追加**し、コード上で同一の語彙で参照できるようにする。
- Orchestrator 本体を直接改造せず、**外側の制御層**として「どこまで自動実行するか」を切り替えられる API を提供する。
- ユニットテストで「権限レベルごとに実行されるフェーズ範囲」が検証できる。

### 1.4 スコープ

- **In-Scope**
  - `AuthorityLevel` 定数の新規追加（HUMAN_CONTROLLED / PARTIALLY_AUTONOMOUS / FULLY_AUTONOMOUS）。
  - Orchestrator のフェーズ実行（requirements/planning/architecture/implementation/testing/review）を「どこまで進めるか」制御する薄いランナー（外側）を追加。
  - `tests/` にユニットテスト追加（LLM 実呼び出し無し、短時間）。

- **Out-of-Scope**
  - `src/nexuscore/core/orchestrator.py` へのチェックポイント追加・大規模改修。
  - UI/HTTP API の仕様変更（新規エンドポイント追加など）。
  - 既存の `autonomy_level(0..2)` の意味の再定義（互換性維持を優先）。

### 1.5 リスク・注意

- 本Specは「最小実装」であり、**実行停止点（人間介入ポイント）**の詳細（どのフェーズで止めるか）は将来拡張余地を残す。
- Freeze 対象に抵触しないため、Orchestrator 本体の分岐ロジックは導入しない（外側で制御）。

### 1.6 完了条件（Definition of Done）

- `AuthorityLevel` がコード上で import 可能。
- 権限レベルにより「実行されるフェーズ範囲」が切り替わるランナーが実装されている。
- `tests/` のユニットテストが追加され、権限レベルの切替が検証される。

---

## 2. Implementation Instruction for Cursor（Cursor 用実装指示書）

### 2.1 変更対象ファイル

- **Add**: `src/nexuscore/orchestrator/constants.py`
- **Add**: `src/nexuscore/orchestrator/__init__.py`
- **Add**: `src/nexuscore/orchestrator/authority_runner.py`
- **Add**: `tests/orchestrator/test_authority_runner.py`

### 2.2 Required Changes（必須変更）

- `src/nexuscore/orchestrator/constants.py` に次を追加すること。

  - `AuthorityLevel` を class 定数として定義する（値は 1/2/3）。
    - `HUMAN_CONTROLLED = 1`
    - `PARTIALLY_AUTONOMOUS = 2`
    - `FULLY_AUTONOMOUS = 3`

- `src/nexuscore/orchestrator/authority_runner.py` に「Orchestrator のフェーズ実行範囲を AuthorityLevel で制御する」関数/クラスを追加すること。
  - Orchestrator 本体は変更せず、既存公開メソッド（例: `run_requirements_phase` など）を呼び出す方式で実装すること。
  - `HUMAN_CONTROLLED` / `PARTIALLY_AUTONOMOUS` / `FULLY_AUTONOMOUS` の最低限の挙動差を実装すること（どこまでフェーズを進めるか）。
  - 実際の LLM 呼び出しに入らないよう、テストで扱える形にすること（Protocol / duck-typing 可）。

- `tests/orchestrator/test_authority_runner.py` にユニットテストを追加すること。
  - Arrange/Act/Assert を明確にすること。
  - 実 LLM 呼び出し禁止（モック/スタブのみ）。

### 2.3 Prohibited Changes（禁止事項）

- `src/nexuscore/core/orchestrator.py` を編集しない（Freeze 対象）。
- `src/nexuscore/llm/llm_router.py` / `src/nexuscore/npe/engine.py` / `src/nexuscore/api/server.py` を編集しない（中核ファイル）。
- `print()` を本番パスに追加しない（logging を使用）。

### 2.4 Testing Requirements

- 追加テストは次で実行できること（例）:

```bash
cd /home/yn441611/NexusCore
bash dev_tools/run_tests.sh tests/orchestrator/
```


