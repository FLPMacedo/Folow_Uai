"""Smoke test integrado: jobs + sender + rotação + intervalo anti-banimento.

Run:
    python -m backend.smoke_test_scheduler

Cenários:
  A. Templates render: variáveis substituem, missing vira literal, derive_cliente_vars
  B. Sender escolhe telefone com `ultimo_envio` mais antigo (NULL primeiro)
  C. Sender respeita intervalo 5min (cooldown): segundo envio mesmo número → pendente
  D. Sender alterna entre 2 números (round-robin via `ultimo_envio`)
  E. Sender registra erro do gateway → status=falha + erro preenchido
  F. dispatch_comemorativo: aniversariante hoje → 1 envio + flag marcada
  G. dispatch_comemorativo: re-rodar não duplica (mensagem_enviada já 1)
  H. dispatch_comemorativo: marco 100 dias parceria dispara
  I. dispatch_expiracao: plano com 30 dias → 1 envio + flag plano marcada
  J. dispatch_expiracao: cliente inativo é ignorado
  K. dispatch_expiracao: re-rodar não duplica
"""
from __future__ import annotations

import os
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SMOKE_DB = (Path(__file__).resolve().parent.parent / "database"
            / "followuai.smoke-sched.db")
os.environ["DB_PATH"] = str(SMOKE_DB)

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlmodel import Session, select  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.database import engine, init_db  # noqa: E402
from backend.jobs import (  # noqa: E402
    dispatch_comemorativo,
    dispatch_evento,
    dispatch_expiracao,
    dispatch_pos_venda,
)
from backend.models import (  # noqa: E402
    Cliente,
    Envio,
    Evento,
    Modulo,
    Plano,
    StatusCliente,
    StatusEnvio,
    StatusTelefone,
    TelefoneWhatsApp,
    TipoEvento,
)
from backend.sender import Sender  # noqa: E402
from backend.templates import (  # noqa: E402
    derive_cliente_vars,
    render,
    required_variables,
)


results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


# ============================================================================
# Fake gateway — comportamento programável
# ============================================================================
class FakeGateway:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.fail_next: int = 0
        self.next_id: int = 1

    def send_text(self, instance, number, text, *, delay_ms=0, link_preview=False):
        if self.fail_next > 0:
            self.fail_next -= 1
            raise RuntimeError("upstream HTTP 500")
        msg_id = f"MOCK_{self.next_id}"
        self.next_id += 1
        self.sent.append({
            "instance": instance, "number": number, "text": text, "id": msg_id,
        })
        return {"key": {"id": msg_id}}

    def send_media(self, instance, number, media_path, *,
                   caption="", mediatype=None, delay_ms=0):
        return self.send_text(instance, number, caption)


# ============================================================================
# Setup / teardown
# ============================================================================
def fresh_db() -> None:
    if SMOKE_DB.exists():
        engine.dispose()
        SMOKE_DB.unlink()
    init_db()


def seed_telefones(session: Session, n: int = 2) -> list[TelefoneWhatsApp]:
    tels: list[TelefoneWhatsApp] = []
    for i in range(1, n + 1):
        t = TelefoneWhatsApp(
            numero=f"+553188888000{i}",
            instancia_evolution=f"smoke-inst-{i}",
            status=StatusTelefone.ativo,
        )
        session.add(t)
        tels.append(t)
    session.commit()
    for t in tels:
        session.refresh(t)
    return tels


# ============================================================================
# Tests
# ============================================================================
def test_templates() -> None:
    s = "Oi {nome}, parceria há {tempo_parceria}!"
    out = render(s, {"nome": "Ana", "tempo_parceria": "6 meses"})
    check("render substitui variáveis",
          out == "Oi Ana, parceria há 6 meses!", f"got={out!r}")

    out = render("Falta {x}", {})
    check("render: missing vira literal", out == "Falta {x}", f"got={out!r}")

    vs = required_variables("oi {a}, voce {b} {a}")
    check("required_variables extrai únicos", vs == {"a", "b"}, f"got={vs}")

    cliente = Cliente(
        nome="Ana", telefone="+5531999990001",
        data_inicio_parceria=date.today() - timedelta(days=200),
    )
    v = derive_cliente_vars(cliente, today=date.today())
    check("derive: nome", v["nome"] == "Ana")
    check("derive: dias_parceria", v["dias_parceria"] == 200, f"got={v['dias_parceria']}")
    check("derive: tempo_parceria '6 meses'",
          v["tempo_parceria"] == "6 meses", f"got={v['tempo_parceria']!r}")


def test_sender_rotation_and_cooldown() -> None:
    fresh_db()
    fake = FakeGateway()
    sender = Sender(fake, intervalo_min=5)

    with Session(engine) as s:
        tels = seed_telefones(s, n=2)
        # cliente isca
        c = Cliente(
            nome="Maria",
            telefone="+5531999990099",
            data_inicio_parceria=date.today() - timedelta(days=10),
        )
        s.add(c); s.commit(); s.refresh(c)

        # base time
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)

        # 1º envio: ambos com ultimo_envio=NULL → ordenação estável por total_envios,
        # depois id. Usa tel[0].
        e1 = sender.send_text(s, c, "msg 1", modulo=Modulo.comemorativo, now=t0)
        check("envio 1 enviado", e1.status == StatusEnvio.enviado,
              f"status={e1.status}")
        check("envio 1 usou tel1", e1.telefone_whatsapp_id == tels[0].id,
              f"used={e1.telefone_whatsapp_id}")

        # 2º envio 1 min depois: tel[0] em cooldown → escolhe tel[1]
        e2 = sender.send_text(s, c, "msg 2", modulo=Modulo.comemorativo,
                              now=t0 + timedelta(minutes=1))
        check("envio 2 alterna pra tel2 (rotação)",
              e2.telefone_whatsapp_id == tels[1].id,
              f"used={e2.telefone_whatsapp_id}")

        # 3º envio ainda 2 min depois: ambos em cooldown → pendente
        e3 = sender.send_text(s, c, "msg 3", modulo=Modulo.comemorativo,
                              now=t0 + timedelta(minutes=2))
        check("envio 3 pendente (todos em cooldown)",
              e3.status == StatusEnvio.pendente and e3.telefone_whatsapp_id is None,
              f"status={e3.status} tel={e3.telefone_whatsapp_id}")

        # 4º envio 6 min depois: tel[0] (mais antigo) liberou → usa tel[0] de novo
        e4 = sender.send_text(s, c, "msg 4", modulo=Modulo.comemorativo,
                              now=t0 + timedelta(minutes=6))
        check("envio 4 volta pra tel1 (ultimo_envio mais antigo)",
              e4.status == StatusEnvio.enviado
              and e4.telefone_whatsapp_id == tels[0].id,
              f"used={e4.telefone_whatsapp_id} status={e4.status}")

        # total_envios bate
        s.refresh(tels[0]); s.refresh(tels[1])
        check("tel1.total_envios = 2", tels[0].total_envios == 2,
              f"got={tels[0].total_envios}")
        check("tel2.total_envios = 1", tels[1].total_envios == 1,
              f"got={tels[1].total_envios}")

        # fake registrou
        check("FakeGateway capturou 3 envios", len(fake.sent) == 3,
              f"got={len(fake.sent)}")


def test_sender_gateway_failure() -> None:
    fresh_db()
    fake = FakeGateway()
    fake.fail_next = 1
    sender = Sender(fake, intervalo_min=5)

    with Session(engine) as s:
        seed_telefones(s, n=1)
        c = Cliente(
            nome="Erro",
            telefone="+5531999991111",
            data_inicio_parceria=date.today() - timedelta(days=5),
        )
        s.add(c); s.commit(); s.refresh(c)

        e = sender.send_text(s, c, "msg", modulo=Modulo.comemorativo)
        check("Gateway falha → envio.status=falha",
              e.status == StatusEnvio.falha, f"status={e.status}")
        check("Envio.erro preenchido",
              e.erro and "RuntimeError" in e.erro and "500" in e.erro,
              f"erro={e.erro!r}")


def test_dispatch_comemorativo() -> None:
    fresh_db()
    fake = FakeGateway()
    sender = Sender(fake, intervalo_min=5)
    today = date(2026, 5, 31)

    with Session(engine) as s:
        seed_telefones(s, n=2)  # 2 números → 2 envios no mesmo tick sem cooldown
        # aniversariante hoje
        s.add(Cliente(
            nome="Aniver",
            telefone="+5531999990001",
            data_nascimento=date(1990, 5, 31),
            data_inicio_parceria=today - timedelta(days=200),
        ))
        # marco 100 dias parceria
        s.add(Cliente(
            nome="Cem",
            telefone="+5531999990002",
            data_inicio_parceria=today - timedelta(days=100),
        ))
        # ninguém:
        s.add(Cliente(
            nome="Neutro",
            telefone="+5531999990003",
            data_nascimento=date(1990, 1, 1),
            data_inicio_parceria=today - timedelta(days=42),
        ))
        # inativo aniversariante (ignorado)
        s.add(Cliente(
            nome="Inativo",
            telefone="+5531999990004",
            data_nascimento=date(1985, 5, 31),
            data_inicio_parceria=today - timedelta(days=300),
            status=StatusCliente.inativo,
        ))
        s.commit()

        stats = dispatch_comemorativo(s, sender, today=today)
        check("Comemorativo: 2 enviados (aniver + 100 dias)",
              stats["enviados"] == 2 and stats["pendentes"] == 0,
              f"stats={stats}")

        envios_iniciais = s.exec(
            select(Envio).where(Envio.modulo == Modulo.comemorativo)
        ).all()
        clientes_alvo = {
            s.get(Cliente, e.cliente_id).nome for e in envios_iniciais
        }
        check("Comemorativo: cliente inativo NÃO enviado",
              "Inativo" not in clientes_alvo,
              f"alvos={clientes_alvo}")
        check("Comemorativo: cliente neutro NÃO enviado",
              "Neutro" not in clientes_alvo,
              f"alvos={clientes_alvo}")

        # rodar de novo: tudo já marcado → 0 envios
        stats2 = dispatch_comemorativo(s, sender, today=today)
        check("Comemorativo idempotente (re-run = 0 envios)",
              stats2["enviados"] == 0
              and stats2["ignorados"] >= 1,
              f"stats={stats2}")

        # mensagens contém nome + tempo_parceria
        envios = s.exec(
            select(Envio).where(Envio.modulo == Modulo.comemorativo)
        ).all()
        textos = [e.mensagem_texto for e in envios]
        check("Comemorativo: render incluiu nome",
              any("Aniver" in t for t in textos),
              f"textos={textos}")


def test_dispatch_expiracao() -> None:
    fresh_db()
    fake = FakeGateway()
    sender = Sender(fake, intervalo_min=5)
    today = date(2026, 5, 31)

    with Session(engine) as s:
        seed_telefones(s, n=1)
        c1 = Cliente(
            nome="Plano30",
            telefone="+5531999990010",
            data_inicio_parceria=today - timedelta(days=300),
        )
        c2 = Cliente(  # inativo
            nome="PlanoInativo",
            telefone="+5531999990011",
            data_inicio_parceria=today - timedelta(days=300),
            status=StatusCliente.inativo,
        )
        c3 = Cliente(  # 50 dias: não bate gatilho
            nome="PlanoNeutro",
            telefone="+5531999990012",
            data_inicio_parceria=today - timedelta(days=100),
        )
        s.add_all([c1, c2, c3])
        s.commit()
        for c in (c1, c2, c3):
            s.refresh(c)

        s.add_all([
            Plano(cliente_id=c1.id, nome_plano="Premium",
                  data_inicio=today - timedelta(days=335),
                  data_fim=today + timedelta(days=30)),
            Plano(cliente_id=c2.id, nome_plano="Premium",
                  data_inicio=today - timedelta(days=335),
                  data_fim=today + timedelta(days=30)),
            Plano(cliente_id=c3.id, nome_plano="Lite",
                  data_inicio=today - timedelta(days=50),
                  data_fim=today + timedelta(days=50)),
        ])
        s.commit()

        stats = dispatch_expiracao(s, sender, today=today)
        check("Expiração: 1 enviado (apenas c1 ativo 30 dias)",
              stats["enviados"] == 1, f"stats={stats}")

        # flag marcada
        p = s.exec(select(Plano).where(Plano.cliente_id == c1.id)).first()
        check("Expiração: flag 30 dias marcada",
              p.mensagem_30_dias_enviada is True,
              f"flag={p.mensagem_30_dias_enviada}")

        # re-run não duplica
        stats2 = dispatch_expiracao(s, sender, today=today)
        check("Expiração idempotente",
              stats2["enviados"] == 0 and stats2["ignorados"] >= 1,
              f"stats={stats2}")

        # mensagem contém dias_restantes
        envios = s.exec(
            select(Envio).where(Envio.modulo == Modulo.expiracao)
        ).all()
        check("Expiração: msg menciona '30 dias'",
              any("30 dias" in e.mensagem_texto for e in envios),
              f"textos={[e.mensagem_texto for e in envios]}")


def test_dispatch_pos_venda() -> None:
    fresh_db()
    fake = FakeGateway()
    # intervalo_min=0 → sem cooldown, vários envios mesmo tick
    sender = Sender(fake, intervalo_min=0)
    today = date(2026, 5, 31)

    with Session(engine) as s:
        seed_telefones(s, n=1)
        cA = Cliente(nome="ComprouHoje",  telefone="+5531999990020",
                     data_inicio_parceria=today - timedelta(days=30))
        cB = Cliente(nome="Comprou2Dias", telefone="+5531999990021",
                     data_inicio_parceria=today - timedelta(days=30))
        cC = Cliente(nome="Comprou7Dias", telefone="+5531999990022",
                     data_inicio_parceria=today - timedelta(days=30))
        cD = Cliente(nome="Comprou3Dias", telefone="+5531999990023",  # não bate
                     data_inicio_parceria=today - timedelta(days=30))
        cE = Cliente(nome="Inativo",      telefone="+5531999990024",
                     data_inicio_parceria=today - timedelta(days=30),
                     status=StatusCliente.inativo)
        s.add_all([cA, cB, cC, cD, cE]); s.commit()
        for c in (cA, cB, cC, cD, cE):
            s.refresh(c)

        s.add_all([
            Evento(cliente_id=cA.id, nome_evento="Tênis Nike",
                   tipo_evento=TipoEvento.pos_venda,
                   data_evento=today, data_compra=today),
            Evento(cliente_id=cB.id, nome_evento="Curso A",
                   tipo_evento=TipoEvento.pos_venda,
                   data_evento=today - timedelta(days=2),
                   data_compra=today - timedelta(days=2)),
            Evento(cliente_id=cC.id, nome_evento="Curso B",
                   tipo_evento=TipoEvento.pos_venda,
                   data_evento=today - timedelta(days=7),
                   data_compra=today - timedelta(days=7)),
            Evento(cliente_id=cD.id, nome_evento="Curso C",
                   tipo_evento=TipoEvento.pos_venda,
                   data_evento=today - timedelta(days=3),
                   data_compra=today - timedelta(days=3)),
            Evento(cliente_id=cE.id, nome_evento="Curso D",
                   tipo_evento=TipoEvento.pos_venda,
                   data_evento=today, data_compra=today),
        ])
        s.commit()

        stats = dispatch_pos_venda(s, sender, today=today)
        check("Pos_venda: 3 enviados (imediato + 48h + 7d)",
              stats["enviados"] == 3,
              f"stats={stats}")

        envios = s.exec(
            select(Envio).where(Envio.modulo == Modulo.pos_venda)
        ).all()
        nomes = {s.get(Cliente, e.cliente_id).nome for e in envios}
        check("Pos_venda: clientes A/B/C alvo",
              nomes == {"ComprouHoje", "Comprou2Dias", "Comprou7Dias"},
              f"alvos={nomes}")
        check("Pos_venda: inativo NÃO disparou",
              "Inativo" not in nomes, f"alvos={nomes}")
        check("Pos_venda: 3 dias (gatilho neutro) NÃO disparou",
              "Comprou3Dias" not in nomes, f"alvos={nomes}")

        # idempotente: re-run não duplica
        stats2 = dispatch_pos_venda(s, sender, today=today)
        check("Pos_venda idempotente (re-run = 0)",
              stats2["enviados"] == 0 and stats2["ignorados"] >= 3,
              f"stats={stats2}")

        # render do {nome} bateu
        texts = [e.mensagem_texto for e in envios]
        check("Pos_venda: render incluiu nome de cliente",
              any("ComprouHoje" in t for t in texts),
              f"textos={texts}")


def test_dispatch_evento() -> None:
    fresh_db()
    fake = FakeGateway()
    sender = Sender(fake, intervalo_min=0)
    today = date(2026, 5, 31)

    with Session(engine) as s:
        seed_telefones(s, n=1)
        cVesp = Cliente(nome="Vespera", telefone="+5531999990030",
                        data_inicio_parceria=today - timedelta(days=30))
        cPos  = Cliente(nome="PosEvento", telefone="+5531999990031",
                        data_inicio_parceria=today - timedelta(days=30))
        cHoje = Cliente(nome="Hoje", telefone="+5531999990032",  # nada (D=0)
                        data_inicio_parceria=today - timedelta(days=30))
        s.add_all([cVesp, cPos, cHoje]); s.commit()
        for c in (cVesp, cPos, cHoje):
            s.refresh(c)

        s.add_all([
            Evento(cliente_id=cVesp.id, nome_evento="Corrida 5K",
                   tipo_evento=TipoEvento.evento,
                   data_evento=today + timedelta(days=1)),
            Evento(cliente_id=cPos.id, nome_evento="Workshop",
                   tipo_evento=TipoEvento.evento,
                   data_evento=today - timedelta(days=1)),
            Evento(cliente_id=cHoje.id, nome_evento="Live",
                   tipo_evento=TipoEvento.evento,
                   data_evento=today),
        ])
        s.commit()

        stats = dispatch_evento(s, sender, today=today)
        check("Evento: 2 enviados (véspera + pós)",
              stats["enviados"] == 2,
              f"stats={stats}")

        # flags marcadas
        evs = s.exec(select(Evento)).all()
        ev_vesp = next(e for e in evs if e.nome_evento == "Corrida 5K")
        ev_pos  = next(e for e in evs if e.nome_evento == "Workshop")
        check("Evento véspera: flag vespera marcada",
              ev_vesp.vespera_mensagem_enviada is True
              and ev_vesp.pos_mensagem_enviada is False)
        check("Evento pós: flag pos marcada",
              ev_pos.pos_mensagem_enviada is True
              and ev_pos.vespera_mensagem_enviada is False)

        # idempotente
        stats2 = dispatch_evento(s, sender, today=today)
        check("Evento idempotente (re-run = 0)",
              stats2["enviados"] == 0 and stats2["ignorados"] >= 2,
              f"stats={stats2}")

        # render incluiu nome_evento
        envios = s.exec(
            select(Envio).where(Envio.modulo == Modulo.evento)
        ).all()
        texts = [e.mensagem_texto for e in envios]
        check("Evento: render incluiu nome_evento",
              any("Corrida 5K" in t for t in texts)
              and any("Workshop" in t for t in texts),
              f"textos={texts}")


def main() -> int:
    print(f"DB: {settings.DB_PATH}")
    test_templates()
    test_sender_rotation_and_cooldown()
    test_sender_gateway_failure()
    test_dispatch_comemorativo()
    test_dispatch_expiracao()
    test_dispatch_pos_venda()
    test_dispatch_evento()

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*60}\n{passed}/{total} checks passed\n{'='*60}")
    if passed != total:
        print("\nFailures:")
        for label, ok, detail in results:
            if not ok:
                print(f"  - {label}: {detail}")
        return 1

    print("\nLimpando smoke DB.")
    engine.dispose()
    SMOKE_DB.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
