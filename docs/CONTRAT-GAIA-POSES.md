# Comparaison Gaia des poses — contrat 1.0

`gar gaia-frames` compare les détections réservées avant recalage aux références d’un catalogue local. Les modèles de `gar register` sont **gelés** : aucun ajustement, résolution, correction du biais ou écrêtage après association. Le contrôle porte sur les coordonnées obtenues par composition pose → pixels de référence → WCS céleste avec SIP.

## Entrées et préservation

Trois entrées explicites, toutes sous `local/` : `workset.json`, `registration.json` et catalogue CSV. Un `provenance.json` contenant l’empreinte `sha256` du catalogue est obligatoire à côté de celui-ci. Les colonnes et unités Gaia sont celles du [contrat astrométrique](CONTRAT-ASTROMETRIE.md) ; les identifiants doivent être non vides et uniques. Un catalogue de 20 000 lignes ou plus est refusé comme potentiellement tronqué. Aucun téléchargement implicite.

Le rapport de recalage doit être de schéma 1.0, correspondre exactement au SHA-256 du workset et conserver les paramètres de détection attendus. Les indices de poses/référence doivent être distincts et valides. Les empreintes des copies sont rapprochées de celles du workset et du recalage avant/après. Le programme lit uniquement `local_copy`, jamais les chemins sources historiques. Les chemins hors de `local/` sont refusés avant sondage ; liens et jonctions sont interdits.

La détection est reproduite sur la référence et les poses, sans nouvel ajustement. Les sélections, formes, coordonnées des associations enregistrées, résidus et partition réservée sont contrôlés. La partition doit reproduire la permutation du lot de recalage (graine `20261116`, quart entier réservé avant ajustement). La matrice doit être une rotation propre, sans échelle ni réflexion. La WCS sérialisée doit être celle de la copie de référence. Un changement de détecteur/ordre ou un modèle incohérent exige une analyse distincte ; il n’est pas corrigé silencieusement.

Tous les fichiers d’entrée — copies sélectionnées, workset, modèle, catalogue et provenance — sont hachés avant/après. Aucun FITS ni rapport antérieur n’est réécrit. Une pose dont le recalage a été refusé reste en échec dans le rapport ; une incohérence de provenance ou d’intégrité arrête l’analyse.

## Échantillon principal et références

L’échantillon principal comprend **toutes les détections réservées** situées dans le recouvrement utile, y compris celles qui n’avaient pas trouvé d’association dans l’empilement. Leur nombre d’associations Gaia peut donc dépasser celui du précédent contrôle pose/empilement. Les étoiles d’ajustement ne contribuent jamais à son verdict. La référence et la pose doivent contenir les points avec une marge de 10 pixels natifs ; le catalogue est projeté sur la référence puis ramené dans la pose par l’inverse de la rotation/translation.

La sélection de références est commune avec `gar astrometry` : G entre 9 et 17,5, RUWE <1,4, positions et mouvements propres finis, voisin le plus proche à au moins 16″. Les mouvements propres sont propagés à midi TCB de la date calendaire déclarée par chaque pose. C’est une époque approximative, **pas une qualification de son heure**. Distance, vitesse radiale et parallaxe ne sont pas intégrées dans un budget complet ; les avertissements sont conservés.

Les associations sont au plus proche, mutuelles et uniques dans un rayon de 8″. Les résidus Est/Nord sont ceux de la référence vers la position mesurée, dans ICRS ; aucune moyenne n’est soustraite. Les détections hors recouvrement et non associées sont comptées séparément. Aucun retrait après association ne masque un grand résidu, mais le rayon initial sélectionne les erreurs observables et peut favoriser des associations fortuites si le modèle est faux.

## Critères préenregistrés

Le plan **`93c13cb`**, enregistré avant code et mesure réelle, exige séparément pour chaque pose :

- au moins **20 associations Gaia réservées** ;
- médiane des écarts tangentiels ≤2″ et percentile 95 ≤4″ ;
- au moins six cellules occupées sur une grille 3×3 de la pose, et les quatre quadrants.

Le minimum de 20 est adapté au quart réservé, distinct des 30 références demandées au contrôle de l’empilement. Aucun seuil n’est abaissé après mesure. Les effectifs, couverture et erreurs doivent être lus ensemble ; un petit sous-ensemble bien associé ne qualifie pas tout le champ.

Le rapport calcule médiane, P95, RMS radial, biais Est/Nord et intervalle bootstrap exploratoire à 95 % de la médiane (500 tirages, graine `20261116`). Il s’agit d’une statistique conditionnelle de l’échantillon associé, pas de l’incertitude absolue de chaque étoile. La médiane/P95 utilisent la norme des résidus tangentiels ; la séparation sphérique exacte est également conservée dans les associations.

Un second bilan `all_diagnostic` utilise toutes les détections éligibles, étoiles d’ajustement comprises, avec sa propre association mutuelle. Il ne porte pas de verdict et ne remplace jamais le contrôle réservé. Les références communes aux contrôles de deux poses sont recensées ; aucun résultat commun n’est traité comme plusieurs mesures indépendantes pour réduire une incertitude.

## Conclusion permise et limites

Le succès signifie une **compatibilité empirique des positions composées avec les références Gaia sélectionnées**, selon ces critères exploratoires. Les étoiles réservées n’ont pas participé au recalage actuel ; leur éventuelle participation à la construction de l’empilement ou à son solveur initial n’est pas connue. La référence, les images et le catalogue peuvent partager des erreurs ou des sources. Une comparaison à Gaia ne démontre donc pas à elle seule leur indépendance statistique.

L’erreur de la référence, les couleurs/Bayer, PSF, centroïdes, distorsions différentielles, covariances, parallaxe, perspective et corrélations ne sont pas réunies dans un budget absolu complet. Les biais entre poses ne sont pas une mesure de déplacement d’un objet. `absolute_error_budget_complete`, `reference_independence_established`, `clock_qualified` et `scientific_submission_certified` restent faux. Aucune vitesse ou soumission MPC n’est produite.

## Commande et produits

```powershell
.\.venv\Scripts\python.exe -m gar gaia-frames ".\local\lot\workset.json" --registration ".\local\recalage-01\registration.json" --catalog ".\local\references\catalog.csv" --output ".\local\gaia-poses-01"
```

La sortie doit être nouvelle. Produits : `gaia-frames.json` (résultats principaux et secondaires, critères, sélections, empreintes, provenance et versions), `matches.csv` (étiquettes `control` ou `all_diagnostic`, non additionnables), `gaia-frames.svg` et `report.md`. Les identifiants potentiellement interprétables comme formules de tableur sont protégés dans le CSV. Le JSON conserve leur texte d’origine.

Codes : `0` si toutes les poses satisfont les critères principaux ; `2` si le rapport produit contient un échec ; `1` si analyse impossible, incohérence d’entrée ou erreur d’écriture. Un répertoire partiel après erreur ne constitue pas un rapport complet ; résoudre le problème et choisir une nouvelle sortie. Les produits réels et la provenance du catalogue peuvent révéler le champ observé : **tout reste privé sous `local/`**.

Références primaires : [Astropy — mouvements propres](https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html), [associations et offsets](https://docs.astropy.org/en/stable/coordinates/matchsep.html), [WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). Les seuils et décisions d’aptitude sont propres au projet, sans équivalence avec une norme de certification instrumentale ou MPC. Le logiciel est testé avec Astropy 7.2.0 ; les pages `stable` peuvent décrire une version ultérieure.
