# launch_dev.ps1 - Gradio UI を開発者モードで起動し、ログも同時記録
$LogDir = "./logs"
$LogFile = "$LogDir/dev_log_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# ログ用ディレクトリを作成（なければ）
if (!(Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# 環境情報表示
Write-Host "🔧 Gradio UI をログ付きで起動します..." -ForegroundColor Cyan
Write-Host "📂 ログ出力先: $LogFile" -ForegroundColor DarkGray
Write-Host "▶️ 実行コマンド: python .\src\main_ui.py" -ForegroundColor Gray
Write-Host ""

# ログ付きで実行（stderrも含めて記録）
$pythonCmd = "python ./src/main_ui.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command `"& { $pythonCmd *>> '$LogFile' }`""

# 終了待機（スクリプトから戻るまで即終了しない）
Start-Sleep -Seconds 2
