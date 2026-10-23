# Scan initial - image API (Binome A)

## Partie 1 - Reconnaissance de l'infrastructure

Commandes utilisees :

```
docker compose up -d --build
docker compose ps
docker network ls
docker compose config
```

### Services declares dans compose.yaml

- `api` : construite depuis `./api`, branchee uniquement sur le reseau `backend`, **pas de
  section `ports`** -> pas de port publie sur l'hote.
- `nginx` : image `nginx:alpine`, branchee sur `backend` ET `frontend`, publie `80:80` sur
  l'hote. Fait reverse proxy vers `http://api:5000` (resolution DNS interne a Docker, via le
  nom du service).

### Volumes et variables d'environnement

`docker compose config` ne montre aucune section `volumes:` ni `environment:` a ce stade : ni
`api` ni `nginx` ne declarent de volume monte, et aucune variable d'environnement n'est
definie (ni dans `compose.yaml`, ni dans les `Dockerfile`). Rien a signaler de ce cote pour
cette reconnaissance initiale.

### Reseaux

`docker network ls` montre deux reseaux crees par compose, en plus des reseaux par defaut :

```
netsecure-binomea_backend    bridge    local
netsecure-binomea_frontend   bridge    local
```

`docker compose config` confirme que le reseau `backend` est declare avec `internal: true`,
donc les conteneurs qui y sont connectes ne peuvent PAS etre joints depuis l'exterieur de
Docker (ni depuis la machine hote), seulement entre eux.

### Ce qui est joignable depuis l'hote

`docker compose ps` :

```
netsecure-binomea-api-1     ...   5000/tcp              (pas de mapping host -> container)
netsecure-binomea-nginx-1   ...   0.0.0.0:80->80/tcp
```

Seul `nginx` publie un port sur l'hote (80). L'API n'en publie aucun : elle expose juste le
port 5000 a l'interieur du reseau Docker, mais ce n'est pas la meme chose que publier le port
sur l'hote (voir reponse Q2 dans `REPONSES.md`).

Verification concrete :

```
curl http://localhost:80/health          -> {"status":"ok"}   (200, via nginx)
curl http://localhost:5000/health        -> echec de connexion (l'API n'est pas joignable
                                             directement depuis l'hote, comme prevu)
```

### Base de donnees

Il n'y a pas de base de donnees dans ce projet (voir la section "TA MISSION" du sujet : on
construit une architecture minimale API + NGINX, sans base). Ce n'est donc pas un probleme ici
puisqu'il n'y a simplement pas de service supplementaire susceptible d'exposer un port
inutilement. Si une base de donnees etait ajoutee plus tard (par exemple par Binome B), il
faudrait la mettre uniquement sur le reseau `backend`, sans section `ports`, exactement comme
pour l'API.

## Partie 2 - Scan Trivy de l'image Docker

Image scannee : `netsecure-binomea-api:latest` (construite par `docker compose up --build`,
verifiee avec `docker images`).

Commande utilisee (sur Windows, avec Git Bash, en desactivant la conversion de chemin pour que
`/var/run/docker.sock` ne soit pas reecrit en chemin Windows) :

```
MSYS_NO_PATHCONV=1 docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL netsecure-binomea-api:latest
```

Resultat global : **44 vulnerabilites detectees, toutes de severite HIGH, 0 CRITICAL.**
Elles viennent toutes de paquets systeme Debian (l'image de base `python:3.12-slim` est basee
sur Debian 13), pas du code de l'application ni des dependances Python (flask, werkzeug,
jinja2, etc. remontent "Clean" / "0" dans le scan).

Trois resultats significatifs :

1. **util-linux (et les paquets lies : bsdutils, libblkid1, libmount1, libuuid1, mount, ...)**
   - CVE : CVE-2026-76642
   - Severite : HIGH
   - Version installee : 2.41.5-0+deb13u1
   - Version corrigee disponible : aucune au moment du scan (colonne "Fixed Version" vide,
     statut "affected")
   - Resume : un helper de montage externe qui echoue continue quand meme a executer des
     "post-hooks" privilegies lies au montage.

2. **libncursesw6 / libtinfo6 / ncurses-base (ncurses)**
   - CVE : CVE-2025-69720
   - Severite : HIGH
   - Version installee : 6.5+20250216-2
   - Version corrigee disponible : aucune au moment du scan
   - Resume : vulnerabilite de depassement de tampon ("buffer overflow") qui pourrait mener
     a de l'execution de code arbitraire.

3. **libsystemd0 / libudev1 (systemd)**
   - CVE : CVE-2026-16742
   - Severite : HIGH
   - Version installee : 257.13-1~deb13u1
   - Version corrigee disponible : aucune au moment du scan
   - Resume : escalade de privileges locale via `systemd-homed`, a cause d'une verification de
     signature manquante sur un "home-record".

Aucune de ces vulnerabilites n'a de "Fixed Version" indiquee par Trivy au moment du scan : ce
sont des paquets systeme de l'image de base, pas des dependances que je controle directement
dans `requirements.txt`. Pour Binome B (Partie 3, durcissement), des pistes evidentes a partir
de ce constat : reduire la surface en utilisant une image de base plus minimale (`-slim` est
deja un bon point de depart, une image "distroless" irait plus loin), ne pas tourner en root
dans le conteneur, et re-scanner apres chaque changement pour voir si ca a reellement reduit le
compte de vulnerabilites.
