# WebhookApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**githubWebhookEndpointApiV1GithubWebhookPost**](#githubwebhookendpointapiv1githubwebhookpost) | **POST** /api/v1/github/webhook | GitHub Webhook endpoint|

# **githubWebhookEndpointApiV1GithubWebhookPost**
> GitHubWebhookResponse githubWebhookEndpointApiV1GithubWebhookPost()

GitHub Webhook エンドポイント  GitHub pull_request イベントを受信して Self-Healing Service を実行する。 既存の Flask 実装 (`handle_github_webhook`) と互換性を保つ。  Args:     request: FastAPI Request オブジェクト（ボディ取得用）     x_github_event: X-GitHub-Event ヘッダー     x_github_delivery: X-GitHub-Delivery ヘッダー     x_hub_signature_256: X-Hub-Signature-256 ヘッダー（署名検証用）  Returns:     GitHubWebhookResponse: Webhook処理結果  Raises:     HTTPException: 署名検証失敗時（401）または内部エラー時（500）

### Example

```typescript
import {
    WebhookApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new WebhookApi(configuration);

let xGitHubEvent: string; // (optional) (default to undefined)
let xGitHubDelivery: string; // (optional) (default to undefined)
let xHubSignature256: string; // (optional) (default to undefined)

const { status, data } = await apiInstance.githubWebhookEndpointApiV1GithubWebhookPost(
    xGitHubEvent,
    xGitHubDelivery,
    xHubSignature256
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **xGitHubEvent** | [**string**] |  | (optional) defaults to undefined|
| **xGitHubDelivery** | [**string**] |  | (optional) defaults to undefined|
| **xHubSignature256** | [**string**] |  | (optional) defaults to undefined|


### Return type

**GitHubWebhookResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**400** | Bad Request |  -  |
|**401** | Unauthorized |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

