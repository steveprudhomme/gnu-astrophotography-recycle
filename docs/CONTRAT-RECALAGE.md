# Recalage relatif exploratoire 1.0

`gar register` utilise exclusivement les copies d’un `workset.json` local, une référence et des indices de poses distincts (numérotation à partir de 1). Les chemins sources historiques ne sont jamais consultés. Les chemins hors de `local/` sont refusés avant de les sonder ; liens et jonctions sont refusés en parcourant les parents depuis la racine. Les empreintes des copies sont vérifiées avant/après. Aucune image n’est réenregistrée, rééchantillonnée ou modifiée. Aucun réseau ni support externe n’est nécessaire.

## Détection et ajustement

Les paramètres sont fixés dans le plan `6480df2` avant code et mesure réelle. La moyenne de blocs 2×2 atténue la réponse Bayer ; la référence à trois plans est d’abord moyennée, sans interprétation de son ordre colorimétrique. Un bloc contenant une valeur non finie ou ≥65 000 ADU est masqué. Pour des dimensions impaires, la dernière ligne/colonne ne participe pas à la détection. Les centres Photutils réduits reviennent aux pixels natifs par `2*x+0,5` (origine zéro). Ce traitement n’est ni une calibration des couleurs ni une mesure photométrique. Les réponses Bayer et les PSF peuvent biaiser les centroïdes ; les tests synthétiques ne caractérisent pas toutes les couleurs réelles.

DAOStarFinder utilise un seuil de 5 sigmas robustes, FWHM 2 pixels réduits et séparation minimale de 4 pixels réduits. Les centres natifs sont limités à une marge de 10 pixels et isolés de 8 pixels. Les détections sont classées par flux décroissant ; aucun flux n’est annoncé comme mesure scientifique.

Avant toute recherche de triangles, association ou ajustement, un quart entier des détections de chaque pose est réservé au contrôle : permutation NumPy avec graine `20261116`, au moins une détection réservée. Les détections réservées ne servent ni aux hypothèses ni au score de sélection ni à l’ajustement final. Les positions de référence restent gelées ; ce contrôle n’établit pas l’indépendance de l’empilement par rapport aux poses.

Les triangles proviennent des 80 détections les plus brillantes disponibles dans chaque ensemble d’ajustement/référence. Les longueurs opposées aux sommets ordonnent les correspondances. Les côtés doivent dépasser 20 pixels, différer de plus de 3 pixels et le double de l’aire dépasser 100 pixels carrés. La recherche retient le plus proche triangle de même orientation, à distance euclidienne ≤2 pixels dans l’espace des trois longueurs, puis au plus 1 000 hypothèses classées par cette distance. Ce plafond et les ambiguïtés des champs réguliers peuvent empêcher ou fausser une identification ; ce n’est pas un solveur aveugle universel.

Chaque hypothèse est une rotation de déterminant +1 et une translation : `p_reference = R @ p_pose + t`. Le score initial compte les voisins d’ajustement à au plus 3 pixels, avec médiane pour départager. Le modèle retenu est réajusté par moindres carrés sur des associations mutuelles uniques, dans le même rayon, au plus dix fois ou jusqu’à stabilisation des associations. Échelle, réflexion, cisaillement et déformation libres sont interdits. Le contrôle est associé seulement après gel du modèle.

## Critères et limites

Tous les critères préenregistrés sont nécessaires :

- au moins 20 associations d’ajustement et 10 de contrôle ;
- médiane des résidus de contrôle ≤0,75 pixel natif et percentile 95 ≤1,5 pixel ;
- étoiles de contrôle dans au moins 6 cellules d’une grille 3×3 et les quatre quadrants de la pose.

Le rapport conserve les détections réservées, les effectifs non associés et tous les résidus après association. Aucun retrait de grands résidus n’est effectué après cette sélection pour réussir les critères. **Le rayon de 3 pixels sélectionne toutefois les erreurs observables**, y compris pendant l’ajustement : un résidu au-delà du rayon ne figure pas parmi les associés. La couverture de cellules n’est pas une garantie pour chaque pixel, les bords ou les sources non détectées.

Le succès signifie un recalage relatif exploratoire. Aucune indépendance statistique vis-à-vis de la fabrication de l’empilement n’est démontrée. Les erreurs de la référence, corrélations, distorsions différentielles, couleurs, bruit et biais de centroïdes ne sont pas réunis dans un budget absolu complet. Aucune incertitude angulaire absolue n’est obtenue en combinant arbitrairement les résidus de deux contrôles.

## Composition céleste

Pour une pose acceptée, le JSON conserve sa transformation et la WCS céleste gelée de la référence, avec SIP. C’est une **composition explicite de transformations**, pas une WCS FITS copiée. Les distorsions par tables externes `CPDIS`/`DET2IM` sont refusées : leur contexte ne serait pas sérialisé dans ce format. La sérialisation SIP et son utilisation sont testées.

La fonction Python `gar.registration.composed_sky(resultat_pose, x, y)` vérifie `model_usable` et le domaine de recouvrement avant d’appliquer la transformation puis la WCS. Les coordonnées sont en pixels natifs, origine zéro, x puis y. La fonction rejette les valeurs non finies et les points hors image/référence. L’erreur absolue est héritée de la référence ; la composition n’ajoute pas une validation contre un catalogue indépendant sur chaque pose. `clock_qualified` et `scientific_submission_certified` restent faux. Aucun milieu de pose UTC ou vitesse de mobile n’est calculé.

## Commande et sorties

```powershell
.\.venv\Scripts\python.exe -m gar register ".\local\lot\workset.json" --reference-index 4 --frame-indices 1 2 3 --output ".\local\recalage-01"
```

La destination doit être nouvelle. Produits : `registration.json` (modèles, paramètres, sélections, résultats, SHA-256, versions et révision), `matches.csv` (associations d’ajustement et de contrôle), `registration.svg` (contrôle par pose), `report.md`. Un échec de détection/recalage d’une pose est conservé avec son motif et n’empêche pas l’examen des autres poses. Une référence inutilisable ou une erreur d’intégrité arrête le lot. Une erreur d’écriture peut laisser un dossier partiel ; choisir une nouvelle sortie après résolution, sans interpréter ce dossier comme complet.

Codes : `0` si toutes les poses satisfont les critères ; `2` si le rapport est produit mais une pose échoue ; `1` si entrée, intégrité ou production impossible. Les résultats réels, en-têtes sérialisés et figures du champ restent privés dans `local/`.

Références : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [SciPy cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html), [Astropy WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). Le choix des triangles, du modèle rigide et des seuils est une décision du projet, évaluée synthétiquement ; ces pages décrivent les bibliothèques utilisées, pas une validation instrumentale du S50.

La commande distincte [gaia-frames](CONTRAT-GAIA-POSES.md) contrôle ensuite les positions composées contre un catalogue local, sur les détections déjà réservées et sans réajuster le modèle. Elle vérifie la reproduction des détections et leur partition ; les heures et le budget absolu restent non qualifiés.

La [recette synthétique recalage/mobiles](RECALAGE-MOBILES-SYNTHETIQUES.md) réutilise `detect` et `register_points` sans modifier ce module ou ses critères. Elle n’appelle pas la composition céleste : elle transforme les détections natives vers le repère mesuré de la première image. Un seul modèle refusé bloque toute la branche après de la séquence. Sur le jeu planifié, cinq séquences principales sont refusées pour contrôle dans trois quadrants, et les cinq négatifs pour effectifs insuffisants ; les critères globaux ne sont pas tous satisfaits. Cela ne modifie pas rétroactivement les conclusions du pilote réel.

Le [lot de contrôle spatial](CONTROLES-SPATIAUX.md), plan publié `bbe9776`, ajoute une partition de recherche dans les exemples, sans changer ce module ou le comportement de `gar register`. Elle réserve les contrôles par intersections quadrants/cellules avant tout ajustement, avec la même fraction et les mêmes critères. Sur les mêmes nouvelles images, disponibilité principale 17/20 historique et 20/20 spatiale, sans faux candidat après ; les quinze négatifs restent bloqués. Les anciens bilans restent inchangés et cette comparaison ne qualifie pas les pixels ou les heures du Seestar.
