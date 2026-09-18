"""
playbook.py
===========
Exécute une action de réponse en fonction de la recommandation du
classifieur. Toutes les actions sont SIMULÉES (elles écrivent un
événement dans un journal dédié plutôt que de vraiment couper quoi que
ce soit) : c'est suffisant pour la démo, et ça évite de casser ton
environnement en pleine soutenance.

Si tu veux une action réellement visible en démo (ex: couper le
conteneur MiniHub), tu peux remplacer `isolate_service()` par un appel à
l'API Docker (docker-py) -- mais teste-le abondamment avant la
soutenance, avec un moyen simple de tout relancer.
"""

import json
import os
from datetime import datetime, timezone

RESPONSE_LOG_PATH = os.environ.get(
    "BLUE_RESPONSE_LOG_PATH", "./logs/blue_agent_responses.log"
)
os.makedirs(os.path.dirname(RESPONSE_LOG_PATH), exist_ok=True)


def _log_response(action, alert, detail):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "rule": alert["rule"],
        "severity": alert["severity"],
        "detail": detail,
    }
    with open(RESPONSE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def monitor(alert):
    return _log_response("monitor", alert, "Anomalie mineure, mise sous surveillance uniquement.")


def alert_team(alert):
    return _log_response(
        "alert_team", alert,
        "Alerte envoyée à l'équipe (simulation - brancher ici un webhook Slack/Discord en vrai déploiement)."
    )


def isolate_service(alert):
    return _log_response(
        "isolate_service", alert,
        "Isolation du service cible SIMULÉE (en production : couper le trafic réseau vers le conteneur compromis)."
    )


def revoke_credentials(alert):
    return _log_response(
        "revoke_credentials", alert,
        "Révocation des identifiants SIMULÉE (en production : appeler l'API du fournisseur cloud pour invalider la clé exposée)."
    )


ACTION_REGISTRY = {
    "monitor": monitor,
    "alert_team": alert_team,
    "isolate_service": isolate_service,
    "revoke_credentials": revoke_credentials,
}


def execute(classified_alert):
    """Exécute l'action recommandée par le classifieur pour une alerte
    déjà enrichie (dict retourné par classifier.classify_alert)."""
    action_name = classified_alert["analysis"].get("recommended_action", "monitor")
    action_fn = ACTION_REGISTRY.get(action_name, monitor)
    return action_fn(classified_alert)
