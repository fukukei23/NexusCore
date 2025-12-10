# HealthApi

All URIs are relative to *http://localhost*

|Method | HTTP request | Description|
|------------- | ------------- | -------------|
|[**healthCheckApiV1HealthGet**](#healthcheckapiv1healthget) | **GET** /api/v1/health | Health Check|

# **healthCheckApiV1HealthGet**
> HealthCheckResponse healthCheckApiV1HealthGet()

Health check エンドポイント  API の稼働状況を返す。 認証不要な公開エンドポイント。  将来的に認証が必要になった場合は、以下のように変更可能: ```python async def health_check(     current_user: AuthenticatedUser = Depends(get_current_user), ) -> HealthCheckResponse: ```  Returns:     HealthCheckResponse: API の稼働状況とバージョン情報

### Example

```typescript
import {
    HealthApi,
    Configuration
} from 'nexuscore-sdk';

const configuration = new Configuration();
const apiInstance = new HealthApi(configuration);

const { status, data } = await apiInstance.healthCheckApiV1HealthGet();
```

### Parameters
This endpoint does not have any parameters.


### Return type

**HealthCheckResponse**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
|**200** | Successful Response |  -  |
|**500** | Internal Server Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

