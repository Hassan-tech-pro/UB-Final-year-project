# Agentic AI Task Automation & Verification System - PowerShell Runner
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Starting Agentic AI Task Automation and Verification System" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$nodePath = "$env:LOCALAPPDATA\Programs\nodejs"
if (Test-Path $nodePath) {
    $env:Path = "$nodePath;$env:Path"
}
$env:PYTHONPATH = Join-Path $scriptDir "backend"

Write-Host "`n[1/2] Verifying Python Environment..." -ForegroundColor Yellow
python -c "import fastapi, pydantic, langgraph, pymupdf, docx, openpyxl, reportlab; print('All core libraries verified.')"

Write-Host "`n[2/2] Starting Server on http://localhost:8000" -ForegroundColor Green
Write-Host "Web Workspace: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Swagger Docs: http://localhost:8000/docs`n" -ForegroundColor Cyan

Set-Location (Join-Path $scriptDir "backend")
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
