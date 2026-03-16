param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AppName = "whisper-key",
    [switch]$Clean
)

function Get-ResolvedPath {
    param($Path, $BaseDir)
    if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $BaseDir $Path }
}

function Get-ProjectVersion {
    param($ProjectRoot)
    $PyProjectFile = Join-Path $ProjectRoot "pyproject.toml"
    foreach ($Line in (Get-Content $PyProjectFile)) {
        if ($Line.StartsWith("version")) {
            return $Line.Split("=")[1].Trim().Trim('"')
        }
    }
    Write-Host "Error: Could not find version in pyproject.toml" -ForegroundColor Red
    exit 1
}

function Patch-IconSupport {
    param($PyAppSourcePath, $IconPath)

    $IconDest = Join-Path $PyAppSourcePath "icon.ico"
    Copy-Item $IconPath $IconDest -Force

    $CargoToml = Join-Path $PyAppSourcePath "Cargo.toml"
    $CargoContent = Get-Content $CargoToml -Raw
    if ($CargoContent -notmatch "winresource") {
        $CargoContent = $CargoContent -replace '\[build-dependencies\]', "[build-dependencies]`nwinresource = `"0.1`""
        Set-Content $CargoToml $CargoContent -NoNewline
        Write-Host "Patched Cargo.toml with winresource dependency" -ForegroundColor Gray
    }

    $BuildRs = Join-Path $PyAppSourcePath "build.rs"
    $BuildContent = Get-Content $BuildRs -Raw
    if ($BuildContent -notmatch "winresource") {
        $IconPatch = @'

    if std::env::var("CARGO_CFG_TARGET_OS").unwrap() == "windows" {
        let mut res = winresource::WindowsResource::new();
        res.set_icon("icon.ico");
        res.compile().expect("Failed to compile Windows resources");
    }
'@
        $BuildContent = $BuildContent -replace '(fn main\(\) \{)', "`$1$IconPatch"
        Set-Content $BuildRs $BuildContent -NoNewline
        Write-Host "Patched build.rs with icon embedding" -ForegroundColor Gray
    }
}

$AppVersion = Get-ProjectVersion $ProjectRoot
Write-Host "Version: $AppVersion" -ForegroundColor Cyan

$ConfigFile = Join-Path $PSScriptRoot "build-config.json"
if (-not (Test-Path $ConfigFile)) {
    Write-Host "Error: Build config not found at $ConfigFile" -ForegroundColor Red
    Write-Host "Copy build-config.example.json to build-config.json and set your paths" -ForegroundColor Yellow
    exit 1
}

$Config = Get-Content $ConfigFile | ConvertFrom-Json
$PyAppSourcePath = Get-ResolvedPath $Config.pyapp_source_path $ProjectRoot
$DistPath = Get-ResolvedPath $Config.dist_path $ProjectRoot

if (-not (Test-Path (Join-Path $PyAppSourcePath "Cargo.toml"))) {
    Write-Host "Error: No Cargo.toml found in $PyAppSourcePath" -ForegroundColor Red
    Write-Host "Download from: https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz" -ForegroundColor Yellow
    exit 1
}

$IconPath = Join-Path $ProjectRoot "src\whisper_key\platform\windows\assets\whisperkey-icon.ico"
if (Test-Path $IconPath) {
    Write-Host "Patching icon support..." -ForegroundColor Yellow
    Patch-IconSupport $PyAppSourcePath $IconPath
} else {
    Write-Host "Warning: Icon not found at $IconPath, building without icon" -ForegroundColor Yellow
}

Write-Host "Starting pyapp build for $AppName v$AppVersion..." -ForegroundColor Green
Write-Host "PyApp source: $PyAppSourcePath" -ForegroundColor Gray
Write-Host "Distribution: $DistPath" -ForegroundColor Gray

$env:PYAPP_PROJECT_NAME = "whisper-key-local"
$env:PYAPP_PROJECT_VERSION = $AppVersion
$env:PYAPP_PYTHON_VERSION = "3.12"
$env:PYAPP_EXEC_CODE = 'from whisper_key.main import main; main()'
$env:PYAPP_SELF_COMMAND = "self"

if ($Clean) {
    $TargetDir = Join-Path $PyAppSourcePath "target"
    if (Test-Path $TargetDir) {
        Write-Host "Cleaning previous Rust build..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $TargetDir
    }
}

Push-Location $PyAppSourcePath
Write-Host "Running cargo build --release..." -ForegroundColor Yellow
cargo build --release
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DistPath)) {
    New-Item -ItemType Directory -Path $DistPath -Force | Out-Null
}

$SourceExe = Join-Path $PyAppSourcePath "target\release\pyapp.exe"
$DestExe = Join-Path $DistPath "$AppName.exe"
Copy-Item $SourceExe $DestExe -Force

$ExeSize = (Get-Item $DestExe).Length / 1MB
Write-Host "Build successful!" -ForegroundColor Green
Write-Host "Executable: $DestExe" -ForegroundColor Green
Write-Host ("Size: {0:N2} MB" -f $ExeSize) -ForegroundColor Green

Pop-Location
Remove-Item Env:\PYAPP_PROJECT_NAME -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_PROJECT_VERSION -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_PYTHON_VERSION -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_EXEC_CODE -ErrorAction SilentlyContinue
Remove-Item Env:\PYAPP_SELF_COMMAND -ErrorAction SilentlyContinue
