# GNU Astrophotography Recycle

**Donner une seconde vie scientifique aux archives du Seestar S50.**

[Dépôt public et suivi du projet](https://github.com/steveprudhomme/gnu-astrophotography-recycle).

Projet de logiciel **libre, à distribution gratuite**, sous **GNU GPL version 3 ou ultérieure** ([texte intégral](COPYING), [application au projet](LICENSE-NOTICE.md)). La GPL permet aussi la redistribution commerciale.

Exception documentaire : les [images et le GIF Seestar réels autorisés](docs/images/reels/LICENCE.md) sont mis à disposition sous **CC0 1.0** ; leur notice précise les cinq fichiers concernés. Le code conserve GPL-3.0-or-later.

**Statut : Alpha 0.10 — inventaire, contrôles stellaires, préparation temporelle, prototype synthétique et premier pilote exploratoire sur huit poses Seestar réelles. Sept alignements acceptés, recherche achevée avec zéro candidat, GIF réel publié sous CC0. L'horloge, les performances sur mobiles réels, la photométrie et la distribution portable restent à qualifier ou développer.**

**Tu débutes ?** Suis [Construire l’application, pas à pas](docs/DEMARRER-DE-ZERO.md), un parcours illustré pour apprendre dès 10 ans : installer, récupérer tout le code, reconstruire l’application et reproduire chaque module sur de fausses images. Les commandes, résultats attendus et solutions aux erreurs y sont expliqués.

Le [contrôle Gaia des poses](docs/CONTRAT-GAIA-POSES.md) est livré dans le [commit `9bcf431`](https://github.com/steveprudhomme/gnu-astrophotography-recycle/commit/9bcf4318fc1fd1f5ffe2afe4ef72d7c364626f6e). Le lot applicatif 0.8 a passé **197 tests** ; ce résultat ne certifie ni l’horloge ni un budget d’erreur absolue complet.

L’Alpha 0.9 ajoute [la préparation des preuves temporelles](docs/CONTRAT-PREUVES-TEMPS.md) et un [protocole illustré de mesure future](docs/PROTOCOLE-QUALIFICATION-TEMPS.md). **223 tests** passent ; aucune mesure instrumentale ou qualification d’horloge n’est annoncée.

La [fiche opérationnelle de campagne](docs/CAMPAGNE-TEMPORELLE.md) complète ce protocole avec cinq canevas : configuration, blocs planifiés, journal de mesures vide, budget à renseigner et revue. Les moyens de référence et les versions non fournis restent à confirmer ; aucune acquisition n’est réalisée ou approuvée par le logiciel.

![Exemple synthétique : trois poses comparées à un catalogue fictif, avec biais connu conservé](docs/images/exemple-gaia-poses.png)

*Résultats réellement calculés sur des données synthétiques, sans observation personnelle. Le [tutoriel de comparaison Gaia](docs/TUTORIEL.md#13-comparer-les-trois-poses-à-gaia-sans-réajuster-les-modèles) fournit les commandes, les critères et la lecture de cette figure. La [procédure de publication](docs/TUTORIEL.md#14-mettre-à-jour-github-et-vérifier-la-publication) explique les vérifications avant et après envoi.*

## Mission

Permettre aux astronomes amateurs de réexaminer leurs poses FITS individuelles du ZWO Seestar S50 pour rechercher des objets mobiles et des variations stellaires. Chaque mesure devra être traçable, accompagnée de ses incertitudes et reproductible. Les originaux resteront intacts ; le traitement scientifique s’effectuera localement, sur Windows 11.

Le projet est indépendant et ne revendique aucune affiliation officielle au projet GNU, à ZWO, à l’AAVSO ou au Minor Planet Center.

## Fonctionnalités prévues

| Étape | Résultat attendu | État |
|---|---|---|
| Inventaire FITS | SHA-256, chaque HDU, anomalies, CSV/JSON et synthèse Markdown/SVG | Première version disponible, phase 1 |
| Séances candidates | Regroupement depuis un manifeste local, exclusions et résumés CSV/JSON/SVG | Première version disponible, phase 1 |
| Diagnostic temporel | Forme des dates, déclarations, cadence et anomalies depuis un manifeste local | Disponible ; ne certifie pas l’horloge, phase 2 |
| Préparation temporelle | En-têtes complets des copies, inconnues, canevas de preuves et protocole | Disponible ; aucun essai instrumental ni export temporel qualifié |
| Diagnostic WCS | Axes et paramètres observés, contrôles numériques limités et contexte manquant | Disponible ; ne certifie pas l’astrométrie, phase 2 |
| Échantillon local | Copie de fichiers sélectionnés, SHA-256 et collecte de tous les en-têtes | Disponible, sources préservées ; aucune mesure scientifique |
| Contrôle sur étoiles | Comparaison de la WCS originale à des références locales, résidus et couverture | Disponible ; critères exploratoires, sans certification de soumission |
| Recalage relatif | Rotation/translation vers une référence WCS gelée, contrôle sur étoiles réservées | Disponible ; composition céleste exploratoire, heures non qualifiées |
| Gaia sur poses | Comparaison des positions composées à un catalogue local, modèles gelés | Disponible ; verdict sur étoiles réservées, budget absolu incomplet |
| Qualification scientifique complète | Budget d’erreur absolue et horodatages vérifiés | À poursuivre, phase 2 |
| Prototype de mobiles | Trajectoires, erreurs, faux candidats et GIF sur données synthétiques | Disponible pour la recherche ; performances réelles non validées, phase 3 |
| Limites du détecteur | Nouveau jeu de 120 séquences fictives, luminosité/vitesse/bruit/géométrie | Bilan descriptif disponible ; moteur inchangé, cas non alignés séparés |
| Recalage puis mobiles | Comparaison des mêmes positions avant/après sur 40 séquences fictives | Expérimental : bénéfice sur séquences disponibles, critères globaux non tous satisfaits |
| Contrôles spatiaux | Comparaison de deux partitions sur 50 nouvelles séquences fictives | Expérimental : 20/20 principales disponibles, quinze négatifs refusés ; comportement habituel inchangé |
| Série Seestar réelle | Copies vérifiées puis recalage contrôlé, recherche et GIF locaux | Premier pilote achevé : sept alignements acceptés, zéro candidat ; performances réelles non qualifiées |
| Injections sur fond Seestar | Points artificiels dans les dérivés d'intensité, recalage gelé et réponses séparées | Bilan conditionnel : 10/36 ajouts retrouvés sur le fond réel, 26 manqués ; aucune découverte |
| Diagnostic des manques | Positions déjà enregistrées suivies aux trois étapes, sans nouvelle recherche | 26 réconciliés : neuf hors vitesse, 17 avec support limité dès les détections ; causes physiques non établies |
| Trace interne du détecteur | Rejeu comparé aux positions gelées, maxima et filtres expliqués | 17 cas examinés : sur 136 images, 115 sans maximum brut proche et 21 avec point retenu ; seuils inchangés |
| Création des maxima | Convolution et portes numériques avant les graines proposées | Parmi les 115 absences : 105 cercles sans réponse dépassant le seuil, dix avec réponse dépassant le seuil mais sans maximum local ; obstacles cumulés conservés |
| Photométrie différentielle | Courbes de lumière et budget d’incertitude | Recherche, phase 4 |
| Passerelles scientifiques | Exports AAVSO, MPC ADES et ALCDEF validés localement | Phase 5 |

## Limites

Le [premier pilote Seestar](docs/PILOTE-MOBILES-SEESTAR.md), plan publié avant code, ajoute 19 tests fictifs, soit **335 tests réussis** à ce lot. Le [nouvel exercice illustré dès 10 ans](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--aligner-les-étoiles-et-chercher-un-mobile) reproduit mobile, témoin et refus en neuf commandes. L'autorisation réaffirmée du mainteneur permet maintenant de publier aussi le GIF et les illustrations réels sous CC0 ; trois tests de diffusion supplémentaires portent la suite à **338 tests réussis**. Zéro candidat sur huit poses ne prouve pas l'absence d'objet mobile.

![Huit vraies poses Seestar, brutes à gauche et affichage aligné à droite, sous CC0](docs/images/reels/seestar-pilote-cc0.gif)

*Observations réelles, différentes des exercices fictifs. Cadence de lecture artificielle de 0,6 seconde par pose ; interpolation uniquement pour l'affichage. Aucun mobile détecté par cet essai. [Provenance et licence CC0](docs/images/reels/LICENCE.md).*

Le [bilan d'injections conditionnelles](docs/INJECTIONS-SEESTAR.md) ajoute 19 tests fictifs, soit **357 tests réussis**. Sur les dérivés du fond réel, 10/36 points artificiels sont retrouvés, 26 manqués et le témoin garde exactement le zéro candidat du pilote naturel. Le recalage est gelé ; ce résultat ne qualifie pas une sensibilité universelle du Seestar. Le [nouvel exercice illustré](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--retrouver-des-points-ajoutés-exprès) se refait en cinq commandes sur un fond entièrement fictif.

Le [diagnostic après score](docs/DIAGNOSTIC-MANQUES.md) ajoute 24 tests fictifs, soit **381 tests réussis**. Sans changer les seuils, il réconcilie les 26 manques : neuf hors plage de vitesse et 17 avec moins de cinq images contenant un point proche dès les positions de détection enregistrées, aux deux voisinages. Cela ne prouve pas une luminosité seule responsable. Le [tutoriel illustré](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--comprendre-les-points-manqués) ajoute deux commandes sur les résultats existants ; aucun accès USB ou nouvelle recherche.

Une détection n’est pas une découverte confirmée. Un GIF ne constitue pas une mesure scientifique. La qualité des archives, des calibrations, des heures et des catalogues détermine les usages possibles. Le vert Bayer n’est pas automatiquement une mesure Johnson V. Aucun format d’export ni aucune acceptation par un organisme n’est garanti à ce stade. Aucune soumission automatique n’est prévue.

La [trace interne du détecteur](docs/TRACE-DETECTEUR.md) approfondit les 17 manques en rejouant les pixels des seuls dérivés locaux, avec égalité exigée aux positions enregistrées. Les 115 absences de maximum proche ne permettent pas de séparer seuil, voisinage, séparation, masque ou bord ; aucun rejet de forme ou de marge proche n'est observé dans ces cas. Les deux rayons donnent les mêmes constats, sans nouvelle trajectoire ou changement de seuil. Un nouveau banc indépendant de douze images fictives et trois commandes pédagogiques illustre les portes. Trois agents ont travaillé en parallèle avec intégration et revue internes ; aucune validation scientifique indépendante n'est annoncée.

Ce lot ajoute 42 tests fictifs : **423 tests réussis en 139,60 s**, depuis le commit propre `f6ec207`. Les trois commandes, douze images et traces fictives, deux figures et 136 traces réelles ont été reproduites ; scores, candidats, copies et cinq médias CC0 sont intacts. Version et moteurs inchangés. Les essais sont locaux, sans nouvel accès USB ni nouvelle injection réelle.

Le [diagnostic des absences de maxima](docs/ABSENCES-MAXIMA.md) suit ensuite convolution, comparaison locale, masque, bord, seuil strict et plateaux/égalités, sans modifier les règles. Dans 105 des 115 situations, aucune réponse échantillonnée proche ne dépasse le seuil aux deux rayons ; dans les dix autres, une réponse le dépasse mais un voisin plus haut est enregistré et aucun maximum local proche n'est proposé. Cela décrit des obstacles numériques, sans démontrer une cause physique unique. Les premières portes vides changent dans 22 situations quand le cercle s'élargit : les deux lectures restent visibles. Trois agents ont travaillé sur un nouveau banc fictif, les tests et le tutoriel illustré ; les rapports réels restent privés.

## Démarrer

Les documents sont lisibles immédiatement. L’inventaire a été testé avec Python 3.13.6, Astropy 7.2.0 et NumPy 2.4.1 sur Windows. Le lanceur `scripts/gar-inventory.bat` utilise votre Python ou l’environnement `.venv` du projet ; voir [INSTALL.md](INSTALL.md). Il n’est pas encore autonome.

1. Lire le [dossier de lancement](docs/DOSSIER-LANCEMENT.md).
2. Suivre la [feuille de route](ROADMAP.md) et le [protocole pilote](docs/VALIDATION-PILOTE.md).
3. Consulter [INSTALL.md](INSTALL.md) et [CONTRIBUTING.md](CONTRIBUTING.md).
4. Suivre le [tutoriel illustré](docs/TUTORIEL.md) pour produire un exemple synthétique et lire les rapports.

Depuis PowerShell, à la racine du projet, avec les dépendances installées :

```powershell
.\scripts\gar-inventory.bat "D:\ArchivesFITS" --output ".\local\premier-inventaire"
```

Choisir une sortie nouvelle et extérieure aux archives. Le calcul SHA-256 lit tous les fichiers et peut prendre du temps. Les rapports contiennent potentiellement des informations privées ; ils restent locaux. Voir le [contrat des sorties et codes de retour](docs/CONTRAT-INVENTAIRE.md).

Pour regrouper un manifeste déjà présent sur l’ordinateur, sans rouvrir les FITS :

```powershell
.\scripts\gar-sessions.bat ".\local\premier-inventaire\manifest.json" --output ".\local\seances-01"
```

Les dates déclarées et les configurations restent séparées ; les interruptions de plus de 30 minutes coupent un groupe par défaut. Les copies, empilements et dates inutilisables sont expliqués dans les exclusions. Le [contrat des séances](docs/CONTRAT-SEANCES.md) précise les limites et le code de retour `2`, qui peut signaler des exclusions attendues. Aucun fichier n’est déplacé. Choisir la destination locale indiquée pour ne rien écrire sur le support externe des observations.

Pour diagnostiquer les horodatages du même manifeste, sans rouvrir les observations :

```powershell
.\scripts\gar-timing.bat ".\local\premier-inventaire\manifest.json" --output ".\local\horodatages-01"
```

Le [diagnostic temporel](docs/CONTRAT-HORODATAGES.md) sépare résolution écrite et exactitude. Aucun milieu de pose n’est calculé ; les heures restent non qualifiées sans preuve indépendante. Le code `2` après production des rapports rappelle cette limite, même si la cadence ne présente aucune anomalie.

Pour examiner les informations WCS disponibles dans le même manifeste :

```powershell
.\scripts\gar-wcs.bat ".\local\premier-inventaire\manifest.json" --output ".\local\wcs-01"
```

Le [diagnostic WCS](docs/CONTRAT-WCS.md) ne rouvre pas les FITS et ne calcule aucune position céleste. Le manifeste étant partiel, le code `2` après production des rapports rappelle qu’aucune solution astrométrique n’est certifiée.

Les FITS personnels, coordonnées d’observation et paramètres locaux ne doivent pas être joints aux contributions publiques. Voir la [politique des données](docs/DONNEES.md).

Pour préparer des copies de travail dans `local/`, suivre le [contrat d’échantillon local](docs/CONTRAT-WORKSET.md) et le [tutoriel illustré](docs/TUTORIEL.md). Les sources sont uniquement lues ; les en-têtes complets et modèles construits restent privés et ne certifient pas les positions célestes.

La commande [astrometry](docs/CONTRAT-ASTROMETRIE.md) permet ensuite une comparaison hors ligne sur étoiles, sans réajuster la WCS. Les critères doivent être fixés avant l’évaluation ; l’acquisition éventuelle d’un catalogue réseau est une étape séparée, explicitement autorisée.

Pour recaler des poses déjà copiées, sans consulter les sources historiques :

```powershell
.\.venv\Scripts\python.exe -m gar register ".\local\lot\workset.json" --reference-index 4 --frame-indices 1 2 3 --output ".\local\recalage-01"
```

Le [contrat de recalage](docs/CONTRAT-RECALAGE.md) explique les étoiles réservées, les critères, la composition vers la WCS de référence et l’erreur héritée. Aucun FITS n’est modifié ; aucun support externe ni catalogue réseau n’est consulté par cette commande. Le [tutoriel](docs/TUTORIEL.md#12-recaler-trois-poses-locales-avec-un-contrôle-réservé) fournit un exemple entièrement synthétique illustré.

Pour contrôler ensuite les coordonnées composées contre le catalogue local, sans réajuster les modèles :

```powershell
.\.venv\Scripts\python.exe -m gar gaia-frames ".\local\lot\workset.json" --registration ".\local\recalage-01\registration.json" --catalog ".\local\references\catalog.csv" --output ".\local\gaia-poses-01"
```

Le [contrat Gaia des poses](docs/CONTRAT-GAIA-POSES.md) distingue le verdict sur étoiles réservées du bilan secondaire sur toutes les détections. Le catalogue doit avoir son `provenance.json` avec SHA-256. Tout est local, sans USB ni téléchargement ; les heures et le budget d’erreur absolue restent non qualifiés.

Pour préparer le dossier temporel depuis les copies déjà locales, sans consulter les originaux :

```powershell
.\.venv\Scripts\python.exe -m gar time-evidence ".\local\lot\workset.json" --output ".\local\preuves-temps-01"
```

Le code **2** signifie que le dossier a été produit avec une heure toujours non qualifiée. Le [tutoriel illustré](docs/TUTORIEL.md#15-préparer-la-qualification-des-horodatages-sur-les-copies-locales) explique les six sorties, le cas synthétique et les preuves encore nécessaires. Aucune date UTC de milieu de pose n’est calculée.

Pour essayer les mobiles sans observation réelle ni accès USB :

```powershell
.\.venv\Scripts\python.exe examples/make_moving_demo.py local/demo-mobiles-input
.\.venv\Scripts\gar.exe moving-synthetic local/demo-mobiles-input/manifest.json --truth local/demo-mobiles-input/truth.json --output local/demo-mobiles-report
```

Le [contrat du prototype](docs/CONTRAT-MOBILES-SYNTHETIQUES.md) explique les critères et les échecs conservés. **381 tests logiciels passent**, avec les bancs de recherche, la préparation de série, le pilote, les injections conditionnelles et leur diagnostic. La suite initiale fictive retrouve les six mobiles nominaux et trois intermittents ; cinq injections faibles ou très lentes sont manquées. Aucun résultat réel ou horodatage instrumental n'est qualifié par cet exercice.

![Animation calculée sur les images fictives du prototype, avec trajectoires mesurées](docs/images/exemple-mobiles-animation.gif)

*Images entièrement synthétiques ; les lignes relient les candidats mesurés. Le [parcours débutant](docs/DEMARRER-DE-ZERO.md#13-mission--retrouver-les-points-qui-bougent) et le [tutoriel de référence](docs/TUTORIEL.md) expliquent comment reproduire l’animation.*

## Explorer les limites

Le [nouveau banc de limites](docs/LIMITES-DETECTEUR.md) mesure le moteur inchangé sur **120 séquences / 960 images fictives**. Les mobiles très lents sont manqués ; l’augmentation du bruit réduit la récupération. Hors de l’hypothèse d’images alignées, la dérive du champ produit de nombreux faux candidats parmi les étoiles. Les témoins et les échecs restent visibles ; aucune performance réelle n’est déduite. La [mission dès 10 ans](docs/DEMARRER-DE-ZERO.md#13-bis-mission--trouver-les-limites-du-chercheur) permet de reproduire cartes et animation, sans USB.

![Carte de récupération réellement calculée sur les nouvelles images fictives](docs/images/limites-detecteur-grille.png)

## Recaler avant de chercher

La [chaîne recalage puis recherche](docs/RECALAGE-MOBILES-SYNTHETIQUES.md) compare 40 nouvelles séquences fictives, sans changer les moteurs ni les pixels FITS. Les critères globaux ne sont **pas tous satisfaits** : seules 15/20 séquences principales sont exploitables après recalage, leurs 15 mobiles sont retrouvés sans faux candidat ; les cinq autres sont bloquées pour couverture de contrôle insuffisante. Sur les sept séquences comparables de dérive/combinaison, 557 faux candidats passent à zéro, sans extrapoler aux séquences bloquées. La [mission dès 10 ans](docs/DEMARRER-DE-ZERO.md#13-ter-mission--stabiliser-les-positions-avant-de-chercher) explique aussi le code 2 attendu, les refus et la superposition de coordonnées sur un fond fixe.

## Répartir les contrôles et préparer le pilote Seestar

La [répartition spatiale des contrôles](docs/CONTROLES-SPATIAUX.md) est comparée à l’ancienne sur **50 nouvelles séquences fictives** : 20/20 principales disponibles contre 17/20 sur ces mêmes images, vingt mobiles retrouvés sans faux candidat, quinze négatifs toujours refusés. Les critères sont inchangés et la commande habituelle de recalage n’est pas remplacée. Les anciens résultats restent conservés. La [mission pédagogique illustrée](docs/DEMARRER-DE-ZERO.md#13-quater-mission--répartir-les-étoiles-de-contrôle) permet de reproduire l’essai.

**Les images Seestar sont maintenant utilisées :** [huit poses réelles préparées en copies locales vérifiées](docs/PREPARER-SERIE-SEESTAR.md) ont servi au pilote naturel, puis à l'essai sur dérivés avec ajouts artificiels. Les FITS restent intacts ; le témoin naturel conserve zéro candidat. Le [tutoriel dès 10 ans](docs/DEMARRER-DE-ZERO.md#nouvelle-mission--retrouver-des-points-ajoutés-exprès) permet de refaire les nouvelles étapes sur un fond fictif, sans clé USB. Temps scientifiques, modèle de capteur et performance de bout en bout restent à qualifier.

![Huit vraies poses Seestar, exemple autorisé CC0](docs/images/reels/seestar-serie-cc0.png)

*Images réelles partagées sous [CC0 1.0](docs/images/reels/LICENCE.md) avec autorisation explicite du mainteneur. Moyenne 2×2 et étirement d’affichage ; aucun FITS réécrit, aucune détection scientifique validée. Le code conserve sa licence GPL-3.0-or-later.*

## Contribuer et vérifier

Proposer un objectif, produire un changement limité, ouvrir une proposition de fusion, attendre la revue et itérer. Toute évolution scientifique doit préciser ses hypothèses, ses références et ses critères de validation. Les décisions sont consignées publiquement ; les données privées restent locales.

Voir [gouvernance](GOVERNANCE.md), [licences tierces](docs/LICENCES-TIERCES.md) et [sources](docs/SOURCES.md).

Une [note de propositions pour les métadonnées Seestar S50](docs/PROPOSITIONS-SEESTAR-S50.md) rassemble les demandes de clarification et améliorations à discuter avec la communauté, en séparant constats limités et recommandations.

[English version — Seestar S50 FITS recommendations](docs/SEESTAR-S50-FITS-RECOMMENDATIONS.en.md), including the translated illustration and references.
