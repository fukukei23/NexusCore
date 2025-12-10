# LatestRunDetail

最新Run詳細モデル  Attributes:     id: Run ID（データベースID）     run_id: Run ID（UUID形式）     status: ステータス（PENDING, RUNNING, SUCCESS, FAILED）     started_at: 開始日時     finished_at: 終了日時

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | Run ID（データベースID） | [default to undefined]
**run_id** | **string** | Run ID（UUID形式） | [default to undefined]
**status** | **string** | ステータス | [default to undefined]
**started_at** | **string** |  | [optional] [default to undefined]
**finished_at** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { LatestRunDetail } from 'nexuscore-sdk';

const instance: LatestRunDetail = {
    id,
    run_id,
    status,
    started_at,
    finished_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
