import { useEffect, useState } from "react";
import { API_BASE } from "../api/client";

type State = "checking" | "ok" | "bad";

export default function HealthBadge() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const base = API_BASE.replace(/\/api$/, "");
        const r = await fetch(`${base}/health`, { cache: "no-store" });
        if (!alive) return;
        setState(r.ok ? "ok" : "bad");
      } catch {
        if (alive) setState("bad");
      }
    };
    void check();
    const id = setInterval(check, 8000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div className="health-badge">
      <span className={`health-dot ${state}`} />
      <span>API {state === "checking" ? "…" : state === "ok" ? "online" : "offline"}</span>
    </div>
  );
}
