# Gouvernance

## Responsabilités proposées

| Rôle | Responsabilité | Attribution initiale |
|---|---|---|
| Fondateur / mainteneur | Cap, versions, revue et décisions motivées | Steve Prud'Homme — [steveprudhomme](https://github.com/steveprudhomme) |
| Référent scientifique | Méthodes, incertitudes, validation | À pourvoir |
| Contributeurs | Changements et preuves de validation | Communauté |

Le mainteneur peut assurer plusieurs rôles au démarrage. Cette concentration de responsabilité est explicite ; les validations indépendantes seront recherchées avant d’annoncer une aptitude scientifique.

Les décisions d’architecture sont proposées dans une issue, discutées puis consignées dans la documentation avec statut et justification. Une décision de rejet doit être motivée. Les modifications de méthode ou de format nécessitent une proposition de fusion dédiée ; les mesures publiées doivent rester reproductibles avec leur version d’origine.

`main` représente l’état relu, pas une garantie scientifique. Avant une version applicative : contrôles réussis, changements documentés, licences auditées et limites annoncées. Les versions suivent une numérotation `0.x.y` pendant l’Alpha ; aucune date de livraison n’est promise.

## GitHub : plan de création

1. Choisir le compte ou l’organisation propriétaire et l’identité publique du mainteneur.
2. Créer le dépôt **public** `gnu-astrophotography-recycle` dès la première publication. Ne pas générer un autre README ni une autre licence sur GitHub.
3. Examiner l’intégralité des fichiers et de l’historique avant le premier envoi ; `.gitignore` ne protège pas un fichier déjà suivi.
4. Publier la base documentaire ; description proposée : « Recyclage scientifique local des archives FITS Seestar S50 — GPL-3.0-or-later — Alpha ».
5. Activer Issues ; ajouter les étiquettes `documentation`, `science`, `bug`, `phase-1`, `phase-2`, `good first issue` et `needs-data`.
6. Créer les jalons Phase 1 et Phase 2 ; reprendre les tâches de la feuille de route. Aucun FITS réel ni paramètre privé dans les tickets.
7. Configurer selon les possibilités du compte les règles de `main` : revue avant fusion, interdiction des envois forcés et contrôles requis une fois ceux-ci créés. Ne pas exiger de contrôle encore inexistant.
8. Ajouter l’intégration continue au premier module ; exécuter les contributions externes sans secrets ni privilèges d’écriture. Éviter `pull_request_target` pour exécuter le code des contributeurs.
9. Publier les versions avec code source correspondant, avis tiers et journal des changements. Réviser la liste des personnes habilitées à chaque arrivée ou départ.

**État du projet :** dépôt public créé sur [GitHub](https://github.com/steveprudhomme/gnu-astrophotography-recycle) le 15 novembre 2026. Après la publication documentaire, un premier inventaire depuis les sources est développé et testé localement. Les mesures scientifiques, les règles de branche et l’intégration continue restent à développer ou configurer. Un commit local ne signifie pas qu’une publication distante a eu lieu.
