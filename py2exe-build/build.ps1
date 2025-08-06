# build/build.ps1
param (
    [switch]$InstallDeps = $false
)

# --- Configuration ---
$RequirementsFile = ".\requirements.txt"
$BuilderScript = ".\py2exe-build\builder.py"

# --- Main Logic ---
Write-Host "--- Starting WhisperKey Build Process ---" -ForegroundColor Cyan

# 1. Dependency Check
if ($InstallDeps) {
    Write-Host "Installing/updating dependencies from $RequirementsFile..."
    pip install -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Dependency installation failed." -ForegroundColor Red
        exit 1
    }
}

# 2. Execute Build
Write-Host "Running Python build script..."
python $BuilderScript
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python build script failed." -ForegroundColor Red
    exit 1
}

Write-Host "--- Build process finished. ---" -ForegroundColor Green