# Installation et utilisation sur Windows 11

## Ce qui fonctionne aujourd’hui

Cette version contient un inventaire FITS en lecture seule, un regroupement indicatif depuis son manifeste et leur documentation. Les lanceurs Windows exécutent le code Python depuis `src/` ; aucun traitement scientifique des pixels n’est livré.

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

## Distribution portable prévue

Une archive autonome devra embarquer un interpréteur redistribuable, les bibliothèques, leurs avis de licence et les moyens d’obtenir le code source correspondant. Les lanceurs `.bat` utiliseront des chemins relatifs et des arguments correctement cités. Rien ne devra écrire dans les originaux ou exiger un service système.

Validation obligatoire sur un compte standard Windows 11 : extraction dans un chemin avec espaces et accents, lancement sans Python installé, réseau désactivé, traitement du pilote, sortie contrôlée en cas de disque plein ou d’absence de droits d’écriture. L’objectif « portable » ne sera annoncé comme acquis qu’après ces essais.

L’installation initiale peut nécessiter Internet. L’analyse scientifique devra fonctionner sans réseau ; catalogues, index astrométriques et tables temporelles nécessaires seront préparés explicitement à l’avance, avec licences et provenance.
