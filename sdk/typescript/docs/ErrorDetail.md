# ErrorDetail

エラー詳細モデル  Attributes:     code: エラーコード（例: \"PROJECT_NOT_FOUND\", \"VALIDATION_ERROR\"）     message: 人間が読めるエラーメッセージ

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**code** | **string** | エラーコード | [default to undefined]
**message** | **string** | 人間が読めるエラーメッセージ | [default to undefined]

## Example

```typescript
import { ErrorDetail } from 'nexuscore-sdk';

const instance: ErrorDetail = {
    code,
    message,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
