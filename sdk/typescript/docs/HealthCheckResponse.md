# HealthCheckResponse

Health check レスポンスモデル  Attributes:     status: API の稼働状況（\"ok\" 固定）     version: API のバージョン     timestamp: レスポンス生成時刻

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**status** | **string** |  | [default to undefined]
**version** | **string** |  | [default to undefined]
**timestamp** | **string** |  | [default to undefined]

## Example

```typescript
import { HealthCheckResponse } from 'nexuscore-sdk';

const instance: HealthCheckResponse = {
    status,
    version,
    timestamp,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
