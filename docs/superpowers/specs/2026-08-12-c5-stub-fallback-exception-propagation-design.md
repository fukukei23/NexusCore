# C5: silent stub-fallback 解消 — 例外伝播設計 (E+α改)

> 📅 2026-08-12 · ステータス: approved (sentaku L1→L4 経由) · 親: バックログP1「LLM stub フォールバック廃止→例外伝播」
> 関連: [[2026-07-30_silent-failure対策-stub応答明示的WARN]] / [[2026-08-05_Qiita六か条観点監査-CRITICAL6件発見]](C5) / [[2026-08-12_C5-stub-fallback解消-呼出2系統発見とL2選択]]

## 1. 背景と目的

NexusCore の LLM 呼出は、real call 失敗時に**例外を投げず stub 文字列を返す**（silent stub-fallback）。下流の 12 エージェント（Coder/Planner 等）がこの stub を本物のコード/JSON と勘違いしてパース・適用し、自己修復ループが検知困難な汚染を起こす（8/5 監査 CRITICAL#5）。

7/30 は `_stub_response`（real 無効時）に WARN 追加で対応したが、8/5 監査で「下流エージェントは WARN を見ず stub をパースする＝構造的に汚染が残る」と判明。根治方針「例外伝播」へ再逆転済み。本 spec はその実装設計。

**成功基準 L2（自動検知・汚染ブロック）**: 下流プログラムが機械的に「失敗」を検知し、stub 文字列をコード生成等に使わないようブロックすること。

## 2. 現状の問題（実コード根拠）

### 発生源は実質 2 箇所に集約（sentaku L1 訂正）
- **`base.py:104-136` `execute_real_or_fallback`**（openai/anthropic/gemini の 3 プロバイダが使用）
  - 行133/136: `except` 節で `return self._stub_fallback_response(...)` — **例外を投げず stub 返却**
- **`openai_compat.py:138/142`**（deepseek/glm/minimax/moonshot/openrouter の 5 プロバイダが継承・薄サブクラスで override/except なし）
  - 同様に `return self._stub_fallback_response(self.stub_label, ...)`

> fcd5 時点の「8 プロバイダ個別修正」は誤り。5 プロバイダは `OpenAICompatLLM` の薄サブクラス（設定値のみ）のため、`openai_compat.py` の 1 ファイル修正で網羅される（ゲート2 クリア確認済み）。

### 二次 silent 経路（α の対象）
- **`base_agent.py:163-166` `execute_llm_task` の最終フォールバック** — `except Exception: return "{}" if as_json else ""`
  - 例外を吸収して空応答を返す。発生源を例外化しても、ここで握りつぶされて別の silent（空の成功）に化ける。7/30 が「案C は破壊的」と判断した真因（握りつぶしの存在）。

### 経路図（訂正版）
```
12エージェント → execute_llm_task(base_agent.py:70)
                   → llm.execute(provider)
                       → execute_real_or_fallback(base.py) / openai_compat.execute
                           → real call 失敗
                           → ★ return _stub_fallback_response (例外を投げない) ← 発生源
                   ← stub 文字列 / または例外 → 行163-166 で {}/"" に握りつぶし ← 二次経路
               ← stub または空応答が「成功」として渡る → 汚染
```

## 3. 要件

### 機能要件
- **FR1**: real call 失敗時、stub 文字列を返さず**例外を伝播**すること（発生源 2 箇所）
- **FR2**: `execute_llm_task` の最終フォールバックで `{}`/`""` を返さず、**失敗を上位に伝播**すること（α）
- **FR3**: real 無効時（API キー無し・CI/テスト）の `_stub_response`（base.py:75 / openai_compat.py:144）は**現状維持**（7/30 の正しい判断を尊重・CI 破壊回避）
- **FR4**: 429（rate limit）は既存 retry 機構（retry_on）で再試行されること。恒久失敗は即停止すること
- **FR5**: orchestrator 層が伝播された例外を**ジョブ失敗（Run.status="FAILED" 等）として集約**すること

### 非機能要件
- **NFR1**: 既存テスト（tests/llm 641+）の回帰なし。stub に依存するテストは `_stub_response`（real 無効）経路で引き続き動作
- **NFR2**: ruff + mypy 緑（変更ファイル）
- **NFR3**: 段階導入可能（発生源 → α → orchestrator の順で独立コミット）

## 4. 設計（E+α改）

### 4.1 例外戦略（実装時に TDD で決定する 2 候補）

#### 候補 A（推奨）: 既存例外の伝播・変換経路再利用
```python
# base.py execute_real_or_fallback
except RequestsHTTPError as e:
    self.log_error("REAL-CALL HTTP error (after retries)", e, body)
    raise  # ← stub 返却を廃止・元例外を伝播
except Exception as e:
    self.log_error("REAL-CALL failed (after retries)", e)
    raise  # ← 同上
```
- 既存の `convert_http_error_to_nexus_error`（base_agent.py:114-116, 137-139）が 429→`ModelRateLimitError`、5xx→`ModelConnectionError` に変換
- 結果: 429 は既存 retry_on で再試行、恒久失敗は即伝播 — 既存 retry 機構と完全整合
- **利点**: 新例外不要・最小変更・既存 retry カテゴリ（`retryable_categories`）に自動追従

#### 候補 B（MiniMax 推奨・予備）: 新例外 `LLMUnavailableError` 新設
- `core/errors.py` に `LLMUnavailableError(NexusCoreError)` 追加・`retry_on` に**含めない**（即停止）
- **利点**: real 失敗を明示的に型区分
- **欠点**: 429 も即停止になる（retry と両立するには 429 を `ModelRateLimitError` に振り分ける二段階が必要）

> **決定方針**: 候補 A を基本とする。ただし「real 失敗全般を 1 例外で表現したい」需要が TDD 過程で出れば候補 B に移行（spec は両者を許容）。

### 4.2 α: execute_llm_task 最終フォールバック廃止
```python
# base_agent.py:163-166（現状）
except Exception as e:
    self.logger.error(f"LLM 実行エラー（Retry 後も失敗）: {e}", exc_info=True)
    return "{}" if as_json else ""   # ← 廃止

# 変更後
except Exception as e:
    self.logger.error(f"LLM 実行エラー（Retry 後も失敗）: {e}", exc_info=True)
    raise  # ← 上位（orchestrator）に伝播
```
- 7/30「破壊的」懸念（握りつぶし）への構造的回答
- 例外を受け止める上位口（orchestrator）が前提（FR5・4.3）

### 4.3 orchestrator 側の受け口（FR5・ゲート1）
- `core/orchestrator.py:140 run_full_project` / `core/dynamic_orchestrator.py:86 run` が、エージェント呼出で伝播された例外を catch し `Run.status="FAILED"` + エラー詳細記録へ集約
- **実装前確認**: 既存の例外受け口の有無と、Run.status 遷移の現状を TDD で把握してから整備

### 4.4 フラグ（D 案要素・統合テスト保護のみ）
- `NEXUSCORE_ALLOW_STUB_FALLBACK=1`（デフォルト OFF）: 本物 API キーを使う統合テストでのみ `_stub_fallback_response` 復活を許可
- 本番・通常 UT は強制例外。real 無効（API キー無し）は `_stub_response` 経路で保護（フラグ不要）

## 5. TDD 計画

### Unit Tests（tests/llm/）
- **T1**: `execute_real_or_fallback` で real call 失敗時、stub でなく例外を raise する（base.py）
- **T2**: `OpenAICompatLLM.execute` で real 失敗時、stub でなく例外を raise する（openai_compat.py・5 プロバイダ継承で網羅）
- **T3**: `execute_real_or_fallback` で real 成功時は従来通り result を返し `last_call_mode="real"`（回帰）
- **T4**: `_stub_response`（real 無効時）は従来通り stub + WARN を返す（FR3 回帰・7/30 決定保持）
- **T5**: `execute_llm_task` で retry 後失敗時、`{}`/`""` でなく例外を raise する（α）
- **T6**: `execute_llm_task` で 429 発生時 `ModelRateLimitError` に変換され retry_on が機能する（FR4）
- **T7**: `execute_llm_task` で恒久失敗（5xx 等）時、retry されず即例外伝播（FR4）
- **T8**: `NEXUSCORE_ALLOW_STUB_FALLBACK=1` 時のみ stub 復活（4.4）

### Integration Tests（tests/agents/ or tests/core/）
- **T9**: orchestrator が伝播された例外を `Run.status="FAILED"` に集約する（FR5・4.3）

### 回帰
- `tests/llm` 641+ が全て PASS（stub 依存テストは `_stub_response` 経路で維持）

## 6. 必須ゲート（実装前・実装中の検証項目）

| # | ゲート | 確認内容 | 状態 |
|---|---|---|---|
| G1 | orchestrator 受け口 | `run_full_project`/`run` が例外を Run.status へ集約する口の有無・必要な整備 | 要 TDD 確認（T9） |
| G2 | openai_compat 配下の網羅 | 5 プロバイダが override/except 持たず openai_compat.py 修正で網羅される | ✅ クリア確認済み |
| G3 | 429 vs 恒久失敗の分類 | `convert_http_error_to_nexus_error` + `retryable_categories` で正しく分類されるか | 要 TDD 検証（T6/T7） |

## 7. 受入基準

- [ ] FR1-5 全て実装・対応テスト PASS
- [ ] NFR1: tests/llm 641+ 回帰なし
- [ ] NFR2: 変更ファイル ruff + mypy 緑
- [ ] NFR3: 段階的コミット（発生源 → α → orchestrator）
- [ ] G1-G3 全てクリア
- [ ] `docs/変更履歴.md` に追記（Keep a Changelog 準拠）

## 8. リスク・最悪ケース（sentaku L1/L3 より）

1. **orchestrator クラッシュ**: 例外受け口（G1）未整備で伝播された例外がジョブ全体をクラッシュ → T9 で整備してから α を有効化
2. **openai_compat 配下の取りこぼし**: MiniMax 指摘・5 プロバイダが将来独自 except を持つと修正が散る → T2 で 5 プロバイダ網羅を確認
3. **retry 境界の分類ミス**: 429 を即停止に分類すると本番で一時エラー停止が多発、逆に恒久失敗を retry すると無限ループ → T6/T7 で機械検証
4. **統合テスト保護フラグの運用ミス**: 本番で `NEXUSCORE_ALLOW_STUB_FALLBACK=1` 残置 → デフォルト OFF・ドキュメント明記

## 9. 過去判断との整合（sentaku L4）

| 過去判断 | 本 spec | 整合 |
|---|---|---|
| 7/30 案A（real 無効時 WARN） | FR3 で `_stub_response` 維持 | ✅ 尊重 |
| 7/30 案C（例外送出）却下「握りつぶしで破壊的」 | α が握りつぶし（base_agent.py:163-166）を廃止 | ✅ 懸念へ構造的回答 |
| 8/5 監査「例外伝播が根治方針」 | FR1/F22 で例外伝播実装 | ✅ 直接実装 |
| バックログP1「stub フォールバック廃止→例外伝播」 | 本 spec がその着手 | ✅ 親タスク実装 |

乖離・矛盾なし。7/30→8/5 の再逆転を本 spec が完結する。

## 10. 実装順序（段階的コミット）

1. **Spec + テスト先行（赤）**: T1-T9 の失敗テストを追加
2. **発生源（FR1）**: base.py + openai_compat.py の stub-fallback → raise（T1-T3 緑化）
3. **α（FR2）**: base_agent.py:163-166 の {}/"" 廃止（T5 緑化）— G1 クリア後
4. **orchestrator（FR5）**: Run.status 集約口の整備（T9 緑化）
5. **フラグ（4.4）**: 統合テスト保護（T8）
6. **回帰確認 + 変更履歴 + SSOT 記録**
