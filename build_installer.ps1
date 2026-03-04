# =============================================================================
#  build_installer.ps1
#  DUBGG Generator HMI - Full Build and Package Script
#
#  Run this script once on your DEVELOPMENT machine.
#  It will produce:
#       dist\DUBGG_HMI.exe   (standalone, ~50-150 MB)
#
#  The resulting EXE can be copied to ANY Windows machine and run directly.
#  It requires NO Python, NO Node.js, NO npm to be installed on the target.
#
#  USAGE (from the project root in PowerShell):
#       .\build_installer.ps1
#
#  Optional switches:
#       -SkipNpm          Skip "npm install" if node_modules already exists
#       -SkipPipInstall   Skip "pip install" if packages already installed
#       -Clean            Delete previous dist/ and build/ before building
# =============================================================================
param(
    [switch]$SkipNpm,
    [switch]$SkipPipInstall,
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -- Helper functions ---------------------------------------------------------

function Write-Header($msg) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step($msg) {
    Write-Host "[STEP] $msg" -ForegroundColor Yellow
}

function Write-OK($msg) {
    Write-Host "[OK]   $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    exit 1
}

function Assert-Command($cmd) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Fail "'$cmd' is not installed or not on PATH. Please install it first."
    }
}

# -- Locate the script's own directory (project root) -------------------------
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $ProjectRoot

Write-Header "DUBGG Generator HMI - Build and Package"
Write-Host "  Project root : $ProjectRoot"
Write-Host "  Date/Time    : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# -- 0. Detect Python executable ----------------------------------------------
Write-Step "Detecting Python executable ..."

# Priority order:
#  1. .venv in the project folder (most reliable - same env that runs api_server)
#  2. py launcher (Windows Python Launcher - avoids Store alias)
#  3. python3
#  4. python (last resort)
$PY = $null

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    $PY = $venvPython
    Write-OK "Using project .venv: $PY"
}

if (-not $PY) {
    foreach ($candidate in @("py", "python3", "python")) {
        $found = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($found) {
            # Make sure it is a real Python, not the Windows Store stub
            $ver = & $candidate --version 2>&1
            if ($ver -match "Python 3") {
                $PY = $candidate
                Write-OK "Using Python: $candidate ($ver)"
                break
            }
        }
    }
}

if (-not $PY) {
    Write-Fail ("No usable Python 3 found. " +
        "Either activate your .venv first, install Python from python.org, " +
        "or disable the Windows Store Python alias in: " +
        "Settings > Apps > Advanced app settings > App execution aliases.")
}

# Verify version is 3.8+
$verOut = & $PY --version 2>&1
Write-OK "Python version: $verOut"

# -- 1. Prerequisite checks (Node / npm) -------------------------------------
Write-Step "Checking Node.js / npm prerequisites ..."
Assert-Command "node"
Assert-Command "npm"

Write-OK "Node : $(node --version)"
Write-OK "npm  : $(npm --version)"

# -- 2. Optional clean --------------------------------------------------------
if ($Clean) {
    Write-Step "Cleaning previous build artefacts ..."
    foreach ($dir in @("dist", "build", "frontend_dist")) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir
            Write-OK "Deleted $dir/"
        }
    }
}

# -- 3. Install Python dependencies -------------------------------------------
if (-not $SkipPipInstall) {
    Write-Step "Installing Python dependencies ..."

    $pipPackages = @(
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "pymodbus",
        "psutil",
        "aiofiles",
        "python-multipart",
        "h11",
        "httptools",
        "websockets",
        "pyinstaller"
    )

    foreach ($pkg in $pipPackages) {
        Write-Host "  pip install $pkg ..." -ForegroundColor DarkGray
        & $PY -m pip install --quiet --upgrade $pkg
        if ($LASTEXITCODE -ne 0) { Write-Fail "Failed to install $pkg" }
    }
    Write-OK "All Python packages installed."
}
else {
    Write-OK "Skipping pip install (-SkipPipInstall)."
}

# -- 4. Install Node packages -------------------------------------------------
if (-not $SkipNpm) {
    Write-Step "Installing Node.js packages (npm install) ..."
    npm install --silent
    if ($LASTEXITCODE -ne 0) { Write-Fail "npm install failed." }
    Write-OK "npm packages installed."
}
else {
    Write-OK "Skipping npm install (-SkipNpm)."
}

# -- 5. Build the React frontend ----------------------------------------------
Write-Step "Building React frontend (npm run build) ..."
npm run build
if ($LASTEXITCODE -ne 0) { Write-Fail "npm run build failed." }

# Vite outputs to "dist/" by default; rename it so PyInstaller can find it
# under the clearer name "frontend_dist/" without colliding with PyInstaller's
# own "dist/" output folder.
if (Test-Path "frontend_dist") {
    Remove-Item -Recurse -Force "frontend_dist"
}
Rename-Item -Path "dist" -NewName "frontend_dist"
Write-OK "Frontend built -> frontend_dist/"

# -- 6. Sanity check ----------------------------------------------------------
$indexHtml = "frontend_dist\index.html"
if (-not (Test-Path $indexHtml)) {
    Write-Fail "Expected frontend_dist\index.html not found after npm build. Check Vite config."
}
Write-OK "frontend_dist\index.html confirmed."

# -- 7. Package with PyInstaller ----------------------------------------------
Write-Step "Running PyInstaller (this may take a few minutes) ..."

& $PY -m PyInstaller DUBGG.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller failed. Check output above." }

$exePath = "dist\DUBGG_HMI.exe"
if (-not (Test-Path $exePath)) {
    Write-Fail "Expected $exePath not found after PyInstaller."
}

$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
Write-OK "EXE built: $exePath  ($exeSize MB)"

# -- 8. Done ------------------------------------------------------------------
Write-Header "Build Successful!"
Write-Host ""
Write-Host "  Output EXE : $(Resolve-Path $exePath)" -ForegroundColor Green
Write-Host ""
Write-Host "  HOW TO DEPLOY:" -ForegroundColor White
Write-Host "  1. Copy  dist\DUBGG_HMI.exe  to the target Windows machine." -ForegroundColor White
Write-Host "  2. Double-click (or run from cmd/PowerShell)." -ForegroundColor White
Write-Host "  3. The browser opens automatically at http://localhost:8000." -ForegroundColor White
Write-Host ""
Write-Host "  NOTE: Port 8000 must not be blocked by the target firewall." -ForegroundColor DarkGray
Write-Host ""

Pop-Location
