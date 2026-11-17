# Feuille de route

Les phases sont ordonnées par dépendances et critères de sortie, sans échéance inventée.

| Phase | Travail | Livrables et critère de sortie |
|---|---|---|
| 0 — Fondation | Identité, GPL, documentation, gouvernance, dépôt public | Base relue, titulaire identifié, première publication publique |
| 1 — Inventaire local | Parcours récursif en lecture seule, HDU, métadonnées, empreintes, regroupement des séances | CSV/JSON et rapport d’anomalies ; aucun fichier perdu silencieusement ; originaux inchangés |
| 2 — Qualification du pilote | Temps, géométrie, WCS, Bayer, calibrations, alignement et diagnostics | Rapport reproductible sur une séance de 30 à plus de 60 min ; preuves et décisions d’aptitude par usage |
| 3 — Objets mobiles | Détection, associations temporelles, vitesses, rejet des artefacts et GIF | Tests d’injection/récupération et faux positifs mesurés ; candidats revus humainement |
| 4 — Photométrie | Comparaisons, étoile de contrôle, mesures natives, incertitudes | Courbes instrumentales reproductibles ; calibration et limites documentées |
| 5 — Passerelles | AAVSO Extended/WebObs, MPC ADES, ALCDEF | Exports locaux vérifiés contre spécifications identifiées ; aucune soumission automatique |
| 6 — Distribution | Paquet portable Windows, audit complet, ergonomie | Essai hors ligne sur compte standard vierge, licences et source correspondante fournis |

## Premières tâches à ouvrir

- P1-01 : définir le manifeste `frame_id`/HDU, provenance et statuts d’erreur.
- P1-02 : générer des FITS synthétiques : valide, tronqué, multi-HDU, métadonnées absentes et doublons.
- P1-03 : implémenter l’inventaire sans écriture des entrées ; tester chemins Unicode, liens et accès refusé.
- P1-04 : figer la première combinaison Python/bibliothèques compatible Windows et auditer les artefacts exacts.
- P1-05 : produire et relire les rapports ; vérifier les empreintes avant/après.
- P2-01 : relever sur le pilote les mots-clés et traitements réellement présents, sans présumer le firmware.
- P2-02 : documenter le sens des heures et la précision disponible ; construire les temps de milieu de pose admissibles.
- P2-03 : mesurer rotation/dérive et valider les WCS avec un catalogue local.
- P2-04 : caractériser les calibrations, la saturation et la voie Bayer ; consigner les inconnues.
- P2-05 : appliquer les critères du protocole pilote et publier uniquement une synthèse anonymisée autorisée.

Les phases 1 et 2 n’impliquent pas que des détections ou des mesures publiables soient déjà disponibles. Un résultat « archives insuffisantes » est une conclusion valide du pilote.

## Lot de travail 1 — inventaire exécutable (plan du 15 novembre 2026)

L’inspection exploratoire locale a révélé des poses mosaïquées, des empilements RGB, des fichiers sans image primaire et des conventions horaires non qualifiées. Le premier module doit préserver ces distinctions. Les fichiers et rapports personnels restent exclus de Git.

Avant chaque nouveau lot : examiner les sous-étapes, compléter cette feuille de route, puis **faire un commit de planification avant l’implémentation**. Tenir le [tutoriel illustré](docs/TUTORIEL.md) et les autres Markdown concernés à jour. Ces règles sont également consignées dans `AGENTS.md`.

| Sous-étape | Travail et critère de sortie | État du lot |
|---|---|---|
| P1-A | Définir le contrat v1 : fichiers/HDU, SHA-256, provenance, statuts, unités et inconnues explicites | Fait — contrat 1.0 documenté |
| P1-B | Ajouter une commande locale, ses arguments et un lanceur Windows ; refuser les sorties dans les entrées, les liens/jonctions et l’écrasement de rapports | Fait — CLI, module, paquet modifiable et `.bat` vérifiés |
| P1-C | Parcourir les FITS sans charger les pixels ; inventorier chaque HDU, y compris les primaires vides et extensions ; enregistrer les erreurs sans arrêter le lot | Fait — cas synthétiques vérifiés |
| P1-D | Hacher les fichiers entiers, détecter les doublons et changements pendant lecture ; distinguer présence WCS et validation, Bayer déclaré et pixels réellement mosaïqués | Fait — limites des heuristiques documentées |
| P1-E | Produire manifeste JSON, table CSV, synthèse Markdown et graphique SVG local ; provenance et avertissements ; aucune conversion temporelle présumée | Fait — exemple synthétique reproductible |
| P1-F | Tester avec fichiers synthétiques : multi-HDU, vide, tronqué, invalide, doublon, dates ambiguës, erreurs d’accès, chemins Unicode, liens et sorties dangereuses | Fait — 25 cas passent, aussi dans l’environnement isolé corrigé |
| P1-G | Exécuter sur le pilote local retenu ; comparer comptages et empreintes avant/après ; conserver les résultats privés | Fait — toutes les empreintes du pilote concordent |
| P1-H | Illustrer le tutoriel avec schéma et exemple synthétique réellement produit ; actualiser README, INSTALL, validation, sources et limites | Fait — diagramme SVG, rapport SVG et illustration PNG |
| P1-I | Relire les fichiers destinés à Git, faire un commit de réalisation avec preuves de validation ; publication distante distincte | Livré dans le commit de réalisation de ce lot |

Ce premier lot couvre l’inventaire depuis les sources. Il ne terminait pas le regroupement, livré séparément ci-dessous. L’audit complet des roues natives, le verrouillage avec empreintes, la distribution portable et la qualification scientifique des heures/WCS restent ouverts.

Plan initial enregistré avant développement : **`6c79043`**. Lors de l’essai d’installation, le retrait de NumPy 2.4.0 a conduit au choix de 2.4.1 et à une nouvelle exécution des tests. La protection CSV contre les formules de tableur a été ajoutée au contrat des rapports. Ces ajustements relèvent des sous-étapes de robustesse et d’installation ci-dessus.

## Lot de travail 2 — regroupement indicatif des séances

Plan du 15 novembre 2026, enregistré dans **`1523035` avant l’implémentation**. La commande travaille **sur un manifeste existant**, sans relire ni modifier les FITS. Une séance est un regroupement de travail, pas une qualification des heures ou une nuit astronomique certifiée.

| Sous-étape | Travail et critère de sortie | État |
|---|---|---|
| S1 | Définir le contrat : cible, instrument, filtre, dimensions, Bayer, mode, site et échelle temporelle déclarée ; garder les dossiers distincts | Fait — contrat des séances 1.0 |
| S2 | Exclure erreurs, HDU non candidates, empilements, copies et dates inutilisables ; expliquer chaque exclusion | Fait — réconciliation des HDU et motifs explicites |
| S3 | Parser les dates complètes sans conversion ; séparer dates déclarées et interruptions selon un seuil configurable | Fait — seuil par défaut de 1 800 s et limites du parseur documentées |
| S4 | Détecter dates dupliquées, durées inconnues et métadonnées absentes ; identifiants stables et provenance SHA-256 | Fait — temps et intégrations non qualifiés restent signalés |
| S5 | Ajouter `gar sessions` et un lanceur Windows ; contrôler manifeste et sorties | Fait — essais CLI et chemins avec espaces/accents |
| S6 | Produire JSON, CSV, Markdown et SVG ; distinguer couverture et intégration déclarée | Fait — aucun total fabriqué si des durées manquent |
| S7 | Tester les configurations, dates, seuils, doublons, extensions et erreurs | Fait — 42 nouveaux cas ; 67 tests au total |
| S8 | Exemple synthétique illustré et comparaison au manifeste privé du pilote | Fait — cinq groupes synthétiques attendus ; membres privés réconciliés sans relire les FITS |
| S9 | Actualiser les Markdown et le tutoriel, vérifier les illustrations et faire le commit de réalisation | Livré dans le commit de réalisation de ce lot |

Choix prudent : découper à minuit de la date **déclarée** pour ce premier regroupement ; cela peut diviser une véritable séance passant minuit. Ne pas appeler ce découpage « nuit locale » ou UTC lorsque l’échelle est absente. La validation instrumentale des heures reste en phase 2. Les groupes incomplets sont signalés ; aucune exposition manquante n’est remplacée par zéro ou par une valeur supposée.

Version du lot : **0.2.0a1**. Les variations exactes du site ou du gain restent séparées, même si elles pourraient provenir d’un bruit de métadonnées : aucune tolérance ni fusion géographique n’est supposée. Le support USB demeure inchangé ; ce lot s’appuie uniquement sur des manifestes locaux. Les résultats détaillés réels restent exclus de Git.

## Lot de travail 3 — diagnostic des horodatages

Plan du 15 novembre 2026, enregistré dans **`e21a5e8` avant développement**. Objectif : distinguer forme lisible, convention déclarée, défaut du standard et exactitude instrumentale **non démontrée**. Les manifestes locaux sont les seules entrées d’observation ; aucun FITS du support externe n’est rouvert. Ce lot ne promet pas de certifier une horloge à partir de ses seuls en-têtes.

| Sous-étape | Travail et critère de sortie | État |
|---|---|---|
| T1 | Examiner les sources officielles FITS et Seestar ; séparer recommandations, preuves instrumentales et inconnues | Fait — références et limites documentées, précision S50 non établie |
| T2 | Définir le contrat : forme, résolution écrite, échelle, commentaire et exactitude inconnue | Fait — contrat des horodatages 1.0 |
| T3 | Ajouter `gar timing`, lanceur, provenance SHA-256 et contrôles des entrées/sorties | Fait — manifestes ambigus également refusés |
| T4 | Auditer dates, échelles, commentaires et durées contradictoires | Fait — déclarations conservées, aucun milieu de pose inventé |
| T5 | Diagnostiquer cadence, doublons, interruptions et intervalles courts | Fait — comparaisons limitées à une configuration et une date |
| T6 | Produire JSON, CSV, Markdown et SVG avec raisons et limites | Fait — heures restent non qualifiées, code de retour 2 explicite |
| T7 | Tester les cas temporels et l’absence d’accès aux FITS | Fait — 33 nouveaux cas ; 100 tests au total |
| T8 | Exemple public illustré et rapprochement du manifeste privé | Fait — anomalies synthétiques attendues ; manifeste privé inchangé |
| T9 | Actualiser les Markdown, vérifier la version et faire le commit/publication sans données privées | Livré avec le commit de réalisation de ce lot |

Pour lever les inconnues instrumentales, il faudra une documentation applicable au firmware ou une mesure indépendante de synchronisation/déclenchement. Une longue série régulière ou six décimales de seconde ne démontre pas l’exactitude de l’heure. Les résultats négatifs ou non conclusifs seront conservés explicitement.

Version du lot : **0.3.0a1**. Le diagnostic est terminé, la qualification instrumentale reste ouverte. Une collecte future des champs non sélectionnés (firmware, DATE-BEG/END, erreurs temporelles déclarées), si nécessaire et autorisée, devra faire l’objet d’un autre plan préalable ; aucune relecture de la clé USB n’est effectuée ici.

## Note communautaire — propositions FITS pour le Seestar S50

Demande du fondateur : consigner des suggestions constructives qu’il pourra transmettre lui-même à la communauté. Préparer cette note sans nouvelle lecture du support externe et sans publier d’observations personnelles.

- C1 — fait : constats vérifiés dans les manifestes locaux et distingués des champs non collectés.
- C2 — fait : références officielles FITS, Siril et AAVSO consultées ; priorités hiérarchisées.
- C3 — fait : note autonome, demandes concrètes, bénéfices, critères et schémas conceptuels PNG/SVG.
- C4 — livré dans le commit documentaire : liens au tutoriel et aux sources, revue de confidentialité et des illustrations. La transmission à la communauté reste l’action du fondateur.

Plan enregistré dans **`2f3302c` avant la rédaction finale**. La [note communautaire](docs/PROPOSITIONS-SEESTAR-S50.md) ne constitue pas une nouvelle fonctionnalité applicative et n’annonce aucune non-conformité générale des fichiers Seestar.

### Version anglaise de la note communautaire

À la demande du fondateur : ajouter une traduction complète, sans remplacer le français.

- EN1 — fait : huit propositions, précautions et références traduites sans constat technique supplémentaire.
- EN2 — fait : illustration anglaise PNG/SVG, liens réciproques et accès depuis le README/tutoriel.
- EN3 — livré dans le commit documentaire local : cohérence, illustrations, liens et confidentialité vérifiés.

Plan enregistré dans **`76c7e56` avant la traduction finale**. La [version anglaise](docs/SEESTAR-S50-FITS-RECOMMENDATIONS.en.md) préserve la note française ; aucun accès aux archives ni changement applicatif n’a été nécessaire.

## Lot de travail 4 — diagnostic des informations WCS disponibles

Plan du 15 novembre 2026, enregistré dans **`a7044f1` avant le code** ; finalisation le 16 novembre. Les notes communautaires française et anglaise sont publiées avant ce lot. Les entrées restent les manifestes locaux ; aucune observation du support externe n’est rouverte.

**Limite déterminante :** le manifeste 1.0 ne conserve pas tous les champs WCS (unités, PC/CDELT, référentiel, distorsions, solutions alternatives). Il ne permet donc pas de reconstruire systématiquement une transformation céleste fidèle. Le diagnostic doit signaler cette limite plutôt que compléter silencieusement les informations manquantes.

| Sous-étape | Travail et critère de sortie | État |
|---|---|---|
| W1 | Définir le contrat des champs observés et limites de collecte | Fait — contrat WCS 1.0 |
| W2 | Commande `gar wcs`, lanceur, provenance et protections | Fait — manifeste local uniquement |
| W3 | Distinguer pointage et WCS ; contrôler axes et références sans unités supposées | Fait — limites explicites |
| W4 | Valeurs CD, singularité et conditionnement numérique | Fait — aucune précision angulaire déduite |
| W5 | Paramétrisations et distorsions non collectées, absence de transfert entre images | Fait — contexte incomplet signalé |
| W6 | JSON, CSV, Markdown et SVG sans certification | Fait — code 2, précision et résidus inconnus |
| W7 | Tests synthétiques et absence d’accès aux FITS | Fait — 36 nouveaux cas ; 136 tests au total |
| W8 | Exemple illustré et rapprochement du pilote | Fait — huit fichiers fictifs/neuf HDU ; identifiants privés réconciliés |
| W9 | Markdown, tutoriel, version, commit et publication | Livré avec le commit de réalisation |

Une résolution astrométrique ou une validation contre catalogue demandera ensuite des images locales de travail et une collecte complète du contexte WCS, avec un nouveau plan. Ce lot n’implique ni résolution d’images, ni qualification temporelle, ni autorisation de modifier les archives.

Version : **0.4.0a1**. L’interruption initiale de l’exécution des tests n’a pas été présentée comme un succès ; les 136 cas ont été exécutés avec succès lors de la reprise.

## Lot de travail 5 — échantillon local et en-têtes complets

Plan du 16 novembre 2026, enregistré dans **`34930d0` avant développement**. Lecture et copie de quelques fichiers explicitement sélectionnés, jamais déplacement ni écriture sur le support source. Tous les nouveaux produits restent dans `local/` du projet, exclu de Git.

- L1 — fait : trois poses et un empilement compatible sélectionnés ; appartenance exacte non prouvée.
- L2 — fait : commande `gar workset`, sélection explicite et protections des sources/destinations.
- L3 — fait : quatre copies identiques aux sources avant/après ; trois empreintes historiques également vérifiées.
- L4 — fait : toutes les cartes et représentations textuelles capturées depuis les copies uniquement.
- L5 — fait : modèle céleste SIP constructible sur l’empilement ; trois poses sans axes primaires déclarés ; aucune validation astrométrique.
- L6 — fait : 11 nouveaux cas, 147 tests au total, exemple public illustré.
- L7 — fait : rapports réels privés, documentation et tutoriel actualisés.
- L8 — livré avec le commit de réalisation : installation, confidentialité, commit et publication du code/documentation uniquement.

La résolution d’images sans solution et la validation sur un catalogue restent des étapes ultérieures. La présence d’un modèle construit par une bibliothèque ne prouve pas son exactitude.

Version du lot : **0.5.0a1**. Aucune suppression, modification ou création de fichier n’a été effectuée sur le support source ; les seules nouvelles données d’observation sont les copies locales demandées.

## Lot de travail 6 — comparaison astrométrique sur étoiles

Plan du 16 novembre 2026, à committer avant le code. Seules les copies locales vérifiées sont utilisées ; aucun accès au support externe. L’empilement conserve son modèle WCS sans réajustement sur les étoiles de contrôle.

- A1 : préparer localement un extrait de référence Gaia DR3, avec origine, requête, époque, mouvements propres, erreurs et empreinte ; aucun FITS, en-tête ou position géographique n’est envoyé au fournisseur. Seul le champ céleste est nécessaire à la requête de catalogue public.
- A2 : fixer les critères avant mesure : au moins 30 associations mutuelles uniques, rayon d’association 8 secondes d’arc, médiane des écarts ≤2 secondes d’arc, percentile 95 ≤4 secondes d’arc, couverture d’au moins 6 cellules sur une grille 3×3 et des quatre quadrants. Ce sont des critères exploratoires du projet, pas une norme MPC.
- A3 : ajouter une commande hors ligne sur copie locale et catalogue local ; détecter des étoiles non saturées et isolées, tracer les rejets, les seuils et la sélection du canal.
- A4 : propager les positions de référence à la date approximative d’observation, sans prétendre qualifier son horloge ; calculer les positions depuis la WCS originale avec SIP, sans recalage, ajustement ou élimination a posteriori des grands résidus pour réussir les critères.
- A5 : mesurer écarts tangentiels, séparation, biais, RMS, percentiles et intervalle bootstrap exploratoire de la médiane ; examiner distribution et résidus dans le champ. Documenter les limites du budget d’erreur, de l’époque et de la sélection par rayon.
- A6 : tester données synthétiques de géométrie connue, décalages, mauvaise WCS, faible effectif, doublons et préservation ; produire images de contrôle réelles et synthétiques, privées/publiques respectivement.
- A7 : exécuter sur l’empilement local, vérifier son SHA-256 avant/après ; rapporter succès ou échec des critères sans certificat de soumission scientifique et sans modifier les copies.
- A8 : actualiser tutoriel illustré et Markdown, dépendances/licences et installation ; commit puis publication du code et exemples fictifs uniquement.

Un manque de références, une géométrie inadéquate ou une dépendance indisponible doit être rapporté explicitement ; ne pas fabriquer de validation. Les données réelles et catalogue de champ restent dans `local/`. La validation temporelle et le transfert de WCS aux poses restent des travaux ultérieurs.

Paramètres fixés avant mesure réelle : détection DAO à 8 écarts-types robustes, FWHM initiale de 3 pixels, marge de 10 pixels, exclusion des pics à au moins 65 000 ADU pour cette image 16 bits et des voisins à moins de 8 pixels ; catalogue G entre 9 et 17,5 et RUWE <1,4, mouvements propres disponibles, références isolées à 16 secondes d’arc. Sur une image à trois plans, utiliser leur moyenne pour la détection uniquement, sans interprétation photométrique des canaux. Si ces paramètres échouent, conserver ce résultat ; tout nouvel essai doit être documenté séparément.

La première requête Gaia a été arrêtée par le contrôle d’approbation avant exécution. Le fondateur a ensuite explicitement autorisé l’envoi de la zone céleste à l’ESA, sans FITS, en-tête complet ni position terrestre. La requête et sa provenance resteront privées.

Réalisation 0.6.0a1 : plan **`d349984`** et paramètres **`fe3b1c4`** préalables aux mesures.

- A1 — fait : catalogue Gaia DR3 acquis après accord, requête et empreinte locales.
- A2 — fait : critères fixés avant mesure, sans modification après lecture des résultats.
- A3/A4 — faits : détection Photutils et propagation des références, analyse hors ligne sur copie, WCS originale conservée.
- A5 — fait : associations uniques, résidus, statistiques, couverture et bootstrap exploratoire ; cartes privées et limites du budget d’erreur documentées.
- A6 — fait : neuf nouveaux cas, soit 156 tests ; biais synthétique de 0,5″ retrouvé sans réajustement.
- A7 — fait : critères empiriques satisfaits sur l’empilement privé, empreinte inchangée ; indépendance des références par rapport au solveur initial non établie.
- A8 — livré avec le commit de réalisation : tutoriel illustré, dépendances et documentation actualisés, publication des données fictives uniquement.

Photutils/SciPy retenus nécessitent désormais Python ≥3.12. Le diagnostic complet du budget d’erreur et l’aptitude des futures mesures à une soumission restent ouverts ; le contrôle ne permet pas de conclure à toutes les sources ni aux objets mobiles.

## Lot de travail 7 — recalage des trois poses locales

Plan du 16 novembre 2026, à committer avant développement. Entrées exclusives : les quatre copies du workset local déjà vérifié. Ne jamais consulter les chemins sources du manifeste, ni accéder au support USB. Aucun téléchargement supplémentaire.

- R1 : ajouter `gar register`, sélectionner explicitement la référence et les trois poses, vérifier leurs empreintes avant/après et refuser liens, sorties existantes ou chemins hors de `local/`.
- R2 : détecter sur moyenne des blocs 2×2, pour atténuer la mosaïque Bayer sans inventer une photométrie ; même réduction géométrique sur la référence, coordonnées ramenées aux centres natifs (`2*x+0,5`). Détection DAO à 5 sigmas robustes, FWHM 2 pixels réduits, saturation native 65 000 ADU, marge native 10 pixels et isolation 8 pixels. Documenter les biais possibles de couleur et de centroïde.
- R3 : réserver avant ajustement 25 % des détections de chaque pose (tirage déterministe, graine 20261116). Identifier des triangles d’étoiles et ajuster uniquement rotation et translation, sans réflexion, échelle libre, cisaillement ou déformation ; associations mutuelles dans un rayon de 3 pixels natifs. Conserver les échecs.
- R4 : figer les critères exploratoires avant mesure : au moins 20 associations d’ajustement, 10 étoiles de contrôle, médiane de contrôle ≤0,75 pixel, percentile 95 ≤1,5 pixel, couverture de contrôle d’au moins 6 cellules sur 3×3 et des quatre quadrants. Ne pas éliminer de grands résidus après association pour réussir ; le rayon limite toutefois les erreurs observables. Contrôle réservé à l’ajustement, pas preuve d’indépendance de l’empilement.
- R5 : exporter la composition explicite pose → pixels de référence → WCS céleste SIP gelée et sa provenance. N’exporter aucune WCS FITS approximative copiée ; modèle utilisable uniquement si les critères sont satisfaits, avec erreur héritée de la référence et horloge toujours non qualifiée.
- R6 : tests synthétiques de rotations/translations, contrôle réservé, mauvais champs, faible effectif, réflexion et intégrité des copies ; rapports JSON/CSV/Markdown et illustrations publiques synthétiques et privées réelles.
- R7 : exécuter les trois poses locales, rapporter les critères séparément, vérifier les quatre empreintes et les limites ; aucune resynchronisation temporelle ni mesure d’objet mobile.
- R8 : actualiser contrats, tutoriel illustré, README et autres Markdown concernés ; vérifier tests, confidentialité et installation ; commit de réalisation et publication du code et exemples synthétiques uniquement.

Le résultat pourra être un échec de recalage ou de couverture. Tout assouplissement ultérieur des paramètres nécessitera un nouvel essai explicitement documenté ; aucune certification astrométrique absolue ni temporelle n’est promise.

Réalisation **0.7.0a1**, plan préalable **`6480df2`** :

- R1/R2 — faits : copies vérifiées, chemins externes rejetés avant sondage, détection sur blocs 2×2 et coordonnées natives ; aucune source historique consultée.
- R3/R4 — faits : triangles, rotation/translation, partition fixée avant ajustement, contrôle réservé et critères inchangés ; effectifs non associés conservés.
- R5 — fait : composition explicite sérialisée avec SIP, utilisation bloquée si critères non satisfaits ou point hors domaine ; aucune WCS FITS copiée.
- R6 — fait : 21 nouveaux cas, soit 177 tests ; figures publiques synthétiques et cartes privées réelles inspectées.
- R7 — fait : les trois poses locales satisfont les critères, quatre empreintes inchangées ; aucun accès USB ni nouveau catalogue.
- R8 — livré dans le commit de réalisation : contrats et tutoriel illustré, Markdown, installation et revue de confidentialité ; code et exemples synthétiques uniquement destinés à la publication.

La précision relative observée ne qualifie pas l’astrométrie absolue des poses, la photométrie ni l’horloge. Le budget d’erreur complet et les contrôles temporels restent à poursuivre avant toute exploitation de mobiles.
