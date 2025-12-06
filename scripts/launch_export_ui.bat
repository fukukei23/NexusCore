@echo off
setlocal
REM ========================================================
REM NexusCore Export UI Launcher (Batch)
REM 日付: 2025-08-28
REM このバッチをダブルクリックで nexus_export_ui.py を起動
REM ========================================================

REM venv を優先的に使用
if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

REM 実行
python tools\nexus_export_ui.py
endlocal
