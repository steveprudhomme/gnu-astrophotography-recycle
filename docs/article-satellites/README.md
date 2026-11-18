# Article scientifique — étude de science citoyenne

Le [PDF de l’article](article.pdf) présente les trois associations plausibles de satellites connus.
Il commence par un résumé français et un **Abstract anglais**, avec les mêmes résultats et limites.
Le manuscrit n’a pas été évalué par les pairs. L’auteur doit le relire avant toute soumission.
Les clubs mentionnés n’endossent pas l’étude par cette mention.

Les sources sont [article.tex](article.tex) et [references.bib](references.bib).
Les citations suivent le guide **UQAM-APA**, avec des adaptations françaises explicites de `biblatex-apa`.
Le mot « et » relie les auteurs ; *et al.* apparaît en italique.
Les références sont classées par auteur, avec initiales, dates et liens vérifiés.
Les pages évolutives indiquent une date de consultation. Une date absente reste « s. d. ».
Voir aussi les [références lisibles en Markdown](../SOURCES-SATELLITES.md).

Le texte couvre la question, les hypothèses concurrentes, les données, la méthode et les résultats.
Il décrit les limites, les contributions citoyennes, les droits et l’assistance par IA.
Le financement et les conflits d’intérêts restent à confirmer par l’auteur avant soumission.
Les photos sont réelles et autorisées. Les lignes, graphiques et schémas sont des calculs identifiés.
Les descriptions des figures sont aussi disponibles dans le [tutoriel depuis zéro](../REPRODUIRE-SATELLITES.md).

## Reconstruire le PDF

Cette partie est facultative pour refaire l’analyse des FITS.
Installe [TeX Live](https://www.tug.org/texlive/) avec XeLaTeX, Biber, `biblatex-apa`, Babel français et les polices TeX Gyre.
Depuis la racine du dépôt, exécute dans PowerShell :

```powershell
powershell -File .\scripts\build-satellite-article.ps1
```

Le script lance XeLaTeX, Biber, puis deux passages XeLaTeX.
Les fichiers intermédiaires restent dans `local/article-build`.
Le PDF final remplace seulement `docs/article-satellites/article.pdf`.
Si une commande est inconnue, vérifie que le dossier des outils TeX Live figure dans `PATH`.
Le script n’installe rien et ne télécharge aucune donnée astronomique.

Avant de publier une nouvelle version, ouvre chaque page du PDF.
Vérifie les accents, les tableaux, les légendes, les liens et toutes les références.
Conserve le journal des modifications ; ne transforme pas une hypothèse en identité confirmée sans preuve.
