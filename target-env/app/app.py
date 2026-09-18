"""
MiniHub - Plateforme factice inspirée de Hugging Face
=======================================================
Application VOLONTAIREMENT VULNERABLE, construite POUR CE HACKATHON
UNIQUEMENT, afin de servir de bac a sable au duel Red Team / Blue Team.

ATTENTION :
- Ne JAMAIS exposer ce service sur Internet en dehors d'un environnement
  de demo controle (reseau Docker isole / VM sans IP publique ouverte).
- Toutes les "cles" et "secrets" presents dans ce code sont FAKE et
  generes uniquement pour la demo.

Vulnerabilites volontairement introduites (a des fins pedagogiques,
inspirees de classes de vulnerabilites reelles documentees sur les
plateformes d'hebergement de modeles et dans le rapport d'incident
OpenAI x Hugging Face) :

  1. Upload de fichier sans validation                    -> VULN-01
     (miroir du vecteur "modele/dataset malveillant uploade")
  2. Endpoint de metadonnees interne non authentifie       -> VULN-02
     (miroir du vol d'identifiants cloud via le service de
      metadonnees d'instance, decrit dans l'incident reel)
  3. Compte admin avec identifiants faibles + mot de passe
     stocke en clair                                       -> VULN-03
     (miroir du detournement de comptes utilisateurs)

Chaque requete est journalisee en JSON structure dans logs/access.log
pour etre consommee plus tard par l'agent Blue Team.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    render_template, send_from_directory, jsonify, abort
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "storage", "models")
LOG_DIR = os.path.join(BASE_DIR, "logs")
DB_FILE = os.path.join(BASE_DIR, "storage", "db.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__)
# VULN-03 (partie configuration) : cle de session faible et codee en dur.
# A NE JAMAIS faire en production - volontaire ici pour la demo.
app.secret_key = "dev-secret-key-do-not-use-in-prod"

# ---------------------------------------------------------------------
# "Base de donnees" ultra simplifiee (fichier JSON) pour rester leger
# ---------------------------------------------------------------------

def _default_db():
    return {
        "users": {
            # VULN-03 : mot de passe stocke EN CLAIR + identifiants faibles
            "admin": {"password": "admin123", "role": "admin"},
            "alice": {"password": "alice2024", "role": "user"},
        },
        "models": [
            {"name": "sentiment-analyzer-fr", "owner": "alice", "downloads": 128},
            {"name": "image-classifier-demo", "owner": "alice", "downloads": 54},
        ],
    }


def load_db():
    if not os.path.exists(DB_FILE):
        db = _default_db()
        save_db(db)
        return db
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


# ---------------------------------------------------------------------
# Journalisation structuree (fondation pour l'agent Blue Team)
# ---------------------------------------------------------------------

access_logger = logging.getLogger("minihub.access")
access_logger.setLevel(logging.INFO)
_handler = logging.FileHandler(os.path.join(LOG_DIR, "access.log"), encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(message)s"))
access_logger.addHandler(_handler)

print(f"[MiniHub] Les logs d'accès seront écrits dans : {os.path.join(LOG_DIR, 'access.log')}")


@app.before_request
def _start_timer():
    request._start_time = time.time()


@app.after_request
def _log_request(response):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ip": request.remote_addr,
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "user": session.get("user"),
        "duration_ms": round(
            (time.time() - getattr(request, "_start_time", time.time())) * 1000, 2
        ),
        "user_agent": request.headers.get("User-Agent", ""),
    }
    line = json.dumps(entry)
    access_logger.info(line)
    _handler.flush()
    # Debug : on affiche aussi dans la console, indépendamment du fichier,
    # pour vérifier immédiatement que les requêtes sont bien reçues même
    # si l'écriture du fichier posait problème.
    print(f"[MiniHub][access.log] {line}")
    return response


# ---------------------------------------------------------------------
# Auth minimaliste
# ---------------------------------------------------------------------

def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        db = load_db()
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = db["users"].get(username)
        if user and user["password"] == password:
            session["user"] = username
            session["role"] = user["role"]
            return redirect(url_for("index"))
        error = "Identifiants invalides."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------------------------------------------------------------------
# Pages principales
# ---------------------------------------------------------------------

@app.route("/")
def index():
    db = load_db()
    return render_template("index.html", models=db["models"], user=session.get("user"))


# VULN-01 : upload sans AUCUNE validation de type/contenu/taille
@app.route("/upload", methods=["GET", "POST"])
@login_required()
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            # Volontairement AUCUNE verification d'extension, de type
            # MIME ou de contenu -> vecteur d'upload de fichier malveillant
            dest = os.path.join(UPLOAD_DIR, file.filename)
            file.save(dest)

            db = load_db()
            db["models"].append({
                "name": file.filename,
                "owner": session["user"],
                "downloads": 0,
            })
            save_db(db)
            return redirect(url_for("index"))
    return render_template("upload.html")


@app.route("/models/<path:filename>")
def download_model(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# VULN-02 : endpoint "interne" cense n'etre accessible que par les
# services internes, mais expose SANS AUCUNE authentification.
# Miroir direct du service de metadonnees cloud detourne dans
# l'incident reel pour voler des identifiants.
@app.route("/internal/metadata")
def internal_metadata():
    return jsonify({
        "service": "minihub-internal",
        "cloud_credentials": {
            "access_key": "FAKE-AKIA-DEMO-1234567890",
            "secret_key": "FAKE-SECRET-DO-NOT-USE-abcdef0123456789",
        },
        "internal_api_token": "FAKE-INTERNAL-TOKEN-9f8e7d6c",
        "note": "Donnee FACTICE generee pour la demo hackathon.",
    })


# Zone admin (protegee, mais atteignable si VULN-02 ou VULN-03 exploitee)
@app.route("/admin/users")
@login_required(role="admin")
def admin_users():
    db = load_db()
    return render_template("admin_users.html", users=db["users"])


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
