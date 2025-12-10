# RunsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**getRunApiV1RunsRunIdGet**](#getrunapiv1runsrunidget) | **GET** /api/v1/runs/{run_id} | Get run by ID|
|[**listRunsApiV1RunsGet**](#listrunsapiv1runsget) | **GET** /api/v1/runs | List runs|

# **getRunApiV1RunsRunIdGet**
> RunResponse getRunApiV1RunsRunIdGet()

Run IDでRunを取得する  GET /api/v1/runs/{run_id}  認証: X-API-Key ヘッダー必須  レスポンス:     {         \"id\": 1,         \"run_id\": \"abc123def456\",         \"project_id\": 1,         \"triggered_by\": 1,         \"status\": \"SUCCESS\",         \"started_at\": \"2025-01-01T00:00:00\",         \"finished_at\": \"2025-01-01T00:05:00\",         \"autonomy_level\": 2,         \"llm_model_summary\": \"gpt-4\",         \"requirement\": \"Run self-healing\",         \"created_at\": \"2025-01-01T00:00:00\"     }  Args:     run_id: Run ID（UUID形式）     current_user: 認証済みユーザー情報  Returns:     RunResponse: Run情報  Raises:     HTTPException: Runが見つからない場合（404）または内部エラー時（500）

### Example

```typescript
import {
    RunsApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let runId: string; // (default to undefined)
let xAPIKey: string; //API Key for authentication (default to undefined)

const { status, data } = await apiInstance.getRunApiV1RunsRunIdGet(
    runId,
    xAPIKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **runId** | [**string**] |  | defaults to undefined|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**RunResponse**

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

# **listRunsApiV1RunsGet**
> RunListResponse listRunsApiV1RunsGet()

Run一覧を取得する  GET /api/v1/runs?project_id=1  認証: X-API-Key ヘッダー必須  クエリパラメータ:     project_id: プロジェクトIDでフィルタ（任意）  レスポンス:     {         \"runs\": [             {                 \"id\": 1,                 \"run_id\": \"abc123def456\",                 \"project_id\": 1,                 \"status\": \"SUCCESS\",                 \"started_at\": \"2025-01-01T00:00:00\",                 \"finished_at\": \"2025-01-01T00:05:00\",                 \"created_at\": \"2025-01-01T00:00:00\"             }         ]     }  Args:     project_id: プロジェクトIDでフィルタ（任意）     current_user: 認証済みユーザー情報  Returns:     RunListResponse: Run一覧  Raises:     HTTPException: 内部エラー時（500）

### Example

```typescript
import {
    RunsApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new RunsApi(configuration);

let xAPIKey: string; //API Key for authentication (default to undefined)
let projectId: number; //プロジェクトIDでフィルタ (optional) (default to undefined)

const { status, data } = await apiInstance.listRunsApiV1RunsGet(
    xAPIKey,
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|
| **projectId** | [**number**] | プロジェクトIDでフィルタ | (optional) defaults to undefined|


### Return type

**RunListResponse**

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
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

