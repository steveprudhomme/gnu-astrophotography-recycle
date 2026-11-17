# Diagnostic WCS 1.0 — paramètres observés, pas de certification

`gar wcs` consomme un manifeste d’inventaire 1.0 local. Il ne rouvre pas les FITS et ne lit aucun pixel. Les sorties doivent rester dans un nouveau dossier local, hors des archives et du support externe. L’empreinte SHA-256 du manifeste, son run source, la version et le commit du programme sont conservés.

## Portée de la collecte

Le manifeste contient certains axes primaires, références et coefficients CD. Il ne conserve pas systématiquement `CUNIT`, les matrices PC et `CDELT`, le référentiel, les coefficients SIP, les tables de distorsion, ou les versions WCS alternatives. **Non collecté ne signifie pas absent du FITS.** Une déclaration CD cohérente ne suffit donc pas à reconstruire fidèlement une transformation céleste.

Le programme ne complète aucune matrice avec des valeurs par défaut. Une autre paramétrisation peut être valide, même si ce diagnostic ne la traite pas. L’absence de champs primaires observés invite à examiner l’en-tête complet avant de conclure qu’une résolution astrométrique est nécessaire. Les seules valeurs RA/DEC de pointage ne sont pas traitées comme une WCS.

## Contrôles

- Toutes les HDU sont comptabilisées ; primaires vides et tables sont identifiées sans être prises pour des images. Les fichiers non `ok` et copies de même `frame_id` ont des statuts distincts.
- Pour une image d’au moins deux dimensions, vérifier les deux axes primaires. Le sous-ensemble pris en charge utilise une paire RA/DEC, dans les deux ordres, avec noms de projection concordants. Les projections hors de l’ensemble du module sont signalées, pas déclarées universellement illégales.
- Vérifier présence et type numérique fini de `CRPIX1/2`, `CRVAL1/2` et des quatre coefficients `CD1_1`, `CD1_2`, `CD2_1`, `CD2_2`. Une déclaration incomplète reste incomplète, sans reconstruction supposée.
- Un pixel de référence extérieur à la plage des centres de pixels est informatif, pas intrinsèquement invalide. Le repère utilisé est celui de FITS, avec centres commençant à 1.
- Si l’unité de déclinaison est effectivement présente dans les métadonnées et reconnue (`deg`, `rad`, `arcmin`, `arcsec`), contrôler sa plage. Sans unité collectée, aucun contrôle angulaire supposant des degrés n’est effectué.
- Évaluer singularité et conditionnement du bloc CD dans ses unités numériques brutes. Le seuil `--max-condition`, par défaut `1e8`, est un contrôle numérique configurable, pas une précision astrométrique. Les limitations numériques extrêmes sont signalées sans les confondre avec une preuve de singularité mathématique exacte.
- Une déclaration SIP est signalée comme contexte de distorsion non collecté ; elle n’est pas supprimée pour fabriquer une solution simplifiée.

La catégorie `linear_block_consistent_context_incomplete` signifie uniquement que les contrôles numériques limités ont réussi. Elle n’affirme ni une échelle angulaire correcte, ni une orientation juste, ni un accord avec les étoiles. Les statuts et détails manquants figurent dans le JSON ; les catégories sont exclusives et leurs effectifs totalisent les HDU inventoriées.

## Sorties et conclusion

| Produit | Contenu |
|---|---|
| `wcs.json` | Référence : provenance, paramètres, chaque HDU, raisons, champs observés et prochaine action indicative |
| `wcs.csv` | Vue de consultation, textes protégés contre les formules de tableur |
| `wcs.svg` | Effectifs des catégories exclusives |
| `report.md` | Synthèse, illustration et limites |

`celestial_transform_reconstructed` et `wcs_validated` restent `false`. Précision et résidus de catalogue restent `null`. `scientific_position_export_allowed` reste `false`. Aucun appel à un solveur, catalogue ou service réseau n’est effectué et aucune WCS d’empilement n’est transférée aux poses.

Code `1` : erreur de manifeste, paramètres, destination ou écriture. Code **`2`** : diagnostic produit, sans qualification astrométrique. Cette version ne retourne pas un code `0` de certification. Un dossier partiellement écrit peut subsister si une erreur survient pendant la production des rapports ; relancer vers une nouvelle destination.

## Références et travail restant

Le [standard FITS 4.0, section 8](https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf) décrit les coordonnées WCS. La [documentation Astropy de validation](https://docs.astropy.org/en/stable/wcs/validation.html) et celle de [WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html) distinguent les contrôles et transformations disponibles. Le présent module ne reconstruit pas une WCS Astropy à partir de champs partiels : il évite que des valeurs implicites donnent une apparence de complétude à la collecte.

La prochaine étape scientifique nécessitera un contexte complet, des images locales de travail et une comparaison des positions d’étoiles à un catalogue indépendant, avec résidus et incertitudes. Cela demandera un plan distinct ; aucune collecte supplémentaire sur la clé USB n’est effectuée ici.
