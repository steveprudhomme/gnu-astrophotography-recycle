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
| Algorithmes, seuils et performances | Propositions d’architecture ; pas de résultats expérimentaux |
| Aptitude AAVSO/MPC/ALCDEF | Objectif ultérieur conditionné par la validation, pas une certification |

Les règles de préservation, contrats de modules, budgets d’erreurs et contrôles par injections sont des décisions d’ingénierie proposées. Elles devront être confrontées aux images et revues par des contributeurs scientifiques. Le cadrage privilégie Python/Windows/S50 conformément à la demande et ne prétend pas comparer toutes les solutions existantes.

## Références du premier inventaire

- [Astropy — ouverture des FITS et options de lecture](https://docs.astropy.org/en/stable/io/fits/api/files.html) et [unités HDU](https://docs.astropy.org/en/stable/io/fits/api/hdus.html) : lecture seule, parcours des unités et informations de stockage. Les comportements effectivement utilisés sont couverts par les tests de la version 7.2.0 installée.
- [pytest — configuration](https://docs.pytest.org/en/stable/reference/customize.html) : configuration du répertoire de tests et du chemin des sources.
- [NumPy 2.4.1 sur PyPI](https://pypi.org/project/numpy/2.4.1/) : version de remplacement retenue après l’avertissement de retrait de NumPy 2.4.0 lors de l’installation. Les versions directes de développement sont consignées dans `requirements/dev-tested.txt` ; cela ne vaut pas verrouillage complet ni audit de redistribution.
- [Contrat d’inventaire 1.0](CONTRAT-INVENTAIRE.md) et [tutoriel illustré](TUTORIEL.md) : comportement réel, provenance, exemples synthétiques et limites.
