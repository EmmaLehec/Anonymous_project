"""
blue_agent.py
=============
Boucle principale de l'agent Blue Team :

  1. Récupère les nouveaux événements (logs HTTP MiniHub + décisions Red Team)
  2. Fait passer chaque événement dans les règles de détection (rapide, gratuit)
  3. Pour chaque alerte déclenchée, demande une analyse fine au LLM (classifier.py)
  4. Exécute l'action de réponse recommandée (playbook.py, simulée)
  5. Journalise tout dans logs/blue_agent_alerts.log pour le dashboard

Tourne en continu (poll toutes les N secondes) -- à lancer PENDANT ou
APRÈS une exécution de l'agent Red Team pour voir la détection en direct.
"""

import json
import os
import time
from datetime import datetime, timezone

from log_reader import poll_events
from rules import evaluate as evaluate_rules
from classifier import classify_alert
from playbook import execute as execute_playbook

POLL_INTERVAL_SECONDS = float(os.environ.get("BLUE_POLL_INTERVAL", "2"))
ALERTS_LOG_PATH = os.environ.get("BLUE_ALERTS_LOG_PATH", "./logs/blue_agent_alerts.log")
os.makedirs(os.path.dirname(ALERTS_LOG_PATH), exist_ok=True)


def _log_alert(classified_alert, response):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule": classified_alert["rule"],
        "severity": classified_alert["severity"],
        "reason": classified_alert["reason"],
        "analysis": classified_alert["analysis"],
        "response_action": response["action"],
        "source_event": classified_alert["event"],
    }
    with open(ALERTS_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def process_new_events():
    """Traite tous les nouveaux événements disponibles. Retourne la liste
    des alertes générées (utile pour les tests et pour l'API/dashboard)."""
    events = poll_events()
    generated_alerts = []

    for event in events:
        raw_alerts = evaluate_rules(event)
        for raw_alert in raw_alerts:
            classified = classify_alert(raw_alert)
            response = execute_playbook(classified)
            entry = _log_alert(classified, response)
            generated_alerts.append(entry)

            print(f"\n[ALERTE] règle={entry['rule']} sévérité={entry['severity']}")
            print(f"  Explication : {entry['analysis'].get('explanation')}")
            print(f"  Confiance   : {entry['analysis'].get('confidence')}")
            print(f"  Action      : {entry['response_action']}")

    return generated_alerts


def run_forever():
    print(f"Agent Blue Team démarré (poll toutes les {POLL_INTERVAL_SECONDS}s)...")
    while True:
        try:
            process_new_events()
        except Exception as e:
            print(f"[blue_agent] Erreur dans le cycle de détection (ignorée, on continue) : {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_forever()
