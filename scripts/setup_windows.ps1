# Run from the extracted project folder. No Docker or Git required.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). Fix the error above and run setup again." }
}
function Refresh-Path {
    $env:PATH = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:PATH
}
function Find-Python {
    $candidates = @(
        (Join-Path $projectRoot '.venv\Scripts\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:ProgramFiles 'Python311\python.exe')
    )
    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -notlike '*WindowsApps*') { $candidates += $command.Source }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -c 'import sys, tkinter, venv; assert (3,11) <= sys.version_info[:2] < (3,14)' 2>$null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        }
    }
}
function Find-Node {
    $command = Get-Command node.exe -ErrorAction SilentlyContinue
    $candidates = @()
    if ($command) { $candidates += $command.Source }
    $candidates += Join-Path $env:ProgramFiles 'nodejs\node.exe'
    $candidates += @(Get-ChildItem -Path (Join-Path $projectRoot '.tools\node*\node.exe') -ErrorAction SilentlyContinue | ForEach-Object FullName)
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $nodeVersion = & $candidate -p 'process.versions.node' 2>$null
            if ($LASTEXITCODE -eq 0 -and ([version]$nodeVersion).Major -ge 22) { return $candidate }
        }
    }
}
function Install-Prerequisite([string]$Package) {
    if (!(Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'Windows App Installer (winget) is missing. Install/update App Installer from Microsoft Store, then rerun Setup TOSS POS.cmd.'
    }
    Invoke-Checked 'winget.exe' @('install', '--id', $Package, '--exact', '--source', 'winget', '--accept-source-agreements', '--accept-package-agreements')
    Refresh-Path
}
try {
    Write-Host 'TOSS POS - one-time Windows setup' -ForegroundColor Magenta
    Write-Host 'Keep this extracted folder in a permanent location. Internet is required for setup.'
    Write-Host 'Missing Python / Node.js will be installed through Windows Package Manager.'
    Write-Host 'Close Run TOSS POS before running setup. Existing passwords and sales are preserved.'
    $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, 8080)
    try { $listener.Start() } catch { throw 'Port 8080 is busy. Stop the POS launcher/server first, then rerun setup.' } finally { $listener.Stop() }
    $pythonExe = Find-Python
    if (!$pythonExe) { Install-Prerequisite 'Python.Python.3.11'; $pythonExe = Find-Python }
    if (!$pythonExe) { throw 'Python was installed but cannot be found. Restart Windows and run setup again.' }
    $nodeExe = Find-Node
    if (!$nodeExe) { Install-Prerequisite 'OpenJS.NodeJS.LTS'; $nodeExe = Find-Node }
    if (!$nodeExe) { throw 'Node.js was installed but cannot be found. Restart Windows and run setup again.' }
    $env:PATH = (Split-Path $nodeExe) + ';' + $env:PATH
    $venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (!(Test-Path -LiteralPath $venvPython)) {
        Invoke-Checked $pythonExe @('-m', 'venv', (Join-Path $projectRoot '.venv'))
    }
    Write-Host 'Installing application dependencies...'
    Invoke-Checked $venvPython @('-m', 'pip', 'install', '-r', (Join-Path $projectRoot 'backend\requirements.lock.txt'))
    Push-Location (Join-Path $projectRoot 'frontend')
    try {
        $npm = Join-Path (Split-Path $nodeExe) 'npm.cmd'
        Invoke-Checked $npm @('ci')
        Invoke-Checked $npm @('run', 'build')
    } finally { Pop-Location }
    Write-Host 'Preparing database and owner login...'
    Invoke-Checked $venvPython @((Join-Path $PSScriptRoot 'initialize_local.py'))
    $desktopPath = [Environment]::GetFolderPath('Desktop')
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktopPath 'Run TOSS POS.lnk'))
    $shortcut.TargetPath = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
    $shortcut.Arguments = '"' + (Join-Path $PSScriptRoot 'run_local.py') + '"'
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = 'Start TOSS POS and show the phone / iPad address'
    $shortcut.Save()
    Write-Host 'Setup complete! Double-click Run TOSS POS on your desktop.' -ForegroundColor Green
    Write-Host 'Allow Python on PRIVATE networks if Windows Firewall asks. Keep the laptop awake.'
    Write-Host 'Connect the iPad to the same Wi-Fi and open the address shown in the launcher.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
