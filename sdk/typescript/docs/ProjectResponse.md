# ProjectResponse

Project 詳細レスポンスモデル  Attributes:     id: プロジェクトID     name: プロジェクト名     repo_url: リポジトリURL     local_path: ローカルパス     context_bundle_path: コンテキストバンドルパス     created_at: 作成日時     updated_at: 更新日時

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | プロジェクトID | [default to undefined]
**name** | **string** | プロジェクト名 | [default to undefined]
**repo_url** | **string** |  | [optional] [default to undefined]
**local_path** | **string** | ローカルパス | [default to undefined]
**created_at** | **string** | 作成日時 | [default to undefined]
**updated_at** | **string** | 更新日時 | [default to undefined]
**context_bundle_path** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { ProjectResponse } from 'nexuscore-sdk';

const instance: ProjectResponse = {
    id,
    name,
    repo_url,
    local_path,
    created_at,
    updated_at,
    context_bundle_path,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
