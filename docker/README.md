# Docker — Evolution API (FollowUai)

## Pré-req
Docker Desktop rodando. Windows 10/11 + virtualização BIOS ativa.

## Subir
```powershell
cd Folow_Uai\docker
docker compose up -d
```

## Verificar
```powershell
docker compose ps
docker compose logs -f evolution-api
```

Evolution: http://localhost:8080 · Swagger: http://localhost:8080/docs

## Criar instância WhatsApp
```powershell
curl.exe -X POST http://localhost:8080/instance/create `
  -H "Content-Type: application/json" `
  -H "apikey: FOLLOWUAI_API_KEY_SEGURA_2026" `
  -d '{\"instanceName\":\"followuai-instancia-1\"}'
```

## Parar / limpar
```powershell
docker compose stop          # pausa
docker compose down          # remove containers, mantém dados
docker compose down -v       # APAGA tudo (cuidado)
```

## Backup volumes
```powershell
$d = Get-Date -Format yyyyMMdd
tar -czf "..\backups\evolution-$d.tar.gz" evolution-data mongodb-data
```

## Notas
- `AUTHENTICATION_API_KEY` em `evolution.env` — trocar antes de produção (`openssl rand -hex 32`).
- Mongo bind localhost (`127.0.0.1:27017`) — não exposto pra rede.
- Volumes: `./evolution-data` (app), `./mongodb-data` (db). Adicionar ao `.gitignore`.
