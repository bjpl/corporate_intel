# Python version checker for Corporate Intelligence Platform (Windows PowerShell)
# Ensures Python 3.10+ is installed

$ErrorActionPreference = "Stop"

$MIN_PYTHON_VERSION = "3.10"
$REQUIRED_VERSION_MAJOR = 3
$REQUIRED_VERSION_MINOR = 10

Write-Host "Corporate Intelligence Platform - Python Version Check" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
$pythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonCmd = "python3"
} else {
    Write-Host "ERROR: Python is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python 3.10 or higher."
    Write-Host "Visit: https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "Recommended: Use winget to install Python:"
    Write-Host "  winget install Python.Python.3.10"
    exit 1
}

# Get Python version
$pythonVersionOutput = & $pythonCmd --version 2>&1
$pythonVersion = $pythonVersionOutput -replace "Python ", ""
$versionParts = $pythonVersion.Split(".")
$pythonMajor = [int]$versionParts[0]
$pythonMinor = [int]$versionParts[1]

Write-Host "Detected Python version: $pythonVersion"
Write-Host ""

# Check version requirement
if ($pythonMajor -lt $REQUIRED_VERSION_MAJOR -or `
    ($pythonMajor -eq $REQUIRED_VERSION_MAJOR -and $pythonMinor -lt $REQUIRED_VERSION_MINOR)) {
    Write-Host "ERROR: Python version $pythonVersion is too old!" -ForegroundColor Red
    Write-Host ""
    Write-Host "This project requires Python $MIN_PYTHON_VERSION or higher."
    Write-Host "Current version: $pythonVersion"
    Write-Host ""
    Write-Host "Please upgrade Python:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1 - winget (recommended):"
    Write-Host "  winget install Python.Python.3.10"
    Write-Host ""
    Write-Host "Option 2 - Download installer:"
    Write-Host "  https://www.python.org/downloads/"
    Write-Host ""
    exit 1
}

Write-Host "✓ Python version check passed!" -ForegroundColor Green
Write-Host ""

# Check for virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Running in virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "WARNING: Not running in a virtual environment" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "It's recommended to use a virtual environment:"
    Write-Host "  python -m venv venv"
    Write-Host "  venv\Scripts\Activate.ps1"
    Write-Host ""
    Write-Host "Note: You may need to enable script execution:"
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    Write-Host ""
}

# Check pip version
$pipVersionOutput = & $pythonCmd -m pip --version 2>&1
$pipVersion = ($pipVersionOutput -split " ")[1]
Write-Host "pip version: $pipVersion"
Write-Host ""

# Check critical dependencies
Write-Host "Checking critical dependencies..."
$criticalPackages = @("fastapi", "pydantic", "sqlalchemy")

foreach ($pkg in $criticalPackages) {
    try {
        & $pythonCmd -c "import $pkg" 2>$null
        Write-Host "  ✓ $pkg installed" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ $pkg not installed (will be installed during setup)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Python environment check complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Create virtual environment: python -m venv venv"
Write-Host "  2. Activate it: venv\Scripts\Activate.ps1"
Write-Host "  3. Install dependencies: pip install -e ."
Write-Host ""

exit 0
