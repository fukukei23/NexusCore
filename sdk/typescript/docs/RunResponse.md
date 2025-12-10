# RunResponse

Run 詳細レスポンスモデル  Attributes:     id: Run ID（データベースID）     run_id: Run ID（UUID形式）     project_id: プロジェクトID     triggered_by: トリガーしたユーザーID     status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）     started_at: 開始日時     finished_at: 終了日時     autonomy_level: 自律レベル     llm_model_summary: 使用されたLLMモデルの概要     requirement: ユーザー要件     created_at: 作成日時

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | Run ID（データベースID） | [default to undefined]
**run_id** | **string** | Run ID（UUID形式） | [default to undefined]
**project_id** | **number** | プロジェクトID | [default to undefined]
**status** | **string** | ステータス | [default to undefined]
**started_at** | **string** |  | [optional] [default to undefined]
**finished_at** | **string** |  | [optional] [default to undefined]
**created_at** | **string** | 作成日時 | [default to undefined]
**triggered_by** | **number** |  | [optional] [default to undefined]
**autonomy_level** | **number** |  | [optional] [default to undefined]
**llm_model_summary** | **string** |  | [optional] [default to undefined]
**requirement** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { RunResponse } from 'nexuscore-sdk';

const instance: RunResponse = {
    id,
    run_id,
    project_id,
    status,
    started_at,
    finished_at,
    created_at,
    triggered_by,
    autonomy_level,
    llm_model_summary,
    requirement,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
