# Préaudit des licences et procédure de distribution

## Recette des satellites — 18 novembre 2026

La recette facultative ajoute SGP4 2.27 et PyProj 3.8.0, déclarés MIT dans les distributions installées.
Voir [SGP4 2.27 et son exemple de référence](https://pypi.org/project/sgp4/2.27/) et [la licence PyProj 3.8.0](https://raw.githubusercontent.com/pyproj4/pyproj/3.8.0/LICENSE).
Pillow 13.0.0 déclare MIT-CMU ; voir [sa notice officielle](https://pillow.readthedocs.io/en/stable/about.html#license).
Ces bibliothèques sont installées séparément. Le dépôt ne redistribue pas leurs roues ou exécutables.
Les exigences d’une future distribution portable restent distinctes.

Le manuscrit utilise TeX Live, BibLaTeX et des polices TeX Gyre/Latin Modern installées.
Leurs licences restent propres à leurs composants ; le texte et ses illustrations ne les relicencient pas.
La GUST Font License est fournie dans la documentation des polices TeX Live.
Les programmes TeX et les fichiers de police complets ne sont pas joints au dépôt.
Les grilles géodésiques et le catalogue orbital sont récupérés auprès de leurs fournisseurs, avec leurs propres droits.
Les [seize FITS du mainteneur](../examples/data/seestar-series34/README.md) et les [figures autorisées](images/satellites/LICENCE.md) ont une notice CC0 séparée.

## Préaudit historique du socle

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

La recette recalage/mobiles du lot 13 réutilise les mêmes paquets et reste dans ce périmètre. Les sources Python nouvelles portent GPL-3.0-or-later et le titulaire ; figures et GIF sont produits depuis les pixels et mesures synthétiques du projet, sans média externe. Aucun binaire tiers n’est redistribué et l’audit exhaustif des roues natives reste à faire.

Le lot 14 de partition spatiale ne change pas les dépendances. Ses nouvelles sources et tests sont GPL-3.0-or-later avec titulaire ; schéma conceptuel, images et GIF sont des productions originales calculées localement. Aucun média d’observation, paquet binaire ou catalogue n’est publié. Le résultat expérimental ne remplace pas l’audit de redistribution du futur portable.

## Images réelles du projet autorisées sous CC0

Le mainteneur a expressément autorisé le 17 novembre 2026 la publication des deux PNG listés dans [images/reels/LICENCE.md](images/reels/LICENCE.md) sous **CC0 1.0 Universal**. Leur notice précise auteur de la mise à disposition, provenance et rendu, périmètre exact et empreintes des PNG, avec liens vers le [résumé CC0](https://creativecommons.org/publicdomain/zero/1.0/) et le [texte juridique](https://creativecommons.org/publicdomain/zero/1.0/legalcode). Les sources officielles distinguent CC0, dédicace par le titulaire, du Public Domain Mark, qui signale une œuvre déjà libre de droits connus.

Cette exception d’images du projet ne relicencie pas le code ou les autres documents GPL-3.0-or-later et ne diffuse pas les FITS, en-têtes ou rapports. Matplotlib/Pillow produisent le rendu et suppriment les métadonnées PNG ; aucune nouvelle dépendance ou distribution binaire n’est ajoutée. Les tests du lot 15 restent synthétiques, y compris la simulation de la branche de diffusion réelle.

Le pilote du lot 16 conserve les dépendances installées. `scipy.ndimage.map_coordinates` sert uniquement à l'interpolation de l'affichage, Matplotlib/Pillow aux figures et GIF. Ses trois médias fictifs restent sous le régime GPL du projet. Au lot 17, l'autorisation réaffirmée du mainteneur ajoute le GIF réel et deux illustrations à la liste exacte des cinq médias [CC0](images/reels/LICENCE.md). Les rapports et FITS restent privés. Les sources Python nouvelles portent titulaire et avis GPL-3.0-or-later ; aucune dépendance n'est ajoutée.

Le lot 18 d'injection/récupération réutilise NumPy, les fonctions gelées et les outils de dessin existants ; aucune dépendance ou distribution binaire nouvelle. Code et trois nouvelles figures publiques entièrement fictives sont des contenus originaux du projet sous GPL-3.0-or-later. Les dérivés et animations mixtes sur fond réel restent locaux, sans extension de la liste des cinq médias CC0. L'usage de `.npy` sans pickle n'ajoute aucun catalogue ou média tiers.

Le lot 19 réutilise ces dépendances pour le diagnostic des positions gelées et leur dessin. Deux recettes Python, tests et trois nouveaux PNG publics fictifs sont des contenus originaux sous GPL-3.0-or-later, avec titulaire dans chaque source. Aucune nouvelle dépendance, image tierce ou extension de la notice CC0 ; les vignettes mixtes réelles restent locales.

Le lot 20 appelle la bibliothèque Photutils 3.1.1 installée pour tracer ses propositions et filtres. Les empreintes servent à identifier l'implémentation utilisée, sans redistribuer le paquet ou copier sa source dans le dépôt. Photutils conserve sa licence BSD à trois clauses ; les nouvelles recettes, tests, textes et figures fictives originaux du projet portent GPL-3.0-or-later. La trace ne vaut pas audit complet de redistribution des dépendances et ne change pas la liste des cinq médias CC0.

Le lot 21 réutilise cette même bibliothèque et ses fonctions internes de convolution, maxima circulaires et égalités avec sources identifiées par empreintes. Aucune copie de paquet ou nouvelle dépendance binaire n'est distribuée. Les nouvelles recettes, tests et illustrations fictives sont des contenus originaux du projet sous GPL-3.0-or-later, avec titulaire dans chaque source Python. Les cinq médias CC0 ne changent pas et le bilan reste distinct d'un audit complet de redistribution.

Le lot 22 réutilise les dépendances installées pour une recette de mouvements représentatifs et les figures issues du nouveau banc fictif. Sources, tests et figures originaux nouveaux sont sous GPL-3.0-or-later avec titulaire dans chaque fichier Python. Les pages du fabricant et de l'IMCCE sont citées par lien ; aucun catalogue, image tierce, roue ou texte intégral n'est redistribué. Aucun nouveau média réel ne rejoint la notice CC0.
