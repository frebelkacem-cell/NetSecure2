# NetSecure

Plateforme de supervision réseau minimale : une API Flask de vérification de port, exposée
derrière un reverse proxy NGINX, le tout orchestré avec Docker Compose. Projet réalisé dans le
cadre du TP3 ISRC5 DevSecOps ("NetSecure : audit de sécurité Docker avec Trivy"), en binôme.

## Architecture

- **`api/`** — API Flask (`/health`, `/check?host=&port=`), conteneurisée avec un utilisateur
  non-root dédié.
- **`nginx/`** — reverse proxy NGINX (image non-privilégiée), seul service publié sur l'hôte
  (port 80).
- **`compose.yaml`** — deux réseaux Docker : `backend` (interne, non joignable depuis l'hôte,
  pour la communication nginx ↔ api) et `frontend` (où seul nginx est exposé).
- **`.github/workflows/security-scan.yml`** — pipeline CI qui construit l'image de l'API et la
  scanne avec Trivy (`aquasecurity/trivy-action`), en échec volontaire si une CVE HIGH/CRITICAL
  est détectée.

Lancer le projet en local :

```bash
docker compose up -d --build
curl http://localhost/health
```

## Répartition du travail (binôme)

Pour ce TP, le travail a été réparti en deux parties, Binôme A et Binôme B, avec un commit et
un push distincts pour chacune.

- **Binôme A** — a posé l'architecture (API, NGINX, réseaux), fait la reconnaissance de
  l'infrastructure et le premier scan de sécurité. Détails : [`SCAN_INITIAL.md`](SCAN_INITIAL.md),
  réponses aux questions 1/2/3/5/7 dans [`REPONSES_A.md`](REPONSES_A.md).
- **Binôme B** — a repris ce travail pour appliquer le durcissement (utilisateur non-root,
  système de fichiers en lecture seule, capacités Linux limitées...) et construire le pipeline
  CI de scan automatique. Détails : [`SCAN_APRES_DURCISSEMENT.md`](SCAN_APRES_DURCISSEMENT.md),
  réponses aux questions 4/6/8 dans [`REPONSES_B.md`](REPONSES_B.md).

Ce README reprend le rapport combiné de l'ensemble du travail réalisé pour ce TP.

## Résultat du scan de sécurité

44 vulnérabilités HIGH (0 CRITICAL) détectées, toutes sur des paquets système de l'image de
base (`python:3.12-slim` / Debian), sans version corrigée disponible au moment du scan — donc
inchangées avant/après durcissement. Le durcissement appliqué réduit ce qu'un attaquant pourrait
faire en cas d'exploitation (defense in depth), pas le nombre de CVE connues : voir le détail
dans les fichiers `SCAN_*.md` ci-dessus.
