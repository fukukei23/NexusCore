# BadgeResponse

Badge レスポンスモデル（shields.io 互換）  Attributes:     schemaVersion: スキーマバージョン（常に1）     label: バッジラベル     message: バッジメッセージ     color: バッジカラー（brightgreen, green, yellow, red, blue, lightgrey）

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schemaVersion** | **number** | スキーマバージョン | [optional] [default to SchemaVersionEnum_NUMBER_1]
**label** | **string** | バッジラベル | [default to undefined]
**message** | **string** | バッジメッセージ | [default to undefined]
**color** | **string** | バッジカラー | [default to undefined]

## Example

```typescript
import { BadgeResponse } from 'nexuscore-sdk';

const instance: BadgeResponse = {
    schemaVersion,
    label,
    message,
    color,
};
```

[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)
