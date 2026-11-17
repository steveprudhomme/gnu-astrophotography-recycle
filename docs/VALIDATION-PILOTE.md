# Protocole pilote et critères de validation

## Objectif et périmètre

Qualifier les archives avant de mesurer. Phases 1 et 2 : inventaire puis contrôle scientifique d’une séance de 30 à plus de 60 minutes, si disponible. Ne pas choisir uniquement les meilleures poses ; conserver celles qui révèlent nuages, dérive et interruptions. Un échantillon privé de trois poses et une référence est désormais disponible en copies locales vérifiées ; il ne représente pas toute la population d’archives.

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

Les seuils exploratoires des modules livrés sont fixés avant leurs essais et leurs résultats sont décrits ci-dessous. Ils ne constituent pas des performances universelles du S50, et la photométrie reste à développer. Définir les nouveaux critères dans une configuration versionnée avant d’examiner le lot d’évaluation final ; ne pas ajuster les seuils pour embellir ce résultat.

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

Le regroupement indicatif ajoute 42 cas, portant le total à 67 tests. Ils vérifient notamment les seuils, configurations, dates déclarées, dossiers, exclusions, réconciliation des HDU, valeurs manquantes, manifestes invalides et absence d’ouverture des FITS. Un exemple synthétique de neuf fichiers produit cinq groupes, six HDU retenues et trois exclusions attendues. Le contrôle réel de ce lot utilise exclusivement un manifeste local préexistant : comparer les identifiants des membres, les comptages et l’empreinte du manifeste avant/après, sans nouvelle lecture ou écriture sur le support externe. Ces tests ne qualifient pas l’exactitude temporelle ni les mesures physiques.

Le diagnostic temporel ajoute 33 cas, soit **100 tests** au total. L’exemple public de onze fichiers donne dix HDU candidates et six retenues pour cadence, avec les anomalies prévues. Le pilote est rapproché uniquement de son manifeste local ; tous les identifiants sont retrouvés et le SHA-256 source reste identique. Même en l’absence de défaut de cadence, `time_validated` reste faux, l’incertitude d’horloge et le milieu de pose UTC restent inconnus. Les sources et conditions d’une future qualification sont consignées dans [CONTRAT-HORODATAGES.md](CONTRAT-HORODATAGES.md).

La CI future exécutera ces contrôles sans réseau pendant les analyses, sur Windows en priorité ; un second système pourra vérifier la portabilité du cœur. Elle vérifiera aussi les imports autorisés, l’absence d’archives suivies, les schémas de sortie et l’audit des dépendances. L’inventaire est exécutable depuis les sources ; les contrôles stellaires exploratoires sont décrits ci-dessous, la validation photométrique reste à développer. La vérification locale du pilote compare indépendamment les empreintes avant inventaire, celles du manifeste et celles recalculées après ; le programme n’annonce pas à lui seul cette vérification supplémentaire.

Le diagnostic WCS ajoute 36 tests, soit **136 tests** au total, portant sur les déclarations et les calculs numériques limités, pas sur la précision astrométrique. Le cas public de huit fichiers/neuf HDU et le rapprochement du manifeste privé sont vérifiés sans rouvrir les archives. Tous les identifiants sont retrouvés et l’empreinte source est inchangée. Le contexte non collecté interdit de conclure à une solution validée ; voir [CONTRAT-WCS.md](CONTRAT-WCS.md).

Le lot d’échantillon local ajoute 11 cas, soit **147 tests**. Avant toute copie réelle, la lecture seule et les refus de sélection/destination/intégrité sont vérifiés synthétiquement. Les copies réelles sélectionnées sont hachées avant copie, après copie et par relecture source ; seules les copies servent ensuite à collecter les en-têtes et construire un modèle. Les empreintes historiques disponibles sont comparées. Ce contrôle ne prouve ni les sources exactes d’un empilement ni la précision du modèle WCS.

La comparaison sur étoiles ajoute neuf cas, soit **156 tests**. Les critères sont ceux fixés dans `d349984` et `fe3b1c4`, avant évaluation. L’essai fictif retrouve le biais connu sans ajuster la WCS ; les cas de mauvaise géométrie, manque d’effectif/couverture et associations fortuites ne passent pas les critères. Le pilote sur copie locale satisfait les seuils empiriques, avec empreinte inchangée. Les résidus et l’intervalle bootstrap ne constituent pas un budget d’erreur absolue complet ; l’indépendance des étoiles de contrôle vis-à-vis de la construction initiale reste inconnue. Voir [CONTRAT-ASTROMETRIE.md](CONTRAT-ASTROMETRIE.md).

Le recalage ajoute 21 cas, soit **177 tests**. Plan `6480df2` préalable au code et aux mesures ; critères de contrôle : ≥20 associations d’ajustement, ≥10 réservées, médiane ≤0,75 pixel, P95 ≤1,5 pixel, ≥6 cellules et les quatre quadrants. Les étoiles réservées ne participent pas au choix des hypothèses ni à l’ajustement. Les trois poses locales satisfont ces critères, avec quatre empreintes inchangées, sans accès USB ou réseau. Le modèle est une composition rotation/translation puis WCS de référence gelée, conservant SIP ; aucune WCS n’est copiée dans les FITS. L’erreur absolue est héritée, la sélection par rayon et les biais Bayer restent des limites. Voir [CONTRAT-RECALAGE.md](CONTRAT-RECALAGE.md) et l’exemple synthétique illustré du tutoriel. La qualification temporelle et les incertitudes de futures mesures restent ouvertes.

Le contrôle Gaia des poses ajoute 20 cas, soit **197 tests**. Plan `93c13cb` préalable : ≥20 associations réservées, médiane ≤2″, P95 ≤4″, ≥6 cellules et quatre quadrants par pose. Le contrôle principal exclut les détections d’ajustement ; le bilan toutes détections est secondaire. Les modèles sont gelés et le biais synthétique connu reste mesuré. Les trois poses privées satisfont les critères, sans modification des entrées ni accès USB/téléchargement. Les références partagées sont recensées ; aucune indépendance statistique, qualification temporelle ou certification de soumission n’est déduite. Voir [CONTRAT-GAIA-POSES.md](CONTRAT-GAIA-POSES.md).

La préparation temporelle ajoute 26 cas, soit **223 tests**. Plan `a157beb` préalable : lecture des en-têtes complets uniquement sur copies vérifiées, sans pixels ni réseau ; ambiguïtés de dates, doublons, unités et erreurs déclarées conservés. Même le cas synthétique riche en métadonnées ne qualifie aucune heure. Sur le pilote, le dossier et les huit exigences sont produits avec quatre copies et workset inchangés ; aucune mesure indépendante n’est fournie à cette commande. Un canevas complété n’est pas ingéré comme preuve et un essai futur ne certifie pas rétroactivement les archives. Voir [CONTRAT-PREUVES-TEMPS.md](CONTRAT-PREUVES-TEMPS.md) et le [protocole préparatoire](PROTOCOLE-QUALIFICATION-TEMPS.md). Les résultats des tests logiciels ne sont pas une qualification temporelle instrumentale.

Le complément opérationnel planifié dans `0ad755c` fournit une [fiche de campagne](CAMPAGNE-TEMPORELLE.md) et cinq canevas documentaires, sans changement de code d’analyse. Leurs structures, blocs proposés, journal vide, valeurs inconnues et refus de qualification sont contrôlés statiquement. Aucune mesure ou nouvelle validation logicielle/instrumentale n’est déduite de ces contrôles ; les 223 tests restent ceux du lot 0.9. Le dossier privé utilise seulement le rapport local existant, préservé par empreinte, sans réouverture de FITS ou accès USB.

Le prototype de mobiles ajoute 18 cas, soit **241 tests**. Plan `a072ff1` et seuils préalables. Sur 18 séquences fictives de huit images, les six injections nominales et trois intermittentes sont retrouvées, sans faux candidat dans les trois témoins. Les cinq injections manquées du scénario faible/lent restent visibles ; le total 16/21 ne remplace pas le bilan par scénario. Positions, vitesses fictives, intégrité, absence de réseau et séparation de vérité sont contrôlées. Les PNG/GIF sont issus des pixels fictifs et des candidats mesurés ; aucune performance sur mobiles réels ou précision d’horloge n’est déduite. Le [contrat](CONTRAT-MOBILES-SYNTHETIQUES.md) expose la sélection et les limites ; le [parcours pédagogique](DEMARRER-DE-ZERO.md) permet de reconstruire l’application depuis le code et reproduire tous les modules sans donnée privée.

Le [banc de limites](LIMITES-DETECTEUR.md), plan publié `6f3e6c5` avant code, ajoute 19 cas : **260 tests logiciels réussis**. Il réutilise le moteur 0.10 inchangé sur 120 séquences / 960 images, cinq nouvelles graines et 110 injections. Le bilan est descriptif, sans validation scientifique globale : les objets lents/faibles et le bruit limitent la récupération, et les défauts communs d’alignement peuvent entraîner les étoiles parmi les faux candidats. La dérive 0,15 pixel/s donne 200 faux candidats sur cinq séquences, sa combinaison avec rotation 194 ; les dix témoins alignés en donnent zéro. Les cas géométriques non alignés sont volontairement hors domaine, sans recalage exécuté ; ils ne certifient ni défaut général du S50 ni performance réelle. Le rapport conserve les manqués, erreurs conditionnelles aux appariements, taux et provenance. Aucun accès USB, mesure instrumentale ou collecte réelle ne complète le pilote dans ce lot.

Le [raccordement recalage/mobiles](RECALAGE-MOBILES-SYNTHETIQUES.md), plan publié `286af43` avant code, ajoute 17 cas : **277 tests logiciels réussis**. Sur 40 nouvelles séquences fictives, les critères globaux ne sont pas tous satisfaits : cinq des vingt séquences principales sont bloquées pour couverture de contrôle insuffisante. Les quinze disponibles retrouvent leurs quinze mobiles sans faux candidat. La comparaison appariée des sept séquences principales disponibles de dérive/combinaison donne 557 → 0 faux candidats, sans perte des sept mobiles ; aucune réduction globale n’est déduite pour les trois branches indisponibles de ces conditions. Les dix témoins acceptés donnent zéro après, les cinq négatifs sont bloqués comme prévu, la rotation 8 degrés reste descriptive. Les moteurs et FITS sont inchangés ; pas d’essai USB ou instrumental, pas de mise à niveau du verdict scientifique du pilote réel.
