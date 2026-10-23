# Reponses - Binome B (FRENDI Belkacem)

## Q4. Quel risque presente un conteneur execute en root ?

Par defaut, un processus qui tourne en root *dans* un conteneur a tous les droits a
l'interieur de ce conteneur (lecture/ecriture sur tous les fichiers, installation de paquets,
modification de la configuration...). Le vrai risque, c'est ce qui se passe si un attaquant
reussit a executer du code dans ce conteneur (par une faille applicative, une dependance
vulnerable, etc.) : avec un process root, il part directement avec tous les droits root a
l'interieur du conteneur, ce qui facilite deux choses :

- il peut plus facilement modifier/corrompre l'application elle-meme (ecrire n'importe ou
  dans le systeme de fichiers du conteneur) ;
- si une mauvaise configuration ou une faille d'isolation existe par ailleurs (montage de
  `/var/run/docker.sock`, mauvaise config de capacites Linux, faille du moteur de conteneurs...),
  un process root dans le conteneur est l'etape la plus simple vers une sortie du conteneur
  (escalade vers root sur la machine hote), alors qu'un process non-root doit d'abord trouver
  un moyen d'elever ses privileges en plus de sortir du conteneur.

C'est pour ca que j'ai ajoute un utilisateur dedie (`appuser`, Dockerfile de l'API) et change
l'image nginx pour sa variante non-privilegiee (Partie 3) : meme si Trivy ne detecte toujours
les memes 44 CVE sur les paquets systeme (voir `SCAN_APRES_DURCISSEMENT.md`), si jamais une de
ces vulnerabilites (ou une future faille applicative) etait exploitee, l'attaquant n'obtient
que les droits d'un utilisateur limite, pas root.

## Q6. Que fait `--exit-code 1` et pourquoi l'utiliser en CI ?

Par defaut, Trivy se contente d'afficher les vulnerabilites trouvees et termine toujours avec
un code de sortie 0 (succes), meme s'il trouve des failles CRITICAL. L'option `--exit-code 1`
(traduite en `exit-code: '1'` dans l'action `aquasecurity/trivy-action` du workflow
`security-scan.yml`) dit a Trivy de terminer avec le code 1 (echec) s'il trouve au moins une
vulnerabilite correspondant au filtre de severite demande (ici `HIGH,CRITICAL`).

C'est important en CI parce qu'un "job" GitHub Actions n'est marque en echec (rouge) que si
une de ses commandes termine avec un code de sortie different de 0. Sans `--exit-code 1`, le
scan Trivy afficherait bien les vulnerabilites dans les logs, mais le job passerait quand meme
au vert : personne ne serait vraiment alerte, et rien n'empecherait de fusionner une image
vulnerable. Avec `--exit-code 1`, une image contenant une vulnerabilite HIGH ou CRITICAL fait
echouer le job automatiquement, ce qui bloque concretement la suite du pipeline (et donc, en
pratique, la fusion/le deploiement) jusqu'a ce que le probleme soit traite ou juge acceptable.

## Q8. Quels risques peuvent subsister apres la mise a jour des dependances ?

Mettre a jour les dependances (ici, `flask==3.0.3` -> `flask==3.1.1` dans
`api/requirements.txt`) ne protege que contre les vulnerabilites **connues au moment de la
mise a jour** sur **ces dependances precises**. Plusieurs risques subsistent quand meme :

- **Les vulnerabilites des paquets systeme de l'image de base ne sont pas touchees.** C'est
  exactement ce que montre mon re-scan (`SCAN_APRES_DURCISSEMENT.md`) : apres avoir mis a jour
  Flask, Trivy trouve toujours les 44 memes vulnerabilites HIGH, parce qu'elles viennent de
  paquets Debian (util-linux, ncurses, systemd...) de l'image `python:3.12-slim`, pas de Flask.
  Mettre a jour une dependance applicative ne met pas a jour le systeme sous-jacent.
- **De nouvelles CVE peuvent etre decouvertes plus tard** sur la version mise a jour
  elle-meme (comme sur n'importe quelle version) : une dependance "a jour" aujourd'hui n'est
  "a jour" qu'au regard de ce qui est connu aujourd'hui (meme raisonnement que la reponse de
  Binome A a Q7 sur une image "sans CVE detectee").
- **Une mise a jour de version peut introduire un nouveau bug ou une regression** qui n'a
  rien a voir avec la securite directement, mais qui peut quand meme affecter la fiabilite du
  service (raison de plus pour re-tester apres chaque mise a jour, comme je l'ai fait avec les
  verifications fonctionnelles dans `SCAN_APRES_DURCISSEMENT.md`).
- **Les vulnerabilites de configuration ou de code ne sont pas corrigees par une mise a jour
  de dependance** : par exemple, si l'application tournait en root ou avait une mauvaise
  gestion des entrees utilisateur, mettre Flask a jour ne change rien a ca (c'est pour ca que
  la Partie 3 combine plusieurs mesures : non-root, filesystem en lecture seule, capacites
  reduites, *et* mise a jour de dependance, plutot que de se reposer sur une seule mesure).

C'est pour ca qu'il faut re-scanner regulierement (le but de la Partie 4 / `security-scan.yml`)
plutot que de considerer qu'une mise a jour ponctuelle "regle" definitivement la securite de
l'image.
