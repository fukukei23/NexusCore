<#
  京都市（緯度経度固定）の現在気温を Open-Meteo で取得し、
  GPT-4o に日本語で整形してもらう簡易スクリプト。
#>

param(
  [string]$City      = 'Kyoto',
  [double]$Lat       = 35.0116,
  [double]$Lon       = 135.7680
)

#----- 1. 現在気温を取得 ------------------------------------------------------
$weatherUrl = "https://api.open-meteo.com/v1/forecast" +
              "?latitude=$Lat&longitude=$Lon&current=temperature_2m"

try {
    $wx = Invoke-RestMethod -Uri $weatherUrl -Method Get -TimeoutSec 10
} catch {
    Write-Error "Weather API error: $_"
    exit 1
}

$temperature = $wx.current.temperature_2m
$prompt = "京都市の現在気温は ${temperature}℃ です。分かりやすく一文で伝えて。"

#----- 2. GPT-4o に要約を依頼 -------------------------------------------------
$headers = @{ Authorization = "Bearer $Env:OPENAI_API_KEY" }

$body = @{
  model    = 'gpt-4o'
  messages = @(
    @{ role = 'system'; content = 'あなたは天気解説アシスタントです。' },
    @{ role = 'user'  ; content = $prompt }
  )
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod `
  -Uri 'https://api.openai.com/v1/chat/completions' `
  -Method Post `
  -Headers $headers `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
  -ContentType 'application/json'

Write-Host "`n--- GPT-4o からの回答 ---`n"
$response.choices[0].message.content
