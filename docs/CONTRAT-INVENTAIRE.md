# Contrat d’inventaire 1.0

La commande `gar inventory` lit les fichiers `.fit`, `.fits`, `.fts` et leurs variantes `.gz`/`.fz`, sans distinction de casse. Les liens et jonctions sont ignorés et signalés. Les fichiers non FITS ne font pas partie du manifeste ; les dossiers inaccessibles deviennent des incidents explicites.

## Fichiers de sortie

| Produit | Contenu |
|---|---|
| `manifest.json` | Document de référence : version de schéma, provenance, fichiers, HDU et incidents |
| `inventory.csv` | Une ligne par HDU ; une ligne d’erreur si aucune HDU lisible ; UTF-8 avec BOM |
| `report.md` | Comptages, avertissements d’usage et graphique associé |
| `summary.svg` | Catégories de HDU ; les copies et extensions sont comptées |

Les rapports restent privés par défaut : ils peuvent contenir coordonnées du site, dates, chemins et informations d’instrument. Aucun fichier n’est envoyé sur Internet.

## Identité et intégrité

`sha256` porte sur **tous les octets du fichier d’origine**, y compris pour un FITS compressé. `frame_id = sha256 + ':' + hdu_index` identifie une HDU dans ce fichier, avec index à partir de zéro. Deux copies binaires ont le même identifiant scientifique ; leurs chemins restent deux entrées distinctes, et `duplicate_of` désigne la première occurrence dans l’ordre des chemins. Des pixels identiques réencodés dans deux fichiers différents ne sont pas détectés comme doublons.

Les statuts fichier sont `ok`, `warning`, `error` et `changed`. Une variation de taille, de date de modification ou d’identité pendant la lecture marque `changed` ; l’empreinte devient non fiable et le fichier ne participe pas aux rapprochements de doublons. Le programme ne verrouille pas les archives et ne détecte pas toute modification concurrente possible : travailler sur une archive au repos. La comparaison indépendante SHA-256 après traitement relève de la validation du pilote, pas d’une garantie automatique du programme.

L’empreinte nécessite la lecture de tous les octets et peut être longue sur un disque lent. Les tableaux de pixels ne sont pas chargés, dématricés ni analysés. Les tailles déclarées sont comparées à la taille physique pour les FITS non enveloppés en gzip ; les avertissements et erreurs d’Astropy sont conservés. Ce contrôle ne remplace pas une vérification scientifique ni une vérification exhaustive des sommes FITS `CHECKSUM`/`DATASUM`.

## HDU et métadonnées

Chaque HDU lisible a son index, sa classe Astropy, ses dimensions dans l’ordre FITS (`NAXIS1`, `NAXIS2`, etc.), ses métadonnées sélectionnées et ses drapeaux. Une primaire vide est conservée, ainsi que les extensions images ou tables. Aucune métadonnée de la primaire n’est héritée automatiquement par les extensions.

`kind` vaut `empty_primary`, `image_2d_candidate`, `stacked_candidate`, `image_other` ou `table_or_other`. La classification des empilements utilise le nom `Stacked_` ou un `STACKCNT > 1` : c’est une indication, pas une preuve instrumentale. Une image 2D n’est pas nécessairement brute ou calibrée. Un `BAYERPAT` sur une image RGB n’autorise pas à la traiter comme une mosaïque native.

`metadata` contient des valeurs brutes sélectionnées, sans conversion d’unité ni correction ; `raw_cards` conserve aussi les commentaires et cartes dupliquées de ces mots-clés. Les mots-clés absents sont `null`. Les valeurs non finies sont ramenées à `null` pour garder un JSON standard. L’en-tête entier n’est pas exporté. `EXPTIME` est une durée déclarée en secondes selon son usage FITS ; un `GAIN` déclaré n’est pas converti en électrons par ADU sans étalonnage.

`DATE-OBS` et `TIMESYS` restent tels que déclarés. Aucun fuseau, temps de début/milieu ou défaut UTC n’est appliqué dans ce premier inventaire. `time_validated` et `wcs_validated` restent toujours `false`. `wcs_axes_present` indique seulement la présence de `CTYPE1` et `CTYPE2`, sans interprétation ni validation des coordonnées.

Les textes potentiellement interprétables comme formules de tableur sont préfixés par une apostrophe dans le CSV ; le JSON conserve leur valeur originale. Le CSV est une vue de consultation, le manifeste JSON fait référence pour les comparaisons.

## Provenance et reproductibilité

Le manifeste enregistre un identifiant d’exécution, les heures UTC du **programme**, la version du logiciel, les versions Python/Astropy/NumPy et le commit disponible avec indication des changements locaux. Ces heures d’exécution ne sont pas les heures astronomiques des poses. Les fichiers et HDU sont ordonnés de façon stable ; les identifiants et dates d’exécution changent normalement entre deux lancements.

## Codes de sortie

- `0` : au moins un fichier, sans avertissement ou incident détecté ; aucune certification scientifique.
- `1` : erreur de configuration ou d’écriture des rapports.
- `2` : fichier en erreur/modifié, avertissement, lien ignoré, incident de parcours ou aucun FITS trouvé ; lire le manifeste.

Un dossier de sortie existant ou situé dans les archives est refusé. Si l’écriture échoue, un dossier de rapports partiel peut rester : conserver le diagnostic et relancer vers un nouveau dossier. Le regroupement automatique en séances n’est pas implémenté dans le contrat 1.0.
