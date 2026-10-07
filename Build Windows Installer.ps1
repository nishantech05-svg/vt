$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not $IsWindows -and $env:OS -ne 'Windows_NT') {
    throw 'Build this installer on Windows.'
}

$pythonOverride = if ($env:VOICE_TYPE_PYTHON) { Get-Command $env:VOICE_TYPE_PYTHON -ErrorAction SilentlyContinue } else { $null }
$pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonOverride) {
    & $pythonOverride.Source -m venv (Join-Path $projectRoot '.build-venv')
} elseif ($pythonLauncher) {
    & $pythonLauncher.Source -3.11 -m venv (Join-Path $projectRoot '.build-venv')
} elseif ($pythonCommand) {
    & $pythonCommand.Source -m venv (Join-Path $projectRoot '.build-venv')
} else {
    throw 'Python 3.11 is needed to build the installer. Install it from https://www.python.org/downloads/windows/, then rerun this script.'
}

$buildPython = Join-Path $projectRoot '.build-venv\Scripts\python.exe'
& $buildPython -m pip install --upgrade pip
& $buildPython -m pip install -r requirements.txt
& $buildPython -m PyInstaller --clean --noconfirm voice_type_windows.spec

$innoCompiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $innoCompiler) {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6\ISCC.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 7\ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 7\ISCC.exe')
    )
    $innoCompiler = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $innoCompiler) {
    throw 'Inno Setup 6 or 7 is needed to create the setup.exe. Install it from https://jrsoftware.org/isinfo.php, then rerun this script.'
}

& $innoCompiler (Join-Path $projectRoot 'installer\VoiceType.iss')
Write-Host "Windows installer created: $(Join-Path $projectRoot 'dist-installer\VoiceType-Setup.exe')"
