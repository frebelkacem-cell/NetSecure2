# Scan apres durcissement - image API (Binome B)

## Partie 3 - Mesures de durcissement appliquees

A partir de ce que Binome A a documente dans `SCAN_INITIAL.md` (44 vulnerabilites HIGH, toutes
sur des paquets systeme Debian de l'image de base, pas sur le code ni sur Flask), j'ai applique
quatre mesures de durcissement :

1. **Utilisateur non-root pour l'API** (`api/Dockerfile`) : creation d'un utilisateur dedie
   `appuser` (sans shell de connexion), `chown` du repertoire `/app`, et `USER appuser` avant
   le `CMD`. Le process Python ne tourne donc plus en root dans le conteneur.

2. **Image NGINX non-privilegiee** (`compose.yaml`, `nginx/nginx.conf`) : remplacement de
   `nginx:alpine` (qui demarre en root) par l'image officielle
   `nginxinc/nginx-unprivileged:1.27-alpine`, qui fait tourner master et workers entierement en
   non-root (uid 101) et ecoute sur le port non privilegie 8080 a l'interieur du conteneur.
   `compose.yaml` publie toujours le port 80 sur l'hote (`"80:8080"`), donc aucun changement
   cote utilisateur de l'API.

3. **Systeme de fichiers racine en lecture seule + capacites Linux reduites au minimum**
   (`compose.yaml`, les deux services) : `read_only: true` sur `api` et `nginx`, avec des
   montages `tmpfs` uniquement pour les repertoires qui doivent rester inscriptibles en usage
   normal (`/tmp` pour l'API ; `/tmp`, `/var/cache/nginx`, `/var/run` pour nginx). `cap_drop:
   [ALL]` et `security_opt: [no-new-privileges:true]` sur les deux services : aucun des deux
   conteneurs n'a besoin d'une capacite Linux particuliere (grace a l'image nginx non-
   privilegiee, pas meme besoin de `CAP_NET_BIND_SERVICE` pour le port 80).

4. **Mise a jour de dependance** (`api/requirements.txt`) : `flask==3.0.3` -> `flask==3.1.1`
   (et ses dependances associees, werkzeug/jinja2/click/..., remontees automatiquement a jour
   par pip). Bonne pratique independante du resultat du scan : rester sur une version
   maintenue plutot que de se figer sur une version plus ancienne.

Aucun port supplementaire n'a ete ouvert ni de secret ajoute : l'architecture reseau de
Binome A (API isolee sur `backend` interne sans `ports:`, seul nginx expose sur l'hote) est
inchangee et reste valide apres durcissement.

### Verification fonctionnelle apres durcissement

```
docker compose up -d --build
docker compose ps
```

```
NAME                        STATUS         PORTS
netsecure-binomeb-api-1     Up             5000/tcp
netsecure-binomeb-nginx-1   Up             0.0.0.0:80->8080/tcp
```

```
curl http://localhost:80/health                      -> {"status":"ok"}  (200, via nginx)
curl "http://localhost:80/check?host=api&port=5000"   -> {"host":"api","open":true,"port":5000}
curl http://localhost:5000/health                     -> echec (API toujours non joignable
                                                          directement depuis l'hote, comme avant)
docker compose exec api whoami    -> appuser (uid 999)
docker compose exec nginx whoami  -> nginx (uid 101)
docker compose exec api sh -c "touch /app/test"  -> "Read-only file system" (attendu)
```

Le service fonctionne exactement comme avant le durcissement : aucune regression.

## Partie 3bis - Re-scan Trivy de l'image API durcie

Meme commande que Binome A, sur la nouvelle image (`netsecure-binomeb-api:latest`, reconstruite
avec le Dockerfile durci) :

```
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image --severity HIGH,CRITICAL netsecure-binomeb-api:latest
```

### Resultat : 44 vulnerabilites HIGH, 0 CRITICAL (identique a avant)

Les memes paquets sont remontes (util-linux et paquets lies, ncurses, systemd...), avec les
memes CVE (CVE-2026-76642, CVE-2025-69720, CVE-2026-16742, et les CVE util-linux
supplementaires CVE-2026-78408/78409/78410 visibles sur ce re-scan). Les paquets Python
(flask 3.1.1, werkzeug, jinja2...) restent "Clean" (0 vulnerabilite), comme avec flask 3.0.3.

### Pourquoi le compte de vulnerabilites n'a pas baisse

Aucune des quatre mesures de durcissement appliquees ne change les paquets systeme installes
dans l'image : on utilise toujours la meme image de base `python:3.12-slim` (Debian 13), donc
les memes paquets Debian (util-linux, ncurses, systemd...) avec les memes versions y sont
installes, et ce sont eux qui portent la totalite des 44 CVE HIGH. Ajouter un utilisateur non-
root, passer le filesystem en lecture seule, retirer les capacites Linux ou mettre a jour
Flask ne desinstalle aucun paquet systeme : Trivy continue donc de les detecter a l'identique.

Ces mesures ne reduisent pas le nombre de CVE connues dans l'image, mais reduisent ce qu'un
attaquant pourrait faire s'il parvenait malgre tout a executer du code dans le conteneur
(defense en profondeur) : pas de droits root a escalader, pas d'ecriture possible sur le
systeme de fichiers hors `/tmp`, et aucune capacite Linux a exploiter. Pour reellement faire
baisser le compte de CVE sur les paquets systeme, il faudrait changer d'image de base (ex :
une variante "distroless" ou une image plus minimale que `-slim`), ce qui sort du cadre des
mesures demandees pour ce TP (voir aussi `REPONSES.md`, Q8).
