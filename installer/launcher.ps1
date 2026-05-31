# =============================================================================
# FollowUai Launcher (Windows)
#
# Sobe Docker (se parado), inicia backend uvicorn em background, espera
# /health, lança painel Electron. Usado como target do atalho do Desktop.
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File launcher.ps1
#
# Flags:
#   -NoElectron        sobe backend + Docker mas não abre painel
#   -BackendOnly       sobe só uvicorn (sem Docker, sem painel)
#   -DockerOnly        sobe só Docker (sem backend, sem painel)
# =============================================================================
[CmdletBinding()]
param(
    [switch]$NoElectron,
    [switch]$BackendOnly,
    [switch]$DockerOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DockerDir   = Join-Path $ProjectRoot "docker"
$VenvPython  = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$HealthUrl   = "http://localhost:8000/health"

function Write-Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn($m) { Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err($m)  { Write-Host "[ERR]  $m" -ForegroundColor Red }

function Test-PortInUse($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $conn
}

function Wait-Health($url, $timeoutSec = 30) {
    $elapsed = 0
    while ($elapsed -lt $timeoutSec) {
        try {
            $r = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
            if ($r.StatusCode -eq 200) { return $true }
        } catch {
            Start-Sleep -Seconds 1
            $elapsed++
        }
    }
    return $false
}

# =============================================================================
# 1. Docker stack
# =============================================================================
if (-not $BackendOnly) {
    Write-Info "Verificando Docker..."
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        Write-Warn "Docker não instalado — pulando Evolution stack"
    } else {
        Push-Location $DockerDir
        try {
            $up = (& docker compose ps --status running --format json 2>$null) -ne $null
            if (-not $up) {
                Write-Info "Subindo Evolution + Mongo (docker compose up -d)"
                docker compose up -d
                if ($LASTEXITCODE -ne 0) { throw "docker compose falhou" }
                Start-Sleep -Seconds 3
            } else {
                Write-Ok "Stack Docker já rodando"
            }
        } finally { Pop-Location }
    }
}

if ($DockerOnly) {
    Write-Ok "Docker iniciado. Saindo."
    exit 0
}

# =============================================================================
# 2. Backend uvicorn
# =============================================================================
if (-not (Test-Path $VenvPython)) {
    Write-Err "venv ausente em $VenvPython. Rode installer\install.ps1 primeiro."
    exit 1
}

if (Test-PortInUse 8000) {
    Write-Ok "Backend já rodando em :8000"
} else {
    Write-Info "Iniciando uvicorn em background (porta 8000)"
    $args = @(
        "-NoProfile", "-WindowStyle", "Hidden",
        "-Command",
        "& '$VenvPython' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
    )
    Start-Process -FilePath "pwsh" -ArgumentList $args `
        -WorkingDirectory $ProjectRoot -WindowStyle Hidden | Out-Null
}

Write-Info "Aguardando /health responder..."
if (-not (Wait-Health $HealthUrl 30)) {
    Write-Err "Backend não respondeu em 30s. Cheque o log com 'docker logs' ou rode uvicorn no terminal."
    exit 2
}
Write-Ok "Backend ok"

if ($BackendOnly) {
    Write-Ok "Backend rodando em http://localhost:8000 — Swagger /docs"
    exit 0
}

# =============================================================================
# 3. Electron app
# =============================================================================
if ($NoElectron) {
    Write-Ok "NoElectron — backend + docker prontos. Acesse http://localhost:8000/docs"
    exit 0
}

$electronBin = Join-Path $FrontendDir "node_modules\.bin\electron.cmd"
if (-not (Test-Path $electronBin)) {
    Write-Err "Electron não instalado. Rode 'npm install' em $FrontendDir."
    exit 3
}

$distMain = Join-Path $FrontendDir "dist-electron\main.js"
if (-not (Test-Path $distMain)) {
    Write-Warn "Build do frontend ausente — rodando 'npm run build'..."
    Push-Location $FrontendDir
    try {
        npm run build --silent
        if ($LASTEXITCODE -ne 0) { throw "build falhou" }
    } finally { Pop-Location }
}

Write-Info "Lançando painel Electron"
Push-Location $FrontendDir
try {
    & $electronBin .
} finally { Pop-Location }
