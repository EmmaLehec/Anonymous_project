"""
llm_client.py
=============
Client LLM générique pour l'agent Red Team.

Deux backends possibles, choisis via la variable d'environnement LLM_BACKEND :

  - "zai"      : GLM-5.3-Flash via l'API Z.AI (celle donnée par le prof,
                 à utiliser avec PARCIMONIE — budget partagé entre équipes)
  - "opencode" : le modèle stealth "Union Alpha" via OpenCode, gratuit
                 pendant une semaine — à privilégier pour TOUT le
                 développement/debug, et à réserver Z.AI aux tests de
                 démo qui comptent vraiment.

Les deux API sont compatibles "chat completions" façon OpenAI, donc un
seul client suffit, on change juste l'URL/le nom du modèle.
"""

import json
import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv est optionnel ; sinon exporte tes variables manuellement

LLM_BACKEND = os.environ.get("LLM_BACKEND", "opencode")  # "opencode" par défaut pour économiser le budget Z.AI

OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY")
OPENCODE_BASE_URL = os.environ.get("OPENCODE_BASE_URL")
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL")


class LLMError(RuntimeError):
    pass


def call_llm(messages, tools=None, temperature=0.2, max_tokens=800):
    """
    Appelle le backend LLM configuré avec une liste de messages au format
    OpenAI-like: [{"role": "system"|"user"|"assistant", "content": "..."}]

    Retourne le texte de la réponse (str).
    """

    url, key, model = OPENCODE_BASE_URL, OPENCODE_API_KEY, OPENCODE_MODEL

    if not key:
        raise LLMError(
            f"Clé API manquante pour le backend '{LLM_BACKEND}'. "
            f"Définis la variable d'environnement correspondante."
        )

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload),
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]
