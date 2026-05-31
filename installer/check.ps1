# =============================================================================
# FollowUai — diagnóstico rápido
#
# Mostra estado de Docker, Python, Node, venv, backend, Evolution.
# Não modifica nada. Use pra diagnosticar problemas.
# =============================================================================
[CmdletBinding()] param()

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython  = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Probe($label, [scriptblock]$block) {
    try {
        $result = & $block
        if ($result) { Write-Host "[OK ] $label — $result" -ForegroundColor Green }
        else         { Write-Host "[OK ] $label" -ForegroundColor Green }
    } catch {
        Write-Host "[!!]  $label — $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============= FollowUai Diagnóstico =============" -ForegroundColor White
Write-Host "Projeto: $ProjectRoot"
Write-Host ""

Probe "Docker instalado" {
    $cmd = Get-Command docker -ErrorAction Stop
    (& docker --version) -replace 'Docker version ', ''
}

Probe "Docker rodando" {
    $out = & docker info --format '{{.ServerVersion}}' 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Docker daemon parado" }
    "server v$out"
}

Probe "Containers Evolution" {
    $names = (& docker ps --filter "name=evolution-api-followuai" --format '{{.Names}}') -split "`n" | Where-Object { $_ }
    if (-not $names) { throw "evolution-api-followuai não está rodando" }
    $names -join ", "
}

Probe "Python 3.11+" {
    $v = & python --version 2>&1
    if ($v -notmatch '3\.(1[1-9]|[2-9][0-9])') { throw "$v (precisa 3.11+)" }
    $v
}

Probe "Node 18+" {
    $v = & node --version 2>&1
    if ($v -notmatch '^v(1[89]|[2-9][0-9])') { throw "$v (precisa 18+)" }
    $v
}

Probe "venv backend" {
    if (-not (Test-Path $VenvPython)) { throw "ausente" }
    & $VenvPython --version
}

Probe "DB SQLite" {
    $db = Join-Path $ProjectRoot "database\followuai.db"
    if (-not (Test-Path $db)) { throw "$db não existe (rode install.ps1)" }
    $size = (Get-Item $db).Length
    "$([math]::Round($size/1024,1)) KB"
}

Probe "Backend /health" {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -UseBasicParsing
    "HTTP $($r.StatusCode)"
}

Probe "Evolution :8080" {
    $r = Invoke-WebRequest -Uri "http://localhost:8080" -TimeoutSec 2 -UseBasicParsing
    "HTTP $($r.StatusCode)"
}

Probe "Frontend node_modules" {
    $nm = Join-Path $ProjectRoot "frontend\node_modules"
    if (-not (Test-Path $nm)) { throw "ausente" }
    "ok"
}

Probe "Frontend build (dist/)" {
    $d = Join-Path $ProjectRoot "frontend\dist\index.html"
    if (-not (Test-Path $d)) { throw "ausente — rode npm run build" }
    "ok"
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor White
