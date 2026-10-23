# Reponses - Binome A (FRENDI Belkacem)

## Q1. Quelle difference entre scanner le code source et scanner une image Docker ?

Scanner le code source (par exemple avec Bandit, comme dans le TP2), c'est analyser le code
que j'ai ecrit moi-meme (ici, `api/app.py`) pour trouver des erreurs de securite dans ma propre
logique : injection, mauvaise gestion des entrees utilisateur, usage dangereux d'une fonction,
etc. Ca ne regarde que mes fichiers Python.

Scanner une image Docker (avec Trivy), c'est regarder tout ce qui compose l'image finale une
fois construite : le systeme Debian de base (`python:3.12-slim`), tous les paquets systeme
installes avec lui, et les dependances Python installees via `requirements.txt`. Dans mon scan,
les 44 vulnerabilites trouvees viennent toutes de paquets systeme Debian (util-linux, ncurses,
systemd...), pas de mon code ni de Flask. Autrement dit : le scan de code verifie ce que j'ai
ecrit, le scan d'image verifie tout ce sur quoi mon code tourne.

## Q2. Quelle est la difference entre un port expose et un port publie sur l'hote ?

Un port **expose** (mot-cle `EXPOSE` dans le Dockerfile, ou juste le fait qu'un serveur ecoute
sur un port a l'interieur du conteneur) ne fait qu'indiquer/documenter sur quel port le service
ecoute a l'interieur du conteneur. Les autres conteneurs sur le meme reseau Docker peuvent s'y
connecter via ce port (c'est comme ca que `nginx` parle a `api:5000`), mais ce n'est PAS
accessible depuis la machine hote.

Un port **publie** (`ports:` dans `compose.yaml`, ou `-p` avec `docker run`) cree en plus un
mapping depuis un port de la machine hote vers le port du conteneur. C'est ce qui rend le
service joignable depuis l'exterieur de Docker.

Dans mon `compose.yaml` : `nginx` publie `80:80` (joignable depuis l'hote sur le port 80),
alors que `api` n'a pas de section `ports` du tout : elle ecoute sur 5000 a l'interieur du
reseau Docker, mais ce port n'est jamais mappe sur l'hote. Je l'ai verifie avec
`curl http://localhost:5000/health`, qui echoue (connexion refusee), alors que
`curl http://localhost:80/health` (via nginx) repond `{"status":"ok"}`.

## Q3. Pourquoi isoler une base de donnees sur le reseau backend ?

Une base de donnees contient en general les donnees les plus sensibles de l'application
(comptes utilisateurs, mots de passe hashes, donnees metier...). Si elle etait accessible
directement depuis l'hote (ou pire, depuis Internet si la machine est un serveur), n'importe
qui pourrait essayer de s'y connecter directement et tenter de la casser (brute-force,
exploitation d'une CVE connue sur le moteur de base de donnees, etc.), en contournant
completement l'application et sa logique de securite (authentification, validation des
entrees...).

En la mettant uniquement sur un reseau Docker interne (`backend`, avec `internal: true`), on
applique le principe du moindre privilege : seuls les conteneurs qui ont vraiment besoin de lui
parler (ici, l'API) peuvent la joindre, et elle reste totalement invisible depuis l'exterieur.
Meme chose pour l'API dans mon architecture : elle n'a aucune raison d'etre joignable
directement depuis l'hote, seul nginx (qui fait l'authentification/le filtrage en frontal) doit
pouvoir lui parler.

## Q5. Que signifient HIGH, CRITICAL, CVE et version corrigee ?

- **CVE** (Common Vulnerabilities and Exposures) : un identifiant unique attribue a une
  vulnerabilite de securite connue et publique (ex: `CVE-2026-76642`), pour pouvoir la
  reference de maniere non ambigue entre outils, bases de donnees et rapports.
- **HIGH** / **CRITICAL** : des niveaux de severite (il y a aussi LOW et MEDIUM) qui indiquent
  a quel point une vulnerabilite est dangereuse si elle est exploitee : CRITICAL = impact tres
  grave et/ou tres facile a exploiter (souvent execution de code a distance sans
  authentification) ; HIGH = impact serieux mais generalement un peu plus de conditions ou de
  prerequis necessaires pour l'exploiter (par exemple, dans mon scan, plusieurs CVE HIGH
  demandent un acces local ou des privileges deja partiels).
- **Version corrigee** ("Fixed Version") : la version du paquet/de la bibliotheque dans
  laquelle le probleme a ete reglé par les mainteneurs. Si elle est disponible, il suffit en
  general de mettre a jour vers cette version (ou une version plus recente) pour ne plus etre
  vulnerable. Dans mon scan, aucune des 44 vulnerabilites n'a de version corrigee listee pour
  l'instant : ce sont des CVE recentes sur des paquets systeme Debian, pas encore patchees au
  moment du scan.

## Q7. Pourquoi une image sans CVE detectee n'est-elle pas necessairement sure ?

Parce que Trivy (comme tout scanner de ce type) ne detecte que les vulnerabilites **connues et
deja publiees** dans ses bases de donnees (CVE, bases de distributions Linux, etc.), a
l'instant ou le scan est lance. Une image "sans CVE detectee" peut quand meme avoir :

- des vulnerabilites **pas encore decouvertes ou pas encore publiees** (0-day) ;
- des **erreurs de configuration ou de code** qui ne sont pas des CVE a proprement parler
  (par exemple, dans mon cas, le scan Trivy ne me dirait rien si j'avais oublie de valider le
  parametre `port` dans `/check` et laisse une faille d'injection, ou si j'avais fait tourner
  le conteneur en root) ;
- de **nouvelles CVE decouvertes plus tard** sur des paquets deja presents dans l'image : une
  image "propre" aujourd'hui peut devenir vulnerable demain sans qu'un seul octet de l'image
  n'ait change, simplement parce qu'une vulnerabilite existante vient d'etre rendue publique.

Donc "0 vulnerabilite detectee" veut dire "rien de connu trouve au moment du scan", pas
"prouve totalement sans danger". C'est pour ca qu'il faut re-scanner regulierement (par
exemple a chaque build, dans le pipeline CI de la Partie 4) plutot que de scanner une fois et
considerer le sujet clos.
