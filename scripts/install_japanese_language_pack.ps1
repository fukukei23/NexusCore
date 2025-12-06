# Cursor IDE 日本語言語パック インストールスクリプト
# PowerShellで実行してください

Write-Host "Cursor IDE 日本語言語パックをインストールしています..." -ForegroundColor Cyan

# Cursorコマンドのパスを確認
$cursorPath = Get-Command cursor -ErrorAction SilentlyContinue
if (-not $cursorPath) {
    # 一般的なCursorのインストールパスを確認
    $possiblePaths = @(
        "$env:LOCALAPPDATA\Programs\cursor\Cursor.exe",
        "$env:ProgramFiles\Cursor\Cursor.exe",
        "$env:ProgramFiles(x86)\Cursor\Cursor.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $cursorPath = $path
            break
        }
    }
}

if ($cursorPath) {
    Write-Host "Cursorが見つかりました: $cursorPath" -ForegroundColor Green
    
    # 拡張機能をインストール
    if ($cursorPath -is [System.Management.Automation.CommandInfo]) {
        & cursor --install-extension ms-ceintl.vscode-language-pack-ja
    }
    else {
        & "$cursorPath" --install-extension ms-ceintl.vscode-language-pack-ja
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n日本語言語パックのインストールが完了しました！" -ForegroundColor Green
        Write-Host "Cursor IDEを再起動してください。" -ForegroundColor Yellow
    }
    else {
        Write-Host "`nインストール中にエラーが発生しました。" -ForegroundColor Red
        Write-Host "手動でインストールしてください：" -ForegroundColor Yellow
        Write-Host "1. Cursor IDEで Ctrl+Shift+X を押す" -ForegroundColor Yellow
        Write-Host "2. 'Japanese Language Pack' を検索" -ForegroundColor Yellow
        Write-Host "3. 'Install' をクリック" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Cursorコマンドが見つかりませんでした。" -ForegroundColor Red
    Write-Host "`n手動でインストールしてください：" -ForegroundColor Yellow
    Write-Host "1. Cursor IDEを開く" -ForegroundColor Yellow
    Write-Host "2. Ctrl+Shift+X で拡張機能パネルを開く" -ForegroundColor Yellow
    Write-Host "3. 'Japanese Language Pack' を検索" -ForegroundColor Yellow
    Write-Host "4. 'Install' をクリック" -ForegroundColor Yellow
    Write-Host "5. Cursor IDEを再起動" -ForegroundColor Yellow
}
