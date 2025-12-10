# ExecuteResponse

Execute レスポンスモデル  Attributes:     message: メッセージ     task_id: タスクID（UUID形式）     status_url: ステータス確認用URL

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**message** | **string** | タスク受け入れメッセージ | [default to undefined]
**task_id** | **string** | タスクID（UUID形式） | [default to undefined]
**status_url** | **string** | ステータス確認用URL（相対パス） | [default to undefined]

## Example

```typescript
import { ExecuteResponse } from 'nexuscore-sdk';

const instance: ExecuteResponse = {
    message,
    task_id,
    status_url,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
