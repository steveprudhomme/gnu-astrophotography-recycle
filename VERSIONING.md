# Versionnage du projet

Depuis le 17 novembre 2026, le projet applique [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html). La version publique canonique est dans [VERSION](VERSION) : **0.10.0-alpha.1**, version de développement actuelle. Cette adoption ne crée pas une release, ne renomme aucun ancien tag et ne change pas les résultats scientifiques.

## Ce que la version décrit

La surface publique comprend les commandes `gar` documentées, leurs options et codes de retour, ainsi que la sémantique des formats promis par les contrats `docs/CONTRAT-*.md`. Les fonctions internes et recettes expérimentales dans `examples/` ne constituent pas une API Python stable. Les versions des schémas de données restent distinctes de la version applicative.

| Changement publié | Version à faire évoluer |
|---|---|
| Correction compatible | PATCH |
| Fonctionnalité compatible | MINOR, PATCH remis à zéro |
| Rupture de la surface publique à partir de 1.0.0 | MAJOR, MINOR et PATCH remis à zéro |

Avant 1.0.0, l'API est en développement. Par politique du projet, une rupture incrémente MINOR et remet PATCH à zéro, avec migration documentée. Une préversion utilise `-alpha.N`, `-beta.N` ou `-rc.N`. Une nouvelle préversion d'une même cible augmente N. Un numéro de lot n'est pas un numéro de release ; les commits identifient précisément les états de travail non publiés.

## Correspondance avec Python

Le projet garde deux écritures équivalentes, car les outils Python suivent [PEP 440](https://packaging.python.org/en/latest/specifications/version-specifiers/) :

| Version publique et tag futur | Paquet Python |
|---|---|
| `0.10.0-alpha.1` / `v0.10.0-alpha.1` | `0.10.0a1` |
| `1.2.3-beta.2` / `v1.2.3-beta.2` | `1.2.3b2` |
| `1.2.3-rc.1` / `v1.2.3-rc.1` | `1.2.3rc1` |
| `1.2.3` / `v1.2.3` | `1.2.3` |

Les trois dernières lignes sont des exemples, pas des versions annoncées. `pyproject.toml`, `gar.__version__` et les métadonnées installées utilisent l'écriture Python. Les anciens rapports la conservent ; ils ne sont pas réécrits. Aucun changement de source du moteur n'est nécessaire pour adopter le nom public actuel.

## Préparer une livraison

1. Choisir le numéro à partir du changement de surface publique et compléter [CHANGELOG.md](CHANGELOG.md), d'abord sous « Non publié ».
2. Mettre en cohérence `VERSION`, `pyproject.toml` et `src/gar/__init__.py` ; réinstaller le paquet modifiable si nécessaire et vérifier leur équivalence avec `packaging.version.Version` et les métadonnées installées. Actualiser les documents concernés.
3. Effectuer les tests adaptés, l'audit des fichiers publics et la revue des formats, licences et migrations ; noter le commit réellement vérifié et les limites scientifiques.
4. Lorsqu'une livraison est explicitement demandée et prête, créer le tag `v` suivi de la version SemVer sur le commit vérifié et publier les notes correspondantes. Un tag ou une release publiée reste immuable : toute correction prend une nouvelle version. Ni envoi forcé ni remplacement des anciens artefacts.

La configuration actuelle ne crée pas de tag ou release automatiquement. Les expériences à seuils gelés conservent leur version de code et leurs empreintes ; un changement de méthode doit avoir son propre protocole et sa propre vérification.
