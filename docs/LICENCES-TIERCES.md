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

Le recalage 0.7 réutilise ces bibliothèques sans nouvelle dépendance scientifique. Le rendu PNG facultatif utilise Matplotlib déjà mentionné ci-dessus ; les SVG applicatifs n’en dépendent pas. Les générateurs, tests et scripts de tracé propres au projet portent l’avis GPL-3.0-or-later et le titulaire. Aucun paquet binaire ni catalogue réel n’est livré dans ce lot.

Le contrôle Gaia des poses 0.8 ne change pas ce socle. Les colonnes de forme Gaia du générateur sont entièrement fictives ; aucun extrait réel ni binaire tiers n’est redistribué. Le préaudit reste distinct d’un audit complet des roues natives ou d’une distribution portable.

La préparation temporelle 0.9 conserve le socle existant ; aucun nouveau paquet scientifique ou binaire n’est redistribué. Les textes FITS et GUM sont référencés par lien, sans copie de leurs PDF dans le dépôt. Les figures et exemples du projet sont originaux, conceptuels ou synthétiques ; le rendu PNG facultatif réutilise Matplotlib.

Le prototype 0.10 conserve le moteur scientifique existant et spécifie séparément les outils de figures : Matplotlib 3.10.8 et Pillow 13.0.0 dans `requirements/figures-tested.txt`. Pillow annonce une [licence MIT-CMU](https://pillow.readthedocs.io/en/stable/about.html#license) ; conserver les avis lors d’une éventuelle redistribution. Les bibliothèques natives et dépendances transitives ne sont pas exhaustivement auditées ici. Aucun binaire de ces paquets n’entre dans Git ; les images et le GIF publics sont des productions originales à partir de données fictives.

Le banc de limites du lot 12 ne change ni moteur ni dépendances. Les nouvelles recettes et leurs tests portent le même avis GPL-3.0-or-later et le titulaire ; les figures sont originales, produites depuis des données synthétiques locales. Aucune roue, archive réelle ou bibliothèque native n’est ajoutée au dépôt. L’audit complet de redistribution reste distinct de cet essai.
