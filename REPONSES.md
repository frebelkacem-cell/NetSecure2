# Réponses aux questions d'analyse (TP3)

## Q1. Quelle différence entre scanner le code source et scanner une image Docker ?

Scanner le code source (par exemple avec Bandit, comme dans le TP2), c'est analyser le code
écrit soi-même (ici, `api/app.py`) pour trouver des erreurs de sécurité dans sa propre
logique : injection, mauvaise gestion des entrées utilisateur, usage dangereux d'une fonction,
etc. Ça ne regarde que les fichiers Python du projet.

Scanner une image Docker (avec Trivy), c'est regarder tout ce qui compose l'image finale une
fois construite : le système Debian de base (`python:3.12-slim`), tous les paquets système
installés avec lui, et les dépendances Python installées via `requirements.txt`. Dans ce scan,
les 44 vulnérabilités trouvées viennent toutes de paquets système Debian (util-linux, ncurses,
systemd...), pas du code applicatif ni de Flask. Autrement dit : le scan de code vérifie ce qui
a été écrit, le scan d'image vérifie tout ce sur quoi ce code tourne.

## Q2. Quelle est la différence entre un port exposé et un port publié sur l'hôte ?

Un port **exposé** (mot-clé `EXPOSE` dans le Dockerfile, ou juste le fait qu'un serveur écoute
sur un port à l'intérieur du conteneur) ne fait qu'indiquer/documenter sur quel port le service
écoute à l'intérieur du conteneur. Les autres conteneurs sur le même réseau Docker peuvent s'y
connecter via ce port (c'est comme ça que `nginx` parle à `api:5000`), mais ce n'est PAS
accessible depuis la machine hôte.

Un port **publié** (`ports:` dans `compose.yaml`, ou `-p` avec `docker run`) crée en plus un
mapping depuis un port de la machine hôte vers le port du conteneur. C'est ce qui rend le
service joignable depuis l'extérieur de Docker.

Dans ce `compose.yaml` : `nginx` publie `80:80` (joignable depuis l'hôte sur le port 80),
alors que `api` n'a pas de section `ports` du tout : elle écoute sur 5000 à l'intérieur du
réseau Docker, mais ce port n'est jamais mappé sur l'hôte. Vérifié avec
`curl http://localhost:5000/health`, qui échoue (connexion refusée), alors que
`curl http://localhost:80/health` (via nginx) répond `{"status":"ok"}`.

## Q3. Pourquoi isoler une base de données sur le réseau backend ?

Une base de données contient en général les données les plus sensibles de l'application
(comptes utilisateurs, mots de passe hashés, données métier...). Si elle était accessible
directement depuis l'hôte (ou pire, depuis Internet si la machine est un serveur), n'importe
qui pourrait essayer de s'y connecter directement et tenter de la casser (brute-force,
exploitation d'une CVE connue sur le moteur de base de données, etc.), en contournant
complètement l'application et sa logique de sécurité (authentification, validation des
entrées...).

En la mettant uniquement sur un réseau Docker interne (`backend`, avec `internal: true`), on
applique le principe du moindre privilège : seuls les conteneurs qui ont vraiment besoin de lui
parler (ici, l'API) peuvent la joindre, et elle reste totalement invisible depuis l'extérieur.
Même chose pour l'API dans cette architecture : elle n'a aucune raison d'être joignable
directement depuis l'hôte, seul nginx (qui fait l'authentification/le filtrage en frontal) doit
pouvoir lui parler.

## Q4. Quel risque présente un conteneur exécuté en root ?

Par défaut, un processus qui tourne en root *dans* un conteneur a tous les droits à
l'intérieur de ce conteneur (lecture/écriture sur tous les fichiers, installation de paquets,
modification de la configuration...). Le vrai risque, c'est ce qui se passe si un attaquant
réussit à exécuter du code dans ce conteneur (par une faille applicative, une dépendance
vulnérable, etc.) : avec un process root, il part directement avec tous les droits root à
l'intérieur du conteneur, ce qui facilite deux choses :

- il peut plus facilement modifier/corrompre l'application elle-même (écrire n'importe où
  dans le système de fichiers du conteneur) ;
- si une mauvaise configuration ou une faille d'isolation existe par ailleurs (montage de
  `/var/run/docker.sock`, mauvaise config de capacités Linux, faille du moteur de conteneurs...),
  un process root dans le conteneur est l'étape la plus simple vers une sortie du conteneur
  (escalade vers root sur la machine hôte), alors qu'un process non-root doit d'abord trouver
  un moyen d'élever ses privilèges en plus de sortir du conteneur.

C'est pour ça qu'un utilisateur dédié (`appuser`, Dockerfile de l'API) a été ajouté, et l'image
nginx changée pour sa variante non-privilégiée (Partie 3) : même si Trivy détecte toujours les
mêmes 44 CVE sur les paquets système (voir `SCAN_APRES_DURCISSEMENT.md`), si jamais une de ces
vulnérabilités (ou une future faille applicative) était exploitée, l'attaquant n'obtient que
les droits d'un utilisateur limité, pas root.

## Q5. Que signifient HIGH, CRITICAL, CVE et version corrigée ?

- **CVE** (Common Vulnerabilities and Exposures) : un identifiant unique attribué à une
  vulnérabilité de sécurité connue et publique (ex: `CVE-2026-76642`), pour pouvoir la
  référencer de manière non ambiguë entre outils, bases de données et rapports.
- **HIGH** / **CRITICAL** : des niveaux de sévérité (il y a aussi LOW et MEDIUM) qui indiquent
  à quel point une vulnérabilité est dangereuse si elle est exploitée : CRITICAL = impact très
  grave et/ou très facile à exploiter (souvent exécution de code à distance sans
  authentification) ; HIGH = impact sérieux mais généralement un peu plus de conditions ou de
  prérequis nécessaires pour l'exploiter (par exemple, dans ce scan, plusieurs CVE HIGH
  demandent un accès local ou des privilèges déjà partiels).
- **Version corrigée** ("Fixed Version") : la version du paquet/de la bibliothèque dans
  laquelle le problème a été réglé par les mainteneurs. Si elle est disponible, il suffit en
  général de mettre à jour vers cette version (ou une version plus récente) pour ne plus être
  vulnérable. Dans ce scan, aucune des 44 vulnérabilités n'a de version corrigée listée pour
  l'instant : ce sont des CVE récentes sur des paquets système Debian, pas encore patchées au
  moment du scan.

## Q6. Que fait `--exit-code 1` et pourquoi l'utiliser en CI ?

Par défaut, Trivy se contente d'afficher les vulnérabilités trouvées et termine toujours avec
un code de sortie 0 (succès), même s'il trouve des failles CRITICAL. L'option `--exit-code 1`
(traduite en `exit-code: '1'` dans l'action `aquasecurity/trivy-action` du workflow
`security-scan.yml`) dit à Trivy de terminer avec le code 1 (échec) s'il trouve au moins une
vulnérabilité correspondant au filtre de sévérité demandé (ici `HIGH,CRITICAL`).

C'est important en CI parce qu'un "job" GitHub Actions n'est marqué en échec (rouge) que si
une de ses commandes termine avec un code de sortie différent de 0. Sans `--exit-code 1`, le
scan Trivy afficherait bien les vulnérabilités dans les logs, mais le job passerait quand même
au vert : personne ne serait vraiment alerté, et rien n'empêcherait de fusionner une image
vulnérable. Avec `--exit-code 1`, une image contenant une vulnérabilité HIGH ou CRITICAL fait
échouer le job automatiquement, ce qui bloque concrètement la suite du pipeline (et donc, en
pratique, la fusion/le déploiement) jusqu'à ce que le problème soit traité ou jugé acceptable.

## Q7. Pourquoi une image sans CVE détectée n'est-elle pas nécessairement sûre ?

Parce que Trivy (comme tout scanner de ce type) ne détecte que les vulnérabilités **connues et
déjà publiées** dans ses bases de données (CVE, bases de distributions Linux, etc.), à
l'instant où le scan est lancé. Une image "sans CVE détectée" peut quand même avoir :

- des vulnérabilités **pas encore découvertes ou pas encore publiées** (0-day) ;
- des **erreurs de configuration ou de code** qui ne sont pas des CVE à proprement parler
  (par exemple, le scan Trivy ne dirait rien si le paramètre `port` dans `/check` n'était pas
  validé et laissait une faille d'injection, ou si le conteneur tournait en root) ;
- de **nouvelles CVE découvertes plus tard** sur des paquets déjà présents dans l'image : une
  image "propre" aujourd'hui peut devenir vulnérable demain sans qu'un seul octet de l'image
  n'ait changé, simplement parce qu'une vulnérabilité existante vient d'être rendue publique.

Donc "0 vulnérabilité détectée" veut dire "rien de connu trouvé au moment du scan", pas
"prouvé totalement sans danger". C'est pour ça qu'il faut re-scanner régulièrement (par
exemple à chaque build, dans le pipeline CI de la Partie 4) plutôt que de scanner une fois et
considérer le sujet clos.

## Q8. Quels risques peuvent subsister après la mise à jour des dépendances ?

Mettre à jour les dépendances (ici, `flask==3.0.3` → `flask==3.1.1` dans
`api/requirements.txt`) ne protège que contre les vulnérabilités **connues au moment de la
mise à jour** sur **ces dépendances précises**. Plusieurs risques subsistent quand même :

- **Les vulnérabilités des paquets système de l'image de base ne sont pas touchées.** C'est
  exactement ce que montre le re-scan (`SCAN_APRES_DURCISSEMENT.md`) : après avoir mis à jour
  Flask, Trivy trouve toujours les 44 mêmes vulnérabilités HIGH, parce qu'elles viennent de
  paquets Debian (util-linux, ncurses, systemd...) de l'image `python:3.12-slim`, pas de Flask.
  Mettre à jour une dépendance applicative ne met pas à jour le système sous-jacent.
- **De nouvelles CVE peuvent être découvertes plus tard** sur la version mise à jour
  elle-même (comme sur n'importe quelle version) : une dépendance "à jour" aujourd'hui n'est
  "à jour" qu'au regard de ce qui est connu aujourd'hui (même raisonnement qu'en Q7 sur une
  image "sans CVE détectée").
- **Une mise à jour de version peut introduire un nouveau bug ou une régression** qui n'a
  rien à voir avec la sécurité directement, mais qui peut quand même affecter la fiabilité du
  service (raison de plus pour re-tester après chaque mise à jour, comme fait dans les
  vérifications fonctionnelles de `SCAN_APRES_DURCISSEMENT.md`).
- **Les vulnérabilités de configuration ou de code ne sont pas corrigées par une mise à jour
  de dépendance** : par exemple, si l'application tournait en root ou avait une mauvaise
  gestion des entrées utilisateur, mettre Flask à jour ne change rien à ça (c'est pour ça que
  la Partie 3 combine plusieurs mesures : non-root, filesystem en lecture seule, capacités
  réduites, *et* mise à jour de dépendance, plutôt que de se reposer sur une seule mesure).

C'est pour ça qu'il faut re-scanner régulièrement (le but de la Partie 4 / `security-scan.yml`)
plutôt que de considérer qu'une mise à jour ponctuelle "règle" définitivement la sécurité de
l'image.
