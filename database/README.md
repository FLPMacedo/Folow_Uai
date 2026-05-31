# Database — SQLite

Arquivo: `followuai.db` (criado na primeira execução; gitignored).

## Aplicar schema do zero
```powershell
sqlite3 followuai.db ".read schema.sql"
```

ou via Python:
```powershell
python -c "import sqlite3; sqlite3.connect('followuai.db').executescript(open('schema.sql', encoding='utf-8').read())"
```

## Verificar tabelas
```powershell
sqlite3 followuai.db ".tables"
sqlite3 followuai.db "SELECT * FROM v_envios_por_modulo;"
```

## Migrations
Sem framework de migration na v0.1 — `schema.sql` é idempotente (`CREATE TABLE IF NOT EXISTS`, `INSERT … WHERE NOT EXISTS`). Pós-MVP avaliar Alembic.

## Source of truth
Spec original: [`../../3 modelo.banco.md`](../../3%20modelo.banco.md). Diffs aplicados aqui:
- `atualizado_e` → `atualizado_em`
- `Campanha_id` → `campanha_id`
- `mensagens_texto` → `mensagem_texto`
- `imagem路径` → `imagem_path`
- `véspera_mensagem_enviada` → `vespera_mensagem_enviada` (sem acento, identificador SQL)
- view `dice_clientes_ativos` → `v_clientes_ativos`
- seeds idempotentes (`WHERE NOT EXISTS`)
- mongo port bind `127.0.0.1` (não expõe rede)
