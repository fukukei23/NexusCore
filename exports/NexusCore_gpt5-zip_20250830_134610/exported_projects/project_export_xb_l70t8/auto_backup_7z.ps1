if ((Get-Date).DayOfWeek -eq 'Sunday') {
    if (rclone copy "$Arch" "$Remote" --stats 10s) {
        Write-Host "[CLOUD] Google Drive へアップロード完了"
    } else {
        Write-Warning "[CLOUD] アップロード失敗"
    }
}
