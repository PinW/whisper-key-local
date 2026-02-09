# py-build/build-windows.ps1
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$AppName = "whisper-key",
    [ValidateSet("cuda", "rocm")]
    [string]$Variant = "cuda",
    [switch]$Clean,
    [switch]$NoZip
)

# Helper function to resolve paths (absolute or relative to base directory)
function Get-ResolvedPath {
    param($Path, $BaseDir)
    if ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path $BaseDir $Path }
}

# Helper function to extract version from pyproject.toml
function Get-ProjectVersion {
    param($ProjectRoot)
    $PyProjectFile = Join-Path $ProjectRoot "pyproject.toml"
    if (-not (Test-Path $PyProjectFile)) {
        Write-Host "Error: pyproject.toml not found at $PyProjectFile" -ForegroundColor Red
        exit 1
    }
    
    try {
        $Content = Get-Content $PyProjectFile
        foreach ($Line in $Content) {
            if ($Line -match '^version\s*=\s*["'']([^"'']+)["'']') {
                return $Matches[1]
            }
        }
        Write-Host "Error: Could not find version in pyproject.toml" -ForegroundColor Red
        exit 1
    } catch {
        Write-Host "Error: Could not parse pyproject.toml: $_" -ForegroundColor Red
        exit 1
    }
}

# Get version from pyproject.toml (required)
$AppVersion = Get-ProjectVersion $ProjectRoot
Write-Host "Using version from pyproject.toml: $AppVersion" -ForegroundColor Cyan

# Write version file for runtime access (no BOM)
$VersionFile = Join-Path $ProjectRoot "src\whisper_key\assets\version.txt"
[System.IO.File]::WriteAllText($VersionFile, $AppVersion)
Write-Host "Version file written: $VersionFile" -ForegroundColor Gray

# Configuration - Check for build config file (variant-specific config takes priority)
$VariantConfigFile = Join-Path $PSScriptRoot "build-config-$Variant.json"
$DefaultConfigFile = Join-Path $PSScriptRoot "build-config.json"
$ConfigFile = if (Test-Path $VariantConfigFile) { $VariantConfigFile } else { $DefaultConfigFile }
if (Test-Path $ConfigFile) {
    Write-Host "Loading build configuration from: $ConfigFile" -ForegroundColor Cyan
    try {
        $Config = Get-Content $ConfigFile | ConvertFrom-Json
        # Expand environment variables in paths
        $ExpandedVenvPath = [Environment]::ExpandEnvironmentVariables($Config.venv_path)
        $ExpandedDistPath = [Environment]::ExpandEnvironmentVariables($Config.dist_path)
        
        # Resolve paths (absolute or relative to project root)
        $VenvPath = Get-ResolvedPath $ExpandedVenvPath $ProjectRoot
        $DistDir = Get-ResolvedPath $ExpandedDistPath $ProjectRoot
    } catch {
        Write-Host "Error reading config file, using defaults: $_" -ForegroundColor Yellow
        $VariantSuffix = if ($Variant -eq "cuda") { "" } else { "-amd-gpu-rocm" }
        $VenvPath = Join-Path $ProjectRoot "venv-$AppName$VariantSuffix"
        $DistDir = Join-Path $ProjectRoot "dist\$AppName-v$AppVersion$VariantSuffix"
    }
} else {
    Write-Host "No build config found, using default paths" -ForegroundColor Yellow
    $VariantSuffix = if ($Variant -eq "cuda") { "" } else { "-amd-gpu-rocm" }
    $VenvPath = Join-Path $ProjectRoot "venv-$AppName$VariantSuffix"
    $DistDir = Join-Path $ProjectRoot "dist\$AppName-v$AppVersion$VariantSuffix"
}

$SpecFile = Join-Path $PSScriptRoot "$AppName.spec"

Write-Host "Starting $AppName build with PyInstaller... [variant: $Variant]" -ForegroundColor Green
Write-Host "Virtual Environment: $VenvPath" -ForegroundColor Gray
Write-Host "Distribution Directory: $DistDir" -ForegroundColor Gray

# Uncomment the next line to test path detection without running build
# exit 0

# Helper function to get hash of dependencies from pyproject.toml
function Get-DependenciesHash {
    param($ProjectRoot)
    $PyProjectFile = Join-Path $ProjectRoot "pyproject.toml"
    $Content = Get-Content $PyProjectFile -Raw

    # Extract dependencies section
    if ($Content -match 'dependencies\s*=\s*\[([\s\S]*?)\]') {
        $DepsSection = $Matches[1]
        # Create hash of the dependencies content
        $Stream = [System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($DepsSection))
        $Hash = Get-FileHash -InputStream $Stream -Algorithm SHA256
        return $Hash.Hash
    }
    return $null
}

# Setup virtual environment (reuse if exists)
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"
$DepsHashFile = Join-Path $VenvPath ".deps-hash"

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        exit 1 
    }
    
    Write-Host "Installing project dependencies..." -ForegroundColor Yellow
    & $VenvPip install $ProjectRoot
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

    # Save dependencies hash
    $CurrentHash = Get-DependenciesHash $ProjectRoot
    if ($CurrentHash) {
        $CurrentHash | Out-File -FilePath $DepsHashFile -NoNewline
    }
} else {
    Write-Host "Reusing existing virtual environment..." -ForegroundColor Green

    # Check if dependencies have changed
    $CurrentHash = Get-DependenciesHash $ProjectRoot
    $StoredHash = if (Test-Path $DepsHashFile) { Get-Content $DepsHashFile -Raw } else { $null }

    if ($CurrentHash -ne $StoredHash) {
        Write-Host "Dependencies changed - syncing venv..." -ForegroundColor Yellow
        & $VenvPip install $ProjectRoot
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to sync dependencies" -ForegroundColor Red
            exit 1
        }
        $CurrentHash | Out-File -FilePath $DepsHashFile -NoNewline
        Write-Host "Dependencies synced successfully" -ForegroundColor Green
    }
}

# Install ROCm CTranslate2 wheel if building ROCm variant
if ($Variant -eq "rocm") {
    $RocmWheelDir = Join-Path $PSScriptRoot "wheels\rocm-rdna2"
    $RocmWheel = Get-ChildItem -Path $RocmWheelDir -Filter "ctranslate2-*.whl" | Select-Object -First 1
    if (-not $RocmWheel) {
        Write-Host "Error: No ROCm CTranslate2 wheel found in $RocmWheelDir" -ForegroundColor Red
        exit 1
    }
    Write-Host "Installing ROCm CTranslate2 wheel: $($RocmWheel.Name)" -ForegroundColor Yellow
    & $VenvPip install $RocmWheel.FullName --force-reinstall --no-deps
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install ROCm CTranslate2 wheel" -ForegroundColor Red
        exit 1
    }
}

# Set build variant environment variable for spec file
$env:WHISPER_KEY_VARIANT = $Variant

# Clean previous build
if (Test-Path $DistDir) {
    Write-Host "Cleaning previous build: $DistDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $DistDir
}

$BuildDir = Join-Path $ProjectRoot "build"
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}

# Execute PyInstaller
$VenvPyInstaller = Join-Path $VenvPath "Scripts\pyinstaller.exe"
Write-Host "Running PyInstaller with spec file: $SpecFile" -ForegroundColor Yellow

& $VenvPyInstaller $SpecFile --distpath $DistDir --clean
if ($LASTEXITCODE -ne 0) { 
    Write-Host "PyInstaller build failed!" -ForegroundColor Red
    exit 1 
}

Write-Host "Build successful!" -ForegroundColor Green
Write-Host "Executable location: $DistDir" -ForegroundColor Green

# Calculate distribution size  
$Size = (Get-ChildItem -Recurse $DistDir | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Distribution size: $Size MB" -ForegroundColor Green

# Create compressed distribution (optional)
if (-not $NoZip) {
    Write-Host "Creating compressed distribution..." -ForegroundColor Yellow
    $VariantSuffix = if ($Variant -eq "cuda") { "" } else { "-amd-gpu-rocm" }
    $ZipFileName = "$AppName-v$AppVersion-windows$VariantSuffix.zip"
    $ZipPath = Join-Path $DistDir $ZipFileName
    $AppDir = Join-Path $DistDir $AppName

    try {
        Compress-Archive -Path $AppDir -DestinationPath $ZipPath -CompressionLevel Optimal
        $ZipSize = (Get-Item $ZipPath).Length / 1MB
        $CompressionRatio = [math]::Round((1 - ($ZipSize / $Size)) * 100, 1)
        Write-Host "Compressed distribution created: $ZipFileName" -ForegroundColor Green
        Write-Host "Compressed size: $([math]::Round($ZipSize, 2)) MB ($CompressionRatio% reduction)" -ForegroundColor Green
    } catch {
        Write-Host "Failed to create compressed distribution: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Skipping zip creation (NoZip parameter specified)" -ForegroundColor Cyan
}

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