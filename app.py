#!/usr/bin/env python3
"""Local-first Matrix operations dashboard. Binds only to loopback."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765
ROOT = Path(__file__).resolve().parent
DATA_DIR = Path.home() / ".matrix-control"
STATE_FILE = DATA_DIR / "state.json"
SSH_DIR = Path.home() / ".ssh"

AGENTS = [
    {"id": "morpheus", "name": "Morpheus", "role": "Infrastructuur", "task": "Serverinventaris en architectuur"},
    {"id": "neo", "name": "Neo", "role": "Incidentcoordinator", "task": "Incidenten prioriteren en voortgang bewaken"},
    {"id": "trinity", "name": "Trinity", "role": "Automatisering", "task": "Veilige, herhaalbare beheertaken"},
    {"id": "smith", "name": "Agent Smith", "role": "Beveiliging", "task": "Defensieve controles en configuratie-audit"},
    {"id": "cypher", "name": "Cypher", "role": "Back-ups", "task": "Back-upstatus en herstelplanning"},
    {"id": "oracle", "name": "Oracle", "role": "Monitoring", "task": "Capaciteit, beschikbaarheid en waarschuwingen"},
    {"id": "tank", "name": "Tank", "role": "Docker", "task": "Containerinventaris en onderhoudsplanning"},
    {"id": "apoc", "name": "Apoc", "role": "Netwerk", "task": "Netwerk- en connectiviteitsinventaris"},
    {"id": "mouse", "name": "Mouse", "role": "Documentatie", "task": "Runbooks en technische documentatie"},
    {"id": "switch", "name": "Switch", "role": "Releasebeheer", "task": "Releasecontrole en wijzigingsregistratie"},
    {"id": "dozer", "name": "Dozer", "role": "Opslag", "task": "Opslaggebruik en retentiecontrole"},
    {"id": "brown", "name": "Agent Brown", "role": "Toegangscontrole", "task": "SSH-toegang en least-privilege review"},
    {"id": "jones", "name": "Agent Jones", "role": "Compliance", "task": "Configuratiebaseline en auditlog"},
]


def load_state() -> dict:
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(state, dict) and isinstance(state.get("tasks"), list) and isinstance(state.get("hosts"), list):
            state["agents"] = AGENTS
            return state
    except (OSError, json.JSONDecodeError):
        pass
    return {"agents": AGENTS, "tasks": [], "hosts": []}


def save_state(state: dict) -> None:
    DATA_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="state-", dir=DATA_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=True, indent=2)
            handle.write("\n")
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, STATE_FILE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def generate_assistant_suggestions(state: dict, prompt: str = "") -> list[dict]:
    tasks = state.get("tasks", [])
    hosts = state.get("hosts", [])
    agent_list = state.get("agents") or AGENTS
    prompt_lower = prompt.lower().strip()
    suggestions: list[dict] = []

    def add(title: str, details: str, *, kind: str, prefill: dict | None = None) -> None:
        suggestions.append({
            "type": kind,
            "title": title,
            "details": details,
            "prefill": prefill or {},
        })

    if any(term in prompt_lower for term in {"docker", "container", "status"}):
        add(
            "Controleer Docker-status",
            "Laat de assistent de lokale containers en status ophalen zonder wijzigingen te doen.",
            kind="docker",
            prefill={},
        )

    if not tasks:
        agent_id = agent_list[0]["id"] if agent_list else "morpheus"
        add(
            "Maak een eerste taak voor de operaties",
            "Vult direct een bruikbare taak in met een agent en een korte beschrijving.",
            kind="task",
            prefill={"title": "Controleer de eerste systeemstatus en noteer de volgende actie", "agent_id": agent_id},
        )

    if not hosts:
        add(
            "Voeg een eerste SSH-host toe",
            "Gebruik een alias of user@host om snel verbindingen te testen en in te vullen.",
            kind="host",
            prefill={"label": "prod-server", "address": "user@server.example"},
        )

    ssh_key_dir = Path.home() / ".ssh"
    if not any(ssh_key_dir.glob("matrix-*")):
        add(
            "Genereer een SSH-sleutel",
            "Maak een lokale ed25519-sleutel voor beveiligde toegang met een verplichte wachtzin.",
            kind="key",
            prefill={"label": "matrix-key"},
        )

    if "incident" in prompt_lower or "kritiek" in prompt_lower or "alarm" in prompt_lower or not tasks:
        add(
            "Plan een incidentcontrole",
            "Gebruik Neo om een incident te prioriteren en de voortgang op te volgen.",
            kind="task",
            prefill={"title": "Prioriteer incident en controleer de eerste bron van gegevens", "agent_id": "neo"},
        )

    add(
        "Controleer backup- en herstelstatus",
        "Gebruik Cypher om de backup- en herstelplanning te valideren.",
        kind="task",
        prefill={"title": "Controleer backup-status en herstelplanning voor de belangrijkste services", "agent_id": "cypher"},
    )

    seen: set[str] = set()
    unique: list[dict] = []
    for suggestion in suggestions:
        key = suggestion["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(suggestion)
    return unique[:5]


def run_readonly(command: list[str], timeout: int = 6) -> dict:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        return {"ok": result.returncode == 0, "output": (result.stdout or result.stderr).strip()[:800]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "output": str(exc)[:300]}


class Handler(BaseHTTPRequestHandler):
    server_version = "MatrixControl/1.0"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _allowed_origin(self) -> bool:
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in {f"{HOST}:{PORT}", f"localhost:{PORT}"} and (origin is None or origin in {f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 16_384:
            raise ValueError("Ongeldige aanvraaggrootte")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON-object verwacht")
        return payload

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            try:
                body = (ROOT / "index.html").read_bytes()
            except OSError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            self._json(200, load_state())
        elif path == "/api/docker":
            version = run_readonly(["docker", "info", "--format", "{{.ServerVersion}}"])
            containers = run_readonly(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"])
            self._json(200, {"available": version["ok"], "version": version["output"], "containers": containers["output"].splitlines() if containers["ok"] and containers["output"] else [], "message": "Docker-status is alleen informatief en veilig. Er worden geen containers gewijzigd."})
        else:
            self._json(404, {"error": "Niet gevonden"})

    def do_POST(self) -> None:
        if not self._allowed_origin():
            self._json(403, {"error": "Alleen lokale aanvragen zijn toegestaan"})
            return
        try:
            payload = self._body()
            path = urlparse(self.path).path
            state = load_state()
            if path == "/api/assistant":
                prompt = str(payload.get("prompt", "")).strip()
                self._json(200, {"prompt": prompt, "suggestions": generate_assistant_suggestions(state, prompt)})
            elif path == "/api/tasks":
                title = str(payload.get("title", "")).strip()[:160]
                agent_id = str(payload.get("agent_id", ""))
                if not title or agent_id not in {agent["id"] for agent in AGENTS}:
                    raise ValueError("Vul een taak en geldige agent in")
                task = {"id": os.urandom(8).hex(), "title": title, "agent_id": agent_id, "status": "Open"}
                state["tasks"].append(task)
                save_state(state)
                self._json(201, task)
            elif path.startswith("/api/tasks/"):
                task_id = path.rsplit("/", 1)[-1]
                state["tasks"] = [task for task in state["tasks"] if task.get("id") != task_id]
                save_state(state)
                self._json(200, {"ok": True})
            elif path == "/api/hosts":
                label = str(payload.get("label", "")).strip()[:60]
                address = str(payload.get("address", "")).strip()[:180]
                if not label or not re.fullmatch(r"[A-Za-z0-9._@:-]+", address) or address.startswith("-"):
                    raise ValueError("Gebruik een hostnaam, SSH-alias of user@host zonder opties")
                host = {"id": os.urandom(8).hex(), "label": label, "address": address}
                state["hosts"].append(host)
                save_state(state)
                self._json(201, host)
            elif path.startswith("/api/hosts/") and path.endswith("/test"):
                host_id = path.split("/")[-2]
                host = next((item for item in state["hosts"] if item.get("id") == host_id), None)
                if host is None:
                    raise ValueError("Host niet gevonden")
                check = run_readonly(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "--", host["address"], "true"], timeout=8)
                self._json(200, check)
            elif path.startswith("/api/hosts/"):
                host_id = path.rsplit("/", 1)[-1]
                state["hosts"] = [host for host in state["hosts"] if host.get("id") != host_id]
                save_state(state)
                self._json(200, {"ok": True})
            elif path == "/api/keys":
                label = str(payload.get("label", "")).strip()
                passphrase = payload.get("passphrase", "")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", label):
                    raise ValueError("Gebruik voor de sleutelnaam 1-32 letters, cijfers, _ of -")
                if not isinstance(passphrase, str) or len(passphrase) < 12 or "\n" in passphrase or "\r" in passphrase:
                    raise ValueError("Kies een SSH-wachtzin van minimaal 12 tekens")
                SSH_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
                os.chmod(SSH_DIR, 0o700)
                key_path = SSH_DIR / f"matrix-{label}"
                if key_path.exists() or key_path.with_suffix(".pub").exists():
                    raise ValueError("Deze sleutel bestaat al; kies een andere naam")
                result = subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-C", f"matrix-{label}", "-f", str(key_path)], input=f"{passphrase}\n{passphrase}\n", capture_output=True, text=True, timeout=15)
                if result.returncode != 0:
                    key_path.unlink(missing_ok=True)
                    key_path.with_suffix(".pub").unlink(missing_ok=True)
                    raise ValueError("Sleutelgeneratie is mislukt")
                public_key = key_path.with_suffix(".pub").read_text(encoding="utf-8").strip()
                self._json(201, {"label": label, "path": str(key_path), "public_key": public_key})
            else:
                self._json(404, {"error": "Niet gevonden"})
        except (ValueError, json.JSONDecodeError, OSError, subprocess.TimeoutExpired) as exc:
            self._json(400, {"error": str(exc)[:300]})


def main() -> None:
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print(f"Kan Matrix Control niet starten: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Matrix Control draait lokaal op http://{HOST}:{PORT}")
    print("Druk Ctrl+C om te stoppen. De app is niet bereikbaar vanaf andere machines.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMatrix Control gestopt.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
