<#
Usage:
    .\stop-services.ps1

Options:
    -NoApi       Skip stopping the backend API.
    -NoUi        Skip stopping the Gradio UI.
    -NoFrontend  Skip stopping the frontend dev server.

Notes:
    - Stops services by command-line signature first, then by listening port.
    - Default ports: API 8000, UI 7861, Frontend 5173.
#>

param(
    [switch]$NoApi,
    [switch]$NoUi,
    [switch]$NoFrontend,
    [int]$ApiPort = 8000,
    [int]$UiPort = 7861,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

function Get-ProcessByCommandLine {
    param(
        [string[]]$Includes
    )

    $results = @()
    $all = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    if (-not $all) { return @() }

    foreach ($proc in $all) {
        $cmd = $proc.CommandLine
        if (-not $cmd) { continue }

        $matched = $true
        foreach ($needle in $Includes) {
            if ($cmd -notmatch [Regex]::Escape($needle)) {
                $matched = $false
                break
            }
        }

        if ($matched) {
            $results += $proc
        }
    }

    return $results
}

function Stop-ByPid {
    param(
        [int[]]$Pids,
        [string]$Name
    )

    $unique = $Pids | Where-Object { $_ -and $_ -gt 0 } | Select-Object -Unique
    if (-not $unique -or $unique.Count -eq 0) {
        Write-Host "[SKIP] ${Name}: no matching process found." -ForegroundColor Yellow
        return
    }

    foreach ($procId in $unique) {
        try {
            $proc = Get-Process -Id $procId -ErrorAction Stop
            Stop-Process -Id $procId -Force
            Write-Host "[STOP] ${Name}: PID $procId ($($proc.ProcessName))" -ForegroundColor Green
        }
        catch {
            Write-Host "[WARN] ${Name}: failed to stop PID $procId ($($_.Exception.Message))" -ForegroundColor Yellow
        }
    }
}

function Get-PidsByListeningPort {
    param([int]$Port)

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) { return @() }
    return ($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
}

Write-Host "Stopping EDISON PRO services..." -ForegroundColor Cyan

if (-not $NoApi) {
    $apiByCmd = Get-ProcessByCommandLine -Includes @("python", "api.py") | Select-Object -ExpandProperty ProcessId
    $apiByPort = Get-PidsByListeningPort -Port $ApiPort
    Stop-ByPid -Pids ($apiByCmd + $apiByPort) -Name "Backend API"
}

if (-not $NoUi) {
    $uiByCmd = Get-ProcessByCommandLine -Includes @("python", "edisonpro_ui.py") | Select-Object -ExpandProperty ProcessId
    $uiByPort = Get-PidsByListeningPort -Port $UiPort
    Stop-ByPid -Pids ($uiByCmd + $uiByPort) -Name "Gradio UI"
}

if (-not $NoFrontend) {
    # Match both npm and node/vite command lines that are typical for frontend dev server.
    $frontendByCmd = @()
    $frontendByCmd += (Get-ProcessByCommandLine -Includes @("npm", "run", "dev") | Select-Object -ExpandProperty ProcessId)
    $frontendByCmd += (Get-ProcessByCommandLine -Includes @("node", "vite") | Select-Object -ExpandProperty ProcessId)

    $frontendByPort = Get-PidsByListeningPort -Port $FrontendPort
    Stop-ByPid -Pids ($frontendByCmd + $frontendByPort) -Name "Frontend"
}

Start-Sleep -Milliseconds 500

$remaining = @()
if (-not $NoApi) { $remaining += @{ Name = "Backend API"; Port = $ApiPort } }
if (-not $NoUi) { $remaining += @{ Name = "Gradio UI"; Port = $UiPort } }
if (-not $NoFrontend) { $remaining += @{ Name = "Frontend"; Port = $FrontendPort } }

foreach ($svc in $remaining) {
    $still = Get-NetTCPConnection -LocalPort $svc.Port -State Listen -ErrorAction SilentlyContinue
    if ($still) {
        $pids = ($still | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
        Write-Host "[WARN] $($svc.Name) still listening on port $($svc.Port) (PID: $pids)" -ForegroundColor Yellow
    }
    else {
        Write-Host "[OK] $($svc.Name) stopped (port $($svc.Port) not listening)." -ForegroundColor Green
    }
}

Write-Host "Done." -ForegroundColor Cyan
