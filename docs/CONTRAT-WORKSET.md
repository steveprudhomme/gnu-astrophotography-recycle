# Échantillon de travail local 1.0

`gar workset` lit une sélection JSON explicite, copie les fichiers en lecture seule puis travaille uniquement sur les copies. Aucun parcours récursif des archives, déplacement, suppression, réparation ou écriture sur le support source n’est effectué.

## Sélection et destination

La sélection a un champ `selection_schema_version` égal à `1.0` et une liste `files`. Chaque entrée contient `source`, chemin absolu, et éventuellement `expected_sha256`, empreinte historique de 64 caractères hexadécimaux minuscules. Des annotations comme `role` peuvent documenter le choix. Les chemins réels rendent ce document privé : le conserver dans `local/`.

Les sources doivent être des fichiers réguliers sans lien ou jonction dans leur chemin. Les sources répétées et empreintes mal formées sont refusées. La destination doit être nouvelle et strictement dans le répertoire `local/` de ce projet ; les chemins qui sortent de cette limite par une jonction sont refusés. Ce périmètre est volontaire pour éviter de placer les copies ou rapports sur le support externe.

Les noms des copies commencent par un numéro de sélection, ce qui évite les collisions de noms entre dossiers. Aucun fichier existant n’est écrasé. Une erreur peut laisser un dossier partiel avec `success: false` et un diagnostic : ne pas l’utiliser comme lot validé, puis relancer vers un nouveau dossier. Aucun nettoyage automatique des sources ou des sorties n’est entrepris.

## Contrôle des octets

Pour chaque fichier : calculer SHA-256 avant copie, comparer l’empreinte historique si fournie, copier par flux `rb` vers un nouveau fichier, puis comparer empreinte de la copie et empreinte de la source relue. Taille et date de modification source sont aussi contrôlées pendant la copie. La copie est hachée à nouveau après la collecte des en-têtes.

Cela vérifie le contenu aux instants contrôlés, sans verrouiller les archives ni garantir leur état futur. Travailler sur une archive au repos. La comparaison historique est facultative : un empilement non haché précédemment bénéficie des comparaisons immédiates mais pas d’une preuve de conservation depuis un ancien inventaire.

## En-têtes et modèle WCS

`workset.json` conserve, pour chaque HDU de chaque copie, toutes les cartes interprétées par Astropy : ordre, mot-clé, valeur, type, commentaire et image textuelle de la carte. Les fichiers `headers/*.hdr` contiennent une représentation textuelle de l’en-tête, y compris commentaires et historique. Il s’agit d’une représentation par la bibliothèque, pas d’une promesse d’extraction physique octet par octet ; la copie FITS exacte reste la preuve complète, avec son empreinte.

Les images ne sont pas réenregistrées. Si les axes primaires sont déclarés, Astropy tente un modèle de deux axes à partir de l’en-tête complet et du contexte HDU de la copie (`relax=True`, `fix=False`). Les distorsions et unités normalisées par la bibliothèque sont rapportées, avec avertissements et erreurs. Les valeurs par défaut de la bibliothèque ne sont pas présentées comme des mots-clés écrits dans l’original.

La construction peut consulter des données de contexte WCS présentes dans la copie ; aucune mesure des étoiles, transformation de coordonnées, résolution ou comparaison au catalogue n’est faite. `scientifically_validated` et `sky_coordinates_computed` restent faux. Une primaire sans axes déclarés ne permet pas de conclure sur toutes les solutions alternatives possibles.

## Utilisation

```powershell
.\.venv\Scripts\python.exe -m gar workset ".\local\selection.json" --output ".\local\echantillon-01"
```

Code `0` : copies et collecte terminées, sans certification scientifique. Code `1` : sélection, intégrité ou traitement en échec. Les produits sont privés : copies FITS, `workset.json` et `headers/`.

Le programme ne choisit pas silencieusement une association poses/empilement. Même cible, filtre et nombre de poses ne prouvent pas la liste exacte des sources d’un empilement.

La [préparation de série du lot 15](PREPARER-SERIE-SEESTAR.md) utilise ce contrat sans le modifier : sélection explicite issue d’un manifeste local, racine source explicitement liée, puis huit copies vérifiées par `gar workset`. Son audit ultérieur n’ouvre que les copies locales et ne qualifie ni recalage, ni heure, ni mobile. Les deux rendus documentaires réels autorisés sont identifiés séparément sous [CC0](images/reels/LICENCE.md) ; le workset et les en-têtes restent privés.

Références : [en-têtes Astropy](https://docs.astropy.org/en/stable/io/fits/api/headers.html), [construction WCS](https://docs.astropy.org/en/stable/api/astropy.wcs.WCS.html). La compatibilité du manifeste d’inventaire 1.0 et de ses anciens diagnostics est conservée ; les en-têtes complets sont un produit séparé.
