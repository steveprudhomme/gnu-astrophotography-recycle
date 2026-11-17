# Données, confidentialité et préservation

Les FITS originaux ne sont jamais modifiés par l’application prévue. Les produits sont écrits dans une destination distincte ; toute collision avec les entrées doit être refusée. Aucun dossier d’observation n’est déplacé ou supprimé automatiquement.

Sur les supports externes de l’utilisateur, ne jamais créer de rapport, cache ou dossier, ni déplacer, modifier ou supprimer de fichier. Le regroupement des séances utilise uniquement les manifestes locaux déjà disponibles ; ses produits restent sur l’ordinateur et dans les répertoires ignorés.

Les en-têtes et journaux peuvent contenir lieu d’observation, nom, heures précises et chemins personnels. L’analyse est locale, sans télémétrie. Les chemins complets restent locaux ; une version publique des rapports utilise des identifiants anonymes et une liste de champs autorisés. La configuration effective peut être sensible et n’est pas exportée publiquement par défaut.

`.gitignore` exclut les archives usuelles, dossiers locaux et secrets courants. Il ne détecte pas toute donnée privée, et n’efface rien d’un historique existant. Avant publication, examiner les fichiers suivis et chaque commit. Ne jamais importer les prompts d’origine avec leurs chemins locaux dans le dépôt public.

Les tests utilisent en priorité des générateurs synthétiques. Un éventuel jeu réel public doit avoir droits de redistribution, licence de données, provenance, consentement pertinent et revue des métadonnées. Préparer une copie de diffusion explicitement autorisée ; conserver l’original local intact.

Les produits scientifiques restent sous la maîtrise de leur auteur. La licence du logiciel ne décide pas à elle seule du statut juridique des observations ou résultats.

La comparaison astrométrique utilise un catalogue local et ne contacte aucun service réseau. L’acquisition séparée d’un extrait par zone du ciel peut révéler la cible observée au fournisseur : elle doit être explicitement autorisée, avec la requête et sa provenance conservées localement. Pour le pilote Gaia, cet accord a été reçu avant l’exécution ; aucune image, en-tête complet ou position terrestre n’a été transmis. Les requêtes et résultats réels ne sont pas publiés sur GitHub.

Le recalage `gar register` ne lit que les chemins `local_copy` du workset local et n’utilise jamais ses chemins sources historiques. Il n’accède pas à la clé USB. Les modèles composés contiennent la WCS du champ : JSON, CSV et illustrations réels sont privés, au même titre que les FITS. Seuls les générateurs, tests et figures synthétiques sont destinés au dépôt public.

`gar gaia-frames` conserve ce périmètre local, avec modèle et catalogue déjà présents. La provenance du catalogue, ses identifiants associés, les résidus et références communes peuvent révéler le champ : tous les produits réels restent privés. Aucun nouveau consentement réseau n’est nécessaire à cette analyse, puisqu’elle n’émet aucune requête.

`gar time-evidence` relit uniquement les en-têtes des copies vérifiées, jamais les chemins sources historiques. Ses cartes, commentaires, indices de firmware, dates et canevas peuvent être sensibles : le dossier réel et les futures preuves complétées restent dans `local/`. Aucun accès USB, réseau d’analyse, acquisition instrumentale ou correction des originaux n’est effectué. Les figures publiques du protocole sont conceptuelles ; celles du dossier sont calculées sur des FITS entièrement synthétiques.

Les canevas publics de `examples/timing-campaign/` sont vides ou proposés. Copier ces fichiers dans `local/` avant d’ajouter identités, versions, informations de matériel, dates, pièces et mesures. Les réponses de l’opérateur restent privées. La préparation opérationnelle lit le rapport temporel local existant et ne rouvre pas les FITS ; remplir une fiche n’autorise aucune nouvelle lecture du support externe ni publication de preuves réelles.

Le prototype `moving-synthetic` et le parcours débutant utilisent uniquement des générateurs fictifs locaux. Ils n’accèdent pas à la clé USB ; les marqueurs synthétiques ne doivent pas être ajoutés à des observations réelles pour contourner le périmètre du prototype. Seuls les graphiques et le GIF d’exemples fictifs sont publiés. Les données personnelles et les renseignements de firmware recueillis dans le dossier privé ne servent pas à ce banc d’essai.

Le banc de limites du lot 12 conserve cette politique : 960 FITS fictifs, protocoles générés, vérité et rapports sous `local/`, sans accès au support externe. Seules les recettes, le protocole expliqué et les figures synthétiques sélectionnées sont publiés. L’autorisation de lecture seule de la clé Seestar ne permet aucune écriture et n’est pas utilisée par cet essai. Aucun fichier d’observation réel n’est transformé en exemple public.
