# ExecuteApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**executeEndpointApiV1ExecutePost**](#executeendpointapiv1executepost) | **POST** /api/v1/execute | Run self-healing job|
|[**getTaskStatusApiV1StatusTaskIdGet**](#gettaskstatusapiv1statustaskidget) | **GET** /api/v1/status/{task_id} | Get task status|

# **executeEndpointApiV1ExecutePost**
> ExecuteResponse executeEndpointApiV1ExecutePost(executeRequest)

Execute エンドポイント  指定されたプロジェクトパスに対して self-healing 実行をトリガーし、 実行IDおよび現在のステータスを返します。  このエンドポイントは認証済みクライアントからのみ利用可能です。 （CR-FASTAPI-003 で認証を追加予定）  Args:     payload: 実行リクエスト（requirement, project_path, constitution_text）  Returns:     ExecuteResponse: タスクIDとステータスURLを含むレスポンス  Raises:     HTTPException: バリデーションエラーまたは内部エラー時

### Example

```typescript
import {
    ExecuteApi,
    Configuration,
    ExecuteRequest
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ExecuteApi(configuration);

let xAPIKey: string; //API Key for authentication (default to undefined)
let executeRequest: ExecuteRequest; //

const { status, data } = await apiInstance.executeEndpointApiV1ExecutePost(
    xAPIKey,
    executeRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **executeRequest** | **ExecuteRequest**|  | |
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ExecuteResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**202** | Successful Response |  -  |
|**401** | Unauthorized |  -  |
|**422** | Unprocessable Entity |  -  |
|**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getTaskStatusApiV1StatusTaskIdGet**
> ExecuteStatusResponse getTaskStatusApiV1StatusTaskIdGet()

Get Task Status エンドポイント  指定されたタスクIDの現在の状態を返します。 既存の Flask 実装 (`get_task_status`) と互換性を保つ。  Args:     task_id: タスクID（UUID形式）  Returns:     ExecuteStatusResponse: タスクの状態情報  Raises:     HTTPException: タスクが見つからない場合（404）

### Example

```typescript
import {
    ExecuteApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ExecuteApi(configuration);

let taskId: string; // (default to undefined)
let xAPIKey: string; //API Key for authentication (default to undefined)

const { status, data } = await apiInstance.getTaskStatusApiV1StatusTaskIdGet(
    taskId,
    xAPIKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **taskId** | [**string**] |  | defaults to undefined|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ExecuteStatusResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**401** | Unauthorized |  -  |
|**404** | Not Found |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

