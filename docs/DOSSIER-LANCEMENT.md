# Dossier de lancement — GNU Astrophotography Recycle

Version de cadrage du 15 novembre 2026, actualisée pour l’Alpha 0.10 le 17 novembre. Les deux prompts fournis servent de cahier des charges ; leurs formulations techniques sont examinées comme des propositions à vérifier. Une inspection privée des en-têtes a guidé l’inventaire ; les contrôles stellaires, la préparation temporelle et le prototype de mobiles fictifs livrés ensuite sont décrits ci-dessous, avec leurs limites. Les références sont rassemblées dans [SOURCES.md](SOURCES.md).

## 1. Identité du projet et modèle de README

**Nom confirmé par le fondateur : GNU Astrophotography Recycle.** Le [dépôt public](https://github.com/steveprudhomme/gnu-astrophotography-recycle) utilise `gnu-astrophotography-recycle`. Le module et la commande locale sont `gar` ; aucun paquet PyPI n’est publié et la disponibilité de ce nom sur un registre n’est pas affirmée. Le préfixe GNU appartient au nom choisi ; il ne désigne pas une reconnaissance officielle. La procédure d’admission comme paquet GNU est distincte du choix de licence.

Mission : réutiliser les archives de poses individuelles du Seestar S50 pour produire des inventaires puis, lorsque leur qualité le permet, des mesures astronomiques traçables. Priorités : préserver les originaux, rendre les erreurs visibles et quantifier les incertitudes.

Le [README livré](../README.md) présente la mission, la licence `GPL-3.0-or-later`, le statut Alpha 0.10, les fonctionnalités disponibles et les limites. Il donne accès au [parcours complet pour débuter dès 10 ans](DEMARRER-DE-ZERO.md), au tutoriel de référence, aux exemples synthétiques et à leur animation. Les performances sur mobiles réels, la photométrie et la distribution portable restent à développer ou valider.

Le [banc de limites du lot 12](LIMITES-DETECTEUR.md) conserve le moteur 0.10 gelé : 120 séquences fictives, cinq nouvelles graines, 19 contrôles supplémentaires et **260 tests** au total. Ses graphiques et son animation expliquent les manqués faibles/lents et les faux candidats dus au déplacement commun du champ. Ces essais descriptifs ne qualifient aucune observation réelle ; le tutoriel ajoute une mission illustrée pour les reproduire.

La [recette recalage/mobiles du lot 13](RECALAGE-MOBILES-SYNTHETIQUES.md) ajoute 17 contrôles, soit **277 tests**, et 40 séquences fictives. Les critères globaux ne sont pas tous satisfaits : cinq séquences principales sont refusées pour couverture de contrôle insuffisante. Les mêmes moteurs et pixels sont conservés ; le tutoriel distingue réduction de faux candidats sur les séquences comparables et indisponibilité sur les autres, avec graphiques et superposition animée de coordonnées.

Le [lot 14](CONTROLES-SPATIAUX.md) ajoute vingt cas, soit **297 tests**, et une partition spatiale expérimentale séparée du module habituel. Sur cinquante nouvelles séquences fictives, elle atteint 20/20 principales disponibles contre 17/20 pour l’ancienne partition sur les mêmes images, sans faux candidat et en bloquant les quinze négatifs. Le [prochain jalon Seestar](PASSAGE-AUX-IMAGES-SEESTAR.md) proposé est la préparation d’une série réelle et d’un pilote exploratoire distinct ; l’échantillon actuel est trop court et les temps scientifiques restent à qualifier.

Le [lot 15](PREPARER-SERIE-SEESTAR.md) prépare huit poses réelles en copies locales vérifiées, sans modifier le support source. Il ajoute 19 tests synthétiques, soit **316 tests**, et six commandes d'exercice public. Deux PNG réels sont diffusés avec l'autorisation du mainteneur sous [CC0 1.0](images/reels/LICENCE.md), avec provenance et métadonnées retirées ; le code reste GPL. Les FITS et rapports restent privés.

Le [lot 16](PILOTE-MOBILES-SEESTAR.md) a ensuite exécuté le premier pilote réel : sept alignements contrôlés acceptés, recherche achevée avec zéro candidat et GIF local avant/après. Il ajoute 19 tests fictifs, soit **335 tests**, et neuf commandes pour mobile, témoin et refus. Aucune nouvelle lecture USB ; temps déclarés non qualifiés, performances de détection réelles non validées. À ce lot, les nouveaux GIF réels et positions restaient privés ; les trois illustrations publiques étaient fictives. L'autorisation réaffirmée au lot 17 permet maintenant de publier le GIF réel et deux illustrations sous CC0 ; les positions et rapports restent privés.

Le lot 17 porte la suite à **338 tests réussis** et la [notice CC0](images/reels/LICENCE.md) à cinq médias réels exactement listés. Les rendus sont publiés dans le tutoriel dès 10 ans, sans FITS, journal ou chemin privé. Le résultat du pilote reste inchangé : aucune nouvelle recherche ou découverte.

**Base de cette proposition :** objectifs des deux prompts ; publication graduée de l’information légale préconisée par GNU ; sources officielles décrivant les formats scientifiques.

## 2. Arborescence unifiée et composants

Les fichiers racines, modèles GitHub et documents ci-dessous sont livrés. L’arborescence suivante reste la cible modulaire à terme ; les paragraphes par version décrivent les composants effectivement disponibles. Le premier module a introduit `src/gar/contracts.py`, `inventory.py`, `reports.py` et `cli.py`, avec `__main__.py`, le lanceur `scripts/gar-inventory.bat`, `tests/test_inventory.py` et `examples/make_demo.py`. Son interface est décrite dans [CONTRAT-INVENTAIRE.md](CONTRAT-INVENTAIRE.md). Le recalage et les comparaisons stellaires exploratoires sont désormais livrés ; les mesures de mobiles et la photométrie restent à développer.

Le lot suivant ajoute `sessions.py`, `session_reports.py`, `scripts/gar-sessions.bat`, les tests et le générateur d’exemple multi-séances. Cette commande travaille sur le manifeste local existant ; elle ne rouvre pas les archives. Son [contrat spécifique](CONTRAT-SEANCES.md) décrit un regroupement indicatif, avec dates et configurations déclarées, sans qualification scientifique des heures. La suite réunit désormais 67 cas synthétiques.

Le diagnostic temporel ajoute `timing.py`, `timing_reports.py`, `scripts/gar-timing.bat`, ses tests et un exemple illustré. Le parseur de date est partagé dans `contracts.py` ; l’orchestrateur fournit les groupes au diagnostic, sans importation réciproque des modules métier. La suite compte désormais 100 cas. Le [contrat temporel](CONTRAT-HORODATAGES.md) laisse l’horloge et la convention instrumentale non qualifiées sans preuve indépendante ; aucune mesure ou heure de milieu de pose n’est inventée.

La version 0.4 ajoute `wcs_audit.py`, `wcs_reports.py` et `scripts/gar-wcs.bat`, leur exemple synthétique et 36 cas supplémentaires, soit 136 au total. Le [diagnostic WCS](CONTRAT-WCS.md) ne consomme que le manifeste partiel ; il ne calcule aucune coordonnée céleste et ne valide pas les solutions sur des étoiles. La collecte complète du contexte et les images de travail seront nécessaires à la suite scientifique.

La version 0.5 ajoute `workset.py` et `gar workset` : sélection explicite, copies locales vérifiées et en-têtes complets, séparés du manifeste 1.0. Les modèles WCS sont construits uniquement depuis les copies et restent non validés. La suite compte 147 tests ; le [contrat workset](CONTRAT-WORKSET.md) décrit les limites, protections et rapports privés.

La version 0.6 ajoute `astrometry.py`, `astrometry_reports.py`, Photutils/SciPy et une comparaison hors ligne sur références locales. Les seuils sont fixés avant mesure, sans nouveau modèle ajusté ni écrêtage des résidus après association. La suite compte 156 tests. Le [contrat astrométrique](CONTRAT-ASTROMETRIE.md) limite la conclusion à une compatibilité empirique sur l’échantillon, sans certification de soumission ou qualification temporelle.

La version 0.7 ajoute `registration.py`, `registration_reports.py` et `gar register` : recalage rigide sur copies locales, étoiles réservées avant ajustement et composition vers la WCS gelée. La suite compte 177 tests. Le [contrat de recalage](CONTRAT-RECALAGE.md) distingue précision relative et erreur absolue héritée ; aucune WCS FITS n’est copiée ou réécrite et les heures restent non qualifiées. Le tutoriel propose trois injections Bayer fictives et leurs graphiques réellement calculés.

La version 0.8 ajoute `gaia_frames.py`, `gaia_frames_reports.py` et `gar gaia-frames`, avec sélection/propagation Gaia commune au contrôle de l’empilement. Les modèles restent gelés ; seul l’échantillon réservé détermine le verdict par pose. Les 197 tests couvrent notamment les biais conservés et la cohérence des partitions/provenances. Le [contrat Gaia des poses](CONTRAT-GAIA-POSES.md) distingue références communes, contrôle empirique et budget absolu incomplet. Les trois copies réelles satisfont les critères, sans accès USB ; seuls les exemples fictifs sont publics.

La version 0.9 ajoute `time_evidence.py`, `time_evidence_reports.py` et `gar time-evidence` : en-têtes complets des copies, inconnues, canevas de preuves et [protocole illustré](PROTOCOLE-QUALIFICATION-TEMPS.md). Les 223 tests vérifient notamment l’absence d’accès aux pixels/réseau, la préservation et le refus de qualification même avec des déclarations riches. Le [contrat des preuves temporelles](CONTRAT-PREUVES-TEMPS.md) maintient l’horloge et les exports non qualifiés ; aucune mesure physique n’est réalisée et l’applicabilité aux anciennes archives reste à démontrer.

Un complément documentaire fournit la [fiche opérationnelle de campagne](CAMPAGNE-TEMPORELLE.md) et cinq canevas : configuration, blocs proposés, journal vide, budget à renseigner et revue. Il ne change pas la version 0.9 ou le code d’analyse. Les références, versions et critères inconnus restent à confirmer ; aucune acquisition n’est effectuée ou déclarée prête, et les anciennes archives demeurent non qualifiées.

La version 0.10 ajoute `moving.py`, `moving_reports.py` et `gar moving-synthetic`, avec 18 nouveaux cas portant la suite à 241 tests. Dix-huit séquences entièrement fictives évaluent des trajectoires avant comparaison à la vérité ; 16/21 injections sont retrouvées et les cinq manquées restent visibles. Les critères nominaux et intermittents sont satisfaits, sans certification sur données réelles. Le parcours pédagogique permet de reconstruire l’application depuis le code et reproduire chaque module avec commandes, résultats attendus, images et dépannage. Les PNG/GIF facultatifs emploient Matplotlib/Pillow ; aucune donnée privée ou lecture USB n’est impliquée.

```text
gnu-astrophotography-recycle/
├── README.md                 # Mission, statut et limites
├── COPYING                   # GPL v3 officielle intégrale, inchangée
├── LICENSE-NOTICE.md         # Choix GPL-3.0-or-later et en-tête type
├── INSTALL.md                # Situation actuelle et cible Windows
├── CONTRIBUTING.md           # Goal / Produce / Submit / Wait / Repeat
├── GOVERNANCE.md             # Responsabilités et création GitHub
├── ROADMAP.md                # Phases et critères de sortie
├── .gitignore                # Archives et données locales exclues
├── .gitattributes            # Fins de ligne et licence préservée
├── .github/
│   ├── ISSUE_TEMPLATE/       # Bug et proposition
│   ├── pull_request_template.md
│   └── workflows/ci.yml      # Futur : tests et audit des dépendances
├── docs/
│   ├── DOSSIER-LANCEMENT.md
│   ├── VALIDATION-PILOTE.md
│   ├── LICENCES-TIERCES.md
│   ├── DONNEES.md
│   ├── SOURCES.md
│   └── decisions/            # Futur : décisions d’architecture
├── pyproject.toml            # Futur : paquet et configuration pytest
├── requirements/             # Futur : versions, empreintes, audit Windows
├── src/gar/                  # Futur : application
│   ├── contracts/            # Schémas, unités, statuts et provenance
│   ├── inventory/            # Lecture récursive, HDU et métadonnées
│   ├── calibration/          # Copies de travail et modèles d’erreurs
│   ├── registration/         # Géométrie, WCS et contrôle qualité
│   ├── motion/               # Candidats mobiles et trajectoires
│   ├── photometry/           # Flux différentiels et incertitudes
│   ├── gateway/              # Validation et exports scientifiques
│   ├── reports/              # CSV/JSON, PNG et GIF
│   └── cli/                  # Orchestration, sans algorithme scientifique
├── scripts/                  # Futur : lanceurs sans élévation
│   ├── gar-inventory.bat
│   ├── gar-qualify.bat
│   └── gar-report.bat
├── tests/                    # Futur : pytest
│   ├── unit/
│   ├── integration/
│   ├── science/
│   └── fixtures/             # Générateurs synthétiques, pas les FITS privés
└── examples/                 # Futur : configuration fictive et exemples publics
```

Les archives réelles, catalogues, index, caches et résultats résident hors du dépôt. Leurs emplacements sont choisis dans une configuration locale ignorée.

### Contrats et absence de cycles

Chaque composant fait une tâche et échange des produits versionnés sur disque. Les interfaces CLI seront spécifiées lors de l’implémentation ; aucun lanceur factice n’est livré.

| Composant | Entrées | Sorties | Importations internes permises |
|---|---|---|---|
| contracts | Aucun module métier | Types et schémas versionnés | Aucune |
| inventory | Racine d’archives en lecture seule | Manifeste, anomalies, regroupements | contracts |
| calibration | Manifeste et calibrations identifiées | Dérivés, masques, variance | contracts |
| registration | Dérivés et catalogue local | Transformations et qualité WCS | contracts |
| motion | Manifeste, dérivés, transformations | Détections, associations, vitesses | contracts |
| photometry | Manifeste, dérivés, positions | Flux, magnitudes instrumentales, erreurs | contracts |
| gateway | Tables de mesures et provenance | Validation, export ou refus motivé | contracts |
| reports | Produits de chaque étape | CSV/JSON, PNG et GIF | contracts |
| cli | Arguments et configuration | Plan d’exécution et codes de sortie | Composants ci-dessus |

Les dépendances entre étapes passent par les fichiers, pas par des importations réciproques. `motion` n’importe pas `photometry` ; `gateway` ne relance pas une mesure. Les utilitaires partagés restent dans une couche inférieure sans imports métier. Un contrôle statique des imports devra vérifier cette règle.

Persistance initiale : manifeste JSON et tables CSV, avec unités et valeurs manquantes décrites dans un schéma. Pas de base de données obligatoire. Un index SQLite pourra être étudié si le volume le justifie ; il restera reconstruisible.

## 3. Cadre GPL et gouvernance

Le second prompt précise « or any later version » ; le projet retient donc **GPL-3.0-or-later**, plutôt que GPL-3.0-only. Le texte de la GPL reste intact dans `COPYING` ; [LICENSE-NOTICE.md](../LICENSE-NOTICE.md) contient l’avis applicable et l’en-tête Python complet.

La GPL protège les libertés d’usage, de modification et de redistribution ; elle n’interdit pas les usages commerciaux. Lors d’une distribution de binaires, prévoir un mécanisme conforme pour le code source correspondant, les scripts nécessaires à sa construction et les avis requis. Un lien vers une branche évolutive ne suffit pas à identifier le source exact d’un binaire. Conserver une archive source par version distribuée et documenter le mode de fourniture retenu.

Les droits des tiers sont conservés ; les catalogues et données ont leurs propres conditions. Aucune obligation de publier les archives personnelles n’est créée par l’utilisation locale de l’outil. Les conditions propres aux données ne doivent pas être confondues avec celles du logiciel.

Les guides [CONTRIBUTING](../CONTRIBUTING.md) et [GOVERNANCE](../GOVERNANCE.md) définissent contributions, revue et décisions. Avant une publication : choisir le titulaire et son contact public, vérifier les droits sur les apports, examiner l’historique, puis publier le dépôt public dès son premier envoi. Aucun mot de passe ni réglage privé n’entre dans Git.

**Base :** texte GPL et guide GNU ; les modalités concrètes sont des choix de gouvernance proposés au fondateur, pas des obligations inventées de la Free Software Foundation.

## 4. Compatibilité des licences tierces

| Élément | Licence principale observée | Position de cadrage | Vérification avant distribution |
|---|---|---|---|
| CPython moderne | PSF et notices historiques | Compatibilité GPL indiquée par Python | Licence complète du runtime et modules embarqués |
| Astropy | BSD 3 clauses | Compatible en principe avec GPL v3 | Notices et composants tiers de la version retenue |
| Photutils | BSD 3 clauses | Compatible en principe avec GPL v3 | Dépendances transitives et avis |
| NumPy | BSD 3 clauses | Compatible en principe avec GPL v3 | Bibliothèques natives réellement dans les roues Windows |
| Matplotlib | Licence propre fondée sur PSF | Compatible en principe, audit à achever | Polices, moteurs, ressources et avis embarqués |
| ExifTool | Choix Artistic/GPL, selon distribution | Optionnel, exclu du socle | Terme exact de la version et de son runtime Perl |

Il s’agit d’une préanalyse, **pas d’un audit de versions distribuables**. Aucune version n’est verrouillée. Le [registre de licences](LICENCES-TIERCES.md) décrit l’audit requis. Astropy suffit à la lecture FITS ; ExifTool ne doit pas devenir une dépendance obligatoire sans besoin démontré.

L’intégration continue future exécutera les tests sur Windows, produira un inventaire des dépendances directes et transitives, et signalera les licences absentes ou modifiées. La décision de compatibilité restera une revue humaine des artefacts exacts, en particulier pour les bibliothèques natives. Conserver les preuves par version.

## 5. Architecture scientifique du traitement FITS

### Ingestion et provenance

Parcourir récursivement les archives sans suivre les liens de répertoire par défaut. Ouvrir les FITS en lecture seule ; jamais de réparation sur place ni de renommage automatique. Énumérer toutes les HDU : une HDU primaire vide n’est pas nécessairement un fichier invalide. Identifier chaque image par empreinte SHA-256 du fichier et index de HDU. Les doublons physiques partagent l’empreinte mais leurs chemins restent inventoriés localement.

Séparer la valeur brute de chaque mot-clé, son interprétation normalisée et la justification. Rechercher notamment `DATE-OBS`, `EXPTIME`, `FILTER`, `RA`, `DEC`, `SITELAT`, `SITELONG`, `TIMESYS`, informations Bayer et WCS ; **leur présence et leur sens sur les fichiers S50 ne sont pas garantis**. L’absence devient un statut explicite, jamais une valeur inventée. Préserver aussi dimensions, type, `BSCALE`/`BZERO`, unités, saturation et historique de traitement quand ils sont connus.

Chaque exécution reçoit un identifiant, le commit du programme, les versions des bibliothèques, la configuration effective, les empreintes des entrées et références locales, les graines aléatoires et les décisions de rejet. Les JSON utilisent `null` pour une valeur inconnue, pas un zéro ni un NaN non standard.

### Temps et lieu

Lire les échelles temporelles selon le standard FITS ; enregistrer les valeurs par défaut éventuelles comme hypothèses. Le fuseau Windows et l’heure de modification du fichier ne sont pas l’heure d’observation. Vérifier par documentation instrumentale et observations de contrôle si `DATE-OBS` représente effectivement le début de pose de ces archives.

Si le début est établi, calculer `t_mid = t_start + EXPTIME / 2` avec `astropy.time` et conserver UTC, JD UTC et durée ; si la convention est inconnue, le temps de milieu reste non validé. Une précision d’écriture à la milliseconde ne prouve pas une horloge exacte. Mesurer ou borner son erreur. Pas de mélange silencieux entre JD UTC, HJD et BJD TDB ; toute correction nécessite lieu, cible, échelle et éphéméride identifiés.

Vérifier unités et signes de latitude/longitude, altitude et référentiel lorsqu’ils sont requis. Les valeurs privées peuvent venir d’une configuration locale avec provenance ; ne jamais les déduire d’un nom de dossier. Le mode hors ligne doit interdire les téléchargements implicites et enregistrer l’âge des tables temporelles locales.

### Géométrie et WCS

Des valeurs RA/DEC de pointage ne constituent pas une WCS complète. Contrôler `CTYPE`, `CRPIX`, `CRVAL`, matrice de transformation, unités, distorsion et couverture du champ. Comparer les positions d’étoiles à un catalogue local daté, avec époque et mouvements propres si nécessaires. Rapporter les résidus et leur distribution, pas uniquement le succès du parseur.

Sans WCS validée, autoriser l’exploration en pixels, mais bloquer positions célestes et vitesses en secondes d’arc. Une résolution astrométrique locale peut être ajoutée par adaptateur ; le solveur, ses index, leur volume et leurs licences restent à sélectionner.

En mode altazimutal, modéliser rotation du champ et translation, puis examiner les résidus spatiaux. Ne pas se contenter de recaler un point central. Le manuel officiel S50 indique aussi un mode équatorial : ne pas supposer que toutes les séances ont la même géométrie. Les transformations servent aux aperçus et aux associations ; privilégier les pixels natifs pour les mesures afin de limiter les erreurs corrélées du rééchantillonnage.

### Calibration, Bayer et photométrie

Vérifier si les archives sont brutes, déjà corrigées ou dématricées avant toute calibration. Pas de soustraction de dark en double. Enregistrer dark, flat, masques et domaine de validité lorsqu’ils existent ; déclarer les calibrations manquantes et étudier leur effet.

Ne pas imposer une matrice RGGB sans preuve. Si la mosaïque est connue, extraire et caractériser les deux sous-réseaux verts en conservant leur géométrie, ou utiliser une méthode documentée qui préserve le flux. Une image RGB déjà interpolée demande une autre stratégie. Luminance d’affichage et flux photométrique sont deux produits distincts.

Mesurer un fond local robuste ; choisir apertures et anneaux de fond en fonction de la PSF, de la contamination et des bords. Écarter saturation et non-linéarité. Construire un ensemble d’étoiles de comparaison avec critères explicites puis tester sa stabilité avec une étoile de contrôle indépendante ; ne pas déclarer stables les étoiles seulement parce qu’elles ont servi à l’ajustement.

Pour un flux positif `F`, `m_inst = -2,5 log10(F)` à constante près. Dans le régime d’erreurs faibles, `sigma_m ≈ (2,5/ln(10)) sigma_F/F`. Le budget doit inclure bruit du signal, fond, lecture, calibrations, références et corrélations pertinentes ; le gain et le bruit de lecture du capteur ne sont pas inventés. Les erreurs de catalogue et effets communs du zéro photométrique ne disparaissent pas par simple moyenne. En cas de paramètres inconnus, utiliser une estimation empirique justifiée et marquer sa portée.

Une courbe différentielle instrumentale peut être utile sans être une magnitude standard. Aucune conversion automatique du vert Bayer en Johnson V ; indiquer le système réellement mesuré, les filtres installés et les transformations validées, le cas échéant.

### Objets mobiles, rapports et passerelle

Après contrôle qualité et alignement stellaire, détecter les résidus et associer les sources entre poses avec temps irréguliers, interruptions et incertitudes. Pour les angles, traiter le passage RA 0/360° et la projection `cos(dec)` ; ajuster dans un plan tangent ou avec une géométrie sphérique adéquate. Propager les erreurs de centroïde, WCS et temps dans les vitesses et résidus de trajectoire.

Un pixel chaud fixe sur le détecteur peut devenir un faux mobile dans une vue recalée ; un rayon cosmique, un satellite ou un résidu au bord d’une galaxie peut aussi tromper une détection. Ce sont des cas de test, pas un diagnostic déjà établi sur votre capteur. Le manuel confirme l’IMX462, sans établir ses caractéristiques de bruit dans vos archives.

Produire CSV/JSON et graphiques PNG ; les GIF montrent un aperçu global et des zooms annotés en UTC, avec saturation visuelle séparée des mesures. Préserver les motifs d’exclusion.

La passerelle est un dernier contrôle local, sans réseau : unités, valeurs requises, identifiants, qualité et provenance. **WebObs 2.0 est une application de soumission ; AAVSO Extended est un format distinct.** ADES syntaxiquement valide n’est pas nécessairement recevable par le MPC. ALCDEF concerne les séries photométriques d’astéroïdes. Aucun identifiant d’observateur, code d’observatoire, filtre ou cible n’est inventé. Un export peut être refusé sans empêcher les rapports exploratoires.

## 6. Protocole pilote et validation

Le [protocole détaillé](VALIDATION-PILOTE.md) lance les phases 1 et 2 avec une séance locale complète de 30 à plus de 60 minutes si disponible. Il associe inventaire exhaustif, contrôle des temps, WCS et Bayer, et qualification par usage. Les essais de détection et de photométrie deviennent des conditions des phases suivantes.

| Décision | Preuve minimale attendue |
|---|---|
| Phase 1 acceptée | Comptage réconcilié, erreurs expliquées, manifestes déterministes et empreintes inchangées |
| Phase 2 acceptée | Rapport de temps, géométrie, WCS, traitement des pixels et inconnues ; aptitude séparée par usage |
| Astrométrie possible | Référence céleste contrôlée, temps et erreurs qualifiés ; aucun défaut bloquant |
| Photométrie possible | Flux linéaires qualifiés, comparaisons et contrôle indépendants, budget d’incertitude |
| Export possible | Critères scientifiques et spécification exacte du destinataire vérifiés |

Le premier inventaire est vérifié par 25 cas synthétiques et un pilote privé avec comparaison des empreintes. Cela ne qualifie pas encore les temps, les solutions WCS ou les mesures scientifiques ; les critères correspondants restent ouverts.

**Biais et limites du cadrage :** priorité donnée à Windows 11, Python et au S50 selon la demande ; ce n’est pas une comparaison exhaustive de logiciels. Les archives disponibles peuvent favoriser les belles images plutôt que les meilleures séries scientifiques. Le pilote peut échouer faute de calibrations, de références ou d’heure fiable. Ces résultats devront être consignés aussi soigneusement qu’un succès.
