<#
Usage:
    .\start-services.ps1

Options:
    -Force       Start services even if expected ports are already listening.
    -NoApi       Skip starting the backend API.
    -NoUi        Skip starting the Gradio UI.
    -NoFrontend  Skip starting the frontend dev server.
#>

param(
    [switch]$Force,
    [switch]$NoApi,
    [switch]$NoUi,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendRoot = Join-Path $projectRoot "frontend"

function Test-PortListening {
    param([int]$Port)

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Test-Url {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [int]$ExpectedPort
    )

    if ((Test-PortListening -Port $ExpectedPort) -and -not $Force) {
        Write-Host "[SKIP] $Name already appears to be running on port $ExpectedPort." -ForegroundColor Yellow
        return $null
    }

    $proc = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory -PassThru -WindowStyle Minimized
    Write-Host "[START] $Name launched (PID: $($proc.Id))." -ForegroundColor Green
    return $proc
}

Write-Host "Starting EDISON PRO services..." -ForegroundColor Cyan

if (-not $NoApi) {
    Start-ServiceProcess -Name "Backend API" -FilePath "python" -ArgumentList @("api.py") -WorkingDirectory $projectRoot -ExpectedPort 8000 | Out-Null
}

if (-not $NoUi) {
    Start-ServiceProcess -Name "Gradio UI" -FilePath "python" -ArgumentList @("edisonpro_ui.py") -WorkingDirectory $projectRoot -ExpectedPort 7861 | Out-Null
}

if (-not $NoFrontend) {
    Start-ServiceProcess -Name "Frontend" -FilePath "npm.cmd" -ArgumentList @("run", "dev") -WorkingDirectory $frontendRoot -ExpectedPort 5173 | Out-Null
}

Write-Host "Waiting for endpoints..." -ForegroundColor Cyan

$targets = @()

if (-not $NoFrontend) {
    $targets += @(
        @{ Name = "Frontend"; Urls = @("http://localhost:5173", "http://localhost:5174") }
    )
}

if (-not $NoApi) {
    $targets += @(
        @{ Name = "Backend API"; Urls = @("http://localhost:8000") }
    )
}

if (-not $NoUi) {
    $targets += @(
        @{ Name = "Gradio UI"; Urls = @("http://localhost:7861", "http://localhost:7860") }
    )
}

foreach ($target in $targets) {
    $isReady = $false
    $readyUrl = $null

    for ($i = 0; $i -lt 20; $i++) {
        foreach ($url in $target.Urls) {
            if (Test-Url -Url $url) {
                $isReady = $true
                $readyUrl = $url
                break
            }
        }

        if ($isReady) {
            break
        }

        Start-Sleep -Seconds 1
    }

    if ($isReady) {
        Write-Host "[OK] $($target.Name): $readyUrl" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] $($target.Name) not reachable yet." -ForegroundColor Yellow
    }
}

Write-Host "Done." -ForegroundColor Cyan