# Create (or update) the project environment and run the test suite.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1 -VenvDir D:\envs\cnet
#
# The venv lives outside the repository by default because the repository sits
# in a OneDrive-synced folder. If you change -VenvDir, set CNET_VENV to the same
# path so run.cmd can find it.
param(
    [string]$VenvDir = $(if ($env:CNET_VENV) { $env:CNET_VENV } else { Join-Path $HOME ".venvs\cnet-xai-audit" })
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Find-Python311 {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $exe = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
    }
    $default = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311\python.exe"
    if (Test-Path $default) { return $default }
    throw "Python 3.11 not found. Install it with: winget install --id Python.Python.3.11 --exact --scope user"
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $Base = Find-Python311
    Write-Host "Creating venv at $VenvDir using $Base"
    & $Base -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
& $VenvPython -m pip install -e $Root
if ($LASTEXITCODE -ne 0) { throw "editable install failed" }

Push-Location $Root
try {
    & $VenvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "tests failed" }
} finally {
    Pop-Location
}
Write-Host "`nEnvironment ready: $VenvDir"
Write-Host "Run project commands with:  .\run.cmd -m pytest"
