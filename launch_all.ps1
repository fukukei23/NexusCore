Write-Host "====== OpenCodeInterpreter 起動モードを選択してください ======" -ForegroundColor Cyan
Write-Host "1. 🟢 開発用ログ付き起動（launch_dev.ps1）"
Write-Host "2. 🟡 Streamlit旧UI起動（launch_streamlit_legacy.ps1）"
Write-Host "Q. ❌ 終了"

do {
    $choice = Read-Host "選択（1/2/Q）"
    switch ($choice.ToUpper()) {
        "1" {
            Write-Host "`n→ launch_dev.ps1 を起動します..." -ForegroundColor Green
            Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File ./launch_dev.ps1"
            break
        }
        "2" {
            Write-Host "`n→ launch_streamlit_legacy.ps1 を起動します..." -ForegroundColor Yellow
            Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File ./launch_streamlit_legacy.ps1"
            break
        }
        "Q" {
            Write-Host "`n終了します。" -ForegroundColor Red
            break
        }
        default {
            Write-Host "無効な選択です。再入力してください。" -ForegroundColor DarkRed
        }
    }
} while ($true)
