# Agent Blue Team — MiniHub

Agent de détection qui surveille en continu une source de logs :
- `target-env/app/logs/access.log` (requêtes HTTP reçues par MiniHub)

Pipeline : règles rapides (gratuites) → LLM pour les cas suspects
(explication + confiance + action recommandée) → playbook de réponse
(simulé) → journalisation pour le dashboard.

## Installation

```bash
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

## Test sans clé API (validation de la mécanique)

```bash
python test_blue_agent_mock.py
```

Génère un scénario d'attaque simulé (bruteforce, accès non authentifié,
chaîne upload → admin) et vérifie que le pipeline complet détecte bien
les 5 alertes attendues, sans appeler de vraie API.

## Lancement réel — mode API

Editer .env : clé API OpenCode

```bash
python api.py
```

Expose :
- `GET http://127.0.0.1:5001/api/alerts` — les 50 dernières alertes
- `GET http://127.0.0.1:5001/api/status` — statut de l'agent