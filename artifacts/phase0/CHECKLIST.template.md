# Phase 0 計測チェックリスト

実施日: <YYYY-MM-DD>
実施者: <name>

## 観測項目（4〜6・全項目に観測コマンド貼付必須）

### 1. MRO
- 観測: `python -m nexuscore.harness.diagnostics mro --class <FQCN>`
- 結果ファイル: `artifacts/phase0/<ts>/mro.txt`
- 判定: MRO衝突なし=OK / 衝突あり=撤退

### 2. 上書き要否
- 観測: `python -m nexuscore.harness.diagnostics override_check --class <FQCN>`
- 結果ファイル: `artifacts/phase0/<ts>/override_check.txt`
- 判定: `mixin_overlap: []`（=上書き不要）=OK / mixin_overlapに列挙=撤退
- ※`watch_defined` は参考情報（既存主力メソッドの自クラス定義・判定には使わない）

### 3. HTTP_FACTORY位置
- 観測: `python -m nexuscore.harness.diagnostics factory_pos`
- 結果ファイル: `artifacts/phase0/<ts>/factory_pos.txt`

### 4. リトライ実装差
- 観測: `python -m nexuscore.harness.diagnostics retry_diff`
- 結果ファイル: `artifacts/phase0/<ts>/retry_diff.json`
- 判定: 実効値（共有層込み）で3種以上欠落=撤退 / 2種以下=OK

### 5. tools受付+echo往復
- 観測: `python -m nexuscore.harness.diagnostics tool_echo --provider <name>`
- 結果ファイル: `artifacts/phase0/<ts>/tools_echo.jsonl`

### 6. Phase 1 着手判定
- 全項目=OK で Phase 1 着手可・1つでもNGなら A案（個別拡張）へ切替
