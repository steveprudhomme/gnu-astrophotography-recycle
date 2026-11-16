# Contrat des séances candidates 1.0

`gar sessions` lit uniquement un manifeste d’inventaire 1.0 déjà enregistré. Il ne parcourt pas les archives, ne rouvre pas les FITS et ne déplace aucun fichier. Dans le flux documenté, les sorties restent dans `local/` sur l’ordinateur : rien n’est créé sur le support externe des observations. Le contrôle de la destination résout les chemins déclarés pour éviter une sortie dans la racine des archives ; il ne remplace pas le choix explicite d’une destination locale hors du support externe.

## Entrée et provenance

Le schéma d’inventaire, la racine absolue déclarée, la structure des fichiers/HDU, les empreintes et identifiants HDU sont contrôlés avant l’écriture. Un manifeste mal formé ou d’une version inconnue est refusé. Il ne suffit pas de renommer un ancien rapport exploratoire en `manifest.json` : il doit respecter le contrat d’inventaire.

L’empreinte SHA-256 porte sur les octets du **manifeste**, pas sur une nouvelle lecture des observations. Le résultat conserve aussi le run et la révision de l’inventaire, la version du logiciel de regroupement, le commit disponible, l’état des changements locaux et les paramètres. Il ne démontre pas que les FITS correspondent encore au manifeste si une autre application les a modifiés depuis.

## Règles de regroupement

1. Retenir uniquement les HDU classées `image_2d_candidate`, avec dimensions positives, dans des fichiers de statut `ok`.
2. Exclure les copies d’un même `frame_id` : chaque HDU identique n’est comptée qu’une fois, même si le manifeste n’a pas renseigné `duplicate_of`. Le chemin de la première occurrence valide dans l’ordre des chemins est retenu.
3. Exiger une date complète `YYYY-MM-DDTHH:MM:SS`, avec éventuellement une à six décimales. Les dates seules, suffixes de fuseau, dates impossibles, secondes intercalaires `:60` et précisions supérieures sont exclues avec un motif explicite. Ces exclusions sont des limites du parseur initial, pas une affirmation que tous ces formats seraient invalides en astronomie.
4. Conserver séparés le dossier parent, la date calendaire déclarée, les dimensions et les valeurs exactes des métadonnées : `OBJECT`, `INSTRUME`, `FILTER`, `BAYERPAT`, `EQMODE`, `TIMESYS`, `GAIN`, `BITPIX`, `BUNIT`, `BSCALE`, `BZERO`, `SITELAT` et `SITELONG`.
5. Trier chronologiquement à l’intérieur d’une configuration ; couper si l’intervalle est **strictement supérieur** à `--gap-seconds`, 1 800 secondes par défaut. À égalité, conserver le même groupe.

Le découpage à minuit peut séparer une véritable séance qui traverse cette limite. Les valeurs exactes de position de site peuvent aussi produire des groupes distincts si elles varient ; cela ne prouve pas un déplacement réel. Aucune tolérance géographique, correction de fuseau, fusion entre dossiers, harmonisation des noms de cibles ou identification par catalogue n’est implicite. Les métadonnées absentes restent `null` et les configurations incomplètes sont signalées.

Chaque identifiant de groupe est le SHA-256 de sa configuration et de ses membres ordonnés, avec la version de méthode. Il reste stable si l’ordre des fichiers dans le manifeste change. Le seuil est conservé en provenance ; changer le seuil sans changer les membres ne change pas l’identité du groupe.

## Résultats

| Fichier | Contenu |
|---|---|
| `sessions.json` | Source de référence : provenance, paramètres, groupes, membres, exclusions et réconciliation |
| `sessions.csv` | Une ligne par groupe, dates brutes, durées déclarées, compte et drapeaux ; UTF-8 avec BOM |
| `sessions.svg` | Nombre de HDU par groupe, au plus les 30 premiers dans l’ordre du JSON/CSV |
| `report.md` | Comptages, motifs d’exclusion, graphique et limites |

`timestamp_span_seconds` est la différence entre le premier et le dernier horodatages. Ce n’est ni une intégration cumulée, ni une durée allant du début de la première à la fin de la dernière pose. Pour une seule pose, cette couverture vaut zéro, pas son temps d’exposition.

`total_exposure_seconds_declared` est la somme des `EXPTIME` numériques positifs des HDU retenues, seulement si tous sont présents et admissibles ; sinon `null`. `known_exposure_sum_seconds` conserve la somme partielle connue, ou `null` si aucune durée n’est connue. Les durées manquantes, nulles, négatives ou textuelles ne sont pas inventées ni converties silencieusement. Deux HDU différentes au même horodatage sont conservées et signalées ; il faut vérifier si elles représentent réellement des expositions distinctes avant d’interpréter la somme physiquement.

Les compteurs satisfont `input_hdus = grouped_hdus + excluded_hdus`. Les erreurs de fichiers sans HDU lisible sont conservées séparément dans `file_events`. Les incidents de parcours issus de l’inventaire sont comptabilisés. Le JSON fournit les motifs détaillés ; le CSV est une vue de consultation avec protection des textes interprétables comme formules.

## Codes de retour et limites

- `0` : regroupement non vide, sans exclusion ou anomalie comptable détectée. Cela ne valide pas les heures, même si elles sont complètes.
- `1` : manifeste, paramètres, destination ou écriture incorrects ; pas de regroupement exploitable garanti.
- `2` : exclusions, incidents, absence de groupe, durées incomplètes ou horodatages dupliqués. Les rapports produits doivent être examinés ; une exclusion attendue d’empilement peut suffire à produire ce code.

Un dossier de sortie existant ou dans la racine des observations déclarée est refusé. Les heures restent brutes : `time_validated` vaut toujours `false`. Les catalogues, alignements, astéroïdes, mesures photométriques et soumissions ne font pas partie de cette commande.
