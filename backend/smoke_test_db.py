"""Smoke test: schema + SQLModel ORM end-to-end.

Run from project root (Folow_Uai/):
    python -m backend.smoke_test_db

Steps:
  1. Wipe + init DB via schema.sql
  2. Verify all 12 tables + 2 views exist
  3. Verify 4 seed templates inserted
  4. Insert Cliente via ORM
  5. Insert Plano with FK to cliente
  6. Insert Tag + ClienteTag (M:N link)
  7. Insert TelefoneWhatsApp, Template, Campanha, Envio
  8. Insert Comemorativo, Evento, Resposta
  9. Query views: v_clientes_ativos, v_envios_por_modulo
 10. Assert FK enforcement (insert Plano with bad cliente_id must fail)
 11. Assert tag M:N navigates back
"""
from __future__ import annotations

import os
import sys
import traceback

# Force UTF-8 stdout (PowerShell defaults to cp1252; breaks on emoji/arrows).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Use ephemeral DB so smoke test is isolated and repeatable.
SMOKE_DB = Path(__file__).resolve().parent.parent / "database" / "followuai.smoke.db"
os.environ["DB_PATH"] = str(SMOKE_DB)

# Ensure project root on path so `backend` package imports cleanly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.database import engine, init_db  # noqa: E402
from backend.models import (  # noqa: E402
    Campanha,
    Cliente,
    ClienteTag,
    Comemorativo,
    Envio,
    Evento,
    Modulo,
    Plano,
    Resposta,
    StatusCampanha,
    StatusCliente,
    StatusEnvio,
    StatusTelefone,
    Tag,
    TelefoneWhatsApp,
    Template,
    TipoComemorativo,
    TipoEvento,
)


EXPECTED_TABLES = {
    "clientes",
    "telefones_whatsapp",
    "templates",
    "campanhas",
    "envios",
    "respostas",
    "eventos",
    "comemorativos",
    "planos",
    "tags",
    "cliente_tags",
    "backups",
}
EXPECTED_VIEWS = {"v_clientes_ativos", "v_envios_por_modulo"}
EXPECTED_SEED_TEMPLATES = 4

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print(f"DB path: {settings.DB_PATH}")
    if SMOKE_DB.exists():
        SMOKE_DB.unlink()
        print("Wiped previous smoke DB.")

    # ----- 1. init schema -----
    try:
        init_db()
        check("init_db() ran schema.sql", True)
    except Exception as exc:
        check("init_db() ran schema.sql", False, repr(exc))
        traceback.print_exc()
        return 1

    # ----- 2. tables + views exist -----
    with engine.connect() as conn:
        tables = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
        views = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='view'")
            )
        }
    missing_tables = EXPECTED_TABLES - tables
    missing_views = EXPECTED_VIEWS - views
    check(
        "All 12 tables present",
        not missing_tables,
        f"missing: {missing_tables}" if missing_tables else f"found {len(tables)}",
    )
    check(
        "Both views present",
        not missing_views,
        f"missing: {missing_views}" if missing_views else f"found {len(views)}",
    )

    # ----- 3. seed templates -----
    with Session(engine) as s:
        seeded = s.exec(select(Template)).all()
    check(
        f"Seeds: {EXPECTED_SEED_TEMPLATES} templates",
        len(seeded) == EXPECTED_SEED_TEMPLATES,
        f"got {len(seeded)}: {[t.nome for t in seeded]}",
    )

    # ----- 4–8. ORM inserts -----
    cliente_id: int | None = None
    with Session(engine) as s:
        c = Cliente(
            nome="Maria Silva",
            telefone="+5531999990001",
            email="maria@example.com",
            data_nascimento=date(1990, 5, 15),
            data_inicio_parceria=date.today() - timedelta(days=200),
            plano="Premium",
            grupo="VIP",
            status=StatusCliente.ativo,
        )
        s.add(c)
        s.commit()
        s.refresh(c)
        cliente_id = c.id
        check("Insert Cliente", c.id is not None, f"id={c.id}")

        # plano vinculado
        p = Plano(
            cliente_id=c.id,
            nome_plano="Premium Anual",
            data_inicio=date.today() - timedelta(days=200),
            data_fim=date.today() + timedelta(days=30),
            dias_restantes=30,
        )
        s.add(p)
        s.commit()
        s.refresh(p)
        check("Insert Plano FK→Cliente", p.id is not None, f"id={p.id}")

        # tag + M:N link
        t = Tag(nome="VIP", cor="#FFD700", descricao="Clientes prioritários")
        s.add(t)
        s.commit()
        s.refresh(t)
        s.add(ClienteTag(cliente_id=c.id, tag_id=t.id))
        s.commit()
        check("Insert Tag + ClienteTag (M:N)", True, f"tag_id={t.id}")

        # telefone WhatsApp + template + campanha + envio
        tel = TelefoneWhatsApp(
            numero="+5531988880001",
            instancia_evolution="followuai-instancia-1",
            nome_fantasia="Linha Principal",
            status=StatusTelefone.ativo,
        )
        s.add(tel)
        s.commit()
        s.refresh(tel)

        tmpl = Template(
            nome="Teste Smoke",
            modulo=Modulo.comemorativo,
            tipo_gatilho="aniversario",
            mensagem_texto="Feliz aniversário, {nome}!",
            variaveis='["nome"]',
        )
        s.add(tmpl)
        s.commit()
        s.refresh(tmpl)

        camp = Campanha(
            nome="Aniversariantes maio",
            modulo=Modulo.comemorativo,
            template_id=tmpl.id,
            telefone_whatsapp_id=tel.id,
            gatilho_data="aniversario",
            valor_gatilho=0,
            status=StatusCampanha.ativo,
        )
        s.add(camp)
        s.commit()
        s.refresh(camp)

        env = Envio(
            cliente_id=c.id,
            telefone_whatsapp_id=tel.id,
            campanha_id=camp.id,
            template_id=tmpl.id,
            modulo=Modulo.comemorativo,
            telefone_destino=c.telefone,
            mensagem_texto="Feliz aniversário, Maria Silva!",
            status=StatusEnvio.enviado,
            mensagem_evolution_id="evo-abc-123",
            enviado_em=datetime.now(timezone.utc),
        )
        s.add(env)
        s.commit()
        s.refresh(env)
        check(
            "Insert Telefone+Template+Campanha+Envio chain",
            all([tel.id, tmpl.id, camp.id, env.id]),
            f"ids={tel.id}/{tmpl.id}/{camp.id}/{env.id}",
        )

        # comemorativo + evento + resposta
        com = Comemorativo(
            cliente_id=c.id,
            tipo=TipoComemorativo.aniversario,
            data_gatilho=date(date.today().year, 5, 15),
            mensagem_enviada=True,
        )
        ev = Evento(
            cliente_id=c.id,
            nome_evento="Corrida 5K",
            tipo_evento=TipoEvento.evento,
            data_evento=date.today() + timedelta(days=10),
        )
        resp = Resposta(
            cliente_id=c.id,
            telefone_origem=c.telefone,
            telefone_destino=tel.numero,
            mensagem_texto="Obrigada!",
            tipo_mensagem="text",
        )
        s.add_all([com, ev, resp])
        s.commit()
        check("Insert Comemorativo + Evento + Resposta", True)

    # ----- 9. views -----
    with engine.connect() as conn:
        ativos = list(
            conn.execute(text("SELECT id, nome, dias_parceria FROM v_clientes_ativos"))
        )
        por_mod = list(
            conn.execute(
                text("SELECT modulo, total_envios, enviados FROM v_envios_por_modulo")
            )
        )
    check(
        "View v_clientes_ativos",
        len(ativos) == 1 and ativos[0][1] == "Maria Silva" and ativos[0][2] >= 199,
        f"rows={ativos}",
    )
    check(
        "View v_envios_por_modulo",
        len(por_mod) == 1 and por_mod[0][0] == "comemorativo" and por_mod[0][2] == 1,
        f"rows={por_mod}",
    )

    # ----- 10. FK enforcement -----
    fk_err = False
    try:
        with Session(engine) as s:
            bad = Plano(
                cliente_id=999_999,
                nome_plano="Fantasma",
                data_inicio=date.today(),
                data_fim=date.today() + timedelta(days=30),
            )
            s.add(bad)
            s.commit()
    except IntegrityError:
        fk_err = True
    except Exception:
        # sqlalchemy can wrap as OperationalError too; treat both as success
        fk_err = True
    check("FK enforced (bad cliente_id rejected)", fk_err)

    # ----- 11. M:N navigation -----
    with Session(engine) as s:
        c = s.get(Cliente, cliente_id)
        tag_names = [t.nome for t in c.tags] if c else []
        cli_back = s.exec(select(Tag).where(Tag.nome == "VIP")).first()
        back_names = [cl.nome for cl in cli_back.clientes] if cli_back else []
    check(
        "Tag M:N nav: cliente.tags",
        tag_names == ["VIP"],
        f"tags={tag_names}",
    )
    check(
        "Tag M:N nav: tag.clientes",
        back_names == ["Maria Silva"],
        f"clientes={back_names}",
    )

    # ----- summary -----
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}\n{passed}/{total} checks passed\n{'='*60}")
    if passed != total:
        print("\nFailures:")
        for label, ok, detail in results:
            if not ok:
                print(f"  - {label}: {detail}")
        return 1
    print("\nSmoke test OK. Removing smoke DB.")
    engine.dispose()
    SMOKE_DB.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
