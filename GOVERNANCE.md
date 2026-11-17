# Gouvernance

## Responsabilités proposées

| Rôle | Responsabilité | Attribution initiale |
|---|---|---|
| Fondateur / mainteneur | Cap, versions, revue et décisions motivées | Steve Prud'Homme — [steveprudhomme](https://github.com/steveprudhomme) |
| Référent scientifique | Méthodes, incertitudes, validation | À pourvoir |
| Contributeurs | Changements et preuves de validation | Communauté |

Le mainteneur peut assurer plusieurs rôles au démarrage. Cette concentration de responsabilité est explicite ; les validations indépendantes seront recherchées avant d’annoncer une aptitude scientifique.

Les décisions d’architecture sont proposées dans une issue, discutées puis consignées dans la documentation avec statut et justification. Une décision de rejet doit être motivée. Les modifications de méthode ou de format nécessitent une proposition de fusion dédiée ; les mesures publiées doivent rester reproductibles avec leur version d’origine.

Un diagnostic non conclusif est un résultat à conserver : le contrôle temporel 0.3 distingue des métadonnées cohérentes d’une horloge scientifiquement qualifiée. Les éléments probants et rapports privés ne sont pas publiés implicitement avec les versions du logiciel.

Le diagnostic WCS 0.4 conserve la même distinction : cohérence numérique d’un sous-ensemble de paramètres et validation astrométrique sont deux résultats différents. Les informations non collectées ne sont pas remplacées par une solution supposée.

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

**État au 17 novembre 2026 :** dépôt public créé sur [GitHub](https://github.com/steveprudhomme/gnu-astrophotography-recycle) le 15 novembre. L'Alpha 0.10 comprend les modules d'inventaire et de contrôle, la préparation temporelle, les bancs de mobiles fictifs, un premier [pilote exploratoire réel](docs/PILOTE-MOBILES-SEESTAR.md) et un [parcours pédagogique illustré](docs/DEMARRER-DE-ZERO.md). La suite compte 517 tests logiciels, dont 46 nouveaux contrôles entièrement fictifs des mouvements représentatifs. Le lot 22 conserve les seuils et démontre une aptitude négative aux scénarios lents 10/30/60 secondes d’arc par heure : 0/12 par fond réel admissible, contre 2/2 contrôles techniques rapides retrouvés. Deux fonds réels sont analysés, un troisième refusé pour durée, seize sources copiées en lecture seule puis toutes analyses locales. Les preuves depuis 61cac96 et neuf nouvelles commandes sont documentées ; aucun contrôle positif naturel ou validation scientifique universelle annoncé. Le lot 21, avec trois agents et plan publié avant code, conserve les 115 absences et le contexte 21 : 105 cercles sans réponse dépassant le seuil et dix avec réponse dépassant le seuil mais sans maximum local proche, avec voisin plus haut enregistré. La reproduction depuis f1f159f conserve les 136 traces, scores et candidats sans changer les seuils ; les preuves détaillées restent locales et les nouvelles figures publiques sont fictives. Le lot 20, mené avec trois agents parallèles et coordination centrale après publication du plan, reproduit les 136 listes des 17 manques : 115 images sans maximum brut proche et 21 avec point retenu, sans cause physique amont départagée. Les moteurs et seuils restent gelés ; le mandat autonome est consigné dans AGENTS.md et les preuves de reproduction depuis f6ec207 sont documentées. Les moteurs et protocoles historiques gardent leurs limites et refus documentés ; la partition spatiale reste expérimentale et ne remplace pas la commande habituelle. Sur huit copies locales réelles, sept alignements sont acceptés et la recherche s'achève avec zéro candidat ; le GIF avant/après est maintenant publié sous CC0 et les rapports restent privés, sans nouvel accès USB. Ce premier essai ne valide pas la sensibilité réelle du détecteur. Le lot 18 retrouve 10/36 points artificiels sur les dérivés du fond réel, avec 26 manques, recalage gelé et témoin naturel inchangé ; les dérivés et rapports mixtes restent privés. Le lot 19 diagnostique ensuite les 26 manques à partir des positions gelées : neuf hors plage de vitesse et 17 avec support déjà insuffisant dès les détections enregistrées, sans cause physique unique démontrée ni changement de seuil. Ces lots passent par des branches dédiées et PR vers main, avec revue et vérifications avant fusion. Cinq médias réels, dont le GIF du pilote et ses illustrations, sont diffusés sous CC0 avec l'autorisation réaffirmée du mainteneur ; les exercices et tests restent fictifs. Aucun essai instrumental de datation n'est réalisé. L'horloge, le budget absolu complet, les performances sur mobiles réels et la photométrie restent à qualifier ou développer ; règles de branche et intégration continue restent à configurer. Un commit local ne prouve pas une publication distante : suivre la [procédure du tutoriel](docs/TUTORIEL.md#14-mettre-à-jour-github-et-vérifier-la-publication) et vérifier le commit présent sur GitHub.
