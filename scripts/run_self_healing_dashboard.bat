@echo off
REM run_self_healing_dashboard.bat
REM NexusCore Self-Healing Dashboard を起動するためのバッチスクリプト
REM 使用例:
REM   scripts\run_self_healing_dashboard.bat
REM   scripts\run_self_healing_dashboard.bat C:\path\to\project

SET PROJECT_ROOT=%1
IF "%PROJECT_ROOT%"=="" (
  SET PROJECT_ROOT=.
)

ECHO Launching Self-Healing Dashboard for project_root=%PROJECT_ROOT%

REM プロジェクトルートの存在確認
IF NOT EXIST "%PROJECT_ROOT%" (
  ECHO エラー: プロジェクトルートが見つかりません: %PROJECT_ROOT%
  EXIT /B 1
)

REM 必要なら venv を有効化 (Python venv の場所に合わせて調整)
IF EXIST venv\Scripts\activate.bat (
  CALL venv\Scripts\activate.bat
) ELSE IF EXIST myenv\Scripts\activate.bat (
  CALL myenv\Scripts\activate.bat
) ELSE IF EXIST .venv\Scripts\activate.bat (
  CALL .venv\Scripts\activate.bat
)

REM プロジェクトルートを環境変数として設定
SET NEXUS_PROJECT_ROOT=%PROJECT_ROOT%

REM Streamlitを実行
streamlit run src\nexuscore\ui\self_healing_dashboard.py -- --server.port 8501 --server.address 0.0.0.0 --server.headless true

