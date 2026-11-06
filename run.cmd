@echo off
rem Run the project's Python (.venv next to this file) without activating it.
rem   run.cmd -m pytest
rem   run.cmd -m src.data.inspection data\raw\unsw_nb15\UNSW_NB15_training-set.csv --label label
setlocal
set "VENV=%~dp0.venv"
if not exist "%VENV%\Scripts\python.exe" (
    echo Project environment not found at %VENV%
    echo Create it with: powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
    exit /b 1
)
"%VENV%\Scripts\python.exe" %*
exit /b %ERRORLEVEL%
