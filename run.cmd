@echo off
rem Run the project's Python without activating the venv.
rem   run.cmd -m pytest
rem   run.cmd -m src.data.inspection data\raw\unsw_nb15\UNSW_NB15_training-set.csv --label label
setlocal
set "VENV=%CNET_VENV%"
if "%VENV%"=="" set "VENV=%USERPROFILE%\.venvs\cnet-xai-audit"
if not exist "%VENV%\Scripts\python.exe" (
    echo Project environment not found at %VENV%
    echo Create it with: powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
    exit /b 1
)
"%VENV%\Scripts\python.exe" %*
exit /b %ERRORLEVEL%
