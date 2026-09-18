"""
tools.py
========
Outils exposés à l'agent Red Team. Chaque outil ne fait qu'appeler
l'environnement cible MiniHub (voir target-env/), qui vous appartient et
tourne dans un réseau Docker isolé. Aucun outil ici ne touche à un
système réel en dehors de ce bac à sable.

Ajoute ici de nouveaux outils si besoin, mais garde toujours la même
philosophie : l'outil ne fait qu'un appel HTTP contrôlé vers TARGET_BASE_URL.
"""

import os
import requests

TARGET_BASE_URL = os.environ.get("TARGET_BASE_URL", "http://127.0.0.1:5000")

# Session HTTP réutilisée pour conserver les cookies entre les appels
# (utile une fois que l'agent s'est connecté avec try_login)
_session = requests.Session()


def scan_endpoint(path: str) -> dict:
    """Fait une requête GET sur un chemin donné du service cible et
    retourne le statut + un extrait du corps de la réponse."""
    try:
        r = _session.get(f"{TARGET_BASE_URL}{path}", timeout=10)
        return {
            "status_code": r.status_code,
            "body_preview": r.text[:500],
        }
    except requests.RequestException as e:
        return {"error": str(e)}


def try_login(username: str, password: str) -> dict:
    """Tente une connexion sur l'interface de login avec les identifiants fournis. Si l'essai échoue, tu DOIS réessayer immédiatement avec un autre mot de passe courant avant de passer à un autre outil."""
    try:
        r = _session.post(
            f"{TARGET_BASE_URL}/login",
            data={"username": username, "password": password},
            timeout=10,
            allow_redirects=False,
        )
        success = r.status_code in (301, 302) and "login" not in r.headers.get("Location", "")
        return {"status_code": r.status_code, "success": success}
    except requests.RequestException as e:
        return {"error": str(e)}


def upload_file(filename: str, content: str) -> dict:
    """Uploade un fichier texte factice vers /upload (nécessite d'être
    connecté au préalable via try_login)."""
    try:
        files = {"file": (filename, content)}
        r = _session.post(f"{TARGET_BASE_URL}/upload", files=files, timeout=10)
        return {"status_code": r.status_code}
    except requests.RequestException as e:
        return {"error": str(e)}


def read_internal_metadata() -> dict:
    """Interroge l'endpoint interne /internal/metadata (VULN-02)."""
    return scan_endpoint("/internal/metadata")


TOOL_REGISTRY = {
    "scan_endpoint": scan_endpoint,
    "try_login": try_login,
    "upload_file": upload_file,
    "read_internal_metadata": read_internal_metadata,
}

TOOLS_DESCRIPTION = """
Outils disponibles (réponds UNIQUEMENT avec un JSON du type
{"tool": "<nom_outil>", "args": {...}} pour en utiliser un, ou
{"tool": "stop", "args": {"reason": "..."}} si tu as fini) :

- scan_endpoint(path: str) : fait un GET sur un chemin du service cible.
- try_login(username: str, password: str) : tente une connexion.
- upload_file(filename: str, content: str) : uploade un fichier texte.
- read_internal_metadata() : consulte l'endpoint interne de métadonnées.
"""
