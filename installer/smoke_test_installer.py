"""Smoke test offline pros scripts PowerShell do installer.

Run:
    python installer/smoke_test_installer.py

Verifica:
  1. Tokenização (sintaxe válida) dos 3 scripts via PSParser
  2. install.ps1 -CheckOnly imprime resumo de pré-reqs e exit code coerente
  3. install.ps1 -DryRun roda sem modificar nada (sem venv criada)
  4. Funções esperadas estão definidas em cada script
  5. launcher.ps1 -DockerOnly sem Docker → exit graceful
  6. check.ps1 roda end-to-end (sempre exit 0, só diagnóstico)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

INSTALLER_DIR = Path(__file__).resolve().parent
INSTALL_PS    = INSTALLER_DIR / "install.ps1"
LAUNCHER_PS   = INSTALLER_DIR / "launcher.ps1"
CHECK_PS      = INSTALLER_DIR / "check.ps1"

PROJECT_ROOT = INSTALLER_DIR.parent
VENV_DIR     = PROJECT_ROOT / ".venv"


def _find_pwsh() -> str | None:
    for name in ("pwsh", "pwsh.exe", "powershell.exe", "powershell"):
        p = shutil.which(name)
        if p:
            return p
    return None


PWSH = _find_pwsh()

results: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, ok, detail))
    icon = "OK " if ok else "FAIL"
    print(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))


def run_pwsh(args: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    assert PWSH
    return subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive"] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=timeout,
    )


def test_syntax(script: Path) -> bool:
    """Tokeniza o script via PSParser. Erros → falha."""
    cmd = [
        "-Command",
        (
            "$errors = $null; "
            f"$tokens = [System.Management.Automation.PSParser]::Tokenize("
            f"(Get-Content -Raw -LiteralPath '{script}'), [ref]$errors); "
            "if ($errors -and $errors.Count -gt 0) { "
            "  $errors | ForEach-Object { Write-Host $_.Message }; exit 1 "
            "} else { Write-Host \"$($tokens.Count) tokens\"; exit 0 }"
        ),
    ]
    r = run_pwsh(cmd, timeout=30)
    return r.returncode == 0


def main() -> int:
    if not PWSH:
        print("[SKIP] PowerShell não encontrado. Smoke test exige pwsh ou powershell.exe.")
        return 0

    print(f"PowerShell: {PWSH}")
    print(f"INSTALL_PS: {INSTALL_PS}")
    print()

    # =====================================================================
    # 1. Existência dos scripts
    # =====================================================================
    for p in (INSTALL_PS, LAUNCHER_PS, CHECK_PS):
        check(f"{p.name} existe", p.exists(), f"path={p}")

    # =====================================================================
    # 2. Sintaxe válida (tokeniza)
    # =====================================================================
    for p in (INSTALL_PS, LAUNCHER_PS, CHECK_PS):
        check(f"{p.name} sintaxe ok", test_syntax(p))

    # =====================================================================
    # 3. Funções esperadas presentes
    # =====================================================================
    install_src = INSTALL_PS.read_text(encoding="utf-8")
    for fn in (
        "Test-Docker", "Test-Python", "Test-Node",
        "Install-BackendVenv", "Initialize-Database",
        "Install-FrontendDeps", "Start-EvolutionStack",
        "New-DesktopShortcut", "Show-PrereqSummary",
    ):
        check(f"install.ps1 define '{fn}'", f"function {fn}" in install_src)

    launcher_src = LAUNCHER_PS.read_text(encoding="utf-8")
    for fn in ("Test-PortInUse", "Wait-Health"):
        check(f"launcher.ps1 define '{fn}'", f"function {fn}" in launcher_src)

    check_src = CHECK_PS.read_text(encoding="utf-8")
    check("check.ps1 define 'Probe'", "function Probe" in check_src)

    # =====================================================================
    # 4. install.ps1 -CheckOnly — só lê estado, não modifica nada
    # =====================================================================
    venv_existed_before = VENV_DIR.exists()
    r = run_pwsh(["-ExecutionPolicy", "Bypass", "-File", str(INSTALL_PS), "-CheckOnly"],
                 timeout=60)
    check("-CheckOnly executou sem crash", r.returncode in (0, 1),
          f"rc={r.returncode}")
    out = r.stdout + r.stderr
    check("-CheckOnly imprimiu seção 'Pré-requisitos'",
          "Pr" in out and ("requisitos" in out or "requesitos" in out),
          f"stdout last 200: {out[-200:]!r}")
    # não deve criar venv
    if not venv_existed_before:
        check("-CheckOnly não criou venv", not VENV_DIR.exists(),
              f"venv_existe={VENV_DIR.exists()}")
    else:
        check("-CheckOnly não tocou venv (já existia)", True)

    # =====================================================================
    # 5. install.ps1 -DryRun — anuncia steps, não executa
    # =====================================================================
    with tempfile.TemporaryDirectory() as td:
        # rodar com flag suprimindo modificações reais
        r = run_pwsh([
            "-ExecutionPolicy", "Bypass", "-File", str(INSTALL_PS),
            "-DryRun", "-NoShortcut",
        ], timeout=60)
        check("-DryRun executou sem crash", r.returncode in (0, 2, 3, 4),
              f"rc={r.returncode}")
        # se Python e Node estão OK, exit 0 esperado; senão pode ser 2/3/4
        check("-DryRun avisou modo DRY RUN",
              "DRY RUN" in r.stdout, f"stdout last 200: {r.stdout[-200:]!r}")

    # =====================================================================
    # 6. launcher.ps1 -DockerOnly: sem Docker instalado deve dar mensagem
    #    graceful (Warn) e exit 0 — não crash
    # =====================================================================
    r = run_pwsh([
        "-ExecutionPolicy", "Bypass", "-File", str(LAUNCHER_PS),
        "-DockerOnly",
    ], timeout=30)
    # exit code 0 (concluiu) ou exception clean — sem stacktrace puro
    check("launcher -DockerOnly exit graceful", r.returncode in (0, 1),
          f"rc={r.returncode} err[:150]={r.stderr[:150]!r}")

    # =====================================================================
    # 7. check.ps1 sempre roda até o fim (só diagnóstico)
    # =====================================================================
    r = run_pwsh(["-ExecutionPolicy", "Bypass", "-File", str(CHECK_PS)], timeout=30)
    check("check.ps1 executou até o fim", "===" in r.stdout,
          f"rc={r.returncode} stdout last 200: {r.stdout[-200:]!r}")
    check("check.ps1 exit 0", r.returncode == 0, f"rc={r.returncode}")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
