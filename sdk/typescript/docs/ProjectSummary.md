# ProjectSummary

Project サマリーモデル（一覧表示用）  Attributes:     id: プロジェクトID     name: プロジェクト名     repo_url: リポジトリURL     local_path: ローカルパス     created_at: 作成日時     updated_at: 更新日時

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **number** | プロジェクトID | [default to undefined]
**name** | **string** | プロジェクト名 | [default to undefined]
**repo_url** | **string** |  | [optional] [default to undefined]
**local_path** | **string** | ローカルパス | [default to undefined]
**created_at** | **string** | 作成日時 | [default to undefined]
**updated_at** | **string** | 更新日時 | [default to undefined]

## Example

```typescript
import { ProjectSummary } from 'nexuscore-sdk';

const instance: ProjectSummary = {
    id,
    name,
    repo_url,
    local_path,
    created_at,
    updated_at,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
