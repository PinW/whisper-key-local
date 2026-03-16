# pyapp-build/build-pyapp.ps1
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AppName = "whisper-key",
    [switch]$Clean,
    [switch]$Test
)

function Get-ResolvedPath {
    param($Path, $BaseDir)
    if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $BaseDir $Path }
}

function Get-ProjectVersion {
    param($ProjectRoot)
    $PyProjectFile = Join-Path $ProjectRoot "pyproject.toml"
    if (-not (Test-Path $PyProjectFile)) {
        Write-Host "Error: pyproject.toml not found at $PyProjectFile" -ForegroundColor Red
        exit 1
    }
    $Content = Get-Content $PyProjectFile
    foreach ($Line in $Content) {
        if ($Line -match '^version\s*=\s*["''']([^"'']+)["''']') {
            return $Matches[1]
        }
    }
    Write-Host "Error: Could not find version in pyproject.toml" -ForegroundColor Red
    exit 1
}

$AppVersion = Get-ProjectVersion $ProjectRoot
Write-Host "Version: $AppVersion" -ForegroundColor Cyan

# Load build config
$ConfigFile = Join-Path $PSScriptRoot "build-config.json"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "Error: Build config not found at $ConfigFile" -ForegroundColor Red
    Write-Host "Copy build-config.example.json to build-config.json and set your paths" -ForegroundColor Yellow
    exit 1
}

$Config = Get-Content $ConfigFile | ConvertFrom-Json
$PyAppSourcePath = Get-ResolvedPath ([Environment]::ExpandEnvironmentVariables($Config.pyapp_source_path)) $ProjectRoot
$DistPath = Get-ResolvedPath ([Environment]::ExpandEnvironmentVariables($Config.dist_path)) $ProjectRoot

if (-not (Test-Path $PyAppSourcePath)) {
    Write-Host "Error: pyapp source not found at $PyAppSourcePath" -ForegroundColor Red
    Write-Host "Download from: https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path (Join-Path $PyAppSourcePath "Cargo.toml"))) {
    Write-Host "Error: No Cargo.toml found in $PyAppSourcePath — is this the pyapp source directory?" -ForegroundColor Red
    exit 1
}

Write-Host "Starting pyapp build for $AppName v$AppVersion..." -ForegroundColor Green
Write-Host "PyApp source: $PyAppSourcePath" -ForegroundColor Gray
Write-Host "Distribution: $DistPath" -ForegroundColor Gray

# Set pyapp environment variables
$env:PYAPP_PROJECT_NAME = "whisper-key-local"
$env:PYAPP_PROJECT_VERSION = $AppVersion
$env:PYAPP_PYTHON_VERSION = "3.12"
$env:PYAPP_EXEC_CODE = "from whisper_key.main import main; main()"
$env:PYAPP_SELF_COMMAND = "self"

# Clean previous build if requested
if ($Clean) {
    $TargetDir = Join-Path $PyAppSourcePath "target"
    if (Test-Path $TargetDir) {
        Write-Host "Cleaning previous Rust build..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $TargetDir
    }
}

# Build
Set-Location $PyAppSourcePath
Write-Host "Running cargo build --release..." -ForegroundColor Yellow
cargo build --release
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Copy binary to dist
if (-not (Test-Path $DistPath)) {
    New-Item -ItemType Directory -Path $DistPath -Force | Out-Null
}

$SourceExe = Join-Path $PyAppSourcePath "target\release\pyapp.exe"
$DestExe = Join-Path $DistPath "$AppName.exe"
Copy-Item $SourceExe $DestExe -Force

$ExeSize = (Get-Item $DestExe).Length / 1MB
Write-Host "Build successful!" -ForegroundColor Green
Write-Host "Executable: $DestExe" -ForegroundColor Green
Write-Host "Size: $([math]::Round($ExeSize, 2)) MB" -ForegroundColor Green

# Clean up env vars
Remove-Item Env:\PYAPP_PROJECT_NAME -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_PROJECT_VERSION -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_PYTHON_VERSION -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_EXEC_CODE -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_SELF_COMMAND -ErrorAction SilentlyContinue

# Play victory sound
try {
    $TadaSound = "$env:WINDIR\Media\tada.wav"
    if (Test-Path $TadaSound) {
        (New-Object System.Media.SoundPlayer $TadaSound).PlaySync()
    }
} catch {}
