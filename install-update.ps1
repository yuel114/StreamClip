param([string]$Plan)
$ErrorActionPreference = 'Stop'

function Get-UpdateHash([string]$Path) {
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant() }
    finally { $stream.Dispose(); $sha.Dispose() }
}

function Install-StreamClipUpdate([string]$PlanPath) {
    $job = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $planFile = [IO.Path]::GetFullPath($PlanPath)
    $target = [IO.Path]::GetFullPath($job.target)
    $staged = [IO.Path]::GetFullPath($job.staged)
    $root = Split-Path -Parent $target
    $folder = Split-Path -Parent $planFile
    $cache = Join-Path $root 'data\updates'
    if ((Split-Path -Leaf $target) -cne 'StreamClip.exe' -or
        (Split-Path -Parent $folder) -ine $cache -or
        $staged -ine (Join-Path $folder 'StreamClip.exe') -or
        $job.sha256 -notmatch '^[a-f0-9]{64}$' -or [int]$job.pid -le 0) {
        throw 'Invalid update plan.'
    }
    $path = $folder
    while ($path.Length -ge $root.Length) {
        if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'Update paths cannot contain directory links.'
        }
        if ($path -ieq $root) { break }
        $path = Split-Path -Parent $path
    }
    $backup = Join-Path $folder 'StreamClip.before.exe'
    $resultPath = Join-Path $cache 'last-result.json'
    $replaced = $false
    try {
        if ((Get-UpdateHash $staged) -ine $job.sha256) {
            throw 'The downloaded executable changed. Download the update again.'
        }
        [IO.File]::WriteAllText((Join-Path $folder 'ready'), 'ready')
        $owner = Get-Process -Id $job.pid -ErrorAction SilentlyContinue
        if ($owner -and -not $owner.WaitForExit(300000)) {
            throw 'The application did not finish exiting. No files were replaced.'
        }
        # PyInstaller's outer process can retain the EXE after its child exits.
        $deadline = [DateTime]::UtcNow.AddSeconds(60)
        do {
            $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
                try { $_.Path -ieq $target } catch { $false }
            })
            if (-not $running) {
                try {
                    [IO.File]::Replace($staged, $target, $backup)
                    $replaced = $true
                    break
                } catch [IO.IOException] {
                    if ([DateTime]::UtcNow -ge $deadline) { throw }
                }
            }
            Start-Sleep -Milliseconds 500
        } while ([DateTime]::UtcNow -lt $deadline)
        if (-not $replaced) { throw 'The application is still in use. No files were replaced.' }
        if ((Get-UpdateHash $target) -ine $job.sha256) {
            throw 'The installed executable failed verification.'
        }
        @{success=$true; version=$job.version; backup=$backup} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
        Start-Process -FilePath $target -WorkingDirectory $root -WindowStyle Normal
    } catch {
        $message = $_.Exception.Message
        if ($replaced -and (Test-Path -LiteralPath $backup)) {
            [IO.File]::Replace($backup, $target, (Join-Path $folder 'StreamClip.failed.exe'))
        }
        @{success=$false; version=$job.version; error=$message} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
        # Reopen the retained version so its version page can show the failure.
        if (-not (Get-Process -Id $job.pid -ErrorAction SilentlyContinue)) {
            Start-Process -FilePath $target -WorkingDirectory $root -WindowStyle Normal
        }
        throw
    }
}

if ($Plan) { Install-StreamClipUpdate $Plan }
