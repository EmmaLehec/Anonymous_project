"""
log_reader.py
=============
Lit en continu deux sources de logs différentes et les normalise en un
flux unique d'événements, triés par ordre chronologique :

  1. Les logs d'accès HTTP de MiniHub (target-env/app/logs/access.log)
     -> un événement par requête HTTP reçue par la cible.
  2. Les logs de décisions de l'agent Red Team (red-agent/logs/red_agent_decisions.log)
     -> un événement par action décidée par l'agent (pensée + outil + résultat).

Chaque lecteur retient sa position (offset en octets) pour ne renvoyer,
à chaque appel, que les NOUVELLES lignes depuis la dernière lecture
(comme un "tail -f" piloté par code plutôt que par un processus).

IMPORTANT : les offsets sont persistés sur disque (fichier JSON dans
STATE_DIR), pas seulement en mémoire. Sans ça, relancer `api.py` ou
`blue_agent.py` repart de zéro et REJOUE tout l'historique des logs à
chaque redémarrage -> avalanche d'anciennes alertes qui donne
l'impression que l'agent "n'arrête jamais".

Pour repartir d'une lecture propre (avant une démo par exemple), il
suffit de supprimer le dossier STATE_DIR (par défaut ./state/), ou
d'appeler reset_offsets().

C'est cette fonction que l'agent Blue Team appelle en boucle pour obtenir
son flux d'événements à analyser.
"""

import json
import os

TARGET_ACCESS_LOG = os.environ.get(
    "TARGET_ACCESS_LOG", "../target-env/app/logs/access.log"
)
RED_AGENT_LOG = os.environ.get(
    "RED_AGENT_LOG", "../red-agent/logs/red_agent_decisions.log"
)

# IMPORTANT (réalisme de la démo) : un vrai défenseur n'a JAMAIS accès au
# raisonnement interne de l'attaquant, seulement à ce que son propre
# système observe. Par défaut, la détection ne lit donc QUE access.log.
# Mets BLUE_BLIND_MODE=false uniquement si tu veux volontairement montrer
# la corrélation attaquant/défenseur à des fins pédagogiques (voir
# attacker_trace_viewer.py pour une vue séparée, hors pipeline d'alerte).
BLUE_BLIND_MODE = os.environ.get("BLUE_BLIND_MODE", "true").lower() == "true"

STATE_DIR = os.environ.get("BLUE_STATE_DIR", "./state")
OFFSETS_FILE = os.path.join(STATE_DIR, "log_offsets.json")


def _load_offsets() -> dict:
    if os.path.exists(OFFSETS_FILE):
        try:
            with open(OFFSETS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"access": 0, "red_agent": 0}


def _save_offsets(offsets: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(OFFSETS_FILE, "w", encoding="utf-8") as f:
        json.dump(offsets, f)


_offsets = _load_offsets()


def _read_new_lines(path, offset_key):
    """Lit les nouvelles lignes d'un fichier depuis la dernière position
    connue (persistée sur disque). Tolère un fichier qui n'existe pas
    encore (retourne [])."""
    if not os.path.exists(path):
        return []
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        f.seek(_offsets[offset_key])
        for line in f:
            line = line.strip()
            if line:
                lines.append(line)
        _offsets[offset_key] = f.tell()
    return lines


def poll_events():
    """Retourne la liste des nouveaux événements normalisés (triés par
    timestamp) depuis les deux sources de logs, depuis le dernier appel."""
    events = []

    for line in _read_new_lines(TARGET_ACCESS_LOG, "access"):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append({
            "source": "target_access",
            "timestamp": raw.get("timestamp"),
            "summary": f"{raw.get('method')} {raw.get('path')} -> {raw.get('status_code')} (user={raw.get('user')})",
            "raw": raw,
        })

    for line in _read_new_lines(RED_AGENT_LOG, "red_agent"):
        if BLUE_BLIND_MODE:
            # En mode réaliste (par défaut), on avance quand même
            # l'offset pour ne pas accumuler ce fichier indéfiniment,
            # mais on n'injecte PAS ces événements dans la détection :
            # un vrai défenseur ne les verrait jamais.
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        events.append({
            "source": "red_agent_decision",
            "timestamp": raw.get("timestamp"),
            "summary": f"step {raw.get('step')}: {raw.get('tool')}({raw.get('args')}) -- {raw.get('thought')}",
            "raw": raw,
        })

    events.sort(key=lambda e: e["timestamp"] or "")

    if events:
        _save_offsets(_offsets)

    return events


def reset_offsets():
    """Utile pour les tests, ou pour repartir d'une lecture propre avant
    une démo : repart de zéro sur les deux fichiers ET efface le fichier
    d'état sur disque."""
    _offsets["access"] = 0
    _offsets["red_agent"] = 0
    if os.path.exists(OFFSETS_FILE):
        os.remove(OFFSETS_FILE)

