param([string]$TestRoot = (Join-Path $env:TEMP ('streamclip-start-test-' + [guid]::NewGuid().ToString('N'))))
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'start.ps1') -CheckOnly

function Assert-True($Condition, $Message) {
    if (-not $Condition) { throw $Message }
}

$realPython = Get-SystemPython
Assert-True ($realPython) 'A working Python is required to run these offline checks.'
Assert-True ((Find-Python -Candidates @('Z:\nonexistent\python.exe', $realPython)) -eq $realPython) 'Interpreter detection failed.'
New-Item -ItemType Directory -Force -Path $TestRoot | Out-Null
$script:logPath = Join-Path $TestRoot 'native-error.log'
$failed = $false
try { Invoke-Python -Python $realPython -Arguments @('-c', 'raise SystemExit(7)') } catch { $failed = $_.Exception.Message -match 'code 7' }
Assert-True $failed 'Native process exit codes must propagate.'
$failed = $false
try { Invoke-Python -Python (Join-Path $TestRoot 'missing-python.exe') -Arguments @('-V') } catch { $failed = $true }
Assert-True $failed 'An unlaunchable process must not inherit an earlier successful exit code.'

# Only external setup/launch operations are replaced. Files, logs and locks
# remain real; this test never installs software or opens production data.
function Find-Python {
    param([string[]]$Candidates)
    if ($script:hasVenv) { return $realPython }
}
function Get-SystemPython { if ($script:hasBase) { return $realPython } }
function Install-Python {
    param([string]$Cache)
    $script:installed = $true
    if ($script:installFails) { throw 'offline installer failure' }
    $script:hasBase = $true
}
function Invoke-Python {
    param([string]$Python, [string[]]$Arguments)
    $script:calls.Add(($Arguments -join ' '))
    if ($Arguments -contains 'venv') { $script:hasVenv = $true }
    if ($Arguments -contains 'ensurepip') { $script:missingPip = $false }
    if ($Arguments -contains 'pip' -and $script:missingPip) { throw 'missing pip' }
    if ($Arguments -contains 'install') {
        if ($script:pipFails) { throw 'offline pip failure' }
        $script:missingDeps = $false
    }
    if ($Arguments -contains '-c' -and $script:missingDeps) { throw 'missing dependency' }
    if ($Arguments -contains (Join-Path $appRoot 'app.py') -and $script:appFails) { throw 'application startup failure' }
}

foreach ($scenario in @('ready', 'missing-deps', 'missing-pip', 'missing-python', 'installer-fails', 'pip-fails', 'broken-venv', 'app-fails', 'locked')) {
    $appRoot = Join-Path $TestRoot $scenario
    New-Item -ItemType Directory -Force -Path $appRoot | Out-Null
    $script:hasVenv = $scenario -notin @('missing-python', 'installer-fails', 'broken-venv')
    $script:hasBase = $scenario -notin @('missing-python', 'installer-fails')
    $script:installed = $false
    $script:installFails = $scenario -eq 'installer-fails'
    $script:pipFails = $scenario -eq 'pip-fails'
    $script:missingDeps = $scenario -in @('missing-deps', 'missing-python', 'pip-fails')
    $script:missingPip = $scenario -eq 'missing-pip'
    $script:appFails = $scenario -eq 'app-fails'
    $script:calls = [Collections.Generic.List[string]]::new()
    $CheckOnly = $scenario -ne 'app-fails'
    $held = $null
    if ($scenario -eq 'broken-venv') {
        $old = Join-Path $appRoot '.venv'
        New-Item -ItemType Directory -Force -Path $old | Out-Null
        'keep' | Out-File -LiteralPath (Join-Path $old 'marker.txt')
    }
    if ($scenario -eq 'locked') {
        New-Item -ItemType Directory -Force -Path (Join-Path $appRoot 'data\logs') | Out-Null
        $held = [IO.File]::Open((Join-Path $appRoot 'data\logs\source-launch.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    }
    try { $result = Start-StreamClip } finally { if ($held) { $held.Dispose() } }
    $expected = if ($scenario -in @('installer-fails', 'pip-fails', 'app-fails', 'locked')) { 1 } else { 0 }
    Assert-True ($result -eq $expected) "$scenario returned $result instead of $expected"
    if ($expected -eq 1) {
        Assert-True ((Get-Content -LiteralPath $script:logPath -Raw) -match 'Startup failed:') "$scenario did not preserve an error log"
    }
    if ($CheckOnly) { Assert-True (-not ($script:calls -match '\bapp\.py$')) 'CheckOnly launched production services.' }
    if ($scenario -eq 'ready') { Assert-True (-not $script:installed -and -not ($script:calls -match ' install ')) 'Healthy startup reinstalled software.' }
    if ($scenario -eq 'missing-python') { Assert-True ($script:installed -and ($script:calls -match '-m venv')) 'Python setup did not create a venv.' }
    if ($scenario -eq 'missing-deps') { Assert-True ([bool]($script:calls -match '--force-reinstall.*requirements.txt')) 'Missing dependencies were not repaired.' }
    if ($scenario -eq 'broken-venv') {
        Assert-True ([bool](Get-ChildItem -LiteralPath $appRoot -Filter '.venv.before-*' -Directory)) 'Broken venv was not preserved.'
    }
}

Write-Host 'Startup checks passed: detection, exit codes, setup, dependency repair, failure logs, environment backup and launch lock.'
