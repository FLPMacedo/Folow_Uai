import { useEffect, useMemo, useState } from "react";
import { getAgenda } from "../api/endpoints";
import type { AgendaItem } from "../api/types";
import Modal from "../components/Modal";
import ErrorBanner from "../components/ErrorBanner";

const MODULO_COR: Record<string, string> = {
  comemorativo: "#3b82f6",  // azul
  expiracao:    "#ef4444",  // vermelho
  pos_venda:    "#10b981",  // verde
  evento:       "#f59e0b",  // laranja
  sumiu:        "#8b5cf6",  // roxo
};

const MESES = [
  "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
  "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro",
];
const DIAS_SEMANA = ["Dom","Seg","Ter","Qua","Qui","Sex","Sáb"];

export default function AgendaPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth()); // 0-indexed
  const [items, setItems] = useState<AgendaItem[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const range = useMemo(() => {
    const first = new Date(year, month, 1);
    const last = new Date(year, month + 1, 0);
    // estender pra cobrir as células visíveis (semanas inteiras)
    const firstWeekday = first.getDay();
    const gridStart = new Date(first);
    gridStart.setDate(first.getDate() - firstWeekday);
    const gridEnd = new Date(last);
    gridEnd.setDate(last.getDate() + (6 - last.getDay()));
    return { gridStart, gridEnd, first, last };
  }, [year, month]);

  const load = async () => {
    try {
      const from = range.gridStart.toISOString().slice(0, 10);
      const to = range.gridEnd.toISOString().slice(0, 10);
      setItems(await getAgenda(from, to));
    } catch (e) { setErr(String(e)); }
  };
  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [year, month]);

  const itemsByDay = useMemo(() => {
    const map = new Map<string, AgendaItem[]>();
    for (const it of items) {
      const arr = map.get(it.data) ?? [];
      arr.push(it);
      map.set(it.data, arr);
    }
    return map;
  }, [items]);

  const prevMonth = () => {
    if (month === 0) { setYear(year - 1); setMonth(11); }
    else setMonth(month - 1);
  };
  const nextMonth = () => {
    if (month === 11) { setYear(year + 1); setMonth(0); }
    else setMonth(month + 1);
  };
  const hoje = today.toISOString().slice(0, 10);

  // grade de células (sempre 6 linhas × 7 colunas = 42)
  const cells: Array<{ iso: string; day: number; inMonth: boolean; isToday: boolean }> = [];
  for (let i = 0; i < 42; i++) {
    const d = new Date(range.gridStart);
    d.setDate(d.getDate() + i);
    const iso = d.toISOString().slice(0, 10);
    cells.push({
      iso, day: d.getDate(),
      inMonth: d.getMonth() === month,
      isToday: iso === hoje,
    });
  }

  // legenda
  const modulosPresentes = Array.from(new Set(items.map((i) => i.modulo)));

  return (
    <div>
      <div className="page-header">
        <h1>Agenda de disparos</h1>
        <div className="btn-row">
          <button className="btn" onClick={prevMonth}>‹ Anterior</button>
          <button className="btn" onClick={() => { setYear(today.getFullYear()); setMonth(today.getMonth()); }}>Hoje</button>
          <button className="btn" onClick={nextMonth}>Próximo ›</button>
        </div>
      </div>
      <ErrorBanner message={err} onClose={() => setErr(null)} />

      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>{MESES[month]} {year}</h2>
          <span className="spacer" />
          <span className="muted">{items.length} disparos previstos</span>
        </div>

        <div style={{
          display: "grid", gridTemplateColumns: "repeat(7, 1fr)",
          gap: 4, marginBottom: 4,
        }}>
          {DIAS_SEMANA.map((d) => (
            <div key={d} className="muted"
              style={{ fontSize: 11, fontWeight: 600, textAlign: "center",
                       padding: 4, textTransform: "uppercase" }}>
              {d}
            </div>
          ))}
        </div>

        <div style={{
          display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4,
        }}>
          {cells.map((cell) => {
            const dayItems = itemsByDay.get(cell.iso) ?? [];
            const groups = groupByModulo(dayItems);
            return (
              <button key={cell.iso}
                onClick={() => dayItems.length > 0 && setSelectedDay(cell.iso)}
                disabled={dayItems.length === 0}
                style={{
                  background: cell.inMonth ? "#fff" : "#f9fafb",
                  border: cell.isToday ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                  borderRadius: 6,
                  minHeight: 70,
                  padding: 6,
                  textAlign: "left",
                  cursor: dayItems.length > 0 ? "pointer" : "default",
                  display: "flex", flexDirection: "column", gap: 4,
                  opacity: cell.inMonth ? 1 : 0.55,
                }}>
                <div style={{
                  fontSize: 11,
                  fontWeight: cell.isToday ? 700 : 500,
                  color: cell.isToday ? "#3b82f6" : "#1f2937",
                }}>
                  {cell.day}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 3 }}>
                  {groups.map(([mod, count]) => (
                    <span key={mod} title={`${mod} (${count})`}
                      style={{
                        display: "inline-flex", alignItems: "center", gap: 2,
                        fontSize: 10,
                        padding: "1px 5px",
                        borderRadius: 999,
                        background: `${MODULO_COR[mod] ?? "#6b7280"}22`,
                        color: MODULO_COR[mod] ?? "#6b7280",
                        fontWeight: 600,
                      }}>
                      <span style={{
                        width: 5, height: 5, borderRadius: 50,
                        background: MODULO_COR[mod] ?? "#6b7280",
                      }} />
                      {count}
                    </span>
                  ))}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {modulosPresentes.length > 0 && (
        <div className="card" style={{ display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
          <strong>Legenda:</strong>
          {modulosPresentes.map((m) => (
            <span key={m} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{
                width: 10, height: 10, borderRadius: 50,
                background: MODULO_COR[m] ?? "#6b7280",
              }} />
              <span className="muted">{m}</span>
            </span>
          ))}
        </div>
      )}

      <Modal title={selectedDay ? `Disparos em ${formatBR(selectedDay)}` : ""}
        open={selectedDay !== null}
        onClose={() => setSelectedDay(null)}
        footer={<button className="btn" onClick={() => setSelectedDay(null)}>Fechar</button>}>
        {selectedDay && (
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {(itemsByDay.get(selectedDay) ?? []).map((it, i) => (
              <li key={i} style={{
                padding: "8px 0",
                borderBottom: "1px solid #f3f4f6",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <span style={{
                  width: 10, height: 10, borderRadius: 50,
                  background: MODULO_COR[it.modulo] ?? "#6b7280",
                  flexShrink: 0,
                }} />
                <div style={{ flex: 1 }}>
                  <div style={{
                    textDecoration: it.ja_processado ? "line-through" : "none",
                    color: it.ja_processado ? "#9ca3af" : "#1f2937",
                  }}>
                    {it.titulo}
                  </div>
                  <div className="muted" style={{ fontSize: 11 }}>
                    {it.cliente_nome} · {it.telefone} · {it.modulo}
                  </div>
                </div>
                {it.ja_processado && (
                  <span className="badge ok">✓ enviado</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </div>
  );
}

function groupByModulo(items: AgendaItem[]): Array<[string, number]> {
  const map = new Map<string, number>();
  for (const it of items) {
    map.set(it.modulo, (map.get(it.modulo) ?? 0) + 1);
  }
  return Array.from(map.entries());
}

function formatBR(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}
