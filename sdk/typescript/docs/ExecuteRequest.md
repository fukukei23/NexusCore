# ExecuteRequest

Execute リクエストモデル  Attributes:     requirement: 実行する要件（必須）     project_path: プロジェクトのパス（必須）     constitution_text: プロジェクト憲法のテキスト（任意）

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**requirement** | **string** | 実行する要件 | [default to undefined]
**project_path** | **string** | プロジェクトのパス | [default to undefined]
**constitution_text** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ExecuteRequest } from 'nexuscore-sdk';

const instance: ExecuteRequest = {
    requirement,
    project_path,
    constitution_text,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
