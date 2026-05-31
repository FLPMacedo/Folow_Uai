# Installer — FollowUai

Scripts PowerShell para instalar, iniciar e diagnosticar.

## Pré-requisitos manuais

Esses **não** são instalados pelo script (precisam admin + reboot):

1. **Docker Desktop** — https://www.docker.com/products/docker-desktop/
2. **Python 3.11+** — https://www.python.org/downloads/ (marque "Add to PATH")
3. **Node 18+** — https://nodejs.org/ (LTS)

Depois rode `check.ps1` para confirmar tudo presente.

## Comandos

### Instalar tudo (primeira vez)
```powershell
pwsh -ExecutionPolicy Bypass -File installer\install.ps1
```

Cria venv, pip install, init DB, npm install + build frontend, sobe Docker
Evolution+Mongo, cria atalho no Desktop.

### Só verificar pré-requisitos
```powershell
pwsh -ExecutionPolicy Bypass -File installer\install.ps1 -CheckOnly
```

### Dry-run (mostra o que faria sem executar)
```powershell
pwsh -ExecutionPolicy Bypass -File installer\install.ps1 -DryRun
```

### Pular partes
- `-SkipDocker`    não sobe docker compose
- `-SkipFrontend`  não roda npm install / build
- `-NoShortcut`    não cria atalho Desktop

### Iniciar diariamente (usado pelo atalho do Desktop)
```powershell
pwsh -ExecutionPolicy Bypass -File installer\launcher.ps1
```

Sobe Docker (se down), uvicorn backend, espera `/health`, lança painel
Electron.

Flags:
- `-NoElectron`    sobe backend + Docker mas não abre painel
- `-BackendOnly`   só backend (sem Docker, sem painel)
- `-DockerOnly`    só Docker

### Diagnóstico
```powershell
pwsh -ExecutionPolicy Bypass -File installer\check.ps1
```

Imprime status de Docker, Python, Node, venv, DB, backend, Evolution,
frontend. Não modifica nada.

## Desinstalar

Não tem script automático. Manual:

```powershell
cd Folow_Uai\docker
docker compose down -v          # remove containers + volumes
Remove-Item .venv -Recurse -Force
Remove-Item database\followuai.db
Remove-Item frontend\node_modules -Recurse -Force
Remove-Item frontend\dist, frontend\dist-electron -Recurse -Force
Remove-Item "$env:USERPROFILE\Desktop\FollowUai.lnk"
```

## Troubleshooting

| Sintoma | Causa | Fix |
|---|---|---|
| `pwsh` não reconhecido | Use PowerShell 7+ ou substitua por `powershell` | `winget install Microsoft.PowerShell` |
| ExecutionPolicy bloqueia | Política restrita | use flag `-ExecutionPolicy Bypass` |
| Docker compose falha | Docker Desktop parado | abra Docker Desktop, espere ícone verde |
| Backend não inicia | DB schema diferente | delete `database/followuai.db`, rode install novamente |
| Electron tela branca | Backend off | abra `check.ps1`, confirme `/health` |
| QR não aparece | Instância nunca criada | rode "Conectar" no painel Telefones |
