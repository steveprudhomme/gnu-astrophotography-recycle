# Sources et statut des affirmations

Sources officielles consultées le **15 novembre 2026**. Les liens `stable`, `latest` et `main` peuvent évoluer ; les versions exactes et empreintes seront archivées avant développement validé et distribution.

## Licence et identité

- [GPL v3, texte brut officiel](https://www.gnu.org/licenses/gpl-3.0.txt) : source du fichier `COPYING`, sans réécriture.
- [Guide GNU d’application des licences](https://www.gnu.org/licenses/gpl-howto.html) : avis de licence et en-têtes ; choix « version 3 ou ultérieure » explicite dans le projet.
- [Évaluation des logiciels pour le projet GNU](https://www.gnu.org/help/evaluation.html) : l’intégration comme paquet GNU est une démarche distincte de l’usage de la GPL. Aucune affiliation officielle n’est revendiquée.
- [Registre des licences tierces](LICENCES-TIERCES.md) : liens vers les licences des projets amont.

## FITS et instrument

- [NASA — page du standard FITS](https://fits.gsfc.nasa.gov/fits_standard.html) : référence de format, WCS et représentation des temps ; utiliser la version applicable identifiée.
- [Astropy — vérification FITS](https://docs.astropy.org/en/stable/io/fits/usage/verification.html) : contrôles des fichiers ; le projet impose de conserver les originaux même si une bibliothèque sait corriger certains écarts.
- [Astropy — temps et dates](https://docs.astropy.org/en/stable/time/index.html) : outils pour les échelles et conversions ; la précision d’une conversion ne démontre pas celle de l’horloge instrumentale.
- [ZWO — paramètres officiels S50](https://i.zwoastro.com/wp-content/uploads/2025/06/4a9ec16c2b004b518b414facc5eab5e5.pdf) : capteur IMX462, monture altazimutale et prise en charge du mode équatorial. Ce document ne prouve pas les mots-clés ni le traitement effectif de vos FITS.

## Réception des mesures

- [AAVSO — WebObs 2.0](https://archive.aavso.org/index.php/blog/webobs2) : application de soumission, à distinguer du format des fichiers.
- [AAVSO — Extended File Format](https://archive.aavso.org/index.php/aavso-extended-file-format) : format pour observations numériques. La page consultée indique une version 1.2 ; ne pas nommer ce format « WebObs 2.0 ».
- [MPC — ADES](https://docs.minorplanetcenter.net/mpc-ops-docs/observations/ades-format/) : représentations XML/PSV et contraintes spécifiques des soumissions ; validation de structure et recevabilité sont distinctes.
- [MPC — signalement des observations](https://docs.minorplanetcenter.net/mpc-ops-docs/astrometry/reporting-observations/) : milieu de pose selon la mesure, qualité astrométrique, observations multiples et prérequis d’observatoire.
- [ALCDEF — spécification officielle](https://alcdef.org/docs/ALCDEF_Standard.pdf) : séries temporelles photométriques d’astéroïdes.

## Ce qui est établi et ce qui reste à vérifier

| Sujet | Statut |
|---|---|
| Nom du projet | Confirmé par l’utilisateur : GNU Astrophotography Recycle |
| Windows 11, local, GPL et phases | Exigences des prompts ; pas des capacités déjà livrées |
| Texte de la licence | Téléchargé officiellement ; octets conservés dans COPYING |
| Bibliothèques | Licences principales consultées ; versions et dépendances transitives non auditées |
| Métadonnées S50, Bayer, calibrations, heure et WCS | Présence de mots-clés examinée localement ; traitement effectif, exactitude horaire et validité WCS restent à qualifier |
| Algorithmes, seuils et performances | Contrôles stellaires et recalage exploratoires disponibles, essais synthétiques/publics et pilote privé ; budgets absolus et photométrie à développer |
| Aptitude AAVSO/MPC/ALCDEF | Objectif ultérieur conditionné par la validation, pas une certification |

Les règles de préservation, contrats de modules, budgets d’erreurs et contrôles par injections sont des décisions d’ingénierie proposées. Elles devront être confrontées aux images et revues par des contributeurs scientifiques. Le cadrage privilégie Python/Windows/S50 conformément à la demande et ne prétend pas comparer toutes les solutions existantes.

## Références du premier inventaire

- [Astropy — ouverture des FITS et options de lecture](https://docs.astropy.org/en/stable/io/fits/api/files.html) et [unités HDU](https://docs.astropy.org/en/stable/io/fits/api/hdus.html) : lecture seule, parcours des unités et informations de stockage. Les comportements effectivement utilisés sont couverts par les tests de la version 7.2.0 installée.
- [pytest — configuration](https://docs.pytest.org/en/stable/reference/customize.html) : configuration du répertoire de tests et du chemin des sources.
- [NumPy 2.4.1 sur PyPI](https://pypi.org/project/numpy/2.4.1/) : version de remplacement retenue après l’avertissement de retrait de NumPy 2.4.0 lors de l’installation. Les versions directes de développement sont consignées dans `requirements/dev-tested.txt` ; cela ne vaut pas verrouillage complet ni audit de redistribution.
- [Contrat d’inventaire 1.0](CONTRAT-INVENTAIRE.md) et [tutoriel illustré](TUTORIEL.md) : comportement réel, provenance, exemples synthétiques et limites.

## Regroupement indicatif

Le [contrat des séances 1.0](CONTRAT-SEANCES.md) définit les choix d’ingénierie : métadonnées exactes, dossiers et dates séparés, seuil configurable, exclusion des copies et absence de conversion horaire. Ce regroupement n’est pas un standard de soumission astronomique. Sa référence est le comportement couvert par les cas synthétiques, pas une promesse de reconstruire les nuits réelles de l’instrument. L’exemple illustré du tutoriel provient du générateur public `examples/make_sessions_demo.py` et des rapports effectivement produits.

## Diagnostic temporel

Le [contrat des horodatages](CONTRAT-HORODATAGES.md) référence le standard FITS 4.0 et les pages officielles Seestar/ZWO consultées le 15 novembre 2026. Les valeurs par défaut du standard sont distinguées des déclarations et des preuves instrumentales. Aucune précision applicable au firmware de l’utilisateur n’a été établie dans les sources examinées ; les cas d’autres caméras ne sont pas transposés au S50. Les graphiques publics proviennent du générateur fictif `examples/make_timing_demo.py` et de rapports réellement produits, pas d’observations personnelles.

## Note communautaire sur les FITS Seestar

La [note de propositions](PROPOSITIONS-SEESTAR-S50.md) ajoute des références primaires : [interopérabilité FITS et Bayer dans Siril](https://siril.readthedocs.io/en/stable/file-formats/FITS.html), [guide DSLR de l’AAVSO](https://www.aavso.org/sites/default/files/publications_files/dslr_manual/AAVSO_DSLR_Observing_Manual_V1-4.pdf) et [conventions FITS de contrôle d’intégrité](https://science.data.nasa.gov/fits/documentation/conventions). Ces références expliquent les usages ; elles ne prouvent pas un défaut général du S50. Les priorités et critères de vérification sont des propositions du projet, fondées sur son objectif de réutilisation scientifique.

La [version anglaise](SEESTAR-S50-FITS-RECOMMENDATIONS.en.md) conserve les mêmes références et limites ; elle ne constitue pas une enquête supplémentaire sur les appareils ou firmwares.

## Diagnostic WCS sur manifeste partiel

Le [contrat WCS](CONTRAT-WCS.md) s’appuie sur le standard FITS 4.0 et la documentation officielle [Astropy WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html) et [validation](https://docs.astropy.org/en/stable/wcs/validation.html). Le module n’appelle pas une reconstruction WCS en complétant les champs manquants : il inspecte un sous-ensemble déclaré, avec NumPy pour le bloc CD. Les catégories, seuils numériques et prochaines actions sont des choix de diagnostic du projet, sans équivalence avec des résidus astrométriques mesurés.

## Copies locales et en-têtes complets

Le [contrat workset](CONTRAT-WORKSET.md) utilise les API officielles [Header](https://docs.astropy.org/en/stable/io/fits/api/headers.html) et [WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). Le nouveau produit complet est distinct du manifeste partiel : une construction WCS peut maintenant être tentée sur les copies avec leur contexte HDU. Cela reste une construction de modèle, pas une comparaison à un catalogue. Les graphiques publics proviennent uniquement du générateur fictif.

## Comparaison stellaire exploratoire

Références primaires : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [propagation des mouvements propres avec Astropy](https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html), [solution astrométrique Gaia](https://arxiv.org/abs/2012.03380) et archive ESA Gaia pour l’extrait DR3. Le [contrat astrométrique](CONTRAT-ASTROMETRIE.md) distingue les algorithmes publiés des seuils exploratoires choisis par ce projet. L’acquisition a été explicitement autorisée et la requête de champ reste locale, avec son empreinte.

## Recalage relatif sur copies

API consultées le 16 novembre 2026 : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [SciPy cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html) et [Astropy WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). Les triangles, l’ajustement rigide et les seuils du [contrat de recalage](CONTRAT-RECALAGE.md) sont des choix du projet, pas des prescriptions instrumentales de ces bibliothèques. La sérialisation de la distorsion SIP et la séparation des étoiles de contrôle sont testées. Les graphiques publics sont calculés depuis les injections de `examples/make_registration_demo.py` ; les figures du pilote réel ne sont pas publiées. Aucun nouveau catalogue ou paquet scientifique n’est acquis pour ce lot.

## Contrôle Gaia des poses

Documentation primaire consultée le 16 novembre 2026 : [Astropy — mouvements propres](https://docs.astropy.org/en/stable/coordinates/apply_space_motion.html), [associations, séparations et offsets](https://docs.astropy.org/en/stable/coordinates/matchsep.html), [WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). Les pages `stable` décrivent désormais une version ultérieure ; le projet reste testé avec Astropy 7.2.0. Le [contrat Gaia des poses](CONTRAT-GAIA-POSES.md) fixe les seuils exploratoires propres au projet et les limites d’indépendance, de sélection et d’incertitude. Les positions et figures publiques proviennent du générateur fictif `examples/make_gaia_frames_demo.py` avec biais connu, sans acquisition supplémentaire d’observations Gaia. Les références du pilote sont celles déjà mises en cache localement.
