# ============================================================================
# Home Rental Management System - One-Terminal PowerShell Launch Script
# ============================================================================

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   HOME RENTAL MANAGEMENT SYSTEM - LOCAL ENVIRONMENT LAUNCHER" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan

# 1. Check or Create Virtual Environment
if (-Not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "`n[1/4] Creating virtual environment (.venv)..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment. Ensure Python is installed." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "`n[1/4] Virtual environment already exists." -ForegroundColor Green
}

# 2. Activate Virtual Environment
Write-Host "`n[2/4] Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# 3. Install Dependencies
Write-Host "`n[3/4] Verifying and installing required packages from requirements.txt..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARNING] pip install returned a warning or non-zero code. Trying standard install..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# 4. Check .env Configuration
Write-Host "`n[4/4] Checking environment configuration..." -ForegroundColor Yellow
if (-Not (Test-Path ".env")) {
    Write-Host "[INFO] Copying .env.example to .env..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[IMPORTANT] Please edit .env with your real Supabase Project credentials." -ForegroundColor Red
}

# 5. Launch Flask Application
Write-Host "`n==================================================================" -ForegroundColor Green
Write-Host "  Starting Flask Web Server on http://127.0.0.1:5000" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop the server at any time." -ForegroundColor Cyan
Write-Host "==================================================================`n" -ForegroundColor Green

python app.py
