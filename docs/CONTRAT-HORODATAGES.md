# Diagnostic temporel 1.0 — contrat et limites

La commande `gar timing` lit un manifeste d’inventaire local 1.0. Elle ne rouvre pas les FITS, ne modifie pas le manifeste et ne déplace aucune observation. Conserver ses sorties dans `local/` sur l’ordinateur, jamais sur le support externe. Les protections de destination sont identiques à celles du regroupement des séances.

## Ce que le diagnostic établit

| Contrôle | Résultat |
|---|---|
| Forme de `DATE-OBS` | Valeur brute, statut lisible/absent/non pris en charge, nombre de décimales lisibles |
| Échelle | Valeur déclarée, reconnaissance dans un ensemble limité, indication normative séparée si absente |
| Commentaires | Cartes brutes sélectionnées et mots évoquant création, début, fin ou milieu ; aucune certification sémantique |
| Durées | Valeurs `EXPTIME` et `EXPOSURE`, absence ou conflit numérique au-delà de 1 microseconde |
| Cadence | Différences naïves d’horodatages, médiane des intervalles positifs, interruptions, dates dupliquées et intervalles courts |
| Provenance | SHA-256 du manifeste, run source, version du logiciel, commit disponible et changements locaux |

Les groupes de même configuration/date sont réunis pour examiner les interruptions entre séances candidates. Les frontières de dossier, date déclarée, configuration et site restent respectées ; aucune comparaison ne traverse ces frontières. Les copies binaires, empilements et dates inutilisables sont exclus de la cadence. Le JSON conserve toutes les HDU et les motifs, y compris celles auxquelles le diagnostic de pose individuelle ne s’applique pas.

Le parseur conserve les limites du regroupement : date complète sans suffixe, jusqu’à six décimales ; dates seules, secondes intercalaires, fractions plus longues et suffixes de fuseau sont explicitement non pris en charge. Le diagnostic n’affirme pas que ces représentations seraient toutes interdites par FITS. Les commentaires sont recherchés par mots simples, pas par une interprétation fiable du langage naturel.

## Résolution écrite et exactitude

`decimal_places_written` et `written_quantum_seconds` décrivent la granularité textuelle d’une date prise en charge. Six décimales donnent un pas écrit de `0.000001 s` ; elles ne démontrent pas une exactitude d’une microseconde. `clock_accuracy_seconds` reste `null`, `exposure_reference_verified` et `time_validated` restent `false`, `mid_exposure_utc` reste `null`.

La présence d’un mot-clé `TIMESYS = UTC` est une déclaration, pas un étalonnage d’horloge. Le champ `fits_scale_default_hint` présente séparément la lecture normative d’un mot-clé absent ; il n’est jamais appliqué pour convertir les observations. L’ensemble d’échelles reconnues dans cet audit est limité à UTC, TAI, TT, TCG, TCB, TDB, GPS et UT1 ; une autre déclaration est signalée comme hors de cet ensemble, sans être automatiquement déclarée illégale en FITS.

Un intervalle positif inférieur à l’`EXPTIME` précédent est une alerte. Sans connaître le sens du timestamp, cela ne prouve pas un chevauchement physique. Un intervalle nul signale une date dupliquée et n’entre pas dans la médiane des intervalles positifs. Une interruption est comptée si l’intervalle est strictement supérieur au seuil, 1 800 secondes par défaut. Le tri utilise les valeurs de date, jamais les noms de fichiers : il ne prétend pas retrouver une inversion d’horloge à partir de l’ordre alphabétique.

Une date régulière ne permet pas de mesurer un décalage absolu constant ; une dérive d’horloge exige une référence indépendante. Les différences affichées ne corrigent ni les échelles, ni les secondes intercalaires, ni les changements de fuseau. Aucun JD, HJD, BJD ou milieu de pose n’est produit.

## Références et niveau de preuve

- [Standard FITS 4.0](https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf), sections 4.4.2 et 9.2.1 : défauts normatifs pour les heures. Pour une date moderne, UTC et début d’observation sont les lectures de référence en l’absence d’indications contraires ; cela ne prouve pas le comportement d’un appareil. La table 35 distingue aussi `DATE-BEG` pour limiter l’ambiguïté historique de `DATE-OBS`.
- [Guide officiel Seestar Telescope Network](https://www.seestar.com/blogs/tutorial/seestar-telescope-network-remote-guide) : l’éditeur souligne l’importance des réglages d’heure en usage distant. Ce guide ne définit pas ici la relation exacte entre `DATE-OBS` et l’exposition, ni une borne d’erreur pour le S50 de l’utilisateur.
- [Discussion technique sur le forum ZWO](https://bbs.zwoastro.com/d/12736-what-time-is-held-in-the-date-obs-field-in-the-fits-header) : le contexte porte sur d’autres caméras et logiciels, avant le S50. Il n’est pas transposé à ce modèle ou à son firmware.

Recherche consultée le 15 novembre 2026 : aucune preuve applicable au firmware et aux archives examinées n’a été établie pour certifier leur convention ou leur exactitude. Ce constat porte sur les sources consultées, pas sur l’inexistence de toute documentation possible.

Les manifestes actuels ne sont pas une copie complète des en-têtes. Des champs comme firmware, `DATE-BEG`, `DATE-END`, `TIMSYER` ou `TIMRDER` n’ont pas été sélectionnés par l’inventaire 1.0. Leur absence du manifeste ne prouve pas leur absence des FITS. Aucune relecture du support externe n’est entreprise dans ce lot pour compléter ces informations.

## Sorties et codes

- `timing.json` : référence complète, lignes par HDU, séquences, intervalles, exclusions, paramètres et provenance.
- `timing.csv` : vue de consultation ; textes protégés contre les formules de tableur ; inconnues vides.
- `timing.svg` et `report.md` : contrôles et conclusion. Les barres du graphique se recouvrent ; il ne faut pas les additionner.

Code `1` : erreur de manifeste, paramètres, destination ou écriture. Code **`2`** après une analyse produite : l’heure scientifique reste non qualifiée et requiert une preuve indépendante, même si aucun défaut de cadence n’est détecté. Cette première version ne retourne pas de code `0` de certification ; `scientific_time_export_allowed` reste `false`. Ce champ n’ajoute aucun export ou accès réseau.

## Conditions pour une qualification future

Obtenir une description applicable au modèle, firmware et mode d’acquisition, puis confronter début/fin d’exposition et synchronisation à une référence indépendante, avec incertitude documentée. Un essai de datation lumineux maîtrisé ou une autre méthode validée pourra servir de contrôle. Conserver références, réglages, protocole, résultats et budget d’erreur ; ne jamais compléter les inconnues en réécrivant les originaux.
