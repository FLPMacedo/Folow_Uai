# FollowUai — Código

Implementação MVP do FollowUai. Specs originais em `..\1Inicio.md`–`..\4 mensagens.md`.

## Stack
- **Backend:** Python 3.11+ · FastAPI · SQLModel · APScheduler · httpx · loguru
- **DB:** SQLite (`database/followuai.db`)
- **WhatsApp:** Evolution API + MongoDB 6 via Docker Desktop
- **Frontend:** (TBD) Electron ou React local

## Layout
```
Folow_Uai/
├── backend/         # FastAPI + scheduler + models + whatsapp client
├── database/        # schema.sql + followuai.db (gitignored)
├── docker/          # docker-compose.yml (Evolution + Mongo)
├── frontend/        # painel desktop
├── images/          # birthdays/ + events/ (anexos WhatsApp)
├── installer/       # scripts de instalação Windows
├── backups/         # backup .tar.gz/.zip
└── docs/            # docs de implementação (≠ specs raiz)
```

## Subir tudo (ordem)

**1. Evolution API + Mongo**
```powershell
cd docker
docker compose up -d
docker compose ps
```
Detalhe: [`docker/README.md`](docker/README.md).

**2. SQLite schema**
```powershell
cd ..\database
sqlite3 followuai.db ".read schema.sql"
```
Detalhe: [`database/README.md`](database/README.md).

**3. Backend (em desenvolvimento)**
```powershell
cd ..\backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

## MVP scope (doc 1 §9)
1. Cadastro manual de clientes
2. Import/export Excel
3. Módulo Comemorativo (aniversário + 100/500/1000 dias parceria)
4. Módulo Expiração (30/15/7 dias)
5. Evolution API rodando local
6. Envio de texto WhatsApp
7. Intervalo 5min entre envios
8. Backup manual SQLite
9. Relatórios básicos
10. Painel JS (Electron/React)

Pós-MVP: Pós-Venda, Evento, Sumiu, webhook receptivo, envio de imagem, multi-idioma.

## Status
- [x] Estrutura de pastas
- [x] docker-compose Evolution + Mongo
- [x] SQL schema (12 tabelas + 2 views + 4 seeds)
- [ ] SQLModel models Python
- [ ] WhatsApp client (Evolution API)
- [ ] APScheduler jobs
- [ ] Excel import/export
- [ ] Backup manual
- [ ] FastAPI endpoints CRUD
- [ ] Frontend painel
- [ ] Installer Windows

## Licença
MIT
