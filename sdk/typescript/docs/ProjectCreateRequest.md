# ProjectCreateRequest

Project 作成リクエストモデル  Attributes:     name: プロジェクト名（必須）     repo_url: リポジトリURL（任意）     local_path: ローカルパス（必須）     context_bundle_path: コンテキストバンドルパス（任意）

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **string** | プロジェクト名 | [default to undefined]
**repo_url** | **string** |  | [optional] [default to undefined]
**local_path** | **string** | ローカルパス | [default to undefined]
**context_bundle_path** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ProjectCreateRequest } from 'nexuscore-sdk';

const instance: ProjectCreateRequest = {
    name,
    repo_url,
    local_path,
    context_bundle_path,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
