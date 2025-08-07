# py-build/build-windows.ps1
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AppName = "whisper-key",
    [string]$AppVersion = "0.1.0"
)

# Configuration - Put venv on Windows filesystem (not WSL)
$VenvPath = Join-Path $env:USERPROFILE "Desktop\venv-$AppName"
$DistDir = Join-Path $ProjectRoot "dist\$AppName-v$AppVersion"
$SpecFile = Join-Path $PSScriptRoot "$AppName.spec"

Write-Host "Starting $AppName build with PyInstaller..." -ForegroundColor Green

# Setup virtual environment (reuse if exists)
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        exit 1 
    }
    
    Write-Host "Installing project dependencies..." -ForegroundColor Yellow
    $RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
    & $VenvPip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "Failed to install dependencies" -ForegroundColor Red
        exit 1 
    }
    
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    & $VenvPip install pyinstaller
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "Failed to install PyInstaller" -ForegroundColor Red
        exit 1 
    }
} else {
    Write-Host "Reusing existing virtual environment..." -ForegroundColor Green
}

# Clean previous build
if (Test-Path $DistDir) {
    Write-Host "Cleaning previous build: $DistDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force (Split-Path $DistDir)
}

$BuildDir = Join-Path $ProjectRoot "build"
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}

# Execute PyInstaller
$VenvPyInstaller = Join-Path $VenvPath "Scripts\pyinstaller.exe"
Write-Host "Running PyInstaller with spec file: $SpecFile" -ForegroundColor Yellow

& $VenvPyInstaller $SpecFile
if ($LASTEXITCODE -ne 0) { 
    Write-Host "PyInstaller build failed!" -ForegroundColor Red
    exit 1 
}

Write-Host "Build successful!" -ForegroundColor Green
Write-Host "Executable location: $DistDir" -ForegroundColor Green

# Calculate distribution size  
$Size = (Get-ChildItem -Recurse $DistDir | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Distribution size: $Size MB" -ForegroundColor Green

# Play victory sound
try {
    $TadaSound = "$env:WINDIR\Media\tada.wav"
    if (Test-Path $TadaSound) {
        Write-Host "Playing victory sound..." -ForegroundColor Cyan
        (New-Object System.Media.SoundPlayer $TadaSound).PlaySync()
    }
} catch {
    # Silently ignore if sound fails to play
}