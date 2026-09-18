# MiniHub — Environnement cible factice (bac à sable Red/Blue Team)

Application volontairement vulnérable, inspirée de Hugging Face, utilisé comme bac à sable et non exposé sur internet.

## Démarrage rapide

```bash
docker compose up --build
```

L'application est alors disponible sur http://127.0.0.1:5000 (uniquement
en local, jamais accessible depuis l'extérieur grâce au binding
`127.0.0.1:5000:5000` dans docker-compose.yml).

Comptes de démo :
- `admin` / `password` (rôle admin)
- `alice` / `alice2024` (rôle user)

## Les 3 vulnérabilités volontaires

| ID | Où | Description | Miroir de l'incident réel |
|---|---|---|---|
| VULN-01 | `POST /upload` | Aucune validation du fichier envoyé | Upload de modèle/dataset malveillant sur un hub |
| VULN-02 | `/login`, `/admin/users` | Identifiants faibles + mot de passe en clair | Détournement de comptes utilisateurs |
| VULN-03 | `GET /internal/metadata` | Endpoint interne sans authentification | Vol d'identifiants via le service de métadonnées cloud |


## Logs

Chaque requête est journalisée en JSON structuré dans `app/logs/access.log`.
C'est ce fichier que l'agent Blue Team devra lire pour détecter les
comportements anormaux (ex : accès à `/internal/metadata` sans session,
uploads en rafale, tentatives de login répétées).

## Sécurité de la démo

- Ne jamais changer `127.0.0.1:5000:5000` en `0.0.0.0:5000:5000` dans
  `docker-compose.yml` sauf si réseau totalement isolé
  et contrôlé.
- Ne jamais réutiliser ce code, ces mots de passe ou cette clé de session
  en dehors de ce hackathon.
- Toutes les données (clés, secrets, credentials) sont fausses (`FAKE-...`)
  et générées uniquement pour la démo.
