# ProjectRunRequest

Project Run リクエストモデル  Attributes:     requirement: ユーザー要件（必須）     autonomy_level: 自律レベル（デフォルト: 2）     fast_lane: 高速レーン実行フラグ（デフォルト: False）

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**requirement** | **string** | ユーザー要件 | [default to undefined]
**autonomy_level** | **number** | 自律レベル | [optional] [default to 2]
**fast_lane** | **boolean** | 高速レーン実行フラグ | [optional] [default to false]

## Example

```typescript
import { ProjectRunRequest } from 'nexuscore-sdk';

const instance: ProjectRunRequest = {
    requirement,
    autonomy_level,
    fast_lane,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
