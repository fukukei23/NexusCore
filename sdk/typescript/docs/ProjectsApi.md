# ProjectsApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**createProjectApiV1ProjectsPost**](#createprojectapiv1projectspost) | **POST** /api/v1/projects | Create project|
|[**getLatestRunApiV1ProjectsProjectIdRunsLatestGet**](#getlatestrunapiv1projectsprojectidrunslatestget) | **GET** /api/v1/projects/{project_id}/runs/latest | Get latest run for project|
|[**getProjectApiV1ProjectsProjectIdGet**](#getprojectapiv1projectsprojectidget) | **GET** /api/v1/projects/{project_id} | Get project by ID|
|[**listProjectsApiV1ProjectsGet**](#listprojectsapiv1projectsget) | **GET** /api/v1/projects | List projects|
|[**triggerProjectRunApiV1ProjectsProjectIdRunPost**](#triggerprojectrunapiv1projectsprojectidrunpost) | **POST** /api/v1/projects/{project_id}/run | Trigger project run|

# **createProjectApiV1ProjectsPost**
> ProjectResponse createProjectApiV1ProjectsPost(projectCreateRequest)

新規プロジェクトを作成する  POST /api/v1/projects  認証: X-API-Key ヘッダー必須  リクエストボディ:     {         \"name\": \"Project Name\",         \"repo_url\": \"https://github.com/owner/repo\",         \"local_path\": \"/path/to/project\",         \"context_bundle_path\": \"/path/to/context.json\"     }  レスポンス:     {         \"id\": 1,         \"name\": \"Project Name\",         \"repo_url\": \"https://github.com/owner/repo\",         \"local_path\": \"/path/to/project\",         \"context_bundle_path\": \"/path/to/context.json\",         \"created_at\": \"2025-01-01T00:00:00\",         \"updated_at\": \"2025-01-01T00:00:00\"     }  Args:     payload: プロジェクト作成リクエスト     current_user: 認証済みユーザー情報  Returns:     ProjectResponse: 作成されたプロジェクト情報  Raises:     HTTPException: バリデーションエラー時（400）または内部エラー時（500）

### Example

```typescript
import {
    ProjectsApi,
    Configuration,
    ProjectCreateRequest
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ProjectsApi(configuration);

let xAPIKey: string; //API Key for authentication (default to undefined)
let projectCreateRequest: ProjectCreateRequest; //

const { status, data } = await apiInstance.createProjectApiV1ProjectsPost(
    xAPIKey,
    projectCreateRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectCreateRequest** | **ProjectCreateRequest**|  | |
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ProjectResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**201** | Successful Response |  -  |
|**400** | Bad Request |  -  |
|**401** | Unauthorized |  -  |
|**422** | Unprocessable Entity |  -  |
|**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **getLatestRunApiV1ProjectsProjectIdRunsLatestGet**
> LatestRunResponse getLatestRunApiV1ProjectsProjectIdRunsLatestGet()

最新の Run の概要を取得する  GET /api/v1/projects/{project_id}/runs/latest  認証: X-API-Key ヘッダー必須  レスポンス:     {         \"run\": {             \"id\": 1,             \"run_id\": \"abc123...\",             \"status\": \"SUCCESS\",             \"started_at\": \"2025-01-01T00:00:00\",             \"finished_at\": \"2025-01-01T00:05:00\"         }     }     または     {         \"run\": null     }  ステータスコード:     - 200: 成功     - 404: プロジェクトが見つからない  Args:     project_id: プロジェクトID     current_user: 認証済みユーザー情報  Returns:     LatestRunResponse: 最新Run情報  Raises:     HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）

### Example

```typescript
import {
    ProjectsApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ProjectsApi(configuration);

let projectId: number; // (default to undefined)
let xAPIKey: string; //API Key for authentication (default to undefined)

const { status, data } = await apiInstance.getLatestRunApiV1ProjectsProjectIdRunsLatestGet(
    projectId,
    xAPIKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**number**] |  | defaults to undefined|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**LatestRunResponse**

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

# **getProjectApiV1ProjectsProjectIdGet**
> ProjectResponse getProjectApiV1ProjectsProjectIdGet()

プロジェクトIDでプロジェクトを取得する  GET /api/v1/projects/{project_id}  認証: X-API-Key ヘッダー必須  レスポンス:     {         \"id\": 1,         \"name\": \"Project Name\",         \"repo_url\": \"https://github.com/owner/repo\",         \"local_path\": \"/path/to/project\",         \"context_bundle_path\": \"/path/to/context.json\",         \"created_at\": \"2025-01-01T00:00:00\",         \"updated_at\": \"2025-01-01T00:00:00\"     }  Args:     project_id: プロジェクトID     current_user: 認証済みユーザー情報  Returns:     ProjectResponse: プロジェクト情報  Raises:     HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）

### Example

```typescript
import {
    ProjectsApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ProjectsApi(configuration);

let projectId: number; // (default to undefined)
let xAPIKey: string; //API Key for authentication (default to undefined)

const { status, data } = await apiInstance.getProjectApiV1ProjectsProjectIdGet(
    projectId,
    xAPIKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**number**] |  | defaults to undefined|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ProjectResponse**

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

# **listProjectsApiV1ProjectsGet**
> ProjectListResponse listProjectsApiV1ProjectsGet()

プロジェクト一覧を取得する  GET /api/v1/projects  認証: X-API-Key ヘッダー必須  レスポンス:     {         \"projects\": [             {                 \"id\": 1,                 \"name\": \"Project Name\",                 \"repo_url\": \"https://github.com/owner/repo\",                 \"local_path\": \"/path/to/project\",                 \"created_at\": \"2025-01-01T00:00:00\",                 \"updated_at\": \"2025-01-01T00:00:00\"             }         ]     }  Args:     current_user: 認証済みユーザー情報  Returns:     ProjectListResponse: プロジェクト一覧  Raises:     HTTPException: 内部エラー時（500）

### Example

```typescript
import {
    ProjectsApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ProjectsApi(configuration);

let xAPIKey: string; //API Key for authentication (default to undefined)

const { status, data } = await apiInstance.listProjectsApiV1ProjectsGet(
    xAPIKey
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ProjectListResponse**

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

# **triggerProjectRunApiV1ProjectsProjectIdRunPost**
> ProjectRunResponse triggerProjectRunApiV1ProjectsProjectIdRunPost(projectRunRequest)

Self-Healing Run を発火する  POST /api/v1/projects/{project_id}/run  認証: X-API-Key ヘッダー必須  リクエスト JSON:     {         \"requirement\": \"Run self-healing for this repo\",         \"autonomy_level\": 2,         \"fast_lane\": true     }  レスポンス:     {         \"run_id\": \"abc123...\",         \"project_id\": 1,         \"status\": \"PENDING\",         \"queue_mode\": \"async\" または \"sync\"     }  ステータスコード:     - 200: 同期実行完了     - 202: 非同期実行開始（キューに入った）     - 400: requirement が未指定     - 404: プロジェクトが見つからない  Args:     project_id: プロジェクトID     request: 実行リクエスト     current_user: 認証済みユーザー情報  Returns:     ProjectRunResponse: 実行結果  Raises:     HTTPException: プロジェクトが見つからない場合（404）、requirement が未指定の場合（400）、または内部エラー時（500）

### Example

```typescript
import {
    ProjectsApi,
    Configuration,
    ProjectRunRequest
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new ProjectsApi(configuration);

let projectId: number; // (default to undefined)
let xAPIKey: string; //API Key for authentication (default to undefined)
let projectRunRequest: ProjectRunRequest; //

const { status, data } = await apiInstance.triggerProjectRunApiV1ProjectsProjectIdRunPost(
    projectId,
    xAPIKey,
    projectRunRequest
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectRunRequest** | **ProjectRunRequest**|  | |
| **projectId** | [**number**] |  | defaults to undefined|
| **xAPIKey** | [**string**] | API Key for authentication | defaults to undefined|


### Return type

**ProjectRunResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/json
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Synchronous execution completed |  -  |
|**202** | Asynchronous execution started |  -  |
|**400** | Bad Request |  -  |
|**401** | Unauthorized |  -  |
|**404** | Not Found |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

