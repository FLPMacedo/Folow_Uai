# =============================================================================
# FollowUai Installer (Windows)
#
# Uso:
#   pwsh -ExecutionPolicy Bypass -File install.ps1            # instalação completa
#   pwsh -ExecutionPolicy Bypass -File install.ps1 -CheckOnly # só verifica pré-reqs
#   pwsh -ExecutionPolicy Bypass -File install.ps1 -DryRun    # mostra o que faria
#
# Flags:
#   -CheckOnly     verifica Docker / Python / Node e sai
#   -DryRun        imprime comandos sem executar
#   -SkipDocker    pula docker compose up
#   -SkipFrontend  pula npm install + build
#   -NoShortcut    não cria atalho no Desktop
# =============================================================================
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$DryRun,
    [switch]$SkipDocker,
    [switch]$SkipFrontend,
    [switch]$NoShortcut
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$BackendDir  = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$DockerDir   = Join-Path $ProjectRoot "docker"
$VenvDir     = Join-Path $ProjectRoot ".venv"
$PythonExe   = Join-Path $VenvDir "Scripts\python.exe"
$LauncherPs  = Join-Path $PSScriptRoot "launcher.ps1"

# =============================================================================
# Log helpers
# =============================================================================
function Write-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)    { Write-Host "[OK]   $msg" -ForegroundColor Green }
function Write-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Err($msg)   { Write-Host "[ERR]  $msg" -ForegroundColor Red }
function Invoke-Step($desc, [scriptblock]$action) {
    Write-Info $desc
    if ($DryRun) { Write-Host "       (DRY RUN — não executado)" -ForegroundColor DarkGray; return }
    & $action
}

# =============================================================================
# Detectores de pré-requisitos
# =============================================================================
function Test-Docker {
    $cmd = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $cmd) { return @{ Found = $false; Version = $null; Running = $false } }
    $version = (& docker --version 2>$null) -replace '^Docker version (\S+),.*', '$1'
    $running = $false
    try {
        & docker info --format '{{.ServerVersion}}' 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { $running = $true }
    } catch {}
    return @{ Found = $true; Version = $version; Running = $running }
}

function Test-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { return @{ Found = $false; Version = $null; Ok = $false } }
    $v = (& python --version 2>&1)
    if ($v -match 'Python (\d+)\.(\d+)\.(\d+)') {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        $ok = ($major -eq 3 -and $minor -ge 11)
        return @{ Found = $true; Version = $v.Trim(); Ok = $ok }
    }
    return @{ Found = $true; Version = $v.Trim(); Ok = $false }
}

function Test-Node {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if (-not $cmd) { return @{ Found = $false; Version = $null; Ok = $false } }
    $v = (& node --version 2>&1).Trim()
    if ($v -match 'v(\d+)\.') {
        $major = [int]$Matches[1]
        return @{ Found = $true; Version = $v; Ok = ($major -ge 18) }
    }
    return @{ Found = $true; Version = $v; Ok = $false }
}

function Show-PrereqSummary($docker, $python, $node) {
    Write-Host ""
    Write-Host "================ Pré-requisitos ================" -ForegroundColor White
    if ($docker.Found) {
        $state = if ($docker.Running) { "rodando" } else { "instalado, parado" }
        Write-Ok "Docker $($docker.Version) ($state)"
    } else {
        Write-Warn "Docker NÃO encontrado. Baixe: https://www.docker.com/products/docker-desktop/"
    }
    if ($python.Ok) {
        Write-Ok "$($python.Version)"
    } elseif ($python.Found) {
        Write-Warn "$($python.Version) — precisa 3.11+. Baixe: https://www.python.org/downloads/"
    } else {
        Write-Warn "Python NÃO encontrado. Baixe: https://www.python.org/downloads/"
    }
    if ($node.Ok) {
        Write-Ok "Node $($node.Version)"
    } elseif ($node.Found) {
        Write-Warn "Node $($node.Version) — precisa 18+. Baixe: https://nodejs.org/"
    } else {
        Write-Warn "Node NÃO encontrado. Baixe: https://nodejs.org/"
    }
    Write-Host "================================================" -ForegroundColor White
    Write-Host ""
}

# =============================================================================
# Steps
# =============================================================================
function Install-BackendVenv {
    Invoke-Step "Criando venv em $VenvDir" {
        if (Test-Path $VenvDir) {
            Write-Warn "venv já existe — reutilizando"
        } else {
            python -m venv $VenvDir
            if ($LASTEXITCODE -ne 0) { throw "venv falhou" }
        }
    }
    Invoke-Step "Atualizando pip" {
        & $PythonExe -m pip install --upgrade pip --quiet
    }
    Invoke-Step "Instalando deps Python (requirements.txt)" {
        & $PythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt") --quiet
        if ($LASTEXITCODE -ne 0) { throw "pip install falhou" }
    }
}

function Initialize-Database {
    Invoke-Step "Aplicando schema.sql (cria followuai.db se ausente)" {
        Push-Location $ProjectRoot
        try {
            & $PythonExe -c "from backend.database import init_db; init_db(); print('DB ok')"
            if ($LASTEXITCODE -ne 0) { throw "init_db falhou" }
        } finally { Pop-Location }
    }
}

function Install-FrontendDeps {
    if ($SkipFrontend) { Write-Info "Frontend pulado (-SkipFrontend)"; return }
    Invoke-Step "npm install no frontend (pode demorar ~1min)" {
        Push-Location $FrontendDir
        try {
            npm install --no-fund --no-audit --silent
            if ($LASTEXITCODE -ne 0) { throw "npm install falhou" }
        } finally { Pop-Location }
    }
    Invoke-Step "Build frontend (tsc + vite)" {
        Push-Location $FrontendDir
        try {
            npm run build --silent
            if ($LASTEXITCODE -ne 0) { throw "npm run build falhou" }
        } finally { Pop-Location }
    }
}

function Start-EvolutionStack {
    if ($SkipDocker) { Write-Info "Docker pulado (-SkipDocker)"; return }
    Invoke-Step "Subindo Evolution API + Mongo via docker compose" {
        Push-Location $DockerDir
        try {
            docker compose up -d
            if ($LASTEXITCODE -ne 0) { throw "docker compose up falhou" }
        } finally { Pop-Location }
    }
}

function New-DesktopShortcut {
    if ($NoShortcut) { Write-Info "Atalho pulado (-NoShortcut)"; return }
    Invoke-Step "Criando atalho no Desktop" {
        $shellApp = New-Object -ComObject WScript.Shell
        $desktop = [Environment]::GetFolderPath("Desktop")
        $lnk = Join-Path $desktop "FollowUai.lnk"
        $shortcut = $shellApp.CreateShortcut($lnk)
        $shortcut.TargetPath = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
        if (-not $shortcut.TargetPath) {
            $shortcut.TargetPath = (Get-Command powershell).Source
        }
        $shortcut.Arguments    = "-ExecutionPolicy Bypass -File `"$LauncherPs`""
        $shortcut.WorkingDirectory = $ProjectRoot
        $shortcut.Description  = "FollowUai — follow-up WhatsApp"
        $shortcut.Save()
        Write-Ok "Atalho criado: $lnk"
    }
}

# =============================================================================
# Main
# =============================================================================
Write-Host "=========================================" -ForegroundColor White
Write-Host "  FollowUai Installer" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor White
if ($DryRun)    { Write-Warn "Modo DRY RUN — nada será executado" }
if ($CheckOnly) { Write-Warn "Modo CHECK-ONLY — apenas verifica pré-reqs" }
Write-Host "Projeto: $ProjectRoot"
Write-Host ""

$docker = Test-Docker
$python = Test-Python
$node   = Test-Node
Show-PrereqSummary $docker $python $node

if ($CheckOnly) {
    $allOk = $docker.Found -and $python.Ok -and ($SkipFrontend -or $node.Ok)
    if ($allOk) { Write-Ok "Pré-requisitos OK"; exit 0 }
    Write-Warn "Pré-requisitos incompletos"
    exit 1
}

if (-not $python.Ok) {
    Write-Err "Python 3.11+ obrigatório. Instale e re-execute."
    exit 2
}
if (-not $SkipFrontend -and -not $node.Ok) {
    Write-Err "Node 18+ obrigatório (ou use -SkipFrontend)."
    exit 3
}
if (-not $SkipDocker -and -not $docker.Found) {
    Write-Err "Docker Desktop obrigatório (ou use -SkipDocker)."
    exit 4
}

Install-BackendVenv
Initialize-Database
Install-FrontendDeps
Start-EvolutionStack
New-DesktopShortcut

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Ok "Instalação concluída"
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos:"
Write-Host "  1. Abra http://localhost:8080 e escaneie QR (Evolution)"
Write-Host "  2. Use o atalho FollowUai no Desktop para iniciar o painel"
Write-Host "     ou rode manualmente:  pwsh -File installer\launcher.ps1"
Write-Host ""
