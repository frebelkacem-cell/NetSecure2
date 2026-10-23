# Coordination binome A / binome B - TP3 NetSecure

Salut Binome B,

Le projet "NetSecure" n'existait pas encore avant ce TP, donc j'ai du poser les bases
(infra minimale) avant de pouvoir commencer la Partie 1 et la Partie 2. Voila ou j'en suis.

## Ce que j'ai fait (Binome A)

- Architecture minimale : une API Flask (`api/`) avec un endpoint `/health` et un endpoint
  `/check?host=...&port=...` qui teste si un port est ouvert.
- Un reverse proxy NGINX (`nginx/`) devant l'API.
- Un `compose.yaml` avec deux reseaux :
  - `backend` (interne, marque `internal: true`) : seul moyen pour nginx de parler a l'api,
    pas joignable depuis la machine hote.
  - `frontend` : seul nginx y est expose sur l'hote (port 80).
- Partie 1 (reconnaissance) et Partie 2 (scan Trivy) : voir `SCAN_INITIAL.md`, resultats
  complets avec 3 CVE detaillees.
- Mes reponses a Q1, Q2, Q3, Q5, Q7 : voir `REPONSES_A.md`.

Tout ca est sur la branche `binome-a/infra-audit`, avec une Pull Request ouverte vers
`main` (je ne la fusionne pas moi-meme).

## Pour Binome B

Tu peux repartir directement de cette branche (ou attendre que la PR soit mergee, selon ce
qui est convenu avec le prof) pour faire :

- Partie 3 (durcissement de l'image / des conteneurs)
- Partie 4 (pipeline CI avec Trivy dans GitHub Actions)
- Questions Q4, Q6, Q8

Regarde `SCAN_INITIAL.md` pour savoir quelles vulnerabilites j'ai trouvees sur l'image de
l'API : ca devrait te servir de base pour ton durcissement (Partie 3).

## Blocages

Aucun blocage de mon cote pour l'instant. Si en avancant sur la Partie 3/4 tu as besoin de
quelque chose cote infra (ex: changer un Dockerfile, ajouter une variable d'env, etc.), tu
peux le faire directement dans ta PR et je regarderai en relecture.

## Note de Binome B (Partie 3/4 terminee, PR #2)

Durcissement applique (voir `SCAN_APRES_DURCISSEMENT.md` pour le detail) : utilisateur non-root
sur l'API, image nginx non-privilegiee, filesystem en lecture seule + tmpfs cibles, capacites
Linux reduites a zero, Flask mis a jour. Re-scan Trivy toujours a 44 HIGH / 0 CRITICAL : ce sont
les memes CVE que dans ton `SCAN_INITIAL.md` (paquets systeme Debian de l'image de base, sans
version corrigee disponible), donc aucune des mesures de durcissement applicatif ne pouvait les
faire disparaitre.

**Etat du pipeline CI (`.github/workflows/security-scan.yml`, PR #2)** : le job `scan` echoue
(`gh pr checks 2` -> fail), et c'est volontaire, pas un bug. Le workflow utilise
`exit-code: '1'` sur `aquasecurity/trivy-action`, donc toute image avec au moins une
vulnerabilite HIGH/CRITICAL fait echouer le job -- exactement ce que demande le sujet (Partie
4, point 8). Comme l'image API contient toujours les 44 CVE HIGH deja identifiees par Binome A
(paquets systeme sans patch disponible au moment du scan), le job echoue a chaque run, meme sur
l'image durcie. Logs complets : voir les runs lies a la PR #2
(`gh run view <id> --repo frebelkacem-cell/NetSecure --log-failed`).
