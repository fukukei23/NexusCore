# PlansApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**listPlansApiV1PlansGet**](#listplansapiv1plansget) | **GET** /api/v1/plans | List plans|

# **listPlansApiV1PlansGet**
> PlanListResponse listPlansApiV1PlansGet()

Plan一覧を取得する  GET /api/v1/plans?project_id=1  認証: X-API-Key ヘッダー必須  クエリパラメータ:     project_id: プロジェクトIDでフィルタ（任意）  レスポンス:     {         \"plans\": [             {                 \"id\": 1,                 \"project_id\": 1,                 \"name\": \"Implementation Plan\",                 \"created_at\": \"2025-01-01T00:00:00\",                 \"updated_at\": \"2025-01-01T00:00:00\"             }         ]     }  注意: 現時点では Plan モデルがデータベースに存在しないため、 空のリストを返します。将来的に Plan モデルが実装されたら、 実際のデータを返すように更新されます。  Args:     project_id: プロジェクトIDでフィルタ（任意）     current_user: 認証済みユーザー情報  Returns:     PlanListResponse: Plan一覧（現時点では空のリスト）  Raises:     HTTPException: 内部エラー時（500）

### Example

```typescript
import {
    PlansApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new PlansApi(configuration);

let xAPIKey: string; //API Key for authentication (default to undefined)
let projectId: number; //プロジェクトIDでフィルタ (optional) (default to undefined)

const { status, data } = await apiInstance.listPlansApiV1PlansGet(
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

**PlanListResponse**

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

