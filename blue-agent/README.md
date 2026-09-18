# Agent Blue Team — MiniHub

Agent de détection qui surveille en continu deux sources de logs :
- `target-env/app/logs/access.log` (requêtes HTTP reçues par MiniHub)
- `red-agent/logs/red_agent_decisions.log` (décisions de l'agent Red Team)

Pipeline : règles rapides (gratuites) → LLM pour les cas suspects
(explication + confiance + action recommandée) → playbook de réponse
(simulé) → journalisation pour le dashboard.

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# édite .env : chemins vers les logs, clé API OpenCode
```

## Test sans clé API (validation de la mécanique)

```bash
python3 test_blue_agent_mock.py
```

Génère un scénario d'attaque simulé (bruteforce, accès non authentifié,
chaîne upload → admin) et vérifie que le pipeline complet détecte bien
les 5 alertes attendues, sans appeler de vraie API.

## Lancement réel — mode CLI

```bash
python3 blue_agent.py
```

Tourne en continu (poll toutes les `BLUE_POLL_INTERVAL` secondes),
affiche chaque alerte en console au fur et à mesure.

## Lancement réel — mode API (pour brancher le dashboard front)

```bash
python3 api.py
```

Expose :
- `GET http://127.0.0.1:5001/api/alerts` — les 50 dernières alertes
- `GET http://127.0.0.1:5001/api/status` — statut de l'agent

## Scénario de démo recommandé

1. Lance MiniHub (`target-env/`).
2. Lance le Blue Team (`python3 api.py`).
3. Lance le Red Team (`red-agent/agent.py`).
4. Regarde le dashboard afficher les alertes en direct au fur et à
   mesure que le Red Team explore/exploite MiniHub — c'est ton moment
   fort de la soutenance.

## Budget API

Même règle que pour le Red Team : `LLM_BACKEND=opencode` (Union Alpha,
gratuit) pour tout le développement, `zai` uniquement pour la démo finale.
