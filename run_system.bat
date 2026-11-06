@echo off
title Agentic AI Task Automation & Verification System
echo =====================================================================
echo Starting Agentic AI Task Automation and Verification System
echo =====================================================================

set "PROJECT_ROOT=%~dp0"
set "PYTHONPATH=%PROJECT_ROOT%backend"
set "NODE_PATH=%LOCALAPPDATA%\Programs\nodejs"

if exist "%NODE_PATH%" (
    set "PATH=%NODE_PATH%;%PATH%"
)

echo.
echo [1/2] Verifying Python Environment...
python -c "import fastapi, pydantic, langgraph, pymupdf, docx, openpyxl, reportlab; print('All core libraries verified.')"
if %errorlevel% neq 0 (
    echo [ERROR] Python dependencies missing. Installing...
    pip install -r backend\requirements.txt
)

echo.
echo [2/2] Launching Backend Server on http://localhost:8000
echo Full Web Workspace available at: http://localhost:8000
echo API Documentation available at: http://localhost:8000/docs
echo.

cd "%PROJECT_ROOT%backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
