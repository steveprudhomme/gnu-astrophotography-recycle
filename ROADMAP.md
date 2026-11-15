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
