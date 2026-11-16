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

L’inventaire est couvert par **25 cas** : préservation des octets, absence de chargement des pixels, types entiers avec `BZERO`, primaire vide et extensions, absence d’héritage implicite, doublons, gzip et compression en tuiles, fichiers invalides/tronqués, Bayer sur RGB, sorties dangereuses, dossiers vides, accès refusé, modification pendant lecture, liens/jonctions, CSV/JSON, valeurs non finies et appels Windows avec espaces et accents. Le lot des séances ajoute 42 cas et le diagnostic temporel 33, soit **100 tests réussis au total**.

Les tests ont révélé un problème de guillemets dans l’appel de test du lanceur Windows ; cet appel a été corrigé puis la suite relancée avec succès. Dans l’environnement de travail contrôlé, les tests de jonctions et de permissions ont nécessité une exécution avec accès au dossier temporaire ; cela ne démontre pas une exigence d’administrateur de l’application. La distribution autonome sur compte standard reste à valider.

Le pilote réel a été traité séparément : toutes ses empreintes indépendantes sont identiques avant inventaire, dans le manifeste et après inventaire. Les preuves détaillées restent dans `local/` : aucune image réelle, coordonnée ni liste privée de fichiers n’entre dans ce tutoriel public. Ce pilote a été exécuté avec l’environnement déjà installé ; la suite complète a ensuite été vérifiée dans l’environnement isolé corrigé. La création du paquet modifiable, la commande `gar --version` et la cohérence des dépendances (`pip check`) ont aussi été contrôlées.

Le succès des tests d’inventaire ne prouve ni l’exactitude de l’horloge, ni la validité d’une WCS, ni la qualité photométrique des pixels. Le regroupement indicatif est disponible avec la commande séparée décrite ci-dessous ; l’alignement, les détections, les courbes de lumière et les exports scientifiques restent à développer. Le verrouillage complet des dépendances, leur audit de redistribution et le paquet portable restent ouverts.

## 5. Retenir une méthode de travail pour la suite

Pour chaque nouveau lot : planifier les sous-étapes, compléter `ROADMAP.md`, faire un commit du plan, implémenter, tester, enrichir ce tutoriel avec des visuels vérifiables et actualiser les autres Markdown. Faire ensuite un commit de réalisation. Une publication GitHub est une action distincte ; les rapports personnels demeurent exclus de Git.

## 6. Regrouper les poses en séances candidates

Le plan S1 à S9 a été enregistré dans **`1523035` avant le développement**. Les commits du lot précédent, `6c79043` et `de15e8f`, ont été publiés sur GitHub avant ce nouveau lot. La commande `gar sessions` utilise uniquement le manifeste déjà enregistré sur l’ordinateur. Elle ne déplace aucun fichier et ne crée ni rapport, ni cache, ni dossier sur la clé USB ou un autre support d’observation.

Elle sépare les cibles, filtres, configurations, dossiers et dates déclarées, puis les interruptions dépassant le seuil. Elle conserve les heures brutes, sans attribuer UTC ou un fuseau à un champ inconnu. Les empilements, copies binaires et dates inutilisables deviennent des exclusions explicites.

### Produire un exemple public sans observations personnelles

Les dossiers ci-dessous doivent être nouveaux ; remplacer leur nom s’ils existent déjà :

```powershell
.\.venv\Scripts\python.exe examples/make_sessions_demo.py ".\local\demo-seances-input"
.\scripts\gar-inventory.bat ".\local\demo-seances-input" --output ".\local\demo-seances-inventory"
.\scripts\gar-sessions.bat ".\local\demo-seances-inventory\manifest.json" --output ".\local\demo-seances-report"
```

Le premier générateur crée neuf FITS fictifs : six poses avec des cibles, filtres, dates et interruptions variés, une pose sans date, une copie et un empilement. L’inventaire produit réellement le manifeste consommé par le regroupement. Le résultat vérifié est :

```text
5 séance(s) candidate(s), 6 HDU retenues, 3 exclues.
```

![Cinq groupes réellement calculés sur les observations synthétiques](images/exemple-seances.png)

*Illustration PNG produite avec Matplotlib à partir du résultat réel de l’exemple synthétique, puis vérifiée visuellement. Le module produit aussi son [graphique SVG](images/exemple-seances.svg). Les dates et cibles de cette illustration sont fictives ; ce n’est pas une capture d’écran.*

Les deux premières poses du champ A restent ensemble. Le champ B et le filtre LP forment des groupes distincts. L’interruption de près d’une heure puis le changement de date créent encore deux groupes. La copie binaire, l’empilement et la pose sans date sont exclus. La commande retourne **`2`** pour inviter à examiner ces trois exclusions attendues ; cela ne signifie pas que les rapports n’ont pas été produits.

### Examiner et ajuster le résultat

Ouvrir `report.md`, `sessions.csv` et `sessions.json` dans la sortie. Le JSON conserve chaque membre et chaque motif d’exclusion ; le CSV résume les groupes. `sessions.svg` donne le nombre de HDU par groupe dans l’ordre du JSON, jusqu’à 30 groupes.

Pour essayer un seuil de séparation de 15 minutes sur le même manifeste :

```powershell
.\scripts\gar-sessions.bat ".\local\demo-seances-inventory\manifest.json" --gap-seconds 900 --output ".\local\demo-seances-seuil-900"
```

La couverture temporelle est l’écart entre premier et dernier horodatages, sans ajouter le temps de pose final. La somme des expositions est une autre valeur. Si une durée manque, le total reste `null` ; la somme partielle connue est conservée à part. Des horodatages identiques sur des HDU différentes sont signalés pour revue, sans fusion arbitraire.

### Vérifications et précautions

Les 42 nouveaux cas couvrent les changements de configuration, dates, dossiers, interruptions et seuils, les doublons, extensions, durées inconnues, dates non prises en charge, manifestes incorrects, destinations refusées et l’appel Windows. Un test interdit explicitement toute ouverture de FITS pendant `sessions`. Les tests du lot précédent restent exécutés, soit 67 cas réussis.

Le pilote a été vérifié sur son **manifeste local uniquement** : tous les membres retenus se réconcilient avec l’inventaire, sans perte ni doublon, et l’empreinte du manifeste est inchangée. Les détails restent privés. Des variations de `SITELAT`/`SITELONG` peuvent créer plusieurs groupes : cela ne prouve pas un déplacement réel du télescope. Le regroupement utilise les valeurs exactes et ne corrige pas implicitement une position GPS.

Le découpage à minuit peut diviser une véritable séance. Les dates seules, suffixes de fuseau, secondes intercalaires et fractions de seconde de plus de six décimales sont explicitement non prises en charge par ce premier parseur, plutôt que converties ou arrondies silencieusement. Ce sont des limites de regroupement, pas une validation scientifique des heures. Voir le [contrat des séances candidates](CONTRAT-SEANCES.md).

## 7. Diagnostiquer les horodatages sans certifier l’horloge

Le lot T1 à T9 a été planifié dans le commit **`e21a5e8` avant le développement**. Il utilise uniquement les manifestes locaux, sans rouvrir les FITS ni créer quoi que ce soit sur le support externe. Le diagnostic distingue le standard, les déclarations de l’en-tête et les preuves instrumentales encore manquantes. Ses [références et limites](CONTRAT-HORODATAGES.md) expliquent cette distinction.

### Reproduire un cas fictif avec des anomalies connues

Choisir des noms de dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_timing_demo.py ".\local\demo-timing-input"
.\scripts\gar-inventory.bat ".\local\demo-timing-input" --output ".\local\demo-timing-inventory"
.\scripts\gar-timing.bat ".\local\demo-timing-inventory\manifest.json" --output ".\local\demo-timing-report"
```

Le générateur crée onze petits FITS fictifs : neuf images individuelles, une copie et un empilement. Il introduit volontairement une date absente, une date sans heure, une seconde intercalaire non prise en charge, un conflit de durées, une interruption, une date dupliquée et un intervalle court. Une des poses déclare UTC et un début de pose ; cela ne constitue pas une mesure de son exactitude.

Résultat réellement produit et vérifié :

```text
10 HDU candidates, 6 retenues pour cadence, 0 heure scientifiquement qualifiée.
```

![Diagnostic réel des horodatages fictifs et absence de qualification d’horloge](images/exemple-horodatages.png)

*Illustration PNG produite avec Matplotlib à partir du résultat synthétique, puis vérifiée visuellement. Le module produit aussi ce [graphique SVG](images/exemple-horodatages.svg). Ce n’est pas une capture d’écran ni une mesure des archives personnelles. Les barres représentent des contrôles qui se recouvrent ; elles ne s’additionnent pas.*

L’exemple donne trois dates inutilisables dans ce parseur, un conflit de durée, une interruption, un intervalle court et une date dupliquée. Les six poses retenues servent seulement au diagnostic de cadence. La copie et l’empilement n’augmentent pas artificiellement cette cadence. Le programme reste incapable de certifier une horloge fictive simplement parce qu’elle écrit six décimales.

### Lire les résultats

Ouvrir `report.md`, `timing.csv`, `timing.json` et `timing.svg` dans le dossier de sortie. Le JSON conserve les statuts, commentaires, séquences et intervalles. Le CSV présente les champs principaux et protège les textes interprétables comme formules. Le SHA-256 du manifeste permet de vérifier quelle entrée a été analysée.

`written_quantum_seconds` décrit le pas écrit, **pas une incertitude mesurée**. `clock_accuracy_seconds` reste inconnu ; `mid_exposure_utc` reste vide et `time_validated` faux. Les indications normatives sont séparées de `timesys_declared` ; aucun fuseau ni milieu de pose n’est appliqué automatiquement. Le commentaire « Image created time » ne prouve pas à lui seul le début ou la fin d’une pose.

La commande retourne **`2`** après production des rapports pour rappeler la non-qualification scientifique, même sans anomalie. Le code `1` reste réservé aux erreurs d’entrée, de paramètres ou d’écriture. Il n’existe pas d’option pour transformer un commentaire ou une cadence régulière en certification.

Pour modifier le seuil d’interruption sans relire les observations :

```powershell
.\scripts\gar-timing.bat ".\local\demo-timing-inventory\manifest.json" --gap-seconds 900 --output ".\local\demo-timing-seuil-900"
```

### Vérifier et interpréter la conclusion

La suite complète passe **100 tests**. Les 33 nouveaux cas vérifient notamment la séparation entre résolution et exactitude, les échelles déclarées, commentaires, formes non prises en charge, durées contradictoires, doublons, interruptions et frontières de comparaison. Ils couvrent aussi les cartes brutes mal formées, les chemins répétés dans un manifeste, la protection des sorties et l’appel Windows. Un contrôle interdit explicitement toute ouverture de FITS pendant cette commande.

Le manifeste privé du pilote est inchangé et ses identifiants sont tous réconciliés. Aucune observation externe n’a été rouverte. Le diagnostic n’a pas relevé d’anomalie dans les séquences comparées, mais les informations disponibles ne suffisent pas à qualifier les heures. Les valeurs et rapports personnels demeurent locaux.

Les sources officielles consultées n’ont pas permis de confirmer une convention et une borne d’erreur applicables à ce firmware. Pour avancer, il faudra une description instrumentale applicable ou une comparaison indépendante de synchronisation et de déclenchement, avec incertitude. Cette preuve ne peut pas être remplacée par les noms de fichiers, les heures de modification Windows ou une longue série régulière. Les champs non sélectionnés par l’inventaire ne sont pas déclarés absents des FITS.
