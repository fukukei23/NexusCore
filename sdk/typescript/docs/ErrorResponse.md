# ErrorResponse

標準化されたエラーレスポンスモデル  すべての API エンドポイントで統一されたエラー構造。  Attributes:     error: エラー詳細情報

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**error** | [**ErrorDetail**](ErrorDetail.md) | エラー詳細情報 | [default to undefined]

## Example

```typescript
import { ErrorResponse } from 'nexuscore-sdk';

const instance: ErrorResponse = {
    error,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
