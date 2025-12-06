@echo off
cd /d "%~dp0"
echo Gradio UIを起動します...

REM 仮想環境をアクティベート（必要に応じてパスを変更）
call venv\Scripts\activate

REM UIメインを起動
python src\main_ui.py

pause
