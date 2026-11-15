# Protocole pilote et critères de validation

## Objectif et périmètre

Qualifier les archives avant de mesurer. Phases 1 et 2 : inventaire puis contrôle scientifique d’une séance de 30 à plus de 60 minutes, si disponible. Ne pas choisir uniquement les meilleures poses ; conserver celles qui révèlent nuages, dérive et interruptions. Aucun FITS réel n’a été fourni à ce stade.

## Préparer le lot local

1. Conserver l’archive originale intacte ; calculer les empreintes SHA-256 avant traitement. Pour les essais destructifs de résistance aux erreurs, fabriquer des données synthétiques.
2. Noter instrument, firmware connu, mode de monture, filtres, réglages d’export et traitements déjà appliqués. Marquer explicitement les inconnues.
3. Relever nombre de fichiers/HDU, durée totale couverte, temps d’exposition cumulé et interruptions. Ne pas confondre durée de séance et intégration cumulée.
4. Placer sorties et références hors du dépôt et hors de la racine des entrées ; prévoir l’espace disponible. Empêcher les écritures vers les entrées.
5. Préparer localement les catalogues/calibrations autorisés. Conserver version, licence, empreinte, époque et date de téléchargement.

## Matrice des contrôles

| Test | Mise en œuvre et mesure | Acceptation |
|---|---|---|
| Intégrité | Empreintes avant/après, lecture seule, chemins distincts | 100 % des originaux inchangés ; toute tentative d’écriture rejetée |
| Exhaustivité | Réconcilier fichiers, HDU, images, doublons et erreurs | Aucun fichier ignoré sans statut explicite |
| Formats | Synthétiques : vide, tronqué, multi-HDU, flottant/entier, mise à l’échelle, compression | Lecture correcte ou rejet motivé ; aucune réparation des entrées |
| Métadonnées | Clés absentes, unités ambiguës, coordonnées hors domaine, filtres inconnus | Données brutes conservées ; inconnues non remplacées par défaut silencieux |
| Temps | Échelles, milieu de pose, ordre, doublons, passage de date et seconde intercalaire synthétique | Pas de confusion de fuseau ; convention et précision documentées ou export bloqué |
| Géométrie | Rotation, translation, bords et recouvrement, comparaison à référence locale | Transformations et résidus documentés ; seuils d’usage définis avant exploitation |
| WCS | Résidus d’étoiles indépendantes, unités et projection, RA 0/360° | Pas de coordonnées scientifiques si référence insuffisante |
| Pixels | Bayer inconnu, RGB, saturation, calibrations et double correction | Voie de traitement établie ou limitation déclarée |
| Reproductibilité | Deux exécutions avec mêmes versions, références, paramètres et graines | Mêmes entrées/sorties scientifiques dans les tolérances numériques déclarées |
| Hors ligne | Réseau coupé, tables absentes ou périmées | Aucun accès réseau implicite ; erreur ou avertissement explicite et traçable |
| Windows | Compte standard, espaces/accents, accès refusé, manque d’espace | Aucun privilège requis, pas de perte silencieuse, erreur exploitable |

Les seuils numériques d’alignement, de photométrie et de détection ne sont pas encore des performances mesurées. Les fixer pour le cas d’usage dans une configuration versionnée avant d’examiner le lot d’évaluation final. Développer sur un sous-lot, puis évaluer sur un autre ; ne pas ajuster les seuils pour embellir le résultat final.

Pour l’astrométrie MPC, consulter la recommandation publiée de cohérence inférieure à une seconde d’arc et ses conditions ; ce n’est pas une performance garantie du S50 ni un critère suffisant à lui seul. Une erreur de temps `sigma_t` produit une contribution de position de l’ordre de `v × sigma_t` pour une vitesse angulaire `v` : elle peut dominer sur un mobile rapide.

## Essais scientifiques à ajouter aux phases 3 et 4

### Objets mobiles

Injecter des sources sur **des copies synthétiques ou dérivées**, avec gamme documentée de flux, vitesses, orientations et distances aux étoiles/bords. Séparer les tests d’association seuls des tests couvrant l’ensemble du traitement. Comparer avec un lot sans mobile, avec pixels chauds, traces, bruit et défauts de recalage.

Rapporter rappel de récupération, faux positifs par image ou surface et par durée, biais de position/vitesse, incertitudes et domaine de sensibilité. Répéter avec plusieurs graines. Un candidat doit être cohérent sur plusieurs poses ; le nombre minimal et les limites temporelles seront fixés avant l’évaluation. Une vérification humaine sur les images natives reste nécessaire. L’absence de candidat ne prouve pas l’absence d’objet.

### Photométrie

Utiliser étoiles de comparaison multiples, contrôle indépendant et injections de variations connues. Tester contamination, fond de galaxie, saturation, nuages, variations de PSF et différences entre sous-réseaux verts. Comparer flux et erreurs avec une méthode de référence indépendante.

Rapporter biais, dispersion de l’étoile de contrôle en fonction du flux, corrélation temporelle, résidus normalisés par leurs erreurs et couverture des intervalles annoncés. Ne pas réduire artificiellement les erreurs jusqu’à obtenir une courbe lisse. Une séance de moins d’une heure ne suffit pas à confirmer toutes les périodes de variabilité.

## Conditions de sortie et livrables

- `manifest.json` et `inventory.csv` : identifiants, HDU, métadonnées et statuts.
- `run.json` : versions, paramètres, empreintes des références et configuration effective.
- `quality.json` : temps, calibration, WCS, motifs d’exclusion et limites.
- `report.md` et PNG : résultats du pilote, comparaison aux critères et anomalies.
- À partir des phases correspondantes : tables de mesures, budgets d’incertitude, GIF, rapport d’export ou refus.

Verdicts distincts : **exploration seulement**, **astrométrie qualifiée**, **photométrie instrumentale qualifiée**, **export qualifié**, ou **données insuffisantes**. La phase 2 peut se terminer avec un constat documenté d’insuffisance ; les voies non qualifiées restent bloquées.

L’autorisation de soumission réelle reste une action distincte de la génération locale d’un export. Vérifier le format AAVSO, le schéma de soumission ADES et la version ALCDEF utilisés ; consigner leur empreinte. Ne jamais publier les produits locaux automatiquement.

## Cadre d’automatisation prévu

Le premier module utilise désormais `pytest` : 25 cas synthétiques couvrent l’inventaire, la préservation, les extensions, compressions, erreurs et interfaces Windows. Exécuter `python -m pytest -q` depuis la racine ; voir le [tutoriel illustré](TUTORIEL.md) et le [contrat d’inventaire](CONTRAT-INVENTAIRE.md). Les tests de temps scientifique, géométrie et mesures, les essais par injections et la distribution portable restent à développer. Les exemples publics sont générés à la demande sous GPL-3.0-or-later ; aucun jeu personnel n’est distribué.

La CI future exécutera ces contrôles sans réseau pendant les analyses, sur Windows en priorité ; un second système pourra vérifier la portabilité du cœur. Elle vérifiera aussi les imports autorisés, l’absence d’archives suivies, les schémas de sortie et l’audit des dépendances. L’inventaire est exécutable depuis les sources ; aucune suite de validation astrométrique ou photométrique n’est encore livrée. La vérification locale du pilote compare indépendamment les empreintes avant inventaire, celles du manifeste et celles recalculées après ; le programme n’annonce pas à lui seul cette vérification supplémentaire.
