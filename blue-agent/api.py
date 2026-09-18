"""
api.py
======
Petite API Flask qui fait tourner la boucle de détection en tâche de
fond et expose les alertes générées, pour que ton front (Open WebUI
custom, ou une page dédiée) puisse les afficher en direct.

Lancement :
    python3 api.py
Puis :
    GET http://127.0.0.1:5001/api/alerts        -> les 50 dernières alertes
    GET http://127.0.0.1:5001/api/status         -> statut de l'agent

CORS ouvert pour simplifier l'intégration avec un front qui tourne sur un
autre port pendant le développement local (à restreindre en production).
"""

import os
import threading
import time

from flask import Flask, jsonify

from blue_agent import process_new_events, POLL_INTERVAL_SECONDS

# Par défaut, on n'écoute QUE sur la machine locale (127.0.0.1) : le
# dashboard qui tourne sur la même machine peut s'y connecter, mais rien
# depuis le réseau ne peut l'atteindre -> plus de popup pare-feu, et
# cohérent avec la règle "jamais de 0.0.0.0" du reste du projet.
# Si tu déploies dans Docker (réseau isolé sandbox-net), passe
# BLUE_API_HOST=0.0.0.0 dans docker-compose.yml pour ce service.
API_HOST = os.environ.get("BLUE_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("BLUE_API_PORT", "5001"))

app = Flask(__name__)

_alerts_buffer = []
_MAX_BUFFER = 200
_started_at = time.time()


@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def _background_loop():
    while True:
        try:
            new_alerts = process_new_events()
            _alerts_buffer.extend(new_alerts)
            del _alerts_buffer[:-_MAX_BUFFER]  # garde uniquement les N dernières
        except Exception as e:
            # Ne JAMAIS laisser une erreur ponctuelle (API LLM en rade,
            # log temporairement illisible...) tuer le thread de fond en
            # silence -- on log l'erreur et on continue au cycle suivant.
            print(f"[api.py] Erreur dans la boucle de détection (ignorée, on continue) : {e}")
        time.sleep(POLL_INTERVAL_SECONDS)


@app.route("/api/alerts")
def get_alerts():
    return jsonify(_alerts_buffer[-50:])


@app.route("/api/status")
def get_status():
    return jsonify({
        "status": "running",
        "uptime_seconds": round(time.time() - _started_at, 1),
        "total_alerts": len(_alerts_buffer),
    })


if __name__ == "__main__":
    thread = threading.Thread(target=_background_loop, daemon=True)
    thread.start()
    print(f"API Blue Team disponible sur http://{API_HOST}:{API_PORT}/api/alerts")
    app.run(host=API_HOST, port=API_PORT, debug=False)
