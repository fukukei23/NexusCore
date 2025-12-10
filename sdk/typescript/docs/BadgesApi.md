# BadgesApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**projectLastRunBadgeApiV1ProjectsProjectIdBadgeLastRunGet**](#projectlastrunbadgeapiv1projectsprojectidbadgelastrunget) | **GET** /api/v1/projects/{project_id}/badge/last_run | Get project last run badge|
|[**projectSuccessRateBadgeApiV1ProjectsProjectIdBadgeSuccessRateGet**](#projectsuccessratebadgeapiv1projectsprojectidbadgesuccessrateget) | **GET** /api/v1/projects/{project_id}/badge/success_rate | Get project success rate badge|

# **projectLastRunBadgeApiV1ProjectsProjectIdBadgeLastRunGet**
> BadgeResponse projectLastRunBadgeApiV1ProjectsProjectIdBadgeLastRunGet()

プロジェクトの最新Runステータスバッジ用 JSON を返す（shields.io endpoint 互換）  GET /api/v1/projects/{project_id}/badge/last_run  認証: 不要（公開エンドポイント）  レスポンス:     {         \"schemaVersion\": 1,         \"label\": \"self-healing\",         \"message\": \"last: SUCCESS\",         \"color\": \"brightgreen\"     }  ステータスコード:     - 200: 成功     - 404: プロジェクトが見つからない  Args:     project_id: プロジェクトID  Returns:     BadgeResponse: 最新Runステータスバッジ情報  Raises:     HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）

### Example

```typescript
import {
    BadgesApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new BadgesApi(configuration);

let projectId: number; // (default to undefined)

const { status, data } = await apiInstance.projectLastRunBadgeApiV1ProjectsProjectIdBadgeLastRunGet(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**number**] |  | defaults to undefined|


### Return type

**BadgeResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**404** | Not Found |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **projectSuccessRateBadgeApiV1ProjectsProjectIdBadgeSuccessRateGet**
> BadgeResponse projectSuccessRateBadgeApiV1ProjectsProjectIdBadgeSuccessRateGet()

プロジェクトの成功率バッジ用 JSON を返す（shields.io endpoint 互換）  GET /api/v1/projects/{project_id}/badge/success_rate  認証: 不要（公開エンドポイント）  レスポンス:     {         \"schemaVersion\": 1,         \"label\": \"self-healing\",         \"message\": \"95.0% success\",         \"color\": \"brightgreen\"     }  ステータスコード:     - 200: 成功     - 404: プロジェクトが見つからない  Args:     project_id: プロジェクトID  Returns:     BadgeResponse: 成功率バッジ情報  Raises:     HTTPException: プロジェクトが見つからない場合（404）または内部エラー時（500）

### Example

```typescript
import {
    BadgesApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new BadgesApi(configuration);

let projectId: number; // (default to undefined)

const { status, data } = await apiInstance.projectSuccessRateBadgeApiV1ProjectsProjectIdBadgeSuccessRateGet(
    projectId
);
```

### Parameters

|Name | Type | Description  | Notes|
|------------- | ------------- | ------------- | -------------|
| **projectId** | [**number**] |  | defaults to undefined|


### Return type

**BadgeResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**404** | Not Found |  -  |
|**500** | Internal Server Error |  -  |
|**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

