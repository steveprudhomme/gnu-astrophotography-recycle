# Tutoriel illustré — construire et comprendre GNU Astrophotography Recycle

**Tu commences, même à 10 ans ? Ouvre d’abord [Construire l’application, pas à pas](DEMARRER-DE-ZERO.md).** Ce parcours fait partie du tutoriel : images à chaque grande mission, mots expliqués, installation depuis zéro, commandes à copier, résultats attendus et dépannage pour tous les modules disponibles. Le présent fichier est le carnet détaillé des étapes de développement ; les contrats permettent ensuite d’approfondir.

Ce guide suit les modules livrés jusqu’à l’Alpha 0.10. Les figures publiques sont des schémas identifiés, des résultats synthétiques ou les deux [rendus Seestar réels expressément autorisés sous CC0](images/reels/LICENCE.md). Les FITS exacts, en-têtes, coordonnées et rapports restent privés ; les tests sont entièrement synthétiques.

Accès direct : [installation](#2-installation-et-exécution), [recalage des poses](#12-recaler-trois-poses-locales-avec-un-contrôle-réservé), [comparaison Gaia](#13-comparer-les-trois-poses-à-gaia-sans-réajuster-les-modèles), [publication GitHub](#14-mettre-à-jour-github-et-vérifier-la-publication), [préparation temporelle](#15-préparer-la-qualification-des-horodatages-sur-les-copies-locales), [fiche de campagne](#16-préparer-la-fiche-opérationnelle-de-campagne-temporelle).

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

L’inventaire est couvert par **25 cas** : préservation des octets, absence de chargement des pixels, types entiers avec `BZERO`, primaire vide et extensions, absence d’héritage implicite, doublons, gzip et compression en tuiles, fichiers invalides/tronqués, Bayer sur RGB, sorties dangereuses, dossiers vides, accès refusé, modification pendant lecture, liens/jonctions, CSV/JSON, valeurs non finies et appels Windows avec espaces et accents. Les séances ajoutent 42 cas, le diagnostic temporel 33, le diagnostic WCS 36, les copies vérifiées 11, la comparaison stellaire neuf, le recalage 21, le contrôle Gaia des poses 20, la préparation temporelle 26, le prototype de mobiles 18, le banc de limites 19, la chaîne recalage/mobiles 17, les contrôles spatiaux 20 et la préparation de série 19, soit **316 tests réussis au total**.

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

## 8. Préparer des propositions à la communauté Seestar

À la demande du fondateur, une [note autonome de propositions FITS](PROPOSITIONS-SEESTAR-S50.md) a été préparée pour qu’il puisse la partager lui-même. Le plan documentaire a été enregistré dans `2f3302c` avant la rédaction finale.

La préparation a consisté à vérifier les constats dans les rapports locaux existants, consulter les références officielles FITS, Siril et AAVSO, puis séparer les faits limités à l’échantillon, les champs non collectés et les suggestions d’amélioration. Aucun FITS de la clé USB n’a été rouvert ni modifié. La note ne contient ni coordonnées, ni identifiants d’instrument, ni dates d’observation personnelles.

![Priorités conceptuelles des propositions communautaires](images/priorites-seestar.png)

*Schéma de synthèse créé pour la note ; ce n’est ni une capture d’écran ni un résultat de test du télescope.*

Les demandes prioritaires portent sur un dictionnaire versionné, la datation et les traitements appliqués aux pixels. Les autres propositions concernent Bayer/RGB, filtres, WCS par pose, empilements, incertitudes et intégrité. Chaque proposition est assortie d’un bénéfice et d’un moyen de vérification ; aucune acceptation automatique de données scientifiques n’est promise.

Les liens, avis de confidentialité et illustrations ont été vérifiés. Aucun code applicatif n’est modifié par ce travail documentaire ; la suite de 100 tests du logiciel n’a pas besoin d’être relancée pour cette note. L’envoi à la communauté reste l’action du fondateur.

### Ajouter la version anglaise

À la demande du fondateur, la [traduction anglaise complète](SEESTAR-S50-FITS-RECOMMENDATIONS.en.md) a été ajoutée après le plan `76c7e56`. Elle conserve les huit propositions, leurs limites, les références et la distinction entre constats et demandes. Le français reste disponible ; les deux versions se renvoient l’une à l’autre.

![English conceptual summary of the recommendations](images/seestar-priorities.en.png)

*Illustration traduite, vérifiée visuellement ; schéma conceptuel, pas une mesure ou une capture d’écran.*

La vérification porte sur la fidélité de la traduction, les mots-clés FITS inchangés, les liens et la lisibilité des images PNG/SVG. Aucun code applicatif ni donnée d’observation ne change. La traduction est enregistrée dans un commit documentaire local pour relecture et partage par le fondateur.

## 9. Diagnostiquer les informations WCS conservées

Le lot W1 à W9 a été enregistré dans **`a7044f1` avant le code**. Les notes communautaires française et anglaise ont été publiées avant ce nouveau lot. Le travail WCS, repris le 16 novembre 2026 après une interruption d’exécution des tests, utilise uniquement les manifestes locaux. Aucun FITS du support externe n’est rouvert, déplacé ou modifié ; aucun fichier n’y est créé.

### Comprendre la limite de la collecte

Le manifeste 1.0 ne capture pas toutes les unités, distorsions, matrices alternatives et informations de référentiel. Le diagnostic ne fabrique donc pas de transformation pixels-vers-ciel avec des valeurs implicites. Une matrice CD numériquement cohérente reste distincte d’une solution astrométrique vérifiée sur des étoiles. Les RA/DEC de pointage ne sont pas assimilées à une WCS.

### Reproduire l’exemple public

Choisir des dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_wcs_demo.py ".\local\demo-wcs-input"
.\scripts\gar-inventory.bat ".\local\demo-wcs-input" --output ".\local\demo-wcs-inventory"
.\scripts\gar-wcs.bat ".\local\demo-wcs-inventory\manifest.json" --output ".\local\demo-wcs-report"
```

Le générateur crée huit petits FITS fictifs avec pointage seul, axes incomplets, bloc CD cohérent, matrice singulière, déclaration SIP, paramètre manquant, copie et primaire vide avec extension image. L’inventaire produit le manifeste réellement utilisé par le diagnostic. Certaines informations présentes dans ces FITS fictifs, notamment unités et coefficients SIP, ne sont pas collectées par l’inventaire actuel : l’exemple illustre cette perte de contexte, sans déclarer les champs absents des fichiers.

Résultat vérifié :

```text
8 fichiers, 9 HDU, 1 doublon(s).
9 HDU examinées, 0 WCS scientifiquement validée.
```

![Catégories réellement produites sur le cas WCS synthétique](images/exemple-wcs.png)

*Illustration PNG produite avec Matplotlib à partir du résultat synthétique et vérifiée visuellement. Le module produit aussi ce [graphique SVG](images/exemple-wcs.svg). Les catégories sont exclusives et totalisent neuf HDU ; ce n’est pas une capture d’écran ni une mesure d’archives personnelles.*

Trois blocs linéaires passent les contrôles numériques limités ; ils restent dans la catégorie « contexte incomplet ». La copie, la primaire vide et les déclarations problématiques sont explicitement comptées. Une WCS partielle SIP n’est pas transformée en WCS simplifiée en supprimant sa distorsion.

### Lire les rapports

`wcs.json` conserve les paramètres observés, statuts, raisons et prochaine action indicative. `wcs.csv` est la vue de consultation, `wcs.svg` le graphique et `report.md` la synthèse. Le programme retourne **`2`** après production du diagnostic pour rappeler qu’aucune WCS n’est scientifiquement validée. Le code `1` indique une erreur d’entrée, de destination ou d’écriture.

Le seuil de conditionnement peut être modifié explicitement :

```powershell
.\scripts\gar-wcs.bat ".\local\demo-wcs-inventory\manifest.json" --max-condition 1000000000 --output ".\local\demo-wcs-seuil"
```

Ce seuil ne définit pas une précision angulaire. Un pixel de référence hors image peut être légitime ; une autre paramétrisation linéaire peut être valide même si ce module ne l’analyse pas. Les [statuts et limites](CONTRAT-WCS.md) doivent être lus avant toute exploitation des nombres.

### Vérifier et décider de la suite

Les **136 tests** passent, dont 36 nouveaux cas : absence de champs, pointage seul, axes inversés, paramètres invalides, matrices incomplètes/singulières/mal conditionnées, limites numériques extrêmes, SIP partiel, références hors image, unités de déclinaison observées ou inconnues, extensions, copies, protections et appel Windows. Un test interdit explicitement toute ouverture de FITS pendant le diagnostic.

Le manifeste privé du pilote reste inchangé et tous ses identifiants sont rapprochés. Ses champs d’axes primaires ne fournissent pas de WCS observable dans cette collecte ; cela ne tranche pas l’existence d’une solution ailleurs ou dans d’autres champs. Aucun catalogue, solveur ou pixel n’a été utilisé. Les détails privés restent dans `local/`.

L’installation modifiable de la version `0.4.0a1`, l’affichage de `gar --version`, l’aide de `gar wcs` et la cohérence des dépendances avec `pip check` ont aussi été vérifiés.

La suite scientifique demandera un contexte WCS complet et des copies locales d’images, puis une comparaison des étoiles à un catalogue ou une résolution si nécessaire. Elle fera l’objet d’un nouveau plan ; les archives d’origine restent intactes et les heures demeurent non qualifiées tant qu’aucune preuve temporelle indépendante n’est fournie.

## 10. Préparer un échantillon local et collecter les en-têtes complets

Plan préalable enregistré dans **`34930d0`**, le 16 novembre 2026. Le choix réel est limité à trois poses chronologiques et un empilement compatible, sélectionnés à partir des rapports locaux. La concordance cible/filtre/nombre ne constitue pas une preuve exacte d’appartenance des poses à l’empilement.

Le nouveau module ouvre chaque source uniquement en `rb`, puis vérifie les empreintes avant copie, sur la copie et après relecture source. Les trois poses ont aussi été rapprochées de leurs empreintes historiques. Les copies et tous les rapports restent dans `local/`, sans déplacement ni écriture sur la clé USB. Le programme lit ensuite les en-têtes **des copies**, sans réenregistrer les images.

### Reproduire sur des données fictives

Choisir trois dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_workset_demo.py ".\local\demo-workset-input"
.\.venv\Scripts\python.exe -m gar workset ".\local\demo-workset-input\selection.json" --output ".\local\demo-workset-report"
```

Le générateur réutilise le cas WCS synthétique et sélectionne trois fichiers fictifs : pointage seul, modèle céleste simple et modèle SIP. Le résultat vérifié est :

```text
3 copies vérifiées ; en-têtes complets collectés.
```

![Résultats réels de l’exemple synthétique de copie et capture complète](images/exemple-workset.png)

*Graphique produit depuis le rapport synthétique et vérifié visuellement. Aucun fichier ou renseignement personnel n’est illustré. Construire deux modèles ne démontre pas leur précision sur des étoiles.*

### Examiner la collecte complète

`copies/` contient les FITS identiques, `headers/` les représentations textuelles de chaque en-tête et `workset.json` les cartes complètes ordonnées, commentaires, empreintes et résultats de construction. Les champs historiquement non collectés, comme unités, coefficients de distorsion et informations de logiciel, deviennent consultables sans revenir aux originaux. Les textes sont des représentations Astropy ; les FITS copiés sont la référence exacte des octets.

Le modèle est essayé avec le contexte complet disponible dans les HDU locales, sans correction automatique (`fix=False`). Les unités normalisées ou valeurs par défaut de la bibliothèque ne sont pas confondues avec des déclarations écrites. Une information de logiciel ne prouve pas à elle seule la version exacte du firmware. Aucune précision d’horloge, coordonnée céleste ou mesure de résidu n’est inventée.

### Résultats et vérifications

Les **147 tests** passent, dont 11 nouveaux cas sur les copies, empreintes historiques erronées, différences de copie, source changée, jonctions, destinations refusées, extensions et conservation des cartes. Les premiers échecs étaient liés au nom réservé d’un utilitaire de test et à son contrôle d’arguments ; ils ont été corrigés avant toute copie réelle.

Sur l’échantillon privé autorisé, les quatre fichiers copiés sont identiques aux sources aux contrôles avant/après. Trois copies n’ont pas d’axes célestes primaires déclarés ; l’empilement permet la construction d’un modèle SIP, sans validation sur catalogue. Les rapports et cartes complets restent privés. L’horloge et l’exactitude astrométrique demeurent à qualifier.

Lire le [contrat de l’échantillon local](CONTRAT-WORKSET.md) pour les sélections, destinations et dossiers partiels en cas d’erreur. Ce lot n’ajoute pas de résolution astrométrique ni de transfert de WCS entre images.

L’installation modifiable de la version 0.5.0a1, `gar --version`, l’aide de `gar workset` et `pip check` ont été vérifiés. Seuls le code, les tests et illustrations fictives sont destinés à GitHub.

## 11. Comparer la WCS originale à des étoiles de référence

Le plan a été committé dans **`d349984`**, puis les paramètres de détection et de sélection ont été figés dans **`fe3b1c4`**, avant les mesures réelles. Les seuils exploratoires demandent au moins 30 associations, médiane ≤2″, percentile 95 ≤4″, au moins six cellules sur neuf et les quatre quadrants. Aucun de ces seuils n’est une norme de soumission scientifique.

### Préparer les références et préserver la confidentialité

Aucun catalogue adapté n’était disponible dans le dossier du projet. La première tentative d’acquisition a été bloquée avant exécution par le contrôle automatique, car la zone céleste provenait d’observations privées. Le fondateur a ensuite explicitement autorisé sa transmission à l’archive Gaia de l’ESA. Seules les coordonnées du champ et sa taille ont servi à extraire des données publiques ; aucune image, aucun en-tête et aucune position terrestre n’ont été envoyés.

L’extrait Gaia DR3, la requête et son empreinte sont conservés localement. L’analyse ultérieure est hors ligne. Les mouvements propres sont pris en compte à la date approximative de l’image, sans certifier son horloge. Le [contrat astrométrique](CONTRAT-ASTROMETRIE.md) précise les colonnes, l’époque et les limites.

### Reproduire un essai fictif complet

Après installation des nouvelles dépendances, choisir de nouveaux dossiers :

```powershell
$env:PYTHONPATH = Join-Path $PWD 'src'
.\.venv\Scripts\python.exe examples/make_astrometry_demo.py ".\local\demo-astrometry-input"
.\.venv\Scripts\python.exe -m gar astrometry ".\local\demo-astrometry-input\workset\workset.json" --file-index 1 --catalog ".\local\demo-astrometry-input\catalog.csv" --output ".\local\demo-astrometry-report"
```

Le générateur crée 36 étoiles et un catalogue **entièrement fictifs**. Un biais de WCS connu de 0,5 seconde d’arc vers l’Est est injecté ; il ne doit pas être soustrait par l’outil de contrôle. Le résultat réellement obtenu est d’environ 0,501″ de médiane pour 36 associations, neuf cellules et quatre quadrants.

![Positions et résidus du cas synthétique avec biais connu de 0,5 seconde d’arc](images/exemple-astrometrie.png)

*Figure créée à partir du rapport synthétique et vérifiée visuellement ; aucune observation personnelle n’est affichée. Le biais injecté est toujours visible, car aucun nouveau modèle n’est ajusté. Le [SVG produit par l’application](images/exemple-astrometrie.svg) est également disponible.*

### Lire les diagnostics

Le programme calcule les positions célestes depuis la WCS originale, avec SIP lorsqu’il est présent. Les étoiles détectées et références sont sélectionnées avec les paramètres enregistrés, puis associées au plus proche de manière mutuelle et unique dans un rayon de 8″. Aucune source n’est retirée après association pour améliorer les résidus. Le rayon initial demeure une sélection : les erreurs dépassant ce rayon ne sont pas représentées par les seuls résidus.

`astrometry.json` contient critères, paramètres, effectifs de sélection, métriques, empreintes et provenance. `matches.csv` conserve les identifiants et résidus par étoile. `residuals.svg` montre les positions des associations et leurs écarts Est/Nord ; `report.md` rassemble les résultats et limites. Pour le pilote, un graphique PNG privé est conservé dans la sortie locale et n’est pas publié.

Les statistiques comprennent biais, RMS radial, médiane, percentile 95 et couverture. L’intervalle bootstrap de la médiane est conditionnel à cet échantillon ; il ne remplace pas une incertitude absolue par position ni un modèle complet des corrélations. L’indépendance par rapport aux étoiles qui auraient servi à construire la WCS initiale n’est pas établie. Les limites de distance/vitesse radiale, parallaxe, centroides et date approximative restent explicites.

### Vérifications et résultat du pilote

Les **156 tests** passent, dont neuf nouveaux cas : champ de géométrie connue, biais conservé, WCS incorrecte avec associations fortuites, faibles effectifs/couverture, associations uniques, absence de modification des entrées, colonnes manquantes, saturation et absence de connexion réseau pendant la comparaison. Un premier essai a révélé une incompatibilité de représentation des repères célestes ; la correction consiste à comparer les positions propagées dans un même repère ICRS, sans changer la WCS.

Sur l’empilement privé, les critères préenregistrés sont satisfaits et le SHA-256 est identique avant/après. Les valeurs détaillées, catalogue et images de contrôle restent privés. La conclusion est une **compatibilité géométrique exploratoire avec les références sélectionnées**, sans certification de soumission, sans qualification d’horloge et sans transfert automatique de WCS aux poses individuelles.

Code `0` : critères exploratoires satisfaits ; `2` : résultat produit mais critères non satisfaits ; `1` : analyse impossible. Une mauvaise WCS peut donner quelques associations fortuites, d’où les exigences d’effectif et de couverture, en plus des résidus.

L’installation modifiable 0.6.0a1, l’aide de la commande, `gar --version` et `pip check` ont été vérifiés. Les graphiques fictifs publics et réels privés ont été inspectés visuellement. Les grands résidus du pilote ne sont pas supprimés pour embellir la présentation.

## 12. Recaler trois poses locales avec un contrôle réservé

Plan enregistré dans **`6480df2` avant le code**, le 16 novembre 2026. Ce lot utilise exclusivement les quatre copies locales déjà vérifiées ; aucun accès à la clé USB, aucune nouvelle acquisition de catalogue. Les rapports réels, leurs coordonnées et en-têtes restent sous `local/`, ignoré par Git. Les exemples ci-dessous sont entièrement synthétiques.

### Reproduire le recalage fictif

À la racine du projet, choisir deux dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_registration_demo.py ".\local\demo-recalage-input"
.\.venv\Scripts\python.exe -m gar register ".\local\demo-recalage-input\workset.json" --reference-index 4 --frame-indices 1 2 3 --output ".\local\demo-recalage-report"
```

Le générateur produit 180 étoiles aléatoires espacées, trois poses avec une réponse Bayer **fictive**, et une référence à trois plans. Les rotations injectées sont −12°, +3° et +18°, avec translations connues conservées dans `truth.json`. Les poses ne contiennent pas de WCS copiée. La moyenne de blocs 2×2 atténue la mosaïque de couleur ; les centres sont ramenés aux pixels natifs. Cette opération ne calibre ni les couleurs ni les flux.

Le programme réserve un quart des détections de chaque pose **avant** recherche de triangles et ajustement. Seules les autres détections servent à déterminer rotation et translation. Le modèle est ensuite gelé et les étoiles réservées sont associées à la référence pour mesurer les écarts. Les critères préalables demandent au moins 20 associations d’ajustement, 10 contrôles, médiane ≤0,75 pixel, P95 ≤1,5 pixel, six cellules sur neuf et les quatre quadrants.

Résultats réellement produits par cet exemple :

| Pose synthétique | Rotation retrouvée | Contrôles associés | Médiane (pixel) | P95 (pixel) | Cellules |
|---|---:|---:|---:|---:|---:|
| 1 | −11,9994° | 44 | 0,122 | 0,212 | 9/9 |
| 2 | +2,9982° | 45 | 0,105 | 0,338 | 9/9 |
| 3 | +18,0005° | 39 | 0,105 | 0,220 | 8/9 |

Les trois cas satisfont les critères. Ils démontrent le fonctionnement sur ces injections, sans garantir ces performances pour les observations réelles.

![Recalage réellement mesuré sur trois images synthétiques, avec étoiles réservées au contrôle](images/exemple-recalage.png)

*Figure calculée depuis le rapport synthétique et inspectée visuellement, pas une capture d’écran. À gauche : répartition spatiale et vecteurs de résidus amplifiés ×20 ; à droite : résidus de contrôle, avec nombre de points éventuellement hors cadre. Le cercle de 0,75 pixel est un repère, pas une obligation pour chaque étoile. Le [SVG directement produit](images/exemple-recalage.svg) est également disponible. Aucune observation personnelle n’est publiée.*

Le SVG ne nécessite aucun outil supplémentaire. Pour reproduire le PNG, utiliser un interpréteur disposant de Matplotlib (outil graphique facultatif, distinct des dépendances d’analyse) :

```powershell
python examples/plot_registration.py ".\local\demo-recalage-report\registration.json" ".\local\demo-recalage-report\registration.png" --synthetic
```

Ne passer `--synthetic` que pour des données effectivement fictives. Pour un rapport réel, l’omettre : le graphique indique alors son caractère privé et doit rester dans `local/`.

### Lire la composition et ses limites

`registration.json` contient modèles, paramètres, indices de détections réservées, effectifs associés/non associés, empreintes et provenance. `matches.csv` sépare ajustement et contrôle. `registration.svg` et `report.md` présentent les résultats par pose ; une pose en échec reste explicitement signalée. Codes : `0` pour tous les critères satisfaits, `2` pour un rapport avec échec, `1` pour une analyse impossible.

La transformation explicite est `p_reference = R @ p_pose + t`, puis la WCS céleste originale de la référence, avec SIP. Aucune réflexion, échelle libre ou déformation n’est ajustée ; aucun FITS n’est réécrit. Le programme ne copie pas la WCS de l’empilement dans les en-têtes des poses. Pour utiliser une composition acceptée depuis Python :

```python
import json
from gar.registration import composed_sky
with open("local/demo-recalage-report/registration.json", encoding="utf-8") as stream:
    report = json.load(stream)
position = composed_sky(report["frames"][0], 384, 384)
print(position)
```

Les entrées sont x, y en pixels natifs d’origine zéro. Les modèles refusés et points hors du recouvrement sont bloqués. L’erreur de référence reste héritée ; le contrôle réservé à l’ajustement ne démontre pas l’indépendance des images par rapport à l’empilement. L’association à 3 pixels sélectionne les résidus observables, même sans retrait après association. Le [contrat de recalage](CONTRAT-RECALAGE.md) détaille les triangles, sélections, distorsions prises en charge et limites.

### Vérifications et essai privé

Les **177 tests passent**, dont 21 nouveaux cas : rotations positives/négatives jusqu’à 145°, perturbation des seules étoiles réservées sans effet sur le modèle, échecs de réflexion/champ distinct/faible effectif/couverture, mosaïque Bayer fictive, saturation, préservation des pixels et empreintes, refus des chemins externes avant sondage, absence de réseau, sorties et conservation de la distorsion SIP dans la composition.

Les trois copies réelles satisfont séparément les critères préenregistrés ; les quatre empreintes sont inchangées et les cartes de résidus ont été inspectées localement. Les nombres, positions, modèles et illustrations du champ réel restent privés. Aucun seuil n’a été assoupli après lecture des résultats. L’installation modifiable 0.7.0a1, l’aide `gar register`, la version et la cohérence des dépendances sont vérifiées avant livraison.

Les contrôles de recalage ne remplacent ni un budget d’erreur astrométrique absolue ni une qualification d’horloge. Les prochaines mesures de mobiles ou de flux nécessiteront leurs propres plans, tests et critères. Aucune vitesse, soumission scientifique ou précision UTC n’est annoncée.

## 13. Comparer les trois poses à Gaia, sans réajuster les modèles

Le plan **`93c13cb`** fixe les sous-étapes et critères avant code et mesure réelle. Les entrées réelles sont exclusivement les copies, le recalage gelé et le catalogue déjà locaux. Aucun accès USB, aucune nouvelle requête réseau. Les coordonnées du champ, les en-têtes et rapports réels restent privés sous `local/` ; les illustrations publiques ci-dessous sont synthétiques.

### Reproduire la chaîne sur des données fictives

Avec les dépendances installées, choisir trois dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_gaia_frames_demo.py ".\local\demo-gaia-poses-input"
.\.venv\Scripts\python.exe -m gar register ".\local\demo-gaia-poses-input\workset.json" --reference-index 4 --frame-indices 1 2 3 --output ".\local\demo-gaia-poses-recalage"
.\.venv\Scripts\python.exe -m gar gaia-frames ".\local\demo-gaia-poses-input\workset.json" --registration ".\local\demo-gaia-poses-recalage\registration.json" --catalog ".\local\demo-gaia-poses-input\catalog.csv" --output ".\local\demo-gaia-poses-report"
```

Le générateur produit trois poses Bayer fictives, une référence et un catalogue de forme Gaia, **sans observation Gaia réelle ni téléchargement**. Le catalogue décrit les positions vraies ; la WCS de référence reçoit un biais connu de 0,5″ vers l’Est avant le recalage. Les copies fictives reçoivent une date déclarée pour permettre la propagation des références. Les poses restent sans WCS copiée dans leurs en-têtes.

Le recalage doit d’abord conserver un quart des détections à l’écart de l’ajustement. La comparaison Gaia reproduit cette partition et utilise la composition déjà calculée, sans nouvel ajustement. Tous les seuils restent ceux du plan : ≥20 associations réservées, médiane ≤2″, P95 ≤4″, six cellules et quatre quadrants. Les seuils temporels et de soumission scientifique ne sont pas définis par ce contrôle.

Résultats réellement obtenus sur cet exemple :

| Pose fictive | Contrôles associés | Médiane (″) | P95 (″) | Biais Est (″) | Cellules |
|---|---:|---:|---:|---:|---:|
| 1 | 44 | 0,510 | 0,775 | +0,517 | 9/9 |
| 2 | 45 | 0,502 | 0,774 | +0,492 | 9/9 |
| 3 | 39 | 0,463 | 0,773 | +0,456 | 8/9 |

Les trois cas satisfont les critères et le biais injecté reste visible. Les écarts entre poses reflètent notamment les centroïdes et les échantillons de contrôle différents ; ils ne démontrent pas un mouvement réel.

![Comparaison réellement calculée sur trois poses synthétiques et un catalogue fictif, sans correction du biais](images/exemple-gaia-poses.png)

*Graphique issu du JSON synthétique, inspecté visuellement ; ce n’est pas une capture d’écran. À gauche, les associations du bilan secondaire sont grises et les contrôles réservés colorés. À droite, tous les résidus de contrôle sont représentés avec la même échelle entre poses ; le biais vers l’Est n’a pas été soustrait. Les couleurs indiquent ≤2″, ≤4″ ou au-delà ; les seuils portent sur médiane/P95, pas sur chaque point. Le [SVG applicatif](images/exemple-gaia-poses.svg) est disponible sans dépendance graphique supplémentaire.*

Pour reproduire le PNG avec un interpréteur disposant de Matplotlib, facultatif :

```powershell
python examples/plot_gaia_frames.py ".\local\demo-gaia-poses-report\gaia-frames.json" ".\local\demo-gaia-poses-report\gaia-frames.png" --synthetic
```

Omettre `--synthetic` pour des observations réelles et conserver leur figure dans `local/`. Les SVG ne nécessitent pas Matplotlib.

### Comprendre les populations et les sorties

Le contrôle porte sur **toutes les détections réservées dans le recouvrement**, y compris celles qui n’avaient pas trouvé de correspondance dans l’empilement. Le nombre d’associations Gaia peut donc dépasser le nombre du contrôle pose/empilement, sans ajout d’étoiles d’ajustement au verdict. Les points hors recouvrement et les détections non associées sont comptés séparément.

`gaia-frames.json` distingue `control` (verdict principal) de `all_diagnostic` (bilan secondaire incluant les étoiles d’ajustement, sans verdict). Il conserve les critères, associations, résidus Est/Nord, séparations sphériques, biais, RMS, médiane/P95, intervalle bootstrap conditionnel, références partagées, SHA-256 et provenance. Les deux échantillons du CSV se chevauchent : ne pas additionner leurs lignes. `gaia-frames.svg` et `report.md` présentent le contrôle principal par pose.

La sélection Gaia conserve G 9–17,5, RUWE <1,4, mouvements propres disponibles et isolation 16″ ; l’époque est midi TCB de la date calendaire approximative de la pose. L’association est mutuelle et unique à 8″. Aucun modèle ni biais n’est réajusté, aucun grand résidu n’est retiré après association ; **le rayon sélectionne toutefois les erreurs observables**. Les références sont limitées au recouvrement avec une marge de 10 pixels dans les deux images. Lire le [contrat Gaia des poses](CONTRAT-GAIA-POSES.md) pour les contrôles de provenance et limites.

Codes de retour : `0` si toutes les poses satisfont les critères principaux ; `2` si le rapport contient un échec ; `1` si la comparaison est impossible ou incohérente. Un effectif insuffisant reste un échec, sans abaisser le seuil après lecture du résultat.

### Vérifications et contrôle privé

Les **197 tests passent**, dont 20 nouveaux cas : biais injecté conservé, étoiles d’ajustement exclues du verdict, mauvaise composition, champ incorrect, faible effectif/couverture, mouvement propre connu, distorsion SIP et passage à zéro en ascension droite, catalogue incomplet ou identifiants dupliqués, provenance/partition/centroïdes/WCS incohérents, absence de réseau et de nouvel ajustement, préservation des entrées et recalage préalablement refusé. La sélection et la propagation Gaia sont mises en commun avec `gar astrometry`, dont les tests sont conservés.

Commande de vérification depuis l’environnement installé :

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="local/pytest-gaia-poses-verification"
.\.venv\Scripts\gar.exe --version
.\.venv\Scripts\gar.exe gaia-frames --help
.\.venv\Scripts\python.exe -m pip check
```

Choisir un dossier de tests neuf : pytest peut nettoyer son dossier temporaire. L’installation modifiable 0.8.0a1, l’aide et les dépendances sont vérifiées avant livraison. Les entrées du pilote réel restent inchangées ; les trois poses satisfont séparément les critères fixés et leurs cartes sont inspectées localement. Les valeurs détaillées, modèles et images du champ restent privés ; seules les données fictives sont illustrées publiquement.

Des références sont communes aux poses. Leur présence dans Gaia ne prouve pas leur indépendance par rapport au solveur initial de l’empilement. Les résultats ne fournissent ni budget d’erreur absolue complet, ni qualification de l’horloge, ni certification MPC. Le bootstrap de la médiane n’est pas l’incertitude absolue de chaque position. La qualification temporelle reste nécessaire avant une future mesure de vitesse d’objet mobile.

## 14. Mettre à jour GitHub et vérifier la publication

Actualisation documentaire planifiée dans **`835eac9`**. Avant cette mise à jour, la présence de la réalisation applicative `9bcf431` sur `main` a été vérifiée directement via GitHub. Le code, les 197 tests du lot 0.8 et les mesures ne sont pas modifiés ici. Le travail complète les accès aux exemples illustrés et corrige les anciens statuts documentaires. Aucun accès USB, aucune réouverture des observations et aucune publication des rapports réels.

![Schéma conceptuel : du plan de documentation au commit publié et vérifié, avec données privées conservées localement](images/publication-github.png)

*Schéma de procédure, sans capture d’écran ni résultat scientifique. Le [SVG](images/publication-github.svg) est aussi disponible. Les figures de résultats visibles dans les sections précédentes proviennent des exemples synthétiques réellement calculés.*

### Examiner les fichiers à publier

Depuis la racine du dépôt, examiner l’état et les différences :

```powershell
git status --short
git diff --stat
git diff --check
```

Le dernier contrôle vérifie les espaces et fins de ligne, pas la confidentialité. Lire les différences et vérifier que les données, en-têtes, coordonnées, chemins et rapports réels restent exclus de Git. Ne pas ajouter tout `local/` ; `.gitignore` ne retire pas une donnée déjà suivie. Pour ce lot documentaire, vérifier les liens Markdown, le XML des SVG et l’affichage des PNG ; les 197 tests sont ceux du lot applicatif précédent, sans nouvelle qualification scientifique.

### Enregistrer puis envoyer les fichiers relus

Exemple pour cette mise à jour, avec une sélection explicite :

```powershell
git add README.md GOVERNANCE.md ROADMAP.md docs/DOSSIER-LANCEMENT.md docs/TUTORIEL.md docs/images/publication-github.png docs/images/publication-github.svg
git diff --cached --check
git diff --cached --stat
git commit -m "docs: actualiser le tutoriel illustre et le statut alpha 0.8"
git push origin main
```

Arrêter à chaque erreur et en résoudre la cause avant l’étape suivante. L’authentification relève de Git/GitHub ; aucun jeton n’est copié dans les documents ou commandes publiées. Si d’autres changements distants sont signalés, les examiner avant de synchroniser ; ne pas utiliser un envoi forcé pour les remplacer.

### Confirmer la publication distante

```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/main
git status --short
```

Après un envoi réussi, les deux premières commandes doivent indiquer le même identifiant de commit pour ce lot. Un état local propre ne prouve pas à lui seul la publication. Vérifier également sur [GitHub](https://github.com/steveprudhomme/gnu-astrophotography-recycle) les documents et illustrations attendus. La publication de fichiers dans `main` ne crée ni version GitHub Releases, ni paquet PyPI, ni logiciel portable certifié.

## 15. Préparer la qualification des horodatages sur les copies locales

Plan préalable **`a157beb`**, enregistré avant code et examen des copies. Ce lot complète le diagnostic du manifeste partiel par une lecture des **en-têtes complets des copies déjà vérifiées**. Aucun accès USB, aucune ouverture des sources historiques, aucun pixel chargé et aucune mesure instrumentale. Le résultat est un dossier de préparation, pas un certificat d’horloge.

### Produire un dossier fictif complet

Choisir deux dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_time_evidence_demo.py ".\local\demo-preuves-temps-input"
.\.venv\Scripts\python.exe -m gar time-evidence ".\local\demo-preuves-temps-input\workset.json" --output ".\local\demo-preuves-temps-report"
$LASTEXITCODE
```

Le dernier résultat attendu est **2** : le dossier est produit mais l’heure reste non qualifiée. Ce code ne signifie pas que l’installation a échoué. Le code 1 indique au contraire une entrée ou une analyse impossible. Le générateur crée directement quatre FITS synthétiques sous `local/` ; il ne copie aucune source externe.

| Fichier fictif | Cas injecté | Résultat préparatoire attendu et obtenu |
|---|---|---|
| 1 | Date de création lisible, échelle et début/fin absents | Informations insuffisantes, précision réelle inconnue |
| 2 | Début/fin, UTC, unité, firmware fictif et erreurs déclarées | Déclarations riches ; aucune preuve indépendante, heure non qualifiée |
| 3 | DATE-OBS dupliquée, fin avant début, durées divergentes, erreur négative | Ambiguïtés et contradictions conservées dans les alertes |
| 4 | Cube de trois plans et compteur d’empilement | Séparé des poses individuelles, aucune heure moyenne supposée |

Résumé réellement produit : quatre fichiers/HDU, trois candidates individuelles, deux `DATE-OBS` lisibles non dupliquées, deux paires début/fin lisibles, deux échelles déclarées et **zéro HDU qualifiée**. Huit exigences de preuve sont à compléter. Une paire lisible peut être contradictoire : la barre « début et fin lisibles » inclut ici le cas 3 et ne signifie pas un intervalle valide.

![Comptages réellement produits sur le dossier synthétique, avec déclarations présentes et aucune horloge qualifiée](images/exemple-preuves-temps.png)

*Figure calculée depuis le JSON fictif et inspectée visuellement ; aucune capture d’écran ni observation personnelle. Les barres se recouvrent et ne doivent pas être additionnées. Ce ne sont pas des scores de confiance. Le [SVG applicatif](images/exemple-preuves-temps.svg) est également disponible.*

Pour reproduire le PNG avec un interpréteur disposant de Matplotlib, facultatif :

```powershell
python examples/plot_time_evidence.py ".\local\demo-preuves-temps-report\time-evidence.json" ".\local\demo-preuves-temps-report\time-evidence.png" --synthetic
```

Omettre `--synthetic` pour un dossier réel et garder sa figure dans `local/`. Le SVG applicatif n’a pas besoin de Matplotlib.

### Lire les six produits et leurs limites

- `time-evidence.json` : cartes, commentaires, doublons, absences dans la liste sélectionnée, diagnostics par HDU, empreintes et provenance.
- `cards.csv` : cartes sélectionnées avec index et textes protégés contre les formules de tableur ; le JSON garde les valeurs originales.
- `time-evidence.svg` et `report.md` : comptages et points à examiner, avec maintien de la non-qualification.
- `evidence-template.json` : canevas de huit exigences, configuration, protocole, incertitudes et résultats encore inconnus.
- `measurement-plan.md` : étapes de mesure à préparer, avec lien vers le protocole détaillé.

Le programme distingue déclarations et preuves. Il ne déduit pas le firmware exact de `PROGRAM`, ne remplace pas une échelle absente par UTC pour convertir les dates et ne transforme pas des décimales écrites en précision réelle. Les coordonnées numériques JD/MJD et origines sont conservées sans interprétation. Les extensions ne reçoivent pas silencieusement les informations du primaire.

Une différence début/fin est uniquement calendaire et naïve ; elle ne constitue pas un temps physique écoulé certifié. La comparaison avec `TELAPSE` exige une unité seconde explicitement déclarée. Les écarts de durées ou erreurs négatives sont signalés sans conclure à une panne de l’instrument. `DATE-AVG` n’est pas automatiquement un milieu arithmétique d’exposition. Le [contrat des preuves temporelles](CONTRAT-PREUVES-TEMPS.md) fixe précisément ces limites.

### Préparer les preuves indépendantes

![Schéma conceptuel des relations à mesurer entre référence indépendante, événement physique, exposition et horodatage](images/schema-qualification-temps.png)

*Schéma d’un essai futur, sans délai, instant ou mesure réelle représenté ; les flèches désignent des relations à caractériser. [Version SVG](images/schema-qualification-temps.svg).*

Le [protocole préparatoire](PROTOCOLE-QUALIFICATION-TEMPS.md) demande de fixer l’usage et les critères avant essai, caractériser une référence indépendante traçable, dater les événements réellement émis/observés, mesurer début/fin, décalage, dérive, dispersion et durée, puis construire un budget avec dépendances et incertitudes. Les 30 répétitions proposées par configuration sont un choix de planification à adapter et préenregistrer, pas une norme de certification.

Le canevas doit être complété et revu séparément. La commande ne l’ingère pas et n’approuve aucune mesure, même si quelqu’un remplit ses champs. Le rattachement aux archives anciennes doit être démontré avec des éléments applicables à leur configuration et à leur époque. Un essai futur ne les qualifie pas rétroactivement ; les statuts temporels et d’export restent faux, et aucun milieu de pose UTC ou vitesse scientifique n’est produit.

### Vérifications et dossier privé

Les **223 tests passent**, dont 26 nouveaux cas : déclarations riches sans qualification, dates hors du sous-ensemble pris en charge, doublons, ordre début/fin, unités et erreurs, firmware non déduit de PROGRAM, distinction pose/cube/table/extension, intégrité, sources ignorées, absence de pixels/réseau, mutations pendant lecture, canevas non ingéré et protection CSV. Les empreintes et les propriétés d’accès sont contrôlées sur des FITS synthétiques.

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="local/pytest-preuves-temps-verification"
.\.venv\Scripts\gar.exe --version
.\.venv\Scripts\gar.exe time-evidence --help
.\.venv\Scripts\python.exe -m pip check
```

Choisir un dossier de tests neuf : pytest peut nettoyer son dossier temporaire. L’installation modifiable 0.9.0a1, l’aide et les dépendances sont vérifiées avant livraison. Le dossier privé a été produit sur les quatre copies locales ; celles-ci et le workset restent inchangés. Les en-têtes examinés ne constituent pas des preuves indépendantes, et leur détail reste dans `local/`. Les figures fictives publiques et le dossier réel privé sont inspectés séparément ; aucun contenu réel n’est destiné à GitHub.

## 16. Préparer la fiche opérationnelle de campagne temporelle

Plan préalable **`0ad755c`**. Le dossier logiciel 0.9 existe déjà : ce complément prépare les documents d’un futur essai, sans refaire l’audit, rouvrir un FITS ou consulter une source historique. Aucun code d’analyse ni version applicative n’est modifié. Les moyens matériels et versions non fournis restent **à confirmer**, sans déduire de l’absence d’information qu’un matériel serait disponible ou absent.

![Schéma conceptuel des documents et décisions à préparer avant une campagne, puis de la revue distincte des archives](images/fiche-campagne-temps.png)

*Schéma de procédure non exécutée, sans capture d’écran ni mesure instrumentale. Les blocs indiquent des travaux à réaliser et des décisions humaines à documenter ; ils ne décrivent pas un essai approuvé. [Version SVG](images/fiche-campagne-temps.svg).*

### Copier et renseigner les canevas

La [fiche opérationnelle](CAMPAGNE-TEMPORELLE.md) fournit les commandes complètes de copie vers un dossier local neuf. Les cinq sources publiques sont :

- [configuration.example.json](../examples/timing-campaign/configuration.example.json) : configuration, usage, référence, critères et état historique ; valeurs inconnues nulles.
- [planned-runs.example.csv](../examples/timing-campaign/planned-runs.example.csv) : proposition non exécutée de trois blocs de dix répétitions ; durées et positions dans la séance restent vides.
- [measurement-log.blank.csv](../examples/timing-campaign/measurement-log.blank.csv) : en-tête de journal, sans ligne de mesure.
- [uncertainty-budget.blank.csv](../examples/timing-campaign/uncertainty-budget.blank.csv) : contributions proposées, sans valeur ni combinaison d’incertitudes.
- [review.blank.md](../examples/timing-campaign/review.blank.md) : questions de revue avant essai puis après résultats, toutes non renseignées.

Après la copie décrite dans la fiche, ces commandes permettent de consulter la configuration et le planning locaux :

```powershell
Get-Content -LiteralPath '.\local\ma-campagne-temps-01\configuration.json'
Import-Csv -LiteralPath '.\local\ma-campagne-temps-01\planned-runs.csv' | Format-Table
Import-Csv -LiteralPath '.\local\ma-campagne-temps-01\measurement-log.csv' | Measure-Object
```

Le journal initial doit contenir **zéro ligne de mesure**. Les trois blocs proposent 30 répétitions au total, sans date, durée d’exposition ou référence inventée. Adapter ce planning à une configuration réellement confirmée avant de le figer ; ce nombre n’est ni un standard instrumental ni une garantie de précision. Conserver les lignes rejetées et leurs motifs lors d’un essai futur.

### Préparer les pièces et la revue

Renseigner l’usage, le mesurande, la tolérance et sa définition ; documenter ensuite la référence indépendante disponible, sa traçabilité, son incertitude et la méthode reliant l’événement physique au timestamp. Les versions firmware/application et le mode doivent être confirmés avec leurs pièces. Les valeurs PROGRAM/CREATOR de l’ancien dossier ne sont pas transformées en firmware vérifié.

Fixer critères, exclusions, durée de session et blocs avant l’essai. Conserver une version figée et son empreinte avec le responsable et l’instant de revue ; une modification après examen des résultats doit rester une révision explicite. Le budget comporte unités, types d’incertitude, couverture et dépendances à examiner ; les blancs ne valent pas zéro et les contributions ne sont pas combinées automatiquement.

Les décisions pour la configuration/époque testées et pour les anciennes archives restent distinctes. Cocher une revue ou modifier un booléen dans un fichier n’est pas un contrôle logiciel, une preuve de performance ou un déblocage des exports. Les anciennes archives restent non qualifiées sans rattachement applicable.

### Résultats de cette préparation et contrôles

Les canevas JSON/CSV et leurs colonnes sont vérifiés, avec trois blocs cohérents, aucune ligne de mesure, aucun résultat inventé et les statuts de qualification faux. Les commandes de copie PowerShell ont été exécutées dans un dossier local de vérification neuf : cinq fichiers copiés, trois blocs proposés, zéro mesure. Les liens, illustrations PNG/SVG et fichiers destinés à Git sont contrôlés. **Les 223 tests sont ceux du lot applicatif 0.9, sans nouvelle exécution revendiquée dans ce complément documentaire.**

Un dossier privé de travail est préparé à partir du seul rapport temporel local déjà produit, dont l’empreinte est conservée avant/après. Le rapport reste inchangé ; aucun FITS ni chemin source historique n’est ouvert. Les canevas renseignés, informations d’opérateur, pièces de matériel et statut local restent dans `local/`, exclus de Git. La préparation ne réalise aucune acquisition et ne déclare pas la campagne prête à qualifier une horloge.

## 17. Chercher des mobiles dans des images inventées

Le plan **`a072ff1`**, du 17 novembre 2026, précède le code et les évaluations. La qualification des heures réelles attend toujours une preuve indépendante ; nous pouvons entraîner et tester un algorithme avec des positions et temps fictifs connus. Aucune image réelle ou clé USB n’est utilisée. Le [parcours dès 10 ans](DEMARRER-DE-ZERO.md#13-mission--retrouver-les-points-qui-bougent) explique cette mission avec des mots simples.

### Fabriquer, chercher, puis compter

Choisir deux dossiers nouveaux :

```powershell
.\.venv\Scripts\python.exe examples/make_moving_demo.py local/demo-mobiles-input
.\.venv\Scripts\python.exe -m gar moving-synthetic local/demo-mobiles-input/manifest.json --truth local/demo-mobiles-input/truth.json --output local/demo-mobiles-report
```

Le générateur fabrique 18 séquences de huit images : six situations, répétées avec trois graines de bruit. Une graine est un nombre qui permet de refaire exactement le même tirage aléatoire. Les images ont 256×256 pixels et sont déjà dans un repère commun ; les secondes sont inventées. Les cas faciles évitent volontairement les étoiles proches ; des cas difficiles sont évalués séparément.

La détection cherche les points, retire ceux qui semblent fixes et essaie des trajectoires rectilignes. Elle construit tous ses candidats **avant de lire les positions de vérité**. Le fichier de réponses n’améliore pas les trajectoires ; il permet ensuite de compter les objets retrouvés, manqués et les faux candidats. Les empreintes des images, du manifeste et de la vérité sont conservées avant/après.

| Situation, sur trois graines | Injectés | Retrouvés | Faux candidats |
|---|---:|---:|---:|
| Deux mobiles brillants isolés par séquence | 6 | 6 | 0 |
| Témoin sans mobile, avec défauts et flashs indépendants | 0 | 0 | 0 |
| Mobile absent sur deux images | 3 | 3 | 0 |
| Mobile faible et mobile très lent | 6 | 1 | 0 |
| Passage près d’une étoile | 3 | 3 | 0 |
| Petit défaut commun de repérage | 3 | 3 | 0 |

![Comptages réellement calculés sur les dix-huit séquences fictives, avec les objets manqués conservés](images/exemple-mobiles-bilan.png)

*Graphique synthétique, pas une capture d’écran. Le témoin 0/0 n’a aucun objet injecté ; son rappel est indéfini, pas égal à 100 %. Les cas difficiles restent visibles. [SVG détaillé par séquence](images/exemple-mobiles-bilan.svg).*

Les critères principaux demandent les six mobiles nominaux et les trois intermittents retrouvés, zéro faux candidat sur les témoins, P95 de position ≤0,75 pixel et erreur vectorielle de vitesse ≤0,03 pixel/s fictive. Ils sont satisfaits sur cette suite : P95 voisin de 0,075 pixel et erreur maximale de vitesse voisine de 0,0012 pixel/s. Au total 16/21 injections sont retrouvées ; les cinq manquées sont dans le scénario faible/lent. Ce bilan ne prouve ni un rappel universel ni un taux réel de faux positifs nul.

Le premier générateur plaçait les flashs distincts du témoin le long d’une ligne. Cette construction a été corrigée pour les rendre spatialement indépendants ; l’essai initial est conservé localement et les résultats illustrés utilisent la suite corrigée, sans changer les seuils.

### Lire les fichiers et créer les images

`moving.json` conserve paramètres, sélections, candidats, erreurs, taux et empreintes. `candidates.csv` donne les trajectoires mesurées en pixels et secondes fictives. `moving.svg` et `report.md` expliquent les résultats et limites par séquence. Code 0 : critères principaux satisfaits sur la suite complète ; code 2 : critères non satisfaits ou suite incomplète ; code 1 : analyse impossible.

Installer les outils graphiques facultatifs dans le même environnement puis fabriquer les figures :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/figures-tested.txt
.\.venv\Scripts\python.exe examples/plot_moving_demo.py local/demo-mobiles-input/manifest.json local/demo-mobiles-report/moving.json local/demo-mobiles-figures
```

![Dernière image fictive avec les positions mesurées des deux candidats](images/exemple-mobiles-image.png)

![Animation de huit images fictives avec les trajectoires mesurées](images/exemple-mobiles-animation.gif)

*Les trois figures sont calculées depuis les pixels synthétiques et le rapport gelé. Le GIF contient huit images ; les traits colorés relient les positions déjà mesurées. Aucune image d’observation personnelle n’est utilisée ou modifiée. La première tentative de tracé utilisait un Python sans le paquet `gar` : le parcours emploie désormais explicitement le Python installé dans `.venv`, avec ses outils graphiques, pour éviter ce mélange d’environnements.*

### Comprendre les limites et vérifier la reconstruction

Le [contrat du prototype](CONTRAT-MOBILES-SYNTHETIQUES.md) détaille les paramètres préenregistrés, la suppression des sources fixes, les rayons et les limites de ressources. Des mobiles trop lents peuvent être retirés avec les étoiles ; des points faibles peuvent rester sous le seuil. Le modèle ne traite pas tous les mélanges, accélérations, traces ou défauts cohérents. Il n’ajoute ni incertitude complète de position/vitesse, ni conversion céleste, ni qualification temporelle réelle.

Les **241 tests passent**, dont 18 nouveaux cas : trajectoire connue, stationnarité, lenteur/vitesse hors domaine, images manquantes, faible effectif, absence de fuite de vérité, association un-à-un, contrôle complet sur pixels, marqueurs/temps/empreintes/chemins invalides, réseau interdit, préservation et sous-ensemble sans verdict complet. L’animation et les graphiques sont inspectés séparément. Les versions, aide, installation, dépendances et reconstruction sont vérifiées avant publication.

La reconstruction dans une copie propre a révélé une instruction manquante : le dossier parent de `--basetemp` n’existait pas encore. Le premier lancement y a donc produit 47 tests réussis et 194 erreurs de préparation, avant l’analyse des cas concernés. Le guide crée désormais `local/parcours` avec `New-Item` avant les tests ; la vérification complète est reprise après cette correction. Cette vérification utilise une nouvelle installation locale des dépendances et uniquement des exemples fictifs, sans accès USB.

Après correction : **241 tests réussis en 32,77 secondes**, dépendances cohérentes (`pip check`), puis **24 commandes de missions réussies** dans cette installation indépendante, y compris les figures et le GIF. Les sorties et traces restent privées dans `local/`. La copie a été reconstruite depuis les seuls fichiers suivis par Git, sans reprendre l’environnement ou les rapports existants ; ce contrôle ne constitue pas un essai sur un système Windows vierge ou avec un enfant.

Le nouveau [guide complet pour débuter](DEMARRER-DE-ZERO.md) reprend depuis l’installation de Python/Git, l’obtention du code, la construction de l’application et l’essai de **chaque module disponible**. Il relie les dossiers aux recettes, explique les nombres de retour, donne les résultats attendus et un tableau de dépannage. Ses images sont des schémas identifiés ou des résultats synthétiques réels, sans fausse capture. Les étapes sont vérifiées sur des dossiers de travail neufs.

## 18. Tester les limites sans changer les règles

Le plan **`6f3e6c5`**, du 17 novembre 2026, a été committé puis publié et vérifié sur GitHub avant le code. Il gèle le moteur et les conditions de l’expérience. La [mission dès 10 ans](DEMARRER-DE-ZERO.md#13-bis-mission--trouver-les-limites-du-chercheur) explique chaque étape avec des mots simples ; le [protocole et les tableaux complets](LIMITES-DETECTEUR.md) conservent les détails et les limites.

### Ce que nous changeons dans les images

Une expérience utile change une condition et regarde ce qui arrive. Ici, les recettes fabriquent **120 séquences, 960 images et 110 mobiles**, avec cinq nouvelles graines. Une graine permet de refaire un tirage ; les mêmes étoiles et bruits par graine servent aux comparaisons entre conditions. Cela ne crée pas une indépendance statistique entre toutes les cases, ni une validation par une autre équipe.

Nous changeons la luminosité, la vitesse, le bruit, puis le mouvement commun du champ. Nous gardons les règles du détecteur. Les cas avec dérive ou rotation sortent volontairement de son hypothèse d’images alignées : aucun recalage n’est effectué dans cet essai. Le programme ne doit pas prétendre réussir une qualification scientifique parce qu’il a terminé son calcul.

### Trois commandes pour reproduire les résultats

Utiliser le Python et les outils graphiques de `.venv`, depuis la racine du projet. Choisir des dossiers nouveaux et prévoir environ 260 Mo pour les images, plus les produits :

```powershell
.\.venv\Scripts\python.exe examples/moving_limits.py make local/limites-entree
.\.venv\Scripts\python.exe examples/moving_limits.py run local/limites-entree/suite.json local/limites-rapport
.\.venv\Scripts\python.exe examples/plot_moving_limits.py local/limites-entree/suite.json local/limites-rapport/limits.json local/limites-figures
```

`make` fabrique, `run` mesure, le dernier programme dessine. Le retour 0 de ces recettes signifie que la tâche demandée a abouti ; il ne promet pas 110 mobiles retrouvés. Une sortie existante est refusée. Les résultats sont dans `report.md`, `limits.json` et `sequences.csv`. Les quatre sous-dossiers conservent les rapports natifs ; leurs verdicts de suite initiale complète restent faux car ce ne sont pas les 18 séquences initiales. `progress.json` indique les lots terminés ; un arrêt garde les produits partiels et ne produit pas de bilan complet. Reprendre dans une nouvelle sortie.

### Lire les images et conserver les échecs

![Carte des nombres réellement retrouvés et des faux candidats sur le jeu fictif](images/limites-detecteur-grille.png)

*Chaque case correspond à cinq répétitions fictives. Pics en ADU au-dessus du fond, vitesses en pixels par seconde inventée ; aucune magnitude ou frontière universelle de détection.*

À 0,03 pixel/s, tous les mobiles sont manqués, même brillants : le filtre stationnaire et la borne de vitesse limitent la recherche. À pic 12 ADU, un seul est retrouvé parmi les 20 injections de la grille ; le petit échantillon ne décrit pas une courbe monotone de sensibilité. À pics 30 et 120, les trois vitesses restantes donnent chacune 5/5. Aucun faux candidat dans la grille.

![Même pic et même vitesse, quatre niveaux de bruit fictif](images/limites-detecteur-bruit.png)

À pic 30 ADU et vitesse 0,5 pixel/s, les bruits sigma 2 et 4 donnent 5/5 ; sigma 8 et 16 donnent 0/5. Le bruit ici est gaussien et ajouté au modèle, sans étalonnage du capteur S50. Le rapport pic/bruit n’est pas un rapport signal/bruit photométrique.

![Bilan descriptif de la géométrie ; les cas non alignés sont hors domaine](images/limites-detecteur-geometrie.png)

Les six conditions géométriques retrouvent chacune 5/5 mobiles, mais la dérive 0,15 produit **200 faux candidats**, et la combinaison avec rotation en produit **194**, sur cinq séquences chacune. Ce sont principalement des étoiles entraînées par le déplacement du champ : les points existent dans les pixels, mais ne sont pas les mobiles injectés recherchés. Les zéros des autres conditions, dont les petites rotations, ne prouvent pas une tolérance générale aux défauts d’alignement.

![Dernière image de la graine 101 : images alignées et champ entraîné, candidats mesurés](images/limites-detecteur-comparaison.png)

![Animation réellement calculée sur huit images fictives du même champ](images/limites-detecteur-animation.gif)

*Comparaison fixée à la graine 101, sans choisir après coup une réalisation favorable. Cercle vert : réponse connue, dessinée après la détection ; croix bleue : candidat apparié ; croix orange : faux candidat de l’exercice. À droite, 40 étoiles entraînées deviennent 40 faux candidats sur cette séquence. Aucun FITS réel et aucune capture d’écran fabriquée.*

Les dix témoins sans mobile donnent zéro faux candidat, y compris avec pixels chauds, flashs indépendants et courte trace sur deux images. Leur rappel est indéfini (0/0). Dix témoins et cinq répétitions par condition ne suffisent pas à démontrer une probabilité universelle de succès ou un taux réel nul de fausses alertes.

### Vérifications, provenance et suite du projet

Les empreintes du texte des deux sources gelées sont vérifiées avant/après ; les FITS, manifestes, vérité, protocole et rapports sont conservés avec leurs empreintes. Les candidats sont construits avant lecture des réponses par le moteur. Les erreurs de position/vitesse ne portent que sur les objets appariés ; les manqués restent comptés, sans erreur numérique inventée. Les taux de faux candidats utilisent la couverture temporelle fictive de 70 secondes, pas une durée de pose instrumentale.

Les 19 nouveaux cas et toute la suite passent : **260 tests en 26,38 secondes** lors de la vérification du lot. Ils contrôlent notamment géométrie connue, génération appariée reproductible, gel du moteur, agrégation, intégrité et interruption conservant les produits partiels. Les premières figures coupaient des légendes ; leur mise en page a été corrigée et les images réexaminées, sans changer les résultats. Les huit images du GIF et la reproduction des commandes sont vérifiées avant publication ; tous les jeux FITS et rapports restent sous `local/`.

La vérification finale a rejoué les **27 commandes du parcours** depuis le code committé `615712e`, sans modification suivie, dans des dossiers fictifs neufs et avec le même environnement Python. Les 960 images ont été régénérées avec des empreintes identiques ; les quatre rapports natifs, les métriques et les cinq figures (quatre PNG et le GIF) sont identiques. Le bilan agrégé consigne la nouvelle provenance ; il n’est pas présenté comme un fichier octet pour octet identique malgré cette provenance différente. Un contrôle supplémentaire associe les 40 faux candidats de dérive de chaque graine aux 40 étoiles distinctes du témoin propre correspondant (écart d’extrapolation maximal inférieur à 0,065 pixel). Les traces restent dans `local/` et les fichiers publics sont revus avant envoi.

L’application reste 0.10.0a1, sans nouvelle dépendance ni changement du moteur. La priorité mise en évidence est de **tester le recalage avant la recherche de mobiles**, dans un prochain lot synthétique avec critères fixés à l’avance et étoiles de contrôle réservées. Ni cette conclusion ni les tests logiciels ne qualifient les horodatages réels, les positions célestes ou les performances sur le Seestar. L’autorisation de lecture USB n’a pas été utilisée : ce lot travaille uniquement sur les fichiers fictifs locaux.

## 19. Relier le recalage à la recherche de mobiles fictifs

Le plan **`286af43`**, du 17 novembre 2026, a été committé, publié et vérifié sur GitHub **avant le code**. Le lot relie les fonctions existantes avec leurs sources gelées et les mêmes dépendances ; l’application reste 0.10.0a1. Les [détails du protocole](RECALAGE-MOBILES-SYNTHETIQUES.md) donnent toutes les conditions, empreintes et critères. La [mission dès 10 ans](DEMARRER-DE-ZERO.md#13-ter-mission--stabiliser-les-positions-avant-de-chercher) explique le même exercice avec des mots simples et des images.

### Fabriquer puis comparer

Les nouvelles graines 607, 701, 809, 907, 1009 donnent 40 séquences de huit images, soit 320 images et 30 mobiles. Quatre conditions principales : alignées, dérive 0,15 pixel/s fictive, rotation totale 2 degrés, combinaison. Une rotation 8 degrés reste descriptive ; deux témoins sans mobile et un cas à seulement 12 étoiles complètent le jeu. Les mêmes champs et bruits par graine rendent les comparaisons appariées, sans indépendance entre toutes les cellules. Les images sont monoplans et simplifiées, pas une simulation calibrée du S50.

Dans des dossiers neufs sous `local/`, prévoir environ 86 Mo pour les FITS, plus les produits :

```powershell
.\.venv\Scripts\python.exe examples/moving_registration.py make local/recalage-mobiles-entree
.\.venv\Scripts\python.exe examples/moving_registration.py run local/recalage-mobiles-entree/manifest.json local/recalage-mobiles-entree/truth.json local/recalage-mobiles-rapport
.\.venv\Scripts\python.exe examples/plot_moving_registration.py local/recalage-mobiles-entree/manifest.json local/recalage-mobiles-entree/truth.json local/recalage-mobiles-rapport/comparison.json local/recalage-mobiles-figures
```

**Résultat attendu : code 2 pour l’analyse, codes 0 pour génération et dessin.** L’analyse termine les 40 séquences mais les critères globaux ne sont pas tous satisfaits. Ce code 2 ne doit être ni ignoré ni présenté comme une panne d’installation. Les résultats et les motifs sont dans `comparison.json`, `comparison.csv` et `report.md`. Les quarante fichiers individuels conservent les modèles et candidats avant évaluation. `progress.json` distingue calcul complet, interruption et séquences achevées ; un arrêt ne fabrique pas de bilan complet.

La branche avant recherche sur les détections natives. La branche après reprend **les mêmes détections**, transformées vers les étoiles mesurées de la première image. Aucun FITS n’est rééchantillonné ou écrit. Les modèles sont estimés sans les mouvements exacts, à partir des détections stellaires du module de recalage. Les contrôles sont séparés avant hypothèses/ajustement dans chaque pose, puis comparés après gel. Ils ne forment pas un catalogue indépendant sur toute la série ; la référence mesurée commune porte des erreurs corrélées. Une seule pose refusée bloque la branche après de sa séquence, sans identité de secours ni retrait discret de cette pose.

### Voir les refus avant de comparer les performances

![Les cinq refus principaux et les cinq négatifs restent visibles](images/recalage-mobiles-disponibilite.png)

Sur les 20 séquences principales, **15 sont exploitables après recalage** et leurs 15 mobiles sont retrouvés, sans faux candidat. Les cinq autres sont bloquées : les contrôles associés ne couvrent que trois quadrants au lieu des quatre requis. Les dix témoins passent le contrôle et donnent zéro candidat après. Les cinq négatifs à 12 étoiles sont tous bloqués : neuf associations d’ajustement et trois de contrôle, sous les minima 20 et 10. Une branche indisponible n’est pas un zéro faux candidat ; les champs correspondants restent `null` ou vides.

![Étoiles d’ajustement et contrôles, avec un quadrant sans contrôle associé](images/recalage-mobiles-refus.png)

*Annotation de pixels synthétiques effectivement générés : premier refus principal dans l’ordre du manifeste, séquence alignée 907, image 3/8. Les résidus sont petits mais la couverture de contrôle reste insuffisante. Aucun assouplissement du critère après mesure.*

### Comparer les mêmes séquences des deux côtés

![Comparaison appariée avant/après, avec nombre de séquences disponibles indiqué](images/recalage-mobiles-comparaison.png)

Pour les conditions dérive et combinaison principales, les **sept séquences comparables** passent de **557 faux candidats à zéro**, et conservent leurs sept mobiles. Il reste trois branches après indisponibles dans ces deux conditions : la réduction globale sur les dix séquences prévues est donc **indéfinie**, pas égale à 100 %. Le total avant des dix est 795 ; annoncer « 795 → 0 » comparerait des ensembles différents. Les tableaux conservent à la fois le bilan de toutes les séquences et les comptages appariés.

Les cinq refus principaux se répartissent ainsi : un aligné, un en dérive, un en rotation et deux en combinaison. Les trois refus de dérive/combinaison sont inclus dans ce total. La rotation 8 degrés, descriptive, donne 5/5 disponibles et mobiles conservés : les listes de contrôle diffèrent entre poses et conditions, ce résultat ne prouve pas qu’une rotation plus grande améliore le recalage.

Sur les quinze mobiles principaux disponibles, P95 des erreurs de position voisin de **0,0761 pixel**, erreur vectorielle maximale de vitesse voisine de **0,000895 pixel/s fictive**. Ces critères numériques sont satisfaits conditionnellement aux appariés. Les exigences portant sur les vingt séquences, leurs vingt mobiles et leur absence globale de faux candidats ne sont pas démontrées. Les contrôles négatifs et témoins remplissent leurs critères. Les huit critères préenregistrés et leur verdict faux sont conservés dans le rapport, sans nouveau réglage des moteurs.

### Une animation de coordonnées, avec pixels inchangés

![Exemple accepté : positions brutes et recalées sur le même fond fixe](images/recalage-mobiles-superposition.png)

![Huit ensembles de positions mesurées superposés au fond de la première image](images/recalage-mobiles-animation.gif)

*Exemple `combined-s607` fixé dans le plan : 79 faux candidats avant, zéro après, mobile conservé. Le fond est la première image et reste fixe ; seuls les symboles des positions mesurées changent. Ce ne sont pas des FITS recalés par interpolation. Gris : détections ; orange : faux candidats ; bleu : candidat apparié ; vert : vérité injectée, ajoutée au dessin seulement après recherche. Le bilan complet conserve les refus des autres graines.*

### Vérifier et conserver les limites

Les moteurs gelés, FITS, manifeste, vérité et rapports individuels sont contrôlés par empreintes. Les coordonnées de vérité ne sont lues qu’après les modèles et candidats des 40 séquences ; leur rôle est le bilan et le dessin. Aucun accès USB ou réseau d’analyse, aucune observation réelle ouverte. Les sorties restent dans `local/`, seules les figures synthétiques choisies sont copiées dans la documentation publique.

Les **277 tests passent en 26,55 secondes**, avec 17 nouveaux cas : géométrie, recouvrement, refus, contrôles réservés, intégrité des pixels, branche native mesurée une seule fois, séparation de vérité, campagnes partielles, critères non satisfaits et comptages comparables. Un premier exemple de test ne changeait que 5 % des erreurs et ne forçait pas le P95 au-dessus de sa limite : le cas synthétique de test a été corrigé, sans changer le seuil ou les données expérimentales. Les légendes gênant la lecture des premières figures ont été déplacées et les figures réexaminées. La reproduction des commandes et des résultats depuis le code committé est vérifiée avant publication.

Vérification finale depuis **`6235af5`**, sans modification suivie, dans des dossiers neufs et avec le même environnement Python : **30 commandes** du parcours aboutissent aux codes attendus, dont le code **2** de la nouvelle analyse. Les 320 images régénérées ont des empreintes identiques ; les 40 rapports individuels gelés, modèles et candidats sont identiques, et les comptages appariés du bilan final sont réconciliés avec les mêmes mesures. Les quatre PNG et le GIF sont identiques aux cinq illustrations publiques. La provenance du rapport change, pas le résultat expérimental : 15 principales disponibles, cinq bloquées, réduction globale indéfinie et critères globaux faux. Aucun test avec un enfant ou Windows vierge n’est revendiqué ; les traces et données restent sous `local/`.

Le résultat invite à étudier **une sélection des étoiles de contrôle mieux répartie**, dans un autre lot avec nouveau plan et jeu d’évaluation, tout en gardant un contrôle réservé et les exigences spatiales. Il ne faut pas lever les refus simplement parce que le modèle semble précis sur les étoiles présentes. Les difficultés faible/lent, la calibration, l’horloge et le budget céleste absolu restent ouverts ; ce lot ne qualifie aucun usage scientifique réel.

## 20. Réserver des contrôles mieux répartis et préparer le pilote Seestar

Le plan **`bbe9776`**, du 17 novembre 2026, a été committé, publié et vérifié sur GitHub avant le code. La [recette détaillée](CONTROLES-SPATIAUX.md) compare les partitions historique et spatiale sur les mêmes nouvelles images, avec mêmes seuils. Elle est dans les exemples expérimentaux : les commandes habituelles et moteurs gelés restent inchangés, l’application reste 0.10.0a1. La [mission dès 10 ans](DEMARRER-DE-ZERO.md#13-quater-mission--répartir-les-étoiles-de-contrôle) explique le principe en images.

### Réserver avant de chercher le modèle

Une réserve de contrôle doit permettre de vérifier plusieurs endroits du champ. La méthode spatiale classe les centres mesurés dans les intersections des quatre quadrants et des cellules 3×3. Elle permute les indices à l’intérieur des compartiments avec graine fixe, puis parcourt les quadrants et cellules à tour de rôle, en sautant les compartiments vides. Le nombre de contrôles reste le quart entier des détections, avec au moins un point ; les autres servent à l’ajustement.

![Partition réellement calculée sur les mêmes étoiles fictives](images/controles-spatiaux-selection.png)

*Bleu : détections utilisées pour ajuster ; orange : contrôles réservés avant appariement, hypothèses et ajustement. Les titres présentent les associations de contrôle mesurées après gel. Aucune réponse connue ou résidu n’a servi à choisir les contrôles.*

Les fonctions historiques de détection, hypothèses, ajustement, association, métriques et recherche des mobiles sont réutilisées. Aucun seuil n’est abaissé, aucune partition n’est réessayée après un refus. Les contrôles restent réservés par pose et partagent une référence mesurée ; cela ne constitue pas une indépendance statistique de toutes les erreurs. Une seule pose refusée continue à bloquer la branche après de sa séquence.

### Reproduire la comparaison

Les graines nouvelles 1103, 1201, 1301, 1409, 1511 donnent **50 séquences, 400 images et 30 mobiles**. Les huit conditions du lot 13 sont complétées par un quadrant réellement vide et une bande étroite, sans mobile. Toutes les images sont fictives, monoplans, sans Bayer ou modèle calibré du S50. Les champs et bruits sont appariés entre conditions pour une même graine.

Depuis la racine et avec les outils graphiques installés, choisir des dossiers neufs et prévoir environ 108 Mo pour les FITS, plus les rapports :

```powershell
.\.venv\Scripts\python.exe examples/compare_spatial_controls.py make local/controles-spatiaux-entree
.\.venv\Scripts\python.exe examples/compare_spatial_controls.py run local/controles-spatiaux-entree/manifest.json local/controles-spatiaux-entree/truth.json local/controles-spatiaux-rapport
.\.venv\Scripts\python.exe examples/plot_spatial_controls.py local/controles-spatiaux-entree/manifest.json local/controles-spatiaux-rapport/spatial.json local/controles-spatiaux-figures
```

**Codes attendus : 0, 0, 0 sur ce jeu.** L’analyse annonce `critères exploratoires : True`. Un code 2 signifierait un rapport produit avec critère non satisfait ; 1 une analyse impossible. L’ancien lot garde son code 2 et ses cinq refus principaux sur son propre jeu. Les données nouvelles ne corrigent pas rétroactivement ce résultat.

`spatial.json` contient les deux méthodes par condition/graine, modèles, indices et métriques de contrôles, candidats, erreurs sur appariés, comptages et transitions. `comparison.csv` et `report.md` donnent le bilan lisible. Les cinquante fichiers individuels gardent les deux méthodes avant évaluation ; ils sont gelés avant la première lecture des coordonnées de vérité. `progress.json` garde l’avancement et les interruptions. Un lot incomplet n’est pas présenté comme terminé, une branche indisponible n’est pas un zéro faux candidat. Les entrées et sorties restent sous `local/`, sans liens, écrasements ou accès réseau d’analyse.

### Compter le gain sans mélanger les jeux

![Disponibilité sur les mêmes images, avec les trois types de négatifs conservés](images/controles-spatiaux-disponibilite.png)

Sur les vingt séquences principales de **ce nouveau jeu**, l’ancienne partition en rend 17 disponibles et la spatiale 20. Les vingt mobiles sont retrouvés par la spatiale, sans faux candidat. Les dix-sept principales acceptées des deux côtés conservent leurs dix-sept mobiles, sans nouveau faux candidat. Les trois autres passent de refusées à disponibles. La rotation descriptive 8 degrés et un témoin gagnent chacun une disponibilité ; aucune séquence acceptée ne devient refusée dans cet essai.

Les vingt mobiles principaux de la méthode spatiale donnent P95 d’erreur de position **≈0,0776 pixel**, erreur vectorielle maximale de vitesse **≈0,00110 pixel/s fictive**. Les dix témoins sont acceptés sans candidat ; les quinze négatifs restent bloqués. Les huit critères fixés avant mesure sont satisfaits. Cela démontre un résultat sur ces images, pas une probabilité universelle de réussite ou une précision réelle du télescope.

La comparaison précédente du lot 13 restait à **15/20 sur ses anciennes graines**. Il ne faut pas annoncer « 15 → 20 » entre jeux différents : ici, la comparaison sur les mêmes nouvelles images est **17 → 20**. Les erreurs sont conditionnelles aux sources appariées et les sous-ensembles acceptés diffèrent ; aucune amélioration universelle de précision n’est déduite du seul gain de disponibilité.

### Les vrais manques restent des refus

![Trois cas d’insuffisance réellement présents dans les images fictives](images/controles-spatiaux-negatifs.png)

*Graine 1103, deuxième image des négatifs : douze étoiles, quadrant vide et bande étroite. Orange : contrôles effectivement sélectionnés. Un meilleur parcours des zones ne crée ni étoiles ni surface couverte. Les quinze séquences négatives restent refusées.*

![Huit images fictives montrant les sélections avant ajustement](images/controles-spatiaux-animation.gif)

*Séquence de combinaison et graine 1103 fixées dans le plan. La première image est la référence commune, sans partition ajustée ; les suivantes montrent les contrôles par pose sur leurs pixels fictifs. Ce sont des images synthétiques réellement calculées, pas des captures d’écran.*

### Contrôles logiciels et correction d’une illustration

Les **297 tests passent en 46,51 secondes**, dont vingt nouveaux cas : déterminisme, indices uniques et complémentaires, couverture et vrais manques, séparation avant ajustement, contrôles perturbés avec partition figée, détection partagée, transitions et comparaison appariée, campagnes partielles, lecture seule et vérité après les deux méthodes de toute la campagne. Les empreintes des moteurs historiques et de la recette antérieure sont vérifiées ; les FITS et rapports gelés sont préservés.

L’inspection visuelle a détecté un mauvais raccord de séquence dans le dessin des négatifs : les cercles provenaient d’un autre cas que le fond affiché. Le programme de dessin a été corrigé avant publication et les figures réexaminées. Les résultats de calcul, critères et pixels n’ont pas été changés. Les premiers dessins restent dans les essais locaux. Reproduction du jeu, des modèles/candidats, des mesures, des figures et des commandes pédagogiques depuis le code committé avant publication.

Cette reproduction a abouti depuis **`74b57b0`**, sans modification suivie, dans des dossiers neufs et le même environnement : **33 commandes** du parcours aux codes attendus, **400 images** identiques par empreinte, cinquante rapports individuels gelés et deux méthodes identiques en modèles/candidats/bilan. Les trois PNG de mesures/sélections, le GIF de huit images et le PNG conceptuel sont identiques aux illustrations publiques. L’ancienne recette garde son code 2 et ses refus ; la nouvelle donne 0 sur le nouveau jeu. La provenance change avec le commit propre, pas les résultats. Les traces restent locales ; aucun test utilisateur avec un enfant ou sur Windows vierge n’est revendiqué.

### Quand passer aux images du Seestar ?

![Préparer la série, faire un essai exploratoire, puis qualifier les mesures scientifiques](images/passage-seestar-pilote.png)

*Schéma conceptuel, pas un résultat instrumental ou une capture d’écran. Il décrit des conditions de passage, sans date promise.*

Les vraies observations servent déjà à l’inventaire et aux contrôles stellaires sur copies locales. Le manifeste local existant confirme seulement le petit échantillon déjà documenté ; aucun FITS réel ou chemin USB n’a été ouvert dans ce lot. Il ne suffit pas à notre chaîne de suivi. Le [document de passage au Seestar](PASSAGE-AUX-IMAGES-SEESTAR.md) propose **le prochain lot pour préparer une série réelle compatible**, en consultant d’abord les manifestes locaux et les copies disponibles. Si cette série convient, planifier et exécuter un pilote exploratoire distinct ; sinon, préciser les fichiers à copier avant d’avancer.

Un essai réel ne doit pas attendre toutes les fonctions du projet, mais il doit établir le traitement des pixels Bayer/mono/RGB, l’ordre des poses, le recalage et ses contrôles. Les heures scientifiques et le budget d’erreur restent à qualifier avant des vitesses physiques ou des soumissions. Les observations réelles ne doivent jamais être réétiquetées comme synthétiques pour contourner les protections. L’autorisation USB reste en lecture seule et n’a pas été utilisée ici ; seules les illustrations fictives/conceptuelles choisies sont publiées.

## 21. Préparer huit poses réelles et publier les exemples autorisés

Le plan **`594c19e`**, du 17 novembre 2026, a été committé, publié et vérifié avant le code et les copies. Le complément **`ae07304`** a ensuite été publié avant le code de diffusion, après l’autorisation explicite du mainteneur de partager les images réelles sous Creative Commons Public Domain, mise en œuvre par **CC0 1.0 Universal**. La [préparation détaillée](PREPARER-SERIE-SEESTAR.md) donne le contrat ; la [mission dès 10 ans](DEMARRER-DE-ZERO.md#nouvelle-mission--préparer-huit-poses-seestar) permet de refaire les étapes sur des images fictives sans clé USB.

### Sélectionner sans regarder les pixels

Nous avons utilisé uniquement le manifeste local existant pour regrouper les séances avec le module déjà livré. Les groupes admissibles sont classés par nombre de membres décroissant, puis identifiant ; le premier bloc chronologique de huit primaires 2D distinctes avec écarts déclarés positifs ≤30 s est retenu. Les configurations restent séparées ; les compteurs d’empilement incompatibles et les chemins dangereux sont refusés. Aucun parcours récursif nouveau de la clé et aucune sélection fondée sur la beauté des images ou sur un mobile détecté.

La racine source est fournie explicitement dans le plan privé ; la commande de planification ne la sonde pas et ne rouvre pas automatiquement l’ancien chemin de l’inventaire. Elle produit `plan.json`, `selection.json` et un rapport local, ou un manque de données explicite (code 2). Les dates, chemins, coordonnées et noms d’observation restent dans les répertoires ignorés.

### Copier seulement les huit fichiers de la liste

Après publication du plan, le support et le dossier déclaré ont été vérifiés. `gar workset` a lu uniquement les sources sélectionnées en `rb`, vers des destinations locales neuves en `xb`. Pour les huit poses, les empreintes historiques, source avant, copie et source relue après concordent ; taille et date de modification source sont contrôlées pendant la copie. Les en-têtes complets sont collectés sur les copies. Aucun fichier FITS n’est réécrit, aucun cache/rapport/dossier n’est créé sur le support et aucune source n’est déplacée ou supprimée.

`prepare_seestar_series.py audit` n’ouvre ensuite que ces copies locales. Il vérifie les empreintes, la correspondance au plan, HDU primaire, dimensions, configuration observée, dates et durées déclarées, puis la lecture des pixels et les valeurs finies. Les champs absents restent inconnus ; le comptage ≥65 000 est descriptif, sans saturation étalonnée supposée. Les huit fichiers ont terminé ce contrôle, avec `copies_prepared: true`. Ce statut ne valide ni un champ commun sur étoiles, ni un recalage, ni l’heure, ni un mobile.

### Refaire les six commandes avec des données fictives

Utiliser des dossiers neufs depuis la racine et les outils graphiques déjà installés :

```powershell
.\.venv\Scripts\python.exe examples/make_series_demo.py local/serie-demo-archives
.\.venv\Scripts\gar.exe inventory local/serie-demo-archives --output local/serie-demo-inventaire
.\.venv\Scripts\python.exe examples/prepare_seestar_series.py plan local/serie-demo-inventaire/manifest.json --source-root local/serie-demo-archives --output local/serie-demo-plan
.\.venv\Scripts\gar.exe workset local/serie-demo-plan/selection.json --output local/serie-demo-copies
.\.venv\Scripts\python.exe examples/prepare_seestar_series.py audit local/serie-demo-plan/plan.json local/serie-demo-copies/workset.json --output local/serie-demo-audit
.\.venv\Scripts\python.exe examples/plot_series_preview.py local/serie-demo-audit/series.json local/serie-demo-apercu
```

**Résultat attendu : six codes 0**, douze poses fictives inventoriées, huit sélectionnées/copiées/contrôlées, aperçu fictif produit. Les refus de sélection donnent un code 2 et pas de sélection inventée ; les problèmes de lecture/intégrité peuvent laisser un rapport incomplet, à conserver. Choisir une nouvelle sortie après résolution, sans nettoyage des sources.

![Aperçu réellement calculé sur les copies fictives de l’exercice public](images/exemple-preparation-serie.png)

*Douze images ont été inventées pour cet exercice, huit sont retenues. Les tests n’utilisent pas les observations personnelles, même pour vérifier les branches de code destinées aux entrées réelles.*

### Regarder une vraie série, avec son autorisation de diffusion

![Huit poses réelles Seestar rendues en gris et diffusées sous CC0](images/reels/seestar-serie-cc0.png)

![Première pose réelle de la même série, exemple CC0](images/reels/seestar-pose-01-cc0.png)

*Vraies observations, pas des pixels synthétiques ou des captures d’écran. La [notice CC0](images/reels/LICENCE.md) liste exactement ces deux PNG et décrit leur provenance. Une moyenne 2×2 puis un étirement asinh, fixé depuis la première pose, servent à l’affichage gris commun. Les FITS exacts ne sont pas modifiés ; aucun dématriçage/calibration scientifique ou candidat de mobile n’est validé par ces images.*

Les aperçus réels sont privés par défaut. À la suite de l’autorisation explicite du mainteneur, `--public-cc0` a produit deux rendus avec titres neutres et réencodage RGB sans EXIF, texte ou métadonnées PNG héritées. Les deux PNG uniquement ont été copiés dans le dossier public dédié, avec notice CC0 1.0 et empreintes de ces PNG. Les FITS, en-têtes complets, dates/coordonnées, chemins et rapports restent sous `local/`. Les pixels célestes sont volontairement publics, sans promesse d’anonymisation du champ. Le code et les autres documents conservent leur régime GPL-3.0-or-later.

### Vérifications et limites conservées

Les **316 tests logiciels passent en 56,97 secondes**, dont 19 nouveaux cas : planification sans accès aux sources, sélection déterministe et chronologique, groupes incompatibles, doublons, dates/gaps, manque de huit poses, chemins dangereux, modification de source, audit strictement local, en-têtes divergents, interruption et export CC0 sans métadonnées. Les tests du mode d’entrée réelle emploient eux aussi des images inventées. Ces vérifications logicielles sont distinctes du constat réel de copie et ne qualifient pas les mesures astronomiques.

La reproduction a abouti depuis le commit propre **`2e57d18`** : six nouvelles commandes pédagogiques réussies dans des dossiers neufs, douze images fictives identiques par empreinte, huit copies préparées et aperçu public fictif identique. Les 33 commandes antérieures gardent leur vérification documentée au lot précédent, leurs sources n’étant pas modifiées ; elles ne sont pas présentées comme rejouées pour ce complément. Le plan et l’audit réels sont identiques, les huit copies inchangées et les deux PNG CC0 reproduits à l’identique. Cette vérification bloque l’ouverture et le sondage du volume source : aucun nouvel accès USB. Les anciennes empreintes source sont celles du journal de copie, pas une nouvelle lecture du support. Les deux PNG publics sont RGB et sans métadonnées intégrées ; notice, liens et fichiers destinés à Git sont contrôlés. Les preuves détaillées restent sous `local/`.

**Et les candidats et les GIF ?** Les animations des sections précédentes montrent des simulations. Dans le dernier essai fictif de contrôle spatial, vingt mobiles ajoutés volontairement ont été retrouvés sur vingt séquences principales, sans faux candidat dans ces cas. Sur les huit vraies poses Seestar de ce lot, aucune recherche n’a encore été lancée : `motion_searched` reste faux. Il n’existe donc pas encore de candidat ni de GIF de mouvement réel issu de cette série. Cela ne signifie pas qu’une recherche a conclu à l’absence d’objet.

La série réelle existe maintenant localement pour le prochain lot : adapter le traitement Bayer et les coordonnées, recaler avec contrôles réservés, puis chercher et revoir les candidats avec une chronologie explicitement non qualifiée. La recette fictive ne peut pas recevoir directement les FITS Seestar de plus grande taille et ne doit pas les réétiqueter en synthétiques. Le [document de passage au réel](PASSAGE-AUX-IMAGES-SEESTAR.md) distingue cette préparation terminée du pilote exploratoire encore à réaliser. Aucun résultat scientifique ou export n’est annoncé.

## 22. Premier essai de recherche sur les huit vraies poses

**Nous avons maintenant un premier résultat réel : sept alignements acceptés vers la première pose, recherche achevée avec zéro candidat et GIF réel avant/après produit localement.** L'essai ne démontre pas l'absence de tout mobile. Il concerne ces huit images et les seuils prévus. L'horloge, la sensibilité réelle du détecteur, la photométrie et l'astrométrie absolue restent non qualifiées.

Le plan [**`8f5a64b`**](https://github.com/steveprudhomme/gnu-astrophotography-recycle/commit/8f5a64b819d301f7c495b5e9903f3c622cf30639) a été committé, publié et vérifié avant le code. La [nouvelle recette](PILOTE-MOBILES-SEESTAR.md) garde les moteurs et anciens protocoles inchangés. Le [parcours dès 10 ans](DEMARRER-DE-ZERO.md#nouvelle-mission--aligner-les-étoiles-et-chercher-un-mobile) propose neuf commandes pour refaire un mobile, un témoin sans mobile et un refus utile. Tous les fichiers de ces exercices sont inventés.

### Comprendre ce que l'on fait

Sur huit photos, le télescope peut bouger : toutes les étoiles glissent ensemble. Nous calculons la rotation et le déplacement qui ramènent leurs positions dans la première photo. Environ un quart des étoiles est réservé comme témoin avant le calcul ; elles ne servent ni aux hypothèses ni à l'ajustement. Si les témoins ne permettent pas de vérifier le résultat, la recherche est bloquée.

La moyenne 2×2 donne un plan d'intensité pour la recherche, pas une couleur calibrée. Les blocs contenant un pixel non fini ou ≥65 000 sont masqués. Les positions détectées reviennent en coordonnées natives par `2*x+0,5`. Seules ces positions sont transformées pour mesurer les trajectoires ; les FITS exacts ne sont jamais réécrits. L'interpolation du GIF est uniquement un outil d'affichage.

![Exercice fictif de la nouvelle recette : brut à gauche, affichage aligné à droite](images/exemple-pilote-seestar.gif)

*Animation calculée sur des images inventées ; aucune fausse capture d'écran. Le cercle montre le candidat mesuré. Le GIF de la vraie série est un fichier distinct, gardé localement. La cadence de 0,6 seconde par pose est artificielle.*

### Trois commandes pour commencer, puis deux témoins

Depuis la racine du projet, avec les dépendances déjà installées et des dossiers neufs :

```powershell
.\.venv\Scripts\python.exe examples/make_seestar_pilot_demo.py local/pilote-exercice
.\.venv\Scripts\python.exe examples/run_seestar_pilot.py local/pilote-exercice/plan/plan.json local/pilote-exercice/workset/workset.json local/pilote-exercice/audit/series.json --output local/pilote-exercice-analyse
.\.venv\Scripts\python.exe examples/plot_seestar_pilot.py local/pilote-exercice-analyse/pilot.json local/pilote-exercice-figures
```

Les trois codes attendus sont 0. Le générateur crée huit images Bayer fictives 512×512, cent étoiles et un mobile, avec dérive et rotation, prépare des copies puis les audite. La vérité reste dans un fichier séparé, que l'analyse n'ouvre pas. Le résultat attendu est un candidat et sept alignements acceptés ; le dessin donne un GIF, un graphique des contrôles et huit vignettes du candidat.

Refaire les commandes complètes du parcours avec `--case control` donne zéro candidat après une recherche achevée, codes 0/0/0. Avec `--case insufficient`, douze étoiles ne suffisent pas : code d'analyse 2, recherche bloquée, candidat `null`, GIF brut seulement ; les codes sont 0/2/0. Un résultat refusé n'est pas un zéro candidat. Les erreurs de lecture/intégrité peuvent garder un rapport `incomplete`, code 1 ; conserver cet essai avant de choisir une autre sortie. Le premier essai de génération avait passé un chemin au lieu du contenu de sélection à `prepare_workset` ; cet appel a été corrigé sur données fictives et le dossier partiel conservé, sans changement de seuil du moteur.

![Les contrôles réservés dans le nouvel exercice fictif](images/exemple-pilote-seestar-controles.png)

![Huit vignettes fictives pour revoir la trajectoire candidate](images/exemple-pilote-seestar-candidat.png)

*Le graphique ne remplace pas les exigences de couverture et d'effectif ; les vignettes utilisent un même champ et les positions mesurées. Les réponses inventées sont lues seulement par la vérification des résultats, jamais par la recherche ou le dessin.*

### Ce que l'essai réel a réellement vérifié

Le programme a réaudité le plan, le workset et les huit copies déjà locales, puis comparé ce nouvel audit à celui fourni. Les en-têtes, dates, dimensions et empreintes correspondent ; aucun chemin d'archive n'est ouvert. L'exécution réelle a bloqué toute ouverture ou sondage d'un volume externe, toute écriture FITS et toute connexion réseau. Aucun nouvel accès USB n'a été tenté.

Les sept modèles passent les critères prévus, sans abaisser un seuil : 64 à 77 contrôles associés par pose, neuf cellules et quatre quadrants, P95 d'environ 0,69 à 1,09 pixel natif sous la limite 1,5. Le champ commun est restreint par les transformations inverses de toutes les poses, avec marge native de 16 pixels. La recherche de trajectoires est terminée : **zéro candidat**, pas une analyse bloquée. Le GIF réel montre les huit images brutes et leur affichage aligné ; aucun cercle de mobile n'y est ajouté.

Les temps sont seulement les différences entre dates déclarées, pas des heures UTC corrigées ou des milieux de pose. Les champs de trajectoire utilisent des secondes déclarées. Le programme ne calcule aucune vitesse physique ou identification astronomique. Les copies sont hachées avant/après analyse et dessin et restent intactes. Le rapport de préparation précédent est conservé : son statut historique ne remplace pas le nouveau verdict dans `pilot.json`.

### Vérifications et limites

Les 19 nouveaux tests fictifs couvrent récupération du mobile connu, témoin sans candidat, refus d'effectif, retour au repère natif, transformation inverse, vrai domaine commun, masques, en-têtes/audit/empreintes incohérents, absence d'accès archive/vérité/réseau, lecture seule, sorties partielles et refus d'écrasement. Une première exécution des tests n'a pas pu créer ses dossiers temporaires à cause des droits Windows ; une nouvelle sortie locale et les droits de création nécessaires ont permis de les exécuter. Ce problème d'environnement n'est pas présenté comme un échec scientifique.

La vérification finale a abouti depuis le commit propre **`80ada2e`** : **335 tests en 83,31 secondes**, neuf nouvelles commandes aux codes attendus, dont 2 pour le refus. Les huit FITS du nominal, ses modèles/positions/candidat et les trois figures publiques sont identiques. Les trois cas donnent respectivement un candidat, zéro et une recherche bloquée. Le pilote réel reproduit conserve les sept modèles, positions et zéro candidat ; ses trois figures privées, dont le GIF de huit poses à 600 ms, sont identiques. Les huit copies restent intactes et les gardes n'enregistrent aucune tentative d'accès externe ou d'écriture FITS. La provenance du rapport suit le commit propre, sans être annoncée octet pour octet identique au premier rapport de développement.

Les 39 commandes pédagogiques antérieures conservent leurs preuves précédentes ; elles n'ont pas été toutes rejouées pour ce lot. Les contrôles publics portent sur 175 fichiers et 32 ancres Markdown ; les deux PNG CC0 restent identiques et sans métadonnées intégrées. Les GIF et rapports réels restent sous `local/`, avec leur provenance ; seules les trois nouvelles figures fictives sont copiées dans la documentation. L'autorisation CC0 des deux PNG réels existants ne publie pas les nouveaux GIF ou coordonnées. Aucun essai avec un enfant ou sur un ordinateur vierge n'est revendiqué.

Un résultat zéro dans huit images ne mesure ni taux de faux positifs ni probabilité de retrouver un objet. La luminosité, les vitesses accessibles, les masques, le Bayer et les étoiles proches limitent cette exploration. Le prochain protocole pourra évaluer la récupération d'injections sur copies réelles et la dépendance aux seuils, en conservant ce premier essai inchangé. Aucune découverte ni soumission scientifique n'est annoncée.

## 23. Publier les exemples réels autorisés sous CC0

Le mainteneur a réaffirmé le 17 novembre 2026 que ses images peuvent être publiées dans le domaine public et servir d'exemples. Cette autorisation couvre aussi le GIF du pilote et ses illustrations. Le plan **`5c662ae`** a été committé, publié et vérifié avant le code de diffusion. La [notice CC0](images/reels/LICENCE.md) liste maintenant exactement cinq médias : les deux PNG précédents, le GIF réel avant/après, sa première vue et le graphique réel des contrôles. Les anciens PNG et leurs empreintes sont conservés.

### Regarder le vrai ciel, puis comprendre le dessin

![Huit vraies poses Seestar avant et après alignement, publiées sous CC0](images/reels/seestar-pilote-cc0.gif)

*Observation réelle, pas un exercice inventé ou une capture d'écran. À gauche, les poses brutes ; à droite, leur affichage aligné. Huit vues, 0,6 seconde par vue, répétées en boucle. C'est une cadence de lecture choisie pour regarder, pas la cadence du télescope. Les étoiles sont alignées par les modèles déjà contrôlés ; aucun mobile n'a été détecté par cet essai.*

Imagine que tu remets des feuilles transparentes au même endroit pour comparer leurs points. L'affichage de droite fait quelque chose de semblable. Il utilise une interpolation pour dessiner les pixels à leur nouvelle place ; cette image dessinée ne sert pas à mesurer les trajectoires. La recherche du lot précédent utilisait les positions mesurées, sans réécrire les FITS. Publier le GIF ne relance pas la recherche et ne change pas son résultat : **zéro candidat aux seuils prévus**.

![Contrôles sur les vraies étoiles réservées, illustration CC0](images/reels/seestar-pilote-controles-cc0.png)

À gauche, chaque point mesure le P95 des erreurs sur les étoiles témoins d'une pose, en pixels de la photo originale ; il reste sous la limite rouge. À droite, la barre compte les témoins associés, au-dessus du minimum dix. Les règles demandent aussi une bonne répartition dans le champ. Ce graphique vient du vrai rapport du pilote, sans fabriquer de valeurs et sans fournir ses positions ou en-têtes privés.

### Préparer un rendu autorisé

Le mode habituel garde un titre privé pour les observations réelles. Si le propriétaire autorise leur diffusion sous CC0, l'option explicite prépare un rendu public depuis le rapport et les copies déjà locales :

```powershell
.\.venv\Scripts\python.exe examples/plot_seestar_pilot.py local/mon-pilote/pilot.json local/mon-pilote-cc0 --public-cc0
```

Les noms ci-dessus sont des exemples : il faut ses propres résultats réels préparés et une sortie neuve. Ce n'est pas une commande à ajouter à l'exercice fictif ; elle refuse les rapports fictifs et les images marquées comme inventées. Tu peux déjà regarder les médias CC0 fournis dans ce dépôt sans posséder les FITS privés. Les commandes des exercices et leurs réponses restent inchangées.

Le programme vérifie les empreintes, lit les copies en lecture seule et crée des titres « images réelles — CC0 1.0 ». Il enlève les métadonnées héritées des PNG. Le GIF garde les informations nécessaires à ses couleurs, huit vues, durées et boucle, mais ni commentaire, EXIF ou XMP privé. Le journal `figures.json` reste local : il ne faut pas le copier avec les images publiques. La notice donne les noms, empreintes, provenance, transformations et licence des seuls médias diffusés.

### Vérifier avant de publier

Les trois nouveaux tests emploient uniquement des pixels inventés, même pour simuler une entrée réelle sans marqueur : refus d'un rapport fictif, refus d'un rapport mal étiqueté dont les images sont fictives, export sans métadonnées privées et conservation des entrées. Les **338 tests passent en 78,93 secondes**. Les nouveaux PNG réels sont RGB sans métadonnées intégrées ; le GIF a huit vues de 600 ms et une boucle. Les deux PNG initiaux, le rapport du pilote et les huit copies sont inchangés. Les gardes ne relèvent aucune tentative d'accès externe ou d'écriture FITS ; aucune nouvelle analyse n'est exécutée.

La reproduction a abouti depuis le commit propre **`305eeed`** : trois nouveaux médias CC0 identiques par empreinte, deux PNG précédents inchangés, trois rendus privés par défaut identiques au lot 16. Les cinq empreintes de notice et 36 ancres Markdown sont vérifiées ; rapport et huit copies sont intacts, sans nouvelle recherche. Les gardes du rendu CC0 n'enregistrent aucune tentative d'accès externe ou d'écriture FITS. Les 178 fichiers publics sont revus avant publication ; les journaux restent sous `local/`.

Les sources des moteurs, le verdict de recherche et les anciennes preuves restent inchangés. Les tests et les exemples fictifs sont distincts des observations CC0 ; les FITS, dates d'observation, chemins, coordonnées et rapports restent ignorés. Les pixels célestes autorisés sont volontairement publics ; ils ne sont pas présentés comme anonymisés. Cette vérification ne revendique pas un essai de compréhension avec un enfant ou sur un ordinateur vierge.

## 24. Chercher des points ajoutés au fond Seestar

**Ce nouvel essai retrouve 10 mobiles artificiels sur 36 sur le fond réel, avec 26 manques et zéro indisponible.** Il ne découvre aucun objet : le témoin sans ajout reproduit exactement le pilote naturel à zéro candidat. Le plan [**`9344495`**](https://github.com/steveprudhomme/gnu-astrophotography-recycle/commit/9344495d49d8051e74663ab41e49de6ce05286eb) a été committé et publié sur `codex/injections-seestar` avant le code. La [méthode détaillée](INJECTIONS-SEESTAR.md) et la [mission dès 10 ans](DEMARRER-DE-ZERO.md#nouvelle-mission--retrouver-des-points-ajoutés-exprès) expliquent les cinq nouvelles commandes.

### Pourquoi ajouter un point que l'on connaît ?

Imagine que nous cachons un petit point dans plusieurs photos, en le faisant avancer. Nous savons où nous l'avons mis, mais le chercheur de points ne reçoit pas ces réponses. Il trouve d'abord ses candidats. Ensuite seulement, nous vérifions ce qu'il a retrouvé, ce qui manque et ce qui est sans correspondance. Cette méthode aide à comprendre les limites d'un résultat « zéro candidat » sur une série naturelle.

![Témoin, point faible et point plus brillant sur un fond entièrement fictif](images/exemple-injections-animation.gif)

*Images et ajouts entièrement fictifs pour le parcours public. Vert : réponse d'injection ajoutée au dessin après recherche et score ; cyan : candidat effectivement associé. Aucun cercle vert n'est une détection inventée. La lecture de 0,6 seconde par pose est artificielle ; l'interpolation sert seulement à l'affichage.*

### Garder le recalage, les seuils et les originaux

Nous conservons les huit modèles déjà acceptés du pilote, le détecteur et l'association, vérifiés par empreintes. Cet essai mesure donc la récupération **conditionnellement au recalage gelé**, pas la capacité de toute la chaîne à recalculer un bon alignement en présence d'un mobile. Les positions d'injection sont ramenées dans chaque pose par l'inverse des mêmes modèles : leur erreur astrophysique n'est pas testée par cette construction.

Trois pics (3/6/12 fois le bruit de première pose), quatre vitesses (0,03/0,15/0,5/1,2 pixel natif par seconde déclarée), trois départs/directions fixes donnent 36 séries à un ajout, plus un témoin. Le pic n'est pas un signal/bruit étalonné. Le point gaussien a sigma 2,2 pixels natifs, tronqué à cinq sigma ; il est ajouté aux plans d'intensité 2×2 float32 dans de nouveaux `.npy` locaux. Aucun FITS n'est réécrit, aucun marqueur synthétique ou faux temps n'est ajouté aux observations. Les masques et confusions avec les étoiles sont conservés, sans repositionnement après résultat.

Un voisinage hors du champ commun avec marge native 32 pixels rend le cas indisponible. La recherche conserve ensuite les mêmes seuils, domaine commun et associations du pilote, sans troncature silencieuse. Le modèle d'ajout ne simule ni réponse Bayer, bruit de photons supplémentaire, PSF instrumentale étalonnée ou traînée intra-pose. Les temps restent déclarés et non qualifiés.

### Refaire les cinq étapes sur un fond inventé

Depuis la racine, avec dépendances installées et sorties neuves :

```powershell
.\.venv\Scripts\python.exe examples/make_injection_background.py local/injections-exercice-fond
.\.venv\Scripts\python.exe examples/injection_recovery.py generate local/injections-exercice-fond/pilot/pilot.json local/injections-exercice-suite
.\.venv\Scripts\python.exe examples/injection_recovery.py analyze local/injections-exercice-suite/manifest.json local/injections-exercice-analyse
.\.venv\Scripts\python.exe examples/injection_recovery.py score local/injections-exercice-suite/manifest.json local/injections-exercice-suite/truth.json local/injections-exercice-analyse/analysis.json local/injections-exercice-bilan
.\.venv\Scripts\python.exe examples/plot_injection_recovery.py local/injections-exercice-bilan/score.json local/injections-exercice-figures
```

Les cinq codes attendus sont **0**. Le fond fictif comprend cent étoiles hors des trois couloirs d'injection, bruit et dérive/rotation inventés. La génération écrit 296 plans dérivés, le manifeste et la vérité séparée. L'analyse ne reçoit pas le fichier de vérité et gèle tous ses résultats avant le score. Le score apparie au plus un candidat par injection sur au moins cinq points, RMS ≤1 pixel natif et erreur vectorielle de vitesse ≤0,05 pixel par seconde déclarée. Le dessin révèle ensuite les réponses pour les cas faible/brillant à vitesse 0,5 et position 1, préchoisis avant mesure.

Résultat fictif : **12/36 retrouvées, 24 manquées, zéro indisponible**, témoin sans candidat. Les trois brillantes à vitesse 0,5 sont retrouvées et aucun ajout trop lent à 0,03 n'est récupéré. Les cas faibles manqués restent publiés. Les couloirs dégagés simplifient cet exercice ; il ne représente pas toute la confusion du fond réel.

![Bilan calculé sur le nouveau fond entièrement fictif](images/exemple-injections-carte.png)

*Chaque case utilise les trois positions prévues. Les cas bloqués restent affichés et ne sont pas transformés en recherches à zéro. Trois trajets sur les mêmes images ne sont pas des observations indépendantes, ni une probabilité universelle de détection.*

### Résultat sur le fond réel et fichiers conservés

Les 36 injections sont testables. Pics 3 : aucune retrouvée ; pics 6 : une à vitesse 0,5 et une à 1,2 ; pics 12 : deux à 0,15, trois à 0,5 et trois à 1,2. Aucun ajout à 0,03 n'est récupéré. Total : **10 retrouvées, 26 manquées, zéro indisponible**. Le témoin garde exactement les détections et trajectoires du pilote initial, avec zéro candidat ; aucun candidat non associé n'apparaît dans ce lot. Sur fond réel, un éventuel non-associé resterait d'origine inconnue, pas un faux positif établi.

Les deux fonds, leurs bruits et leurs temps déclarés diffèrent : les 12/36 et 10/36 ne comparent pas statistiquement l'efficacité de deux capteurs. Le tableau complet est dans le document de méthode ; les rapports, positions, dérivés et animations mixtes restent privés sous `local/`, avec titre explicite « fond réel + ajouts artificiels ». Les trois nouvelles figures publiques sont entièrement fictives ; les cinq médias réels CC0 existants restent inchangés. Aucune lecture USB ou connexion réseau d'analyse, aucune écriture FITS ; copies et rapport naturel intacts.

### Vérifications et prochaines décisions

Les 18 nouveaux tests sont entièrement fictifs : récupération nominale et vitesse trop lente, amplitude/masque et transformation inverse, appariement unique, absence d'accès à la vérité/archives/réseau, déterminisme, refus de modèles/chemins/empreintes/pickle, limites et interruptions. Une analyse incomplète ou modifiée ne peut pas être scorée ; tous les cas bloqués gardent des candidats `null`, même dans les comptes globaux inconnus. Le code 2 signale des cas indisponibles ou l'échec des critères de l'exercice fictif ; le code 1 conserve les erreurs/incomplétudes. Choisir une nouvelle sortie après correction, sans effacer les essais.

La suite complète a passé **356 tests en 123,53 secondes**. L'inspection des premières vignettes montrait peu les points faibles ; le contraste d'affichage a été rendu lisible avec des limites fixées au fond de première pose −3 sigma et +15 sigma, communes aux trois vues. Le détecteur, les mesures et les résultats restent inchangés ; le contrôle de dessin est rejoué après cet ajustement. Reproduction des cinq commandes, dérivés, candidats, bilans et figures depuis le code committé avant publication, en conservant les anciennes preuves sans tout rejouer.

Ce premier bilan indique des manques dans les conditions prévues, sans magnitude limite ou efficacité universelle annoncée. Toute nouvelle PSF, trajectoire ou modification de seuil demandera un protocole préenregistré ; les seuils ne sont pas abaissés pour faire réussir ce lot. La branche dédiée sera publiée et revue dans une PR vers `main`, puis fusionnée après les vérifications prévues.
