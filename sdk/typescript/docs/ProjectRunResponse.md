# ProjectRunResponse

Project Run レスポンスモデル  Attributes:     run_id: Run ID（UUID形式）     project_id: プロジェクトID     status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）     queue_mode: キューモード（\"async\" または \"sync\"）

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**run_id** | **string** | Run ID（UUID形式） | [default to undefined]
**project_id** | **number** | プロジェクトID | [default to undefined]
**status** | **string** | ステータス | [default to undefined]
**queue_mode** | **string** | キューモード | [default to undefined]

## Example

```typescript
import { ProjectRunResponse } from 'nexuscore-sdk';

const instance: ProjectRunResponse = {
    run_id,
    project_id,
    status,
    queue_mode,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
