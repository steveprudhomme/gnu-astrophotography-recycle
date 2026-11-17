# Installation et utilisation sur Windows 11

## Ce qui fonctionne aujourd’hui

L’Alpha 0.10 contient l’inventaire, le regroupement, les diagnostics, les copies vérifiées, les contrôles stellaires, la préparation temporelle et un prototype de mobiles sur données synthétiques. L’installation depuis le code source est disponible ; le paquet portable et les performances scientifiques sur mobiles réels restent à valider. Pour un premier atelier dès 10 ans, suivre le [parcours pédagogique illustré](docs/DEMARRER-DE-ZERO.md).

## Environnement depuis les sources

Combinaison testée sur Windows : Python 3.13.6, Astropy 7.2.0, NumPy 2.4.1 et pytest 7.4.4. Photutils n’est pas nécessaire à l’inventaire. Sous PowerShell, à la racine du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements/dev-tested.txt
.\.venv\Scripts\python.exe -m pytest -q
.\scripts\gar-inventory.bat "D:\ArchivesFITS" --output ".\local\inventaire-01"
```

Installer Python pour l’utilisateur courant. L’appel explicite à l’interpréteur évite de modifier la politique d’exécution PowerShell. L’installation des dépendances nécessite Internet ou un dépôt de paquets préparé à l’avance ; l’inventaire lui-même est local. Le fichier `requirements/dev-tested.txt` décrit les versions directes testées, **pas un verrouillage complet ni un audit des roues distribuées**.

Si votre Python dispose déjà des versions nécessaires, le lanceur fonctionne sans créer `.venv`. Pour appeler le module directement :

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
python -m gar inventory "D:\ArchivesFITS" --output ".\local\inventaire-02"
```

L’installation locale modifiable du paquet a aussi été vérifiée : après les dépendances, exécuter `.\.venv\Scripts\python.exe -m pip install --no-deps -e .`, puis `.\.venv\Scripts\gar.exe --version`. Cette étape peut télécharger l’outil de construction setuptools. Les autres combinaisons de versions restent à valider. Aucun paquet PyPI ni binaire portable n’est publié. Le [tutoriel](docs/TUTORIEL.md) décrit un premier essai entièrement synthétique ; le [contrat](docs/CONTRAT-INVENTAIRE.md) détaille les erreurs, limites et sorties.

## Regrouper un inventaire existant

Aucune dépendance supplémentaire n’est nécessaire. Les commandes suivantes lisent un manifeste local ; elles ne refont pas l’inventaire et ne rouvrent pas les FITS :

```powershell
.\scripts\gar-sessions.bat ".\local\inventaire-01\manifest.json" --output ".\local\seances-01"
.\.venv\Scripts\python.exe -m gar sessions ".\local\inventaire-01\manifest.json" --gap-seconds 900 --output ".\local\seances-seuil-900"
```

Le seuil est en secondes ; une séparation se produit au-delà du seuil, et aussi lors d’un changement de date déclarée ou de configuration. Les sorties ne doivent pas exister ni se trouver dans les archives. Un code `2` signale des exclusions ou anomalies à examiner dans les rapports, même si ceux-ci ont bien été créés. Voir le [tutoriel illustré](docs/TUTORIEL.md) et le [contrat des séances](docs/CONTRAT-SEANCES.md).

## Diagnostiquer les horodatages depuis un manifeste local

Aucun paquet supplémentaire n’est requis. Ne pas relancer l’inventaire sur le support externe pour cette étape :

```powershell
.\scripts\gar-timing.bat ".\local\inventaire-01\manifest.json" --output ".\local\horodatages-01"
.\.venv\Scripts\python.exe -m gar timing ".\local\inventaire-01\manifest.json" --gap-seconds 900 --output ".\local\horodatages-seuil-900"
```

Choisir une sortie nouvelle sur l’ordinateur. Le code de retour `2` accompagne un diagnostic produit mais non qualifié scientifiquement ; examiner `report.md`, `timing.json`, `timing.csv` et `timing.svg`. Une cadence régulière ne certifie pas l’horloge. Voir le [contrat des horodatages](docs/CONTRAT-HORODATAGES.md).

## Examiner les informations WCS du manifeste

Aucune dépendance supplémentaire n’est nécessaire. Les observations ne sont pas rouvertes :

```powershell
.\scripts\gar-wcs.bat ".\local\inventaire-01\manifest.json" --output ".\local\wcs-01"
.\.venv\Scripts\python.exe -m gar wcs ".\local\inventaire-01\manifest.json" --max-condition 100000000 --output ".\local\wcs-autre-01"
```

Les sorties sont `wcs.json`, `wcs.csv`, `wcs.svg` et `report.md`. Le code `2` signifie que le diagnostic est produit sans certification astrométrique ; les unités et distorsions non collectées ne sont pas inventées. Voir le [contrat WCS](docs/CONTRAT-WCS.md) et l’exemple du [tutoriel](docs/TUTORIEL.md).

## Préparer des copies locales vérifiées

Avec une sélection JSON locale conforme au [contrat](docs/CONTRAT-WORKSET.md) :

```powershell
.\.venv\Scripts\python.exe -m gar workset ".\local\selection.json" --output ".\local\echantillon-01"
```

La sortie doit être nouvelle et dans `local/` du projet. Le code `0` signifie que copies et collecte ont réussi ; il ne certifie aucune WCS. Les originaux sont ouverts en lecture seule ; aucun fichier n’est créé sur leur support. Pour un premier essai sans observation réelle, utiliser le générateur indiqué dans le tutoriel.

## Comparer une copie à un catalogue local

La version 0.6 ajoute Photutils 3.1.1 et SciPy 1.18.1 à `requirements/dev-tested.txt`. Leurs versions retenues nécessitent Python 3.12 ou ultérieur ; les essais du projet utilisent Python 3.13.6. Réinstaller les dépendances si l’environnement provient d’un lot précédent :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/dev-tested.txt
.\.venv\Scripts\python.exe -m gar astrometry ".\local\lot\workset.json" --file-index 1 --catalog ".\local\references\catalog.csv" --output ".\local\controle-01"
```

La commande ne télécharge rien et ne traite que des fichiers dans `local/`. Préparer le catalogue et sa provenance avant l’analyse, suivant le [contrat astrométrique](docs/CONTRAT-ASTROMETRIE.md). Le code `0` désigne uniquement le passage des critères exploratoires, pas une certification MPC ou une qualification d’horloge.

## Recaler des poses locales

La version 0.7 réutilise les dépendances de la comparaison stellaire, sans nouveau paquet scientifique. Après mise à jour de l’installation modifiable :

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\gar.exe register ".\local\lot\workset.json" --reference-index 4 --frame-indices 1 2 3 --output ".\local\recalage-01"
```

Les quatre copies sont vérifiées en lecture seule ; les chemins sources ne sont pas consultés. Aucune clé USB n’est nécessaire. Lire le [contrat de recalage](docs/CONTRAT-RECALAGE.md) pour les critères et codes de retour. Les SVG sont produits sans dépendance graphique supplémentaire. Le générateur PNG facultatif `examples/plot_registration.py` nécessite Matplotlib dans l’interpréteur utilisé ; Matplotlib ne fait pas partie des dépendances d’analyse.

## Comparer à Gaia les poses recalées

La version 0.8 conserve les mêmes dépendances scientifiques. Actualiser l’installation modifiable, puis fournir le workset et le recalage déjà produits, ainsi que le catalogue local et sa provenance :

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\gar.exe gaia-frames ".\local\lot\workset.json" --registration ".\local\recalage-01\registration.json" --catalog ".\local\references\catalog.csv" --output ".\local\gaia-poses-01"
```

Ne pas refaire les copies ou consulter les archives externes pour cette étape. Les modèles restent gelés. Le [contrat Gaia des poses](docs/CONTRAT-GAIA-POSES.md) précise les critères, la vérification des entrées et les codes `0`/`2`/`1`. Le [tutoriel](docs/TUTORIEL.md) donne une chaîne d’essai entièrement fictive. Le SVG n’exige pas Matplotlib ; le tracé PNG facultatif `examples/plot_gaia_frames.py` l’utilise séparément.

## Préparer les preuves temporelles depuis les copies

La version 0.9 ne change pas les dépendances scientifiques. Après mise à jour de l’installation modifiable :

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\gar.exe time-evidence ".\local\lot\workset.json" --output ".\local\preuves-temps-01"
```

Cette commande lit les en-têtes des copies déjà présentes, sans pixels, réseau ou accès USB. Le code **2 est attendu** après production du dossier : il ne s’agit pas d’un échec d’installation, mais du maintien de la non-qualification temporelle. Code 1 si l’analyse est impossible. Le [contrat des preuves temporelles](docs/CONTRAT-PREUVES-TEMPS.md) et le [protocole illustré](docs/PROTOCOLE-QUALIFICATION-TEMPS.md) précisent les limites et la préparation d’un futur essai. Le SVG est produit sans outil graphique ; Matplotlib est facultatif pour `examples/plot_time_evidence.py`.

La [fiche de campagne](docs/CAMPAGNE-TEMPORELLE.md) fournit ensuite des commandes pour copier les cinq canevas documentaires dans un nouveau dossier `local/`. Cette préparation ne demande aucun paquet supplémentaire ni modification du logiciel. Le journal initial est vide ; les moyens matériels, versions et critères restent à confirmer avant un éventuel essai.

## Essayer le prototype de mobiles synthétiques

Le moteur utilise les dépendances scientifiques existantes. Mettre à jour l’installation modifiable, puis choisir de nouveaux dossiers locaux :

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe examples/make_moving_demo.py local/demo-mobiles-input
.\.venv\Scripts\gar.exe moving-synthetic local/demo-mobiles-input/manifest.json --truth local/demo-mobiles-input/truth.json --output local/demo-mobiles-report
```

Pour les PNG/GIF facultatifs, installer les versions graphiques testées dans **le même environnement**, puis lancer :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/figures-tested.txt
.\.venv\Scripts\python.exe examples/plot_moving_demo.py local/demo-mobiles-input/manifest.json local/demo-mobiles-report/moving.json local/demo-mobiles-figures
```

Matplotlib 3.10.8 et Pillow 13.0.0 sont facultatifs pour l’analyse, nécessaires à cet exemple de graphique/animation. Ce fichier n’est pas un verrouillage exhaustif des dépendances transitives. Le [contrat](docs/CONTRAT-MOBILES-SYNTHETIQUES.md) précise marqueurs fictifs, limites, critères et codes. Les images réelles ne doivent pas être réétiquetées comme synthétiques.

## Banc de limites synthétiques

Le [banc de limites du détecteur](docs/LIMITES-DETECTEUR.md) réutilise ces mêmes dépendances et conserve l’application 0.10.0a1. Ses trois commandes fabriquent, analysent et illustrent 120 séquences fictives locales ; prévoir environ 260 Mo pour les FITS seuls. Le [parcours dès 10 ans](docs/DEMARRER-DE-ZERO.md#13-bis-mission--trouver-les-limites-du-chercheur) donne les commandes et les résultats attendus. Aucun accès USB ni outil supplémentaire n’est nécessaire.

## Recalage puis recherche synthétiques

La [recette de recalage puis recherche](docs/RECALAGE-MOBILES-SYNTHETIQUES.md) réutilise également les mêmes outils et la version 0.10.0a1. Prévoir environ 86 Mo pour ses 320 FITS fictifs, plus les produits. Sa commande d’analyse retourne **2 sur le jeu livré**, car certaines branches sont bloquées et les critères ne sont pas tous satisfaits ; les rapports complets permettent ensuite le dessin. Les commandes et explications sont dans la [mission pédagogique](docs/DEMARRER-DE-ZERO.md#13-ter-mission--stabiliser-les-positions-avant-de-chercher). Aucun nouveau paquet ou accès USB n’est nécessaire.

## Répartition expérimentale des contrôles

La [comparaison des contrôles spatiaux](docs/CONTROLES-SPATIAUX.md) utilise encore les mêmes dépendances. Ses 400 FITS fictifs demandent environ 108 Mo, plus les rapports et figures. Les trois commandes de la [mission illustrée](docs/DEMARRER-DE-ZERO.md#13-quater-mission--répartir-les-étoiles-de-contrôle) donnent 0 sur le jeu livré, tout en gardant le code 2 de l’ancienne mission sur son ancien jeu. La méthode reste une recette expérimentale séparée des commandes habituelles. Le [passage aux images Seestar](docs/PASSAGE-AUX-IMAGES-SEESTAR.md) exige une préparation de série et une adaptation réelle distinctes, pas un réétiquetage en données fictives.

## Préparer une série réelle et refaire l’exercice fictif

La [préparation de huit poses réelles](docs/PREPARER-SERIE-SEESTAR.md) ajoute trois recettes d’exemple, sans nouvelle dépendance ni modification de version. Les six commandes de la [nouvelle mission pédagogique](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--préparer-huit-poses-seestar) reproduisent sélection→copie→audit→aperçu avec douze FITS fictifs et aucune clé USB. Les rendus réels publics sont des PNG autorisés [CC0](docs/images/reels/LICENCE.md), pas les FITS de l’exercice.

## Essai exploratoire sur la série locale

Le [pilote Seestar](docs/PILOTE-MOBILES-SEESTAR.md) ajoute un générateur fictif, une recette d'analyse des copies et un dessin avant/après, avec les dépendances déjà installées (y compris Matplotlib/Pillow pour les figures). Les neuf commandes du [parcours illustré](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--aligner-les-étoiles-et-chercher-un-mobile) créent trois petits jeux de huit images, leurs copies, rapports et figures. Codes attendus : 0/0/0 pour le mobile et le témoin, 0/2/0 pour le refus de contrôle. Toujours choisir des sorties neuves sous `local/`. Le premier essai réel est achevé avec zéro candidat ; sa recette ne change pas la commande `moving-synthetic` ni la version du logiciel. Pour les images réelles dont le titulaire autorise la diffusion, `plot_seestar_pilot.py --public-cc0` prépare un rendu CC0 sans métadonnées privées. Le GIF et les illustrations autorisés sont déjà inclus dans la documentation ; aucun FITS privé n'est nécessaire pour les regarder.

## Injections conditionnelles dans des dérivés

Le [lot d'injections](docs/INJECTIONS-SEESTAR.md) ajoute trois recettes expérimentales avec les dépendances existantes. Les cinq commandes du [nouvel exercice](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--retrouver-des-points-ajoutés-exprès) créent un fond fictif, génèrent 37 séquences, analysent sans réponses, scorent puis dessinent ; leurs codes attendus sont 0. Prévoir environ 100 Mo pour l'exercice et 650 Mo par génération sur le fond réel, plus l'espace des autres essais conservés. Les dérivés `.npy` sont float32 et chargés sans pickle, uniquement sous `local/`. Les FITS ne sont pas écrits, aucun accès USB n'est nécessaire. Un code 2 conserve les indisponibles ou l'échec des critères fictifs, un code 1 les erreurs/incomplétudes. La version reste 0.10.0a1.

## Distribution portable prévue

Une archive autonome devra embarquer un interpréteur redistribuable, les bibliothèques, leurs avis de licence et les moyens d’obtenir le code source correspondant. Les lanceurs `.bat` utiliseront des chemins relatifs et des arguments correctement cités. Rien ne devra écrire dans les originaux ou exiger un service système.

Validation obligatoire sur un compte standard Windows 11 : extraction dans un chemin avec espaces et accents, lancement sans Python installé, réseau désactivé, traitement du pilote, sortie contrôlée en cas de disque plein ou d’absence de droits d’écriture. L’objectif « portable » ne sera annoncé comme acquis qu’après ces essais.

L’installation initiale peut nécessiter Internet. L’analyse scientifique devra fonctionner sans réseau ; catalogues, index astrométriques et tables temporelles nécessaires seront préparés explicitement à l’avance, avec licences et provenance.
