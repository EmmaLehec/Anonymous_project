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

ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_BASE_URL = os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/chat/completions")
ZAI_MODEL = os.environ.get("ZAI_MODEL", "glm-5.3-flash")

OPENCODE_API_KEY = os.environ.get("OPENCODE_API_KEY", "")
OPENCODE_BASE_URL = os.environ.get("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1/chat/completions")
OPENCODE_MODEL = os.environ.get("OPENCODE_MODEL", "union-alpha")


class LLMError(RuntimeError):
    pass


def call_llm(messages, tools=None, temperature=0.2, max_tokens=800):
    """
    Appelle le backend LLM configuré avec une liste de messages au format
    OpenAI-like: [{"role": "system"|"user"|"assistant", "content": "..."}]

    Retourne le texte de la réponse (str).
    """
    if LLM_BACKEND == "zai":
        url, key, model = ZAI_BASE_URL, ZAI_API_KEY, ZAI_MODEL
    elif LLM_BACKEND == "opencode":
        url, key, model = OPENCODE_BASE_URL, OPENCODE_API_KEY, OPENCODE_MODEL
    else:
        raise LLMError(f"Backend LLM inconnu: {LLM_BACKEND}")

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

    try:
        message = data["choices"][0]["message"]
        content = message.get("content")
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError(
            f"Structure de réponse inattendue de l'API '{LLM_BACKEND}': "
            f"{json.dumps(data, ensure_ascii=False)[:500]}"
        ) from e

    if not content or not content.strip():
        # Certains modèles (raisonnement) renvoient le texte dans un
        # champ différent au lieu de "content" -> on tente un repli
        # avant d'abandonner, et on affiche la réponse brute pour debug.
        content = message.get("reasoning_content") or message.get("reasoning")
        if not content or not content.strip():
            raise LLMError(
                f"Champ 'content' vide (ou juste des espaces) dans la réponse "
                f"de '{LLM_BACKEND}' (modèle '{model}'). Réponse brute : "
                f"{json.dumps(data, ensure_ascii=False)[:500]}"
            )

    return content
