"""
test_blue_agent_mock.py
========================
Génère des logs simulés (comme si MiniHub avait été attaqué par l'agent
Red Team), les écrit dans des fichiers temporaires, et fait tourner UNE
passe de détection du Blue Team dessus -- avec le LLM mocké pour ne
consommer aucun budget API.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

import log_reader


def _write_jsonl(path, entries):
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def fake_call_llm(messages, **kwargs):
    return json.dumps({
        "explanation": "Comportement anormal détecté et confirmé par l'analyse contextuelle.",
        "confidence": 0.87,
        "recommended_action": "alert_team",
    })


def main():
    tmp_dir = tempfile.mkdtemp()
    access_log_path = os.path.join(tmp_dir, "access.log")
    red_agent_log_path = os.path.join(tmp_dir, "red_agent_decisions.log")

    now = datetime.now(timezone.utc).isoformat()

    # Scénario simulé : login échoué, login réussi, accès metadata sans
    # session, upload, puis accès admin -- exactement la chaîne qu'on a
    # vue avec le vrai agent Red Team.
    access_events = [
        {"timestamp": now, "ip": "127.0.0.1", "method": "POST", "path": "/login", "status_code": 200, "user": None, "duration_ms": 1.2, "user_agent": "test"},
        {"timestamp": now, "ip": "127.0.0.1", "method": "POST", "path": "/login", "status_code": 302, "user": "admin", "duration_ms": 1.1, "user_agent": "test"},
        {"timestamp": now, "ip": "127.0.0.1", "method": "GET", "path": "/internal/metadata", "status_code": 200, "user": None, "duration_ms": 0.5, "user_agent": "test"},
        {"timestamp": now, "ip": "127.0.0.1", "method": "POST", "path": "/upload", "status_code": 200, "user": "admin", "duration_ms": 3.0, "user_agent": "test"},
        {"timestamp": now, "ip": "127.0.0.1", "method": "GET", "path": "/admin/users", "status_code": 200, "user": "admin", "duration_ms": 0.4, "user_agent": "test"},
    ]
    red_agent_events = [
        {"timestamp": now, "step": 1, "thought": "Test", "tool": "try_login", "args": {"username": "admin", "password": "admin123"}, "observation": {"success": True}},
        {"timestamp": now, "step": 2, "thought": "Test", "tool": "read_internal_metadata", "args": {}, "observation": {"status_code": 200}},
    ]

    _write_jsonl(access_log_path, access_events)
    _write_jsonl(red_agent_log_path, red_agent_events)

    log_reader.TARGET_ACCESS_LOG = access_log_path
    log_reader.RED_AGENT_LOG = red_agent_log_path
    log_reader.reset_offsets()

    import rules
    rules.reset_state()

    with patch("classifier.call_llm", side_effect=fake_call_llm):
        from blue_agent import process_new_events
        alerts = process_new_events()

    print(f"\n{len(alerts)} alerte(s) générée(s) au total.")
    assert len(alerts) >= 3, "On attendait au moins 3 alertes (metadata non auth, bruteforce, upload+admin)"
    print("OK : le pipeline de détection fonctionne de bout en bout.")


if __name__ == "__main__":
    main()
