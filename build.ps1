param(
    [string]$BuildRoot = 'E:\CodexBuildCache\StreamClip'
)

$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = [System.IO.Path]::GetFullPath($BuildRoot)
$distRoot = Join-Path $buildRoot 'dist'
$appName = 'StreamClip'
$outputName = $appName + '.exe'
$outputPath = Join-Path $appRoot $outputName
New-Item -ItemType Directory -Force -Path $buildRoot, $distRoot | Out-Null
$taskTemp = Join-Path $buildRoot 'tmp'
New-Item -ItemType Directory -Force -Path $taskTemp | Out-Null
$env:PYINSTALLER_CONFIG_DIR = Join-Path $buildRoot 'cache'
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:LIVECLIP_UI_TEST_OUTPUT = Join-Path $buildRoot 'ui-check'

# Build first. Never stop an active recorder or remove unrelated executables.

# 避免构建工具 PATH 中的 Poppler ICU 覆盖 Qt 使用的 Windows ICU。
$taskPython = (Get-Command python).Source
$taskPythonRoot = Split-Path -Parent $taskPython
$taskOriginalPath = $env:PATH
try {
$env:PATH = "$taskPythonRoot;$taskPythonRoot\Scripts;$env:SystemRoot\System32;$env:SystemRoot"
& $taskPython -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name $appName `
  --collect-data 'ttkbootstrap' `
  --hidden-import 'PySide6.QtMultimedia' `
  --icon (Join-Path $appRoot 'assets\ui\app-icon.ico') `
  --add-data ((Join-Path $appRoot 'assets\ui') + ';assets/ui') `
  --add-data ((Join-Path $appRoot 'recordings.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'WorkspacePages.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'GlossaryDialog.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'FormFields.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'ChoiceBox.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'ActionButton.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'ListEntry.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'PageTab.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'MediaFilters.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'AppDialog.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'RoundedField.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'RoundedImage.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'SegmentedBar.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'ToggleSwitch.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'SkinTransition.qml') + ';.') `
  --add-data ((Join-Path $appRoot 'THIRD_PARTY_NOTICES.md') + ';.') `
  --add-data ((Join-Path $appRoot 'LICENSE') + ';.') `
  --add-data ((Join-Path $appRoot 'licenses\hikami-go-LICENSE') + ';licenses') `
  --add-data ((Join-Path $appRoot 'licenses\qt-LGPL-3.0.txt') + ';licenses') `
  --add-data ((Join-Path $appRoot 'licenses\ffmpeg-LGPL-2.1.txt') + ';licenses') `
  --add-data ((Join-Path $appRoot 'licenses\lucide-LICENSE') + ';licenses') `
  --workpath (Join-Path $buildRoot 'build') `
  --specpath $buildRoot `
  --distpath $distRoot `
  (Join-Path $appRoot 'app.py')
} finally {
    $env:PATH = $taskOriginalPath
}

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$built = Join-Path $distRoot $outputName
# Verify shipped QML, not just the source tree, before replacing the user's EXE.
& $taskPython -c "import sys; from pathlib import Path; from PyInstaller.archive.readers import CArchiveReader; archive = CArchiveReader(sys.argv[1]); sources = list(Path(sys.argv[2]).glob('*.qml')); assert sources; [None if archive.extract(source.name) == source.read_bytes() else sys.exit('Packaged QML differs: ' + source.name) for source in sources]; print('Packaged QML matches source')" $built $appRoot
if ($LASTEXITCODE -ne 0) { throw 'Executable QML verification failed.' }
$check = Start-Process -FilePath $built -ArgumentList '--self-test' -WindowStyle Hidden -PassThru
if (-not $check.WaitForExit(120000)) { $check.Kill($true); throw 'Executable self-test timed out.' }
if ($check.ExitCode -ne 0) { throw "Executable self-test failed: $($check.ExitCode)" }
if (-not $env:LIVECLIP_TEST_FFMPEG) {
    $bundledFfmpeg = Join-Path $appRoot 'tools\ffmpeg.exe'
    if (Test-Path -LiteralPath $bundledFfmpeg) {
        $env:LIVECLIP_TEST_FFMPEG = $bundledFfmpeg
    } else {
        $env:LIVECLIP_TEST_FFMPEG = (Get-Command ffmpeg -ErrorAction Stop).Source
    }
}
$uiCheck = Start-Process -FilePath $built -ArgumentList '--ui-self-test' -WindowStyle Hidden -PassThru
if (-not $uiCheck.WaitForExit(180000)) { $uiCheck.Kill($true); throw 'Executable Qt UI self-test timed out.' }
if ($uiCheck.ExitCode -ne 0) { throw "Executable Qt UI self-test failed: $($uiCheck.ExitCode)" }
$running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    try { $_.Path -eq $outputPath } catch { $false }
}
if ($running) { throw 'The app is still running. The verified new executable remains in the build directory.' }
$staged = Join-Path $appRoot ($appName + '.update.exe')
Copy-Item -LiteralPath $built -Destination $staged -Force
if (Test-Path -LiteralPath $outputPath) {
    $backup = Join-Path $buildRoot ($appName + '.before-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.exe')
    [System.IO.File]::Replace($staged, $outputPath, $backup)
} else {
    Move-Item -LiteralPath $staged -Destination $outputPath
}
# SHCNE_ASSOCCHANGED invalidates cached icons; UPDATEITEM alone can retain the old EXE icon.
& $taskPython -c "import ctypes; notify = ctypes.windll.shell32.SHChangeNotify; notify.argtypes = [ctypes.c_long, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]; notify.restype = None; notify(0x08000000, 0x1000, None, None)"
if ($LASTEXITCODE -ne 0) { throw 'Executable updated, but Shell icon cache refresh failed.' }
Write-Output ('Updated: ' + $outputPath)
Get-FileHash -LiteralPath $outputPath -Algorithm SHA256
