# Comparaison astrométrique exploratoire 1.0

`gar astrometry` lit un lot de copies vérifiées et un catalogue CSV local. Tous les chemins doivent rester dans `local/` du projet, sans liens ou jonctions. La copie choisie est vérifiée par SHA-256 avant/après ; l’original externe n’est jamais ouvert. Aucun service réseau n’est appelé pendant cette analyse.

## Préparer le catalogue séparément

Le CSV doit contenir `source_id`, `ra`, `dec`, `pmra`, `pmdec`, `ref_epoch`, `phot_g_mean_mag` et `ruwe`. Les angles sont en degrés ICRS, les mouvements propres en mas/an (`pmra` inclut cos(dec)), l’époque en années juliennes TCB. Les erreurs disponibles restent dans le fichier source. Le catalogue est privé par défaut : sa requête peut révéler la cible observée.

Pour l’essai réel, un extrait **Gaia DR3 de l’archive ESA** a été acquis après accord explicite du fondateur. Seule la zone céleste a été transmise, sans FITS, en-tête complet ni position terrestre. La requête, la version et l’empreinte sont conservées dans `provenance.json`, à côté du CSV. Le programme vérifie cette empreinte lorsque ce fichier existe. Un catalogue de 20 000 lignes ou plus est refusé dans cette version pour éviter d’accepter une extraction potentiellement tronquée.

La comparaison ne télécharge pas son catalogue implicitement. Les identifiants relient les associations au catalogue d’origine ; la licence et les obligations de citation des catalogues restent distinctes de la GPL du logiciel. Les données réelles ne sont pas redistribuées dans le dépôt.

## Paramètres fixés avant mesure

La détection utilise Photutils DAOStarFinder : seuil de 8 écarts-types robustes du fond, FWHM initiale de 3 pixels, marge de 10 pixels, séparation de 8 pixels et exclusion des pixels à au moins 65 000 ADU. Ces valeurs sont adaptées à ce pilote 16 bits et ne constituent pas un étalonnage universel de tout FITS. Pour une image à trois plans, leur moyenne arithmétique sert seulement à détecter les positions ; aucun ordre RGB ni système photométrique n’est déduit.

Les références doivent avoir G entre 9 et 17,5, RUWE <1,4 et des coordonnées/mouvements propres finis. Elles sont propagées à une époque approximative correspondant à midi TCB de la date calendaire déclarée. Cela ne qualifie ni le fuseau effectif ni l’horloge instrumentale. Le calcul omet distance et vitesse radiale ; avertissements et limites sont conservés. Les références sont limitées à l’intérieur du champ et isolées de 16 secondes d’arc.

La WCS originale avec son contexte SIP est utilisée sans réajustement. L’association est au plus proche, mutuelle et unique, dans un rayon de 8 secondes d’arc. Aucun décalage n’est soustrait, aucun nouveau modèle n’est ajusté et aucun grand résidu n’est retiré après association. Le rayon sélectionne néanmoins les erreurs observables : ce contrôle n’est pas une recherche aveugle de solution et ne démontre rien sur les sources non associées.

## Critères exploratoires préenregistrés

Tous les critères suivants sont requis :

- au moins 30 associations ;
- médiane des écarts ≤2 secondes d’arc ;
- percentile 95 ≤4 secondes d’arc ;
- au moins 6 cellules occupées sur une grille de 3×3 et les quatre quadrants.

Ils ont été fixés dans `d349984` avant mesure, puis les paramètres de sélection ont été consignés dans `fe3b1c4`. Un changement futur doit rester un essai distinct et documenté, sans remplacer silencieusement un échec. Ces seuils ne sont pas une norme MPC.

## Résultats et incertitudes

Le rapport mesure séparations, résidus tangentiels Est/Nord, biais moyens, RMS radial, médiane, percentile 95 et couverture spatiale. Un bootstrap de 500 tirages avec graine `20261116` donne un intervalle exploratoire à 95 % pour la médiane de cet échantillon. Ce n’est **pas** l’incertitude absolue de chaque position : dépendances spatiales, erreurs de centroïde, covariance complète Gaia, parallaxe et perspective ne sont pas intégrées dans un budget exhaustif.

Un catalogue externe ne garantit pas que les étoiles soient statistiquement indépendantes de celles utilisées par le solveur initial. Ce lien n’a pas été établi pour l’empilement réel. Le passage des critères signifie une compatibilité géométrique sur l’échantillon sélectionné, pas une certification des futures mesures de mobiles, de toutes les positions du champ ou d’une soumission scientifique. `scientific_submission_certified` et `clock_qualified` restent faux.

## Commande et produits

```powershell
.\.venv\Scripts\python.exe -m gar astrometry ".\local\lot\workset.json" --file-index 1 --catalog ".\local\references\catalog.csv" --output ".\local\controle-01"
```

`--file-index` commence à 1 dans la liste du lot. Les sorties doivent être nouvelles : `astrometry.json`, `matches.csv`, `residuals.svg` et `report.md`. Le JSON conserve critères, paramètres, sélections, empreintes, environnement et résultat ; le CSV relie chaque association au catalogue. Les cartes de résidus ne montrent aucun réajustement.

Code `0` : critères exploratoires satisfaits. Code `2` : calcul produit mais critères non satisfaits. Code `1` : analyse impossible ou entrée incorrecte. Une erreur avant la production du rapport ne doit pas être interprétée comme un échec scientifique mesuré.

Références : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [Astropy — mouvements propres](https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html), [Gaia — solution astrométrique](https://arxiv.org/abs/2012.03380). Les données du pilote proviennent de l’ESA Gaia Archive et du consortium Gaia DPAC ; ce dépôt ne les héberge pas.

Le [recalage relatif](CONTRAT-RECALAGE.md) est une commande distincte : il ajuste une rotation/translation vers une référence puis compose sa WCS. Il ne transforme pas ce contrôle sans réajustement en une certification absolue des poses.
