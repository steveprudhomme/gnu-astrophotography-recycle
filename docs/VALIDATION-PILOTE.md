# Protocole pilote et critères de validation

## Premier pilote de mobiles sur huit copies locales

Le [lot 16](PILOTE-MOBILES-SEESTAR.md), plan `8f5a64b` publié avant code, a exécuté le recalage puis la recherche sur les huit poses préparées au lot 15. Sept modèles acceptés avec 64 à 77 contrôles, neuf cellules et quatre quadrants ; P95 de contrôle entre environ 0,69 et 1,09 pixel natif. Recherche achevée avec zéro candidat, GIF réel privé avant/après, copies intactes et aucun nouvel accès USB/réseau. Ce n'est pas une validation de sensibilité, de taux de fausses alertes, d'heure ou de mesure scientifique.

Les 19 nouveaux tests sont fictifs : un mobile connu retrouvé, zéro candidat du témoin, refus d'effectif sans faux zéro, transformations natives et domaine commun, masques, audit/intégrité, absence d'accès aux sources et à la vérité, lecture seule et sorties partielles. La suite compte **335 tests réussis**. Les anciennes expériences restent documentées ci-dessous ; leur résultat ne change pas avec ce premier pilote réel.

L'autorisation réaffirmée au lot 17 ajoute la diffusion CC0 du GIF réel et de deux illustrations à la notice des médias. Trois tests fictifs supplémentaires vérifient le mode réel explicite et les métadonnées, soit **338 tests réussis en 78,93 secondes**. Il s'agit d'une vérification de diffusion, sans nouvelle recherche ni qualification scientifique ; les copies et le rapport restent intacts.

## Récupération conditionnelle sur dérivés, lot 18

Plan `9344495` publié avant code sur une branche dédiée. Avec le recalage accepté gelé, les [injections](INJECTIONS-SEESTAR.md) testent trois pics, quatre vitesses et trois départs fixés : 36 séries plus un témoin. Sur fond réel : **10/36 ajouts artificiels retrouvés, 26 manqués, zéro indisponible**, aucun candidat non associé, témoin identique au pilote naturel sans candidat. Ce résultat conditionnel ne teste ni l'erreur astrophysique du recalage, ni un modèle complet de capteur ou une limite en magnitude ; trois trajets sur les mêmes poses ne sont pas indépendants.

Sur le fond entièrement fictif du nouvel exercice : 12/36 retrouvés, 24 manqués, témoin sans candidat, trois brillants nominaux retrouvés et aucun trop lent à 0,03 récupéré. Dix-neuf tests fictifs nouveaux portent la suite à **357 tests réussis en 123,13 secondes** ; le contrôle des figures est rejoué après un ajustement d'affichage, sans changement des mesures. Les FITS, le rapport naturel et les moteurs restent intacts, sans accès USB. La génération, l'analyse aveugle et le score sont séparés, avec candidats gelés avant lecture des réponses.

## Diagnostic après score, lot 19

Plan `b69ca08` publié avant code. Le [diagnostic](DIAGNOSTIC-MANQUES.md) lit les positions et scores gelés sans appeler les fonctions de recherche : 26 manques réconciliés, neuf hors plage de vitesse et 17 avec support limité dès la détection enregistrée. Pour ces 17, neuf ont zéro image avec un point proche, quatre en ont deux, trois en ont trois et un en a quatre, aux rayons 1,5 et 3 pixels natifs ; aucun n'atteint cinq images. Les restrictions de champ et de filtre ne retirent pas de support supplémentaire observé dans ces cas. Ce n'est pas une preuve de cause physique ou de faible luminosité seule.

Vingt-quatre tests entièrement fictifs portent la suite à **381 tests réussis** ; ils couvrent aussi ambiguïtés, refus d'entrées modifiées, états inconnus/incomplets, sous-ensembles et absence d'appels au moteur. Les neuf exclusions de vitesse conservent leurs autres pertes observées. Récupérations, candidats, rapports d'origine, dérivés, copies, moteurs et seuils restent inchangés. Les dessins utilisent les pixels après le diagnostic pour l'affichage seulement, sans lecture USB ; les figures publiques nouvelles sont fictives.

## Trace des décisions internes, lot 20

Plan `08219f0` publié avant code et trois agents parallèles sur fichiers distincts. La [trace](TRACE-DETECTEUR.md) utilise le même détecteur et Photutils 3.1.1 avec sources épinglées ; les filtres reconstitués doivent reproduire la bibliothèque, puis le moteur et les positions gelées en pixels natifs à 10⁻⁹ près. Les 17 cas donnent 136 listes identiques : aux deux rayons, 115 images sans maximum brut proche et 21 avec point retenu, sans rejet de forme ou marge proche observé. Les causes possibles de l'absence de maximum restent non départagées ; les images partagent les mêmes fonds et ne sont pas indépendantes.

Les 42 nouveaux tests fictifs vérifient portes connues, inconnues, intégrité, divergences, absence de trajectoires/injections nouvelles et dessin sans redétection. Depuis le commit propre **`f6ec207`**, la suite complète donne **423 tests réussis en 139,60 s** ; trois commandes aux codes 0 reproduisent douze images et traces fictives et deux PNG. Les 136 traces réelles sont identiques, 360 entrées et notices/médias intactes ; gardes à zéro pour association, filtre stationnaire, injection, accès externe/réseau et écriture FITS/NPY. Les pixels sont relus uniquement pour la trace autorisée et l'affichage ; cela ne change pas la preuve sans pixels du lot 19. Les cinq médias CC0 restent inchangés, les nouveaux détails réels privés. Revue interne seulement, aucun essai instrumental ou enfant, aucun contrôle automatique GitHub configuré.

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

Le [lot 14 de contrôles spatiaux](CONTROLES-SPATIAUX.md), plan publié `bbe9776` avant code, ajoute vingt cas, soit **297 tests logiciels réussis**. Cinquante séquences fictives et nouvelles graines comparent les deux partitions avec critères inchangés : 17/20 principales disponibles historique et 20/20 spatiale sur ces mêmes images, vingt mobiles retrouvés sans faux candidat, quinze négatifs réellement insuffisants bloqués. Les huit critères exploratoires sont satisfaits sur ce jeu ; les anciens refus ne sont pas réécrits. Cela prépare la [revue d’une série réelle](PASSAGE-AUX-IMAGES-SEESTAR.md), mais ne valide ni Bayer ni l’horloge ou le budget céleste. La préparation de ce lot ne relit qu’un manifeste local et les documents existants, sans FITS réel ou USB.

Le [lot 15](PREPARER-SERIE-SEESTAR.md), plans publiés `594c19e` et `ae07304` avant leurs réalisations, prépare huit poses réelles successives en copies locales vérifiées : empreintes historiques/source avant/copie/source après concordantes, audit local de configuration et lecture des pixels terminé. Ces contrôles ne valident ni champ commun sur étoiles, ni mouvement ou horloge ; tous ces statuts restent faux. Les 19 nouveaux tests **entièrement fictifs** portent la suite à **316 tests réussis**. La diffusion des deux PNG réels rendus est explicitement autorisée [CC0](images/reels/LICENCE.md) ; FITS, en-têtes et rapports restent privés. Prochain lot : adapter et exécuter un pilote exploratoire sur les copies préparées, sans réétiquetage synthétique.
