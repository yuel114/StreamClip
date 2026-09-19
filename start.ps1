param([switch]$CheckOnly)

$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$probe = "import sys,struct,venv,ensurepip,tkinter,ssl,sqlite3; assert (3,11) <= sys.version_info[:2] < (3,14) and struct.calcsize('P') == 8; print(sys.executable)"

function Find-Python {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if (-not $candidate -or -not (Test-Path -LiteralPath $candidate -PathType Leaf)) { continue }
        # Ignore native stderr here; failed probes are expected on moved venvs.
        $ErrorActionPreference = 'Continue'
        try {
            $result = & $candidate -E -X utf8 -c $probe 2>$null
            if ($LASTEXITCODE -eq 0 -and $result) { return [string]@($result)[-1] }
        } catch {
            continue
        } finally {
            $ErrorActionPreference = 'Stop'
        }
    }
}

function Invoke-Python {
    param([string]$Python, [string[]]$Arguments)
    $ErrorActionPreference = 'Continue'
    try {
        $global:LASTEXITCODE = $null
        & $Python -E -X utf8 -B @Arguments 2>&1 | ForEach-Object {
            "$_" | Out-File -LiteralPath $script:logPath -Append -Encoding utf8
            Write-Host "$_"
        }
        $code = $global:LASTEXITCODE
    } finally {
        $ErrorActionPreference = 'Stop'
    }
    if ($code -ne 0) { throw "Python exited with code $code. See $script:logPath" }
}

function Install-Python {
    param([string]$Cache)
    # Official CPython release, pinned and hash-verified before execution.
    $version = '3.13.15'
    $expectedHash = 'edec09c4853aeae9ac36efb8c9f95b6b8e2fee65eee56d9767a8b7c69c574403'
    $installer = Join-Path $Cache "python-$version-amd64.exe"
    if (-not (Test-Path -LiteralPath $installer) -or
        (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expectedHash) {
        Write-Host "Downloading Python $version from python.org ..."
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -UseBasicParsing -TimeoutSec 300 -Uri "https://www.python.org/ftp/python/$version/python-$version-amd64.exe" -OutFile $installer
    }
    if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $expectedHash) {
        throw 'Python installer checksum mismatch. Nothing was executed.'
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
        throw 'Python installer signature verification failed. Nothing was executed.'
    }
    Write-Host 'Installing Python for the current Windows user (no PATH changes) ...'
    $process = Start-Process -FilePath $installer -ArgumentList @(
        '/quiet', 'InstallAllUsers=0', 'PrependPath=0', 'Include_launcher=0',
        'AssociateFiles=0', 'Shortcuts=0', 'Include_test=0', 'Include_doc=0',
        'Include_pip=1', 'Include_tcltk=1', '/log', ('"' + (Join-Path $Cache 'python-install.log') + '"')
    ) -WindowStyle Hidden -PassThru -Wait
    if ($process.ExitCode -notin @(0, 3010)) { throw "Python installation failed: $($process.ExitCode). See $Cache\python-install.log" }
}

function Get-SystemPython {
    $candidates = @()
    $command = Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*\Microsoft\WindowsApps\*') { $candidates += $command.Source }
    foreach ($registry in @('HKCU:\Software\Python\PythonCore\*\InstallPath', 'HKLM:\Software\Python\PythonCore\*\InstallPath')) {
        foreach ($key in @(Get-ItemProperty -Path $registry -ErrorAction SilentlyContinue)) {
            if ($key.ExecutablePath) { $candidates += $key.ExecutablePath }
            elseif ($key.'(default)') { $candidates += Join-Path $key.'(default)' 'python.exe' }
        }
    }
    Find-Python -Candidates ($candidates | Select-Object -Unique)
}

function Start-StreamClip {
    $script:logPath = $null
    $lock = $null
    try {
        if (-not [Environment]::Is64BitOperatingSystem) { throw 'StreamClip requires 64-bit Windows 10/11.' }
        Set-Location -LiteralPath $appRoot
        $logRoot = Join-Path $appRoot 'data\logs'
        New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
        $script:logPath = Join-Path $logRoot ('startup-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + "-$PID.log")
        "StreamClip startup $(Get-Date -Format o)" | Out-File -LiteralPath $script:logPath -Encoding utf8
        Write-Host "Startup log: $script:logPath"
        # Hold the lock until this launched instance closes, including setup.
        $lock = [IO.File]::Open((Join-Path $logRoot 'source-launch.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
        $cache = Join-Path $appRoot '.runtime'
        New-Item -ItemType Directory -Force -Path $cache | Out-Null
        $env:PIP_CACHE_DIR = Join-Path $cache 'pip-cache'
        $env:TEMP = $env:TMP = $cache
        $env:PYTHONIOENCODING = 'utf-8'
        $venv = Join-Path $appRoot '.venv'
        $python = Find-Python -Candidates @((Join-Path $venv 'Scripts\python.exe'))
        if (-not $python) {
            $basePython = Get-SystemPython
            if (-not $basePython) {
                Install-Python -Cache $cache
                $basePython = Get-SystemPython
            }
            if (-not $basePython) { throw 'Python 3.11-3.13 (64-bit, with Tcl/Tk and pip) is required. See README.md.' }
            if (Test-Path -LiteralPath $venv) {
                # Preserve a moved/broken environment, never recursively delete it.
                $resolved = (Resolve-Path -LiteralPath $venv).Path
                if ($resolved -ne (Join-Path $appRoot '.venv')) { throw 'Unexpected virtual environment path.' }
                if ((Get-Item -LiteralPath $venv).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                    throw 'The virtual environment is a link. Repair its target manually; it was not moved.'
                }
                Move-Item -LiteralPath $resolved -Destination ($venv + '.before-' + [guid]::NewGuid().ToString('N'))
            }
            Write-Host 'Creating isolated .venv ...'
            Invoke-Python -Python $basePython -Arguments @('-m', 'venv', $venv)
            $python = Find-Python -Candidates @((Join-Path $venv 'Scripts\python.exe'))
            if (-not $python) { throw 'Virtual environment validation failed.' }
        }
        $check = @'
import importlib.metadata as m
from pathlib import Path
for line in Path('requirements.txt').read_text(encoding='utf-8-sig').splitlines():
    line = line.split('#', 1)[0].strip()
    if line:
        name, version = line.split('==')
        assert m.version(name) == version, name + ' version mismatch'
import app, quick_ui
from PySide6 import QtMultimedia
print('Python packages and Qt runtime imports: OK')
'@
        Write-Host 'Checking runtime dependencies ...'
        try {
            Invoke-Python -Python $python -Arguments @('-c', $check)
            Invoke-Python -Python $python -Arguments @('-m', 'pip', '--isolated', 'check')
        } catch {
            Write-Host 'Installing/repairing pinned dependencies from PyPI ...'
            Invoke-Python -Python $python -Arguments @('-m', 'ensurepip')
            Invoke-Python -Python $python -Arguments @(
                '-m', 'pip', '--isolated', '--disable-pip-version-check', 'install',
                '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
                '--force-reinstall', '--cache-dir', (Join-Path $cache 'pip-cache'),
                '--requirement', (Join-Path $appRoot 'requirements.txt')
            )
            Invoke-Python -Python $python -Arguments @('-c', $check)
            Invoke-Python -Python $python -Arguments @('-m', 'pip', '--isolated', 'check')
        }
        foreach ($tool in @('ffmpeg', 'ffprobe', 'yt-dlp')) {
            if (-not (Test-Path -LiteralPath (Join-Path $appRoot "tools\$tool.exe")) -and
                -not (Get-Command "$tool.exe" -ErrorAction SilentlyContinue)) {
                Write-Warning "$tool is missing. Keep the release tools folder or set its path in Settings. See README.md."
            }
        }
        if ($CheckOnly) {
            Write-Host 'Environment check passed. No recording, AI or upload services were started.'
        } else {
            Write-Host 'Starting StreamClip. Keep this console open while the application is running.'
            Invoke-Python -Python $python -Arguments @((Join-Path $appRoot 'app.py'))
        }
        return 0
    } catch {
        $message = "Startup failed: $($_.Exception.Message)"
        Write-Host $message -ForegroundColor Red
        if ($script:logPath) { $message | Out-File -LiteralPath $script:logPath -Append -Encoding utf8 }
        return 1
    } finally {
        if ($lock) { $lock.Dispose() }
    }
}

if ($MyInvocation.InvocationName -ne '.') { exit (Start-StreamClip) }
