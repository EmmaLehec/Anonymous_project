"""
decision_logger.py
===================
Journalise chaque étape de raisonnement de l'agent (pensée -> action ->
observation) dans un fichier JSON Lines, séparé des logs d'accès HTTP de
MiniHub. C'est ce fichier qui alimentera le dashboard et, plus tard,
l'agent Blue Team (qui pourra croiser les deux sources de logs).
"""

import json
import os
from datetime import datetime, timezone

LOG_PATH = os.environ.get("RED_AGENT_LOG_PATH", "./logs/red_agent_decisions.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def log_step(step_number: int, thought: str, tool: str, args: dict, observation):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "step": step_number,
        "thought": thought,
        "tool": tool,
        "args": args,
        "observation": observation,
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry
