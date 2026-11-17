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

## Préparer les preuves temporelles

Références primaires consultées le 16 novembre 2026 : [FITS 4.0, section 9 et table 35](https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf), [Rots et al., représentations temporelles FITS](https://arxiv.org/abs/1409.7583), [Astropy, ouverture des FITS](https://docs.astropy.org/en/stable/io/fits/api/files.html) et [JCGM 100:2008, GUM](https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf), sections 5–6 pour les incertitudes et corrélations. Le [contrat des preuves](CONTRAT-PREUVES-TEMPS.md) décrit des diagnostics volontairement limités ; le [protocole](PROTOCOLE-QUALIFICATION-TEMPS.md) distingue prescriptions normatives, préparation d’un futur essai et choix du projet. La liste de huit exigences et les 30 répétitions proposées ne sont pas des standards instrumentaux du S50. Aucune nouvelle preuve de synchronisation applicable à son firmware ou aux anciennes archives n’est revendiquée. Les figures publiques proviennent du générateur synthétique ou d’un schéma conceptuel explicitement identifié.

La [fiche opérationnelle de campagne](CAMPAGNE-TEMPORELLE.md), ses cinq canevas et ses blocs proposés sont un complément documentaire du projet à ce protocole. Ils ne constituent ni nouvelle source instrumentale ni résultat de mesure. Leur schéma est conceptuel et leurs valeurs inconnues restent non renseignées ; la référence matérielle et les versions ne sont pas déduites des archives.

## Prototype synthétique et pédagogie

Sources primaires consultées le 17 novembre 2026 : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [SciPy linear_sum_assignment](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html), [Python sur Windows](https://docs.python.org/3.13/using/windows.html) et [installation officielle de Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git). Le filtre stationnaire, les associations et seuils du [contrat de mobiles](CONTRAT-MOBILES-SYNTHETIQUES.md) sont des choix expérimentaux propres au projet. Les figures/animation proviennent du générateur public et du rapport gelé, pas d’archives réelles. Le [parcours débutant](DEMARRER-DE-ZERO.md) distingue apprentissage, reconstruction depuis le code, essais logiciels et validation instrumentale ; ses schémas ne sont pas des captures d’écran.

## Banc de limites du moteur gelé

Pour le [lot 12](LIMITES-DETECTEUR.md), documentation primaire consultée le 17 novembre 2026 : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html) et [NumPy Generator](https://numpy.org/doc/stable/reference/random/generator.html). La page NumPy `stable` décrit désormais 2.5 ; le banc reste exécuté avec 2.4.1, sans changement de dépendances. Les graines nouvelles, les comparaisons appariées, les conditions et les comptages sont des choix et résultats du projet. Ce modèle gaussien simplifié ne constitue ni modèle calibré du capteur Seestar ni étalonnage de sensibilité réelle. Les graphiques et le GIF sont calculés depuis les pixels fictifs et les rapports gelés.

## Relier recalage et recherche fictive

Sources primaires revues le 17 novembre 2026 : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html) et [SciPy cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html). La [recette du lot 13](RECALAGE-MOBILES-SYNTHETIQUES.md) réutilise les algorithmes et versions testées du projet, sans nouveaux paramètres des moteurs ou dépendances. La séparation de contrôles par pose, les critères de couverture, la porte bloquant les séquences et les conditions synthétiques sont des choix du projet. Le résultat négatif global et les comparaisons conditionnelles sont conservés ; les sources des bibliothèques n’en font pas une validation du S50.

## Partition spatiale et préparation des images Seestar

API [SciPy cKDTree](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.cKDTree.html) revue le 17 novembre 2026 ; algorithmes et versions antérieurs réutilisés. La [partition du lot 14](CONTROLES-SPATIAUX.md), le parcours des quadrants/cellules, les profils et critères sont des choix propres au projet, sans nouvelle prescription instrumentale. Le [passage au réel](PASSAGE-AUX-IMAGES-SEESTAR.md) s’appuie sur les contrats et le pilote déjà documentés, plus le seul manifeste local existant ; aucun FITS réel, fournisseur ou support USB n’est consulté. Les délais restent conditionnels à la disponibilité des copies et au traitement adapté, pas aux seuls résultats fictifs.

## Préparation d’une série Seestar et exemples CC0

Le [lot 15](PREPARER-SERIE-SEESTAR.md) réutilise les contrats séances/workset et [Astropy FITS](https://docs.astropy.org/en/stable/io/fits/api/files.html). Les paramètres de sélection (huit poses, groupe le plus fourni et premier bloc, écarts déclarés ≤30 s) sont des choix du projet, pas un standard de validation instrumentale. Les données réelles restent locales et les deux PNG autorisés ont une provenance décrite dans leur [notice](images/reels/LICENCE.md), sans publication des en-têtes ou chemins.

Sources primaires Creative Commons consultées le 17 novembre 2026 : [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/) et [outils du domaine public](https://creativecommons.org/public-domain/). Elles expliquent la dédicace CC0 employée à la demande explicite du mainteneur. Les tests et l’exercice reproductible utilisent des pixels fictifs ; l’exemple réel diffusé n’est pas une mesure scientifique validée.

## Premier pilote de mobiles sur copies réelles

Le [lot 16](PILOTE-MOBILES-SEESTAR.md) réutilise les moteurs et versions installés. Sources primaires consultées le 17 novembre 2026 : [Astropy FITS](https://docs.astropy.org/en/stable/io/fits/api/files.html), [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [SciPy map_coordinates](https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.map_coordinates.html). La dernière API fait une interpolation aux coordonnées d'entrée : dans ce projet, elle est réservée à l'affichage, jamais à la mesure des positions. Les pages `stable` peuvent décrire des versions plus récentes ; les dépendances locales n'ont pas été mises à jour. Moyenne Bayer 2×2, critères de contrôle, seuils, champ commun et temps déclarés relèvent du protocole du projet. Le premier résultat réel sans candidat n'établit pas les performances instrumentales.

## Injections conditionnelles sur plans d'intensité

Le [lot 18](INJECTIONS-SEESTAR.md) emploie [NumPy load](https://numpy.org/doc/stable/reference/generated/numpy.load.html) et [NumPy save](https://numpy.org/doc/stable/reference/generated/numpy.save.html), documentation primaire consultée le 17 novembre 2026. Les appels fixent `allow_pickle=False` pour les tableaux float32 locaux. La page `stable` décrit NumPy 2.5 ; l'environnement conserve 2.4.1, sans mise à jour. Les pics relatifs au bruit, largeur gaussienne, trajets, critères d'appariement et séparation génération/analyse/score sont des choix préenregistrés du projet, pas une calibration ou une prescription du fabricant. Les compteurs sur trois trajets ne fournissent pas une probabilité universelle de détection.

## Diagnostic des positions après score

Le [lot 19](DIAGNOSTIC-MANQUES.md) s'appuie sur les tableaux, scores et recettes gelés du projet : [moteur de mobiles](../src/gar/moving.py), [recette d'injection](../examples/injection_recovery.py) et [diagnostic](../examples/diagnose_injection_misses.py). Rayons de proximité 1,5/3 pixels, comparaison des supports, catégories et règle des exemples sont des choix du protocole prépublié ; ce ne sont pas de nouveaux réglages du détecteur ou une prescription instrumentale. Le diagnostic ne rejoue pas les critères internes du détecteur et ne démontre pas la cause physique d'une absence de point enregistré. Les bibliothèques et versions restent inchangées.

## Trace interne du détecteur gelé

Le [lot 20](TRACE-DETECTEUR.md) a consulté le 17 novembre 2026 la [source officielle de DAOStarFinder 3.1.1](https://photutils.readthedocs.io/en/3.1.1/_modules/photutils/detection/daofinder.html), ainsi que les fichiers de cette même version installée. La détection des maxima précède les critères de finitude, de position et de forme ; le projet applique ensuite sa marge habituelle. Le seuil porte sur une image convoluée, avec un facteur interne lié au noyau. Une absence de maximum proposé ne suffit donc pas à attribuer une cause physique ou un unique filtre. Les empreintes de bibliothèque et les sorties comparées au moteur identifient précisément le rejeu ; les rayons de proximité et le banc fictif sont des choix du protocole du projet.

## Création des maxima et absences

Le [lot 21](ABSENCES-MAXIMA.md) s'appuie sur les sources **installées de Photutils 3.1.1**, consultées le 17 novembre 2026 : `detection/peakfinder.py`, `detection/core.py`, `detection/daofinder.py` et `utils/_convolution.py`. La copie installée et ses empreintes, avec les listes gelées du projet, sont les références du rejeu ; les liens de documentation de versions spécifiques n'ont pas pu être récupérés pendant ce lot. La comparaison au maximum circulaire, le masque, le bord, le seuil strict et le départage des plateaux relèvent de l'implémentation de cette bibliothèque. Le bilan par cercle, les obstacles simultanés, les deux rayons et le banc fictif sont des choix du protocole du projet. Aucun résultat de proximité ou de réponse convoluée n'est une mesure photométrique ou une preuve de cause physique unique.

## Identification future de candidats

À la demande du mainteneur, références primaires consultées le 17 novembre 2026 : [SkyBoT, recherche dans un champ daté](https://ssp.imcce.fr/webservices/skybot/api/conesearch/) et [manuel JPL Horizons](https://ssd.jpl.nasa.gov/horizons/manual.html). SkyBoT recherche les objets du Système solaire connus dans un champ à une époque ; Horizons fournit des positions et mouvements prédits selon le temps et l'observateur. Leur usage pour confronter plusieurs positions d'un candidat et ses incertitudes est une proposition de méthode du projet, pas une fonctionnalité livrée ou une garantie d'identification. Aucun champ observé, site ou FITS n'a été envoyé pour cette consultation documentaire. La qualification des heures et du budget astrométrique reste nécessaire à une identification fiable ; aucune correspondance trouvée ne suffirait à établir une découverte.
