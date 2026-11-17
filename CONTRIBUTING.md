# Contribuer

Documentation en français ; noms de modules, champs et interfaces en anglais pour faciliter les contributions internationales. Une traduction est bienvenue.

Pour toute nouvelle page et toute section révisée, suivre le [guide de rédaction accessible](docs/REDACTION-ACCESSIBLE.md). Il donne les références, les règles pratiques et les preuves à conserver. Expliquer les mots techniques à leur première utilisation. Écrire une action par étape et annoncer le résultat attendu. Ajouter une description en texte pour chaque figure. Signaler les vérifications encore absentes : un guide de rédaction ne prouve pas une conformité complète ou un niveau de lecture.

## Goal / Produce / Submit / Wait / Repeat

1. **Goal** : ouvrir une issue avec le problème, l’usage, la phase et un résultat vérifiable. Pour un changement de méthode, décrire les hypothèses et références avant l’implémentation.
2. **Produce** : créer une branche courte depuis `main` ; produire un changement ciblé, sa documentation et les tests nécessaires. Utiliser des cas synthétiques reproductibles.
3. **Submit** : ouvrir une pull request reliée à l’issue ; préciser résultat, validation, effets sur les formats et provenance/licences des ajouts.
4. **Wait** : laisser le temps de la revue ; répondre aux questions et fournir les éléments manquants. Les changements touchant les mesures demandent une revue scientifique.
5. **Repeat** : corriger, relancer les contrôles utiles et soumettre à nouveau.

## Versionner une livraison

Pour les prochaines livraisons, appliquer [SemVer et la procédure du projet](VERSIONING.md). Décrire les effets sur les commandes et contrats publics, choisir la progression appropriée, tenir [CHANGELOG.md](CHANGELOG.md) à jour et vérifier l'équivalence de `VERSION` avec les versions Python du paquet et de l'installation. Aucun tag/release ne doit être remplacé après publication ; les numéros de lots ne sont pas des versions applicatives.

## Signaler un problème

Indiquer version ou commit, Windows/Python, opération, résultat attendu, erreur et cas minimal anonymisé. Retirer chemins privés, coordonnées, identifiants, adresses et en-têtes bruts. Ne pas joindre un FITS personnel sans décision explicite de publication et vérification des droits.

Les candidats astronomiques ne se valident pas dans une simple issue : joindre les diagnostics et appliquer le protocole scientifique.

## Droits et qualité

En proposant une contribution, confirmer disposer des droits nécessaires et accepter `GPL-3.0-or-later` pour les contenus originaux concernés. Chaque personne conserve ses droits ; aucune cession globale n’est demandée. Préserver les avis des tiers et documenter toute nouvelle dépendance avant son intégration.

Préférer des interfaces petites et des fichiers d’échange explicites. Ne pas ajouter de dépendance circulaire, de téléchargement implicite, de télémétrie ou de modification des entrées. Les tests d’inventaire utilisent `pytest` ; exécuter `python -m pytest -q` depuis la racine. Leur portée figure dans [VALIDATION-PILOTE.md](docs/VALIDATION-PILOTE.md).

Avant de coder un nouveau lot, détailler ses sous-étapes dans `ROADMAP.md` et faire un commit du plan. Documenter les opérations dans [TUTORIEL.md](docs/TUTORIEL.md), avec des images explicatives ou des résultats synthétiques réels. Mettre à jour les autres Markdown concernés. Les règles persistantes sont dans [AGENTS.md](AGENTS.md).

Les échanges doivent rester respectueux. Critiquer les méthodes et les résultats, sans attaques personnelles. Le mainteneur motive les décisions et consigne les désaccords techniques.
