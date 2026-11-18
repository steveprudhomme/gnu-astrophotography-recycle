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

`main` contient les changements relus. Il ne garantit pas l'aptitude scientifique. Avant une livraison, vérifier le code, les documents, les licences et les limites annoncées. Suivre les [règles SemVer](VERSIONING.md) pour choisir la version et conserver les versions déjà publiées. Aucune date de livraison n'est promise.

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

**État au 17 novembre 2026.** Le dépôt est public depuis le 15 novembre.
La version de développement est [0.16.0-alpha.1](VERSION), sans création de tag ou de release.
Le [journal](CHANGELOG.md) résume les changements. La [feuille de route](ROADMAP.md) conserve les plans et les preuves historiques.

Le lot 23 utilise trois agents, avec coordination et revue internes. Le plan est publié avant le code.
Le profil lent est séparé ; les moteurs et les résultats historiques restent intacts.
Ce lot a passé 594 tests. Son parcours est reproduit depuis le commit propre `6f9950f`.

Les essais réservés restent partiels : chaque fond fictif retrouve 5/12 ajouts et manque le critère prévu.
Un fond fictif révèle aussi une ambiguïté d'orientation du recalage.
Les fonds réels retrouvent 6/12 puis 9/12 ajouts, sans candidat naturel proposé.
Ces résultats ne qualifient pas la sensibilité scientifique ou l'identité d'un objet.

Le lot 24 ajoute un diagnostic sans nouvelle recherche réelle et un banc fictif irrégulier.
Il conserve les trois manques brillants et leurs supports proches insuffisants.
Les orientations du nouveau banc passent le contrôle de fabrication ; ses critères brillants restent manqués.
Ce lot a passé 620 tests. Les seuils et les moteurs historiques restent inchangés.

Le lot 25 trace les décisions du détecteur sur les dérivés fictifs existants, sans nouvelle recherche de trajectoire.
Les six absences initiales n'ont aucun maximum local proche, malgré une réponse supérieure au seuil.
Les dix photos suivantes possèdent un centre proche retenu. Les positions enregistrées et les scores sont conservés.
Ce lot a passé 638 tests. Le diagnostic numérique ne constitue pas une qualification scientifique.

Le lot 26 compare un nouveau détecteur à voisinage réduit, avec seuil de luminosité et moteurs historiques inchangés.
Les deux fonds fictifs réservés retrouvent leurs six ajouts brillants, sans faux candidat fictif ni perte de récupération.
Les résultats sur fonds réels restent inchangés, sans nouveau candidat naturel. Ce lot a passé 668 tests.
Le coordinateur réalise la revue ; aucune validation indépendante n'est annoncée.

Le lot 27 élargit l'essai à quatre fenêtres préchoisies, soit 32 poses distinctes de deux séances du même champ.
Les alignements et les deux recherches sont disponibles ; chaque série donne zéro candidat avec chaque profil.
Aucun seuil, moteur ou ancien résultat ne change. Aucun contrôle positif naturel n'est encore disponible.
Ce lot a passé 689 tests. La revue du coordinateur reste interne.

Le lot 28 prépare un contrôle avec une comète mentionnée par le mainteneur.
Une requête limitée au nom et à huit dates est autorisée explicitement ; les réponses restent privées.
La référence reste géocentrique, avec UTC supposé. Huit copies intègres gardent leur refus du contrat historique.
La vitesse de référence sort aussi du domaine conservé. Aucun moteur, seuil ou en-tête n'est modifié.
Aucun contrôle positif naturel n'est validé. La revue du coordinateur reste interne.
La suite finale donne 728 tests réussis. Le parcours est reproduit hors ligne depuis `f189c22` propre.

Les analyses utilisent des copies locales vérifiées. Les sources sélectionnées sont seulement lues pour les copier.
Les nouveaux détails réels restent privés. Les cinq médias réels déjà autorisés gardent leur licence CC0 et leurs empreintes.
Les nouvelles figures publiques et tous les tests sont fictifs.

Les [règles de rédaction accessible](docs/REDACTION-ACCESSIBLE.md) s'appliquent aux nouveaux documents et aux sections révisées.
Le tutoriel explique les opérations avec des images et leurs descriptions. Aucun audit WCAG complet ou essai enfant n'est revendiqué.

Les temps, le budget d'erreur absolue, la photométrie et les performances sur mobiles réels restent à qualifier.
Les règles de branche et l'intégration continue restent à configurer.
Un commit local ne prouve pas une publication distante : vérifier aussi le commit sur GitHub, selon le [tutoriel](docs/TUTORIEL.md#14-mettre-à-jour-github-et-vérifier-la-publication).
