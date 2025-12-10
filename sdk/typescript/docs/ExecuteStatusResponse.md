# ExecuteStatusResponse

Execute Status レスポンスモデル  タスクの状態を表すモデル。既存のFlask実装では `tasks` 辞書の値がそのまま返されるため、 柔軟な構造を許容する必要がある。  Attributes:     status: タスクの状態（\"running\", \"completed\", \"error\" など）     message: ステータスメッセージ

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **string** | タスクの状態 | [default to undefined]
**message** | **string** | ステータスメッセージ | [default to undefined]

## Example

```typescript
import { ExecuteStatusResponse } from 'nexuscore-sdk';

const instance: ExecuteStatusResponse = {
    status,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
