# Préaudit des licences et procédure de distribution

État au 15 novembre 2026 : sources officielles consultées et première combinaison de développement spécifiée dans `requirements/dev-tested.txt`. Les dépendances transitives, roues natives et paquet portable n’ont pas encore fait l’objet d’un audit exhaustif de redistribution. Une licence principale n’épuise pas les obligations des composants embarqués. Les conclusions ci-dessous sont des orientations à confirmer sur les artefacts exacts.

| Élément | Preuve officielle | Compatibilité envisagée / action |
|---|---|---|
| Python | [Copyright Python](https://www.python.org/doc/copyright/) | Versions modernes déclarées compatibles GPL ; conserver licence PSF et notices historiques |
| Astropy | [Licence du dépôt officiel](https://raw.githubusercontent.com/astropy/astropy/main/LICENSE.rst) | BSD-3-Clause ; conserver avis, conditions et exonération |
| Photutils | [Licence officielle](https://docs.astropy.org/projects/photutils/en/latest/development/license.html) | BSD-3-Clause ; mêmes obligations, vérifier les dépendances |
| NumPy | [Licence officielle](https://numpy.org/doc/stable/license.html) | BSD-3-Clause ; vérifier en plus BLAS/LAPACK et autres composants des roues sélectionnées |
| Matplotlib | [Licence et composants embarqués](https://matplotlib.org/stable/project/license.html) | Licence Matplotlib dérivée de PSF ; conserver avis et licences annexes ; résumer les modifications si nécessaire |
| ExifTool, optionnel | [README officiel](https://raw.githubusercontent.com/exiftool/exiftool/master/README), [LICENSE](https://raw.githubusercontent.com/exiftool/exiftool/master/LICENSE) | README : choix selon les termes de Perl, Artistic ou GPL ; fichier LICENSE courant : GPL v3. Résoudre les termes de la distribution exacte avant intégration, y compris Perl et ses modules ; aucune version Artistic supposée |

L’usage de composants permissifs dans un ensemble sous GPL ne supprime pas leurs avis et ne change pas leur licence d’origine. ExifTool est exclu du socle initial : la lecture FITS relève d’Astropy.

## Audit à chaque version

1. Sélectionner la version Python et verrouiller les paquets compatibles Windows x64 avec leurs empreintes ; inclure les dépendances transitives et outils de construction distribués.
2. Produire une nomenclature : nom, version, origine, empreinte, licence déclarée, fichiers de licence constatés, rôle et destination de redistribution. Les noms issus des métadonnées PyPI ne sont qu’un point de départ.
3. Examiner le contenu réel des roues, runtime et éventuel outil de création de portable, y compris bibliothèques natives, polices et ressources. Répertorier les exceptions et licences multiples.
4. Vérifier chaque condition de redistribution et sa compatibilité avec la GPL v3 retenue. Une licence inconnue ou non compatible bloque la distribution concernée ; remplacer ou retirer l’élément.
5. Constituer `THIRD_PARTY_NOTICES` et un dossier de licences avec les textes requis. Ne pas produire aujourd’hui un avis donnant l’impression que des versions non choisies ont été auditées.
6. Fournir le code source correspondant de la version applicative et les éléments requis pour les composants redistribués selon leurs licences. Documenter construction, modifications et mode de fourniture des sources.
7. Revoir séparément les conditions des catalogues, éphémérides et index astrométriques : accès libre ne signifie pas redistribution autorisée. Préférer une acquisition explicite si leur réhébergement n’est pas autorisé.
8. Archiver le rapport d’audit et sa validation avec la version ; faire signaler automatiquement toute nouvelle dépendance ou changement de licence.

Une vérification automatique ne remplace pas la lecture des conditions. Un cas ambigu sera documenté et résolu avant distribution ; il ne sera pas déclaré compatible par défaut.

## Dépendances ajoutées au contrôle stellaire

Photutils 3.1.1 et SciPy 1.18.1 sont utilisés dans l’environnement de développement (Python ≥3.12). Photutils conserve sa licence BSD 3 clauses ; SciPy annonce une [licence BSD modifiée](https://scipy.org/about/). Cela ne remplace pas l’audit des composants natifs des roues. Aucun binaire de ces bibliothèques n’est redistribué par ce lot. Les données Gaia et leurs obligations de reconnaissance sont distinctes de la licence du code ; l’extrait réel et sa requête ne sont pas inclus dans Git.
