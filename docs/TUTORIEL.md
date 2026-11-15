# Tutoriel illustré — construire et utiliser l’inventaire

## 1. Planifier avant de coder

Le premier lot transforme le relevé exploratoire en une commande réutilisable. Les sous-étapes P1-A à P1-I sont consignées dans [ROADMAP.md](../ROADMAP.md). Le plan a été enregistré dans le commit **`6c79043` avant l’implémentation**. Les règles de suivi figurent dans [AGENTS.md](../AGENTS.md).

![Schéma du traitement prévu, des archives en lecture seule aux rapports séparés](images/plan-inventaire.svg)

*Schéma d’architecture, pas une capture d’écran ni un résultat scientifique.*

L’inventaire parcourt les fichiers, calcule leurs empreintes, relève chaque HDU et produit des rapports dans un dossier distinct. Les heures restent brutes tant que leur convention n’est pas validée. Les données personnelles ne font pas partie de ce tutoriel public.

## 2. Installation et exécution

Installer les dépendances avec les instructions de [INSTALL.md](../INSTALL.md). La combinaison retenue est Python 3.13.6, Astropy 7.2.0, NumPy 2.4.1 et pytest 7.4.4. Les premiers essais utilisaient le NumPy 2.4.0 déjà installé ; l’installation isolée a signalé que cette version avait été retirée des versions recommandées pour un défaut de compatibilité. Le fichier de dépendances a été corrigé et les 25 tests passent aussi dans l’environnement corrigé. [Version NumPy retenue sur PyPI](https://pypi.org/project/numpy/2.4.1/).

Depuis PowerShell à la racine du projet, créer les cinq fichiers fictifs de l’exemple :

```powershell
.\.venv\Scripts\python.exe examples/make_demo.py ".\local\demo-tutoriel"
.\scripts\gar-inventory.bat ".\local\demo-tutoriel" --output ".\local\demo-rapport"
```

Le générateur crée deux images 2D, une copie identique, un empilement RGB et un FITS avec primaire vide et extension image. Il n’utilise aucune observation personnelle. Les noms des dossiers sont des exemples ; s’ils existent déjà, choisir de nouveaux noms. Ni le générateur ni l’inventaire n’écrasent leurs sorties.

Le lanceur Windows utilise `.venv` si elle existe, sinon le Python disponible. La commande équivalente depuis les sources est :

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.\.venv\Scripts\python.exe -m gar inventory ".\local\demo-tutoriel" --output ".\local\demo-rapport-02"
```

Pour vos archives, remplacer la source par leur dossier et garder la sortie dans `local/`, hors des archives. Le calcul SHA-256 lit chaque fichier entier ; les images ne sont pas chargées en mémoire. Un rapport peut contenir des chemins, dates et coordonnées : il reste local.

## 3. Comprendre les résultats

Le lancement synthétique a produit :

```text
5 fichiers, 6 HDU, 1 doublon(s).
```

![Graphique tiré du manifeste réel des cinq FITS synthétiques](images/exemple-inventaire.png)

*Illustration PNG produite à partir des comptages du manifeste avec Matplotlib, puis vérifiée visuellement. Le module produit aussi son [graphique SVG réel](images/exemple-inventaire.svg). Ces figures utilisent les données fictives de `examples/make_demo.py`, pas l’archive de l’utilisateur. Matplotlib n’est pas nécessaire à l’inventaire.*

La primaire vide et son extension sont deux HDU : cela explique les six HDU pour cinq fichiers. Les quatre images 2D comprennent la copie et l’extension ; le graphique compte les occurrences, pas seulement les images uniques. Le doublon est identifié par l’empreinte complète ; il n’est ni supprimé ni déplacé.

Ouvrir les produits dans le dossier de sortie :

- `report.md` : synthèse et limites ; `summary.svg` : graphique.
- `inventory.csv` : une ligne par HDU, lisible dans un tableur ; certains textes sont protégés contre l’interprétation comme formules.
- `manifest.json` : document de référence, avec empreintes, chaque HDU, métadonnées sélectionnées, commentaires, provenance et incidents.

Une date brute sans convention confirmée n’est pas un temps de milieu de pose. Une présence de `CTYPE1`/`CTYPE2` n’est pas une validation WCS. Un mot-clé Bayer sur un empilement RGB ne rend pas cette image mosaïquée. Lire le [contrat 1.0](CONTRAT-INVENTAIRE.md) avant d’exploiter les colonnes.

## 4. Vérifier et connaître les limites

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

La suite comporte **25 cas** : préservation des octets, absence de chargement des pixels, types entiers avec `BZERO`, primaire vide et extensions, absence d’héritage implicite, doublons, gzip et compression en tuiles, fichiers invalides/tronqués, Bayer sur RGB, sorties dangereuses, dossiers vides, accès refusé, modification pendant lecture, liens/jonctions, CSV/JSON, valeurs non finies et appels Windows avec espaces et accents.

Les tests ont révélé un problème de guillemets dans l’appel de test du lanceur Windows ; cet appel a été corrigé puis la suite relancée avec succès. Dans l’environnement de travail contrôlé, les tests de jonctions et de permissions ont nécessité une exécution avec accès au dossier temporaire ; cela ne démontre pas une exigence d’administrateur de l’application. La distribution autonome sur compte standard reste à valider.

Le pilote réel a été traité séparément : toutes ses empreintes indépendantes sont identiques avant inventaire, dans le manifeste et après inventaire. Les preuves détaillées restent dans `local/` : aucune image réelle, coordonnée ni liste privée de fichiers n’entre dans ce tutoriel public. Ce pilote a été exécuté avec l’environnement déjà installé ; la suite complète a ensuite été vérifiée dans l’environnement isolé corrigé. La création du paquet modifiable, la commande `gar --version` et la cohérence des dépendances (`pip check`) ont aussi été contrôlées.

Le succès des tests d’inventaire ne prouve ni l’exactitude de l’horloge, ni la validité d’une WCS, ni la qualité photométrique des pixels. Le programme n’effectue pas encore le regroupement en séances, l’alignement, les détections, les courbes de lumière ou les exports scientifiques. Le verrouillage complet des dépendances, leur audit de redistribution et le paquet portable restent ouverts.

## 5. Retenir une méthode de travail pour la suite

Pour chaque nouveau lot : planifier les sous-étapes, compléter `ROADMAP.md`, faire un commit du plan, implémenter, tester, enrichir ce tutoriel avec des visuels vérifiables et actualiser les autres Markdown. Faire ensuite un commit de réalisation. Une publication GitHub est une action distincte ; les rapports personnels demeurent exclus de Git.

## 6. Plan du regroupement des séances

Le lot S1 à S9 de `ROADMAP.md` prépare une nouvelle commande qui lira le manifeste JSON, sans rouvrir les observations. Elle séparera les cibles, filtres, configurations, dates déclarées et grandes interruptions ; les empilements et copies binaires seront exclus des sommes d’exposition. Les heures conserveront leur statut non qualifié. Ce plan doit être committé avant le développement ; l’exemple illustré et les résultats seront ajoutés après vérification.
