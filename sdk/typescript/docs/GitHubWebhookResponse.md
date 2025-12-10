# GitHubWebhookResponse

GitHub Webhook レスポンスモデル  既存のFlask実装のレスポンス形式に準拠。  Attributes:     accepted: Webhookが受け入れられたかどうか     result: 実行結果（accepted=Trueの場合）     reason: 拒否理由（accepted=Falseの場合）     error: エラーメッセージ（エラー時）     status: ステータス（\"skipped\", \"fixed\", \"not_fixed\", \"no_issues\", \"error\" など）     summary: サマリー

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**accepted** | **boolean** | Webhookが受け入れられたかどうか | [default to undefined]
**result** | **{ [key: string]: any; }** |  | [optional] [default to undefined]
**reason** | **string** |  | [optional] [default to undefined]
**error** | **string** |  | [optional] [default to undefined]
**status** | **string** |  | [optional] [default to undefined]
**summary** | **string** |  | [optional] [default to undefined]

## Example

```typescript
import { GitHubWebhookResponse } from 'nexuscore-sdk';

const instance: GitHubWebhookResponse = {
    accepted,
    result,
    reason,
    error,
    status,
    summary,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
