# Installation et utilisation sur Windows 11

## Ce qui fonctionne aujourd’hui

Cette version contient un inventaire FITS en lecture seule, un regroupement indicatif et des diagnostics temporel/WCS depuis son manifeste. Les lanceurs Windows exécutent le code Python depuis `src/` ; aucun traitement scientifique des pixels n’est livré.

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

## Distribution portable prévue

Une archive autonome devra embarquer un interpréteur redistribuable, les bibliothèques, leurs avis de licence et les moyens d’obtenir le code source correspondant. Les lanceurs `.bat` utiliseront des chemins relatifs et des arguments correctement cités. Rien ne devra écrire dans les originaux ou exiger un service système.

Validation obligatoire sur un compte standard Windows 11 : extraction dans un chemin avec espaces et accents, lancement sans Python installé, réseau désactivé, traitement du pilote, sortie contrôlée en cas de disque plein ou d’absence de droits d’écriture. L’objectif « portable » ne sera annoncé comme acquis qu’après ces essais.

L’installation initiale peut nécessiter Internet. L’analyse scientifique devra fonctionner sans réseau ; catalogues, index astrométriques et tables temporelles nécessaires seront préparés explicitement à l’avance, avec licences et provenance.
