"""
rules.py
========
Détection par règles simples (rapides, gratuites, pas d'appel LLM).
Chaque règle regarde un événement (et un peu d'état accumulé) et renvoie
None si rien d'anormal, ou un dict décrivant l'alerte sinon.

Philosophie : les règles servent de PREMIER FILTRE bon marché. Seuls les
événements qu'elles jugent suspects sont ensuite envoyés au LLM
(classifier.py) pour une analyse plus fine et une explication en langage
naturel -> on économise des appels API.
"""

from collections import defaultdict

# État accumulé entre les appels (compteurs simples)
_failed_logins = defaultdict(int)
_recent_actions = []  # les 20 derniers événements, pour détecter des séquences
MAX_RECENT = 20


def _remember(event):
    _recent_actions.append(event)
    if len(_recent_actions) > MAX_RECENT:
        _recent_actions.pop(0)


def check_unauthenticated_internal_access(event):
    """VULN-02 : accès à /internal/metadata sans utilisateur authentifié."""
    if event["source"] != "target_access":
        return None
    raw = event["raw"]
    if raw.get("path") == "/internal/metadata" and not raw.get("user"):
        return {
            "rule": "unauthenticated_internal_access",
            "severity": "high",
            "reason": "Accès à l'endpoint interne /internal/metadata sans session authentifiée.",
            "event": event,
        }
    return None


def check_login_bruteforce(event):
    """Plusieurs échecs de connexion suivis d'un succès -> pattern bruteforce."""
    if event["source"] != "target_access":
        return None
    raw = event["raw"]
    if raw.get("path") != "/login" or raw.get("method") != "POST":
        return None

    ip = raw.get("ip", "unknown")
    if raw.get("status_code") == 200:
        # Flask renvoie 200 sur un échec de login (réaffiche le formulaire)
        _failed_logins[ip] += 1
    elif raw.get("status_code") in (301, 302):
        # redirection = connexion réussie
        attempts = _failed_logins.get(ip, 0)
        _failed_logins[ip] = 0
        if attempts >= 1:
            return {
                "rule": "login_bruteforce_pattern",
                "severity": "medium",
                "reason": f"Connexion réussie après {attempts} tentative(s) échouée(s) depuis {ip}.",
                "event": event,
            }
    return None


def check_upload_then_admin_access(event):
    """Séquence suspecte : un upload suivi peu après d'un accès à la zone admin."""
    if event["source"] != "target_access":
        return None
    raw = event["raw"]
    if raw.get("path") == "/admin/users" and raw.get("status_code") == 200:
        had_recent_upload = any(
            e["source"] == "target_access" and e["raw"].get("path") == "/upload"
            for e in _recent_actions[-5:]
        )
        if had_recent_upload:
            return {
                "rule": "upload_then_admin_access",
                "severity": "medium",
                "reason": "Accès à la zone admin peu après un upload de fichier : chaîne d'exploitation possible.",
                "event": event,
            }
    return None


def check_red_agent_tool_use(event):
    """Toute action de l'agent Red Team sur un outil sensible est notée
    (sévérité faible seule, mais utile pour la corrélation)."""
    if event["source"] != "red_agent_decision":
        return None
    raw = event["raw"]
    sensitive_tools = {"try_login", "read_internal_metadata", "upload_file"}
    if raw.get("tool") in sensitive_tools:
        return {
            "rule": "red_agent_sensitive_tool_use",
            "severity": "low",
            "reason": f"L'agent Red Team a utilisé l'outil sensible '{raw.get('tool')}'.",
            "event": event,
        }
    return None


ALL_RULES = [
    check_unauthenticated_internal_access,
    check_login_bruteforce,
    check_upload_then_admin_access,
    check_red_agent_tool_use,
]


def evaluate(event):
    """Fait passer un événement par toutes les règles, mémorise
    l'événement pour les règles à état, et retourne la liste des
    alertes déclenchées (peut être vide)."""
    _remember(event)
    alerts = []
    for rule_fn in ALL_RULES:
        result = rule_fn(event)
        if result:
            alerts.append(result)
    return alerts


def reset_state():
    """Pour les tests : repart avec un état vide."""
    _failed_logins.clear()
    _recent_actions.clear()
