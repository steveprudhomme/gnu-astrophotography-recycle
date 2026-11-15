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

Ce lot couvre un premier inventaire utilisable depuis les sources. L’audit complet des roues natives, le verrouillage avec empreintes, la distribution portable, le regroupement automatique des séances et la qualification scientifique des heures/WCS restent des travaux ouverts ; ils ne sont pas déclarés terminés par ce lot.

Plan initial enregistré avant développement : **`6c79043`**. Lors de l’essai d’installation, le retrait de NumPy 2.4.0 a conduit au choix de 2.4.1 et à une nouvelle exécution des tests. La protection CSV contre les formules de tableur a été ajoutée au contrat des rapports. Ces ajustements relèvent des sous-étapes de robustesse et d’installation ci-dessus.
