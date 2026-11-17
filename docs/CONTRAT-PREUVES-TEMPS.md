# Préparation des preuves temporelles — contrat 1.0

`gar time-evidence` prépare un dossier à partir des en-têtes complets des **copies locales déjà vérifiées**. Cette commande complète `gar timing`, qui utilise le manifeste partiel d’inventaire. Elle ne certifie aucune heure et ne transforme pas des déclarations en mesures d’horloge.

## Entrée et protections

Fournir un workset local avec `success: true`, liste non vide de copies `local_copy` et `sha256_copy`. Tous les chemins doivent rester dans `local/`, sans lien ni jonction. Les chemins hors de ce périmètre sont rejetés avant sondage. Les copies doivent être distinctes et rester dans le dossier du workset. **Les chemins sources historiques ne sont jamais utilisés.**

Le SHA-256 du workset et de chaque copie est vérifié avant/après. Les FITS sont ouverts en lecture seule, sans mise à l’échelle ou accès aux tableaux de pixels. Chaque HDU est examinée avec ses propres cartes ; aucune information primaire n’est implicitement héritée par une extension. Les fichiers existants, copies, workset et rapports antérieurs ne sont pas réécrits. Aucun réseau ni accès USB n’est effectué par l’analyse.

## Champs conservés et limites de couverture

Le JSON expose la liste exacte `selected_keywords`, les cartes sélectionnées dans leur ordre, index, type, commentaire et représentation textuelle. La liste couvre dates de création/observation/début/moyenne/fin, coordonnées temporelles numériques et origines, échelle/unité/référence, durées, erreurs déclarées et indices de logiciel/firmware. `absent_selected_keywords` désigne une absence dans **cette HDU locale**, pas dans tout l’instrument ou les autres archives. Les doublons sont conservés et les clés dupliquées ne servent pas aux calculs.

Ce n’est pas un validateur exhaustif de toutes les conventions FITS : colonnes temporelles de tables, axes temporels WCS, variantes de mots-clés et unités spécialisées ne sont pas interprétés. Les données des tables ne sont pas lues. `PROGRAM`, `CREATOR`, `SWCREATE` ou `VERSION` sont des indices de logiciel, sans preuve du firmware exact ; même `FIRMWARE`/`FWVERSION` explicites restent des déclarations non vérifiées. Les mots-clés non standard sont collectés comme tels, sans garantie de signification instrumentale.

Les images 2D sans indice d’empilement sont des candidates à une pose individuelle, pas des expositions physiquement certifiées. Un cube à trois axes ou `STACKCNT > 1` est séparé comme empilement/cube ; une table ou une image vide n’est pas une pose individuelle. La somme ou moyenne temporelle d’un empilement n’est pas déduite de son `EXPTIME` ou `TOTALEXP`.

## Diagnostic déclaratif

Le parseur de dates reste celui du diagnostic existant : date complète sans suffixe, au plus six décimales. Dates seules, suffixes de fuseau, secondes intercalaires et fractions plus longues sont conservés mais explicitement non pris en charge, sans les déclarer illégaux en FITS. La granularité textuelle n’est pas une mesure d’exactitude. Les mots de commentaire sont des indices, pas une interprétation sémantique prouvée.

Les échelles reconnues et les indices normatifs UTC/unité seconde sont séparés des déclarations réellement écrites. Aucun défaut n’est appliqué pour convertir une date. Les valeurs JD/MJD, origines et décalages numériques sont conservés **sans conversion ni réconciliation** ; leur présence produit un avertissement de limite. Une incohérence entre représentations n’est donc pas exclue par ce dossier.

Si `DATE-BEG` et `DATE-END` sont uniques et lisibles, le rapport calcule seulement une **différence calendaire naïve**. Ce nombre ne corrige ni échelle, fuseau, seconde intercalaire, ni latence. Une fin antérieure au début ou une `DATE-AVG` hors de l’intervalle est signalée. `DATE-AVG` n’est pas supposée être le milieu arithmétique de la pose.

La différence avec `TELAPSE` n’est affichée que si `TIMEUNIT = 's'` est explicitement déclaré et `TELAPSE` numérique non négatif. La tolérance de comparaison est 1 microseconde, **sans être une précision instrumentale**. Aucune durée physique n’est certifiée. Les nombres `EXPTIME`/`EXPOSURE` positifs différents sont signalés comme valeurs d’alias divergentes avec unités non vérifiées, sans conclure à un défaut matériel. Les valeurs d’erreur négatives/non numériques et durées négatives sont signalées ; zéro n’est jamais une preuve d’incertitude nulle.

## Canevas et refus de qualification

Huit exigences structurent `evidence-template.json` : configuration applicable, événement daté, échelle/référence, mesure indépendante, décalage/dérive/dispersion, durée/lecture, budget/critères et rattachement aux archives anciennes. Le canevas ne contient aucune mesure inventée. Il doit être complété séparément et revu ; **la commande n’ingère pas ce fichier comme preuve et n’approuve aucun résultat**. Le [protocole détaillé](PROTOCOLE-QUALIFICATION-TEMPS.md) définit la préparation d’un futur essai.

Même avec toutes les cartes présentes et cohérentes : `time_validated`, `exposure_reference_verified`, `firmware_applicability_verified` et `scientific_time_export_allowed` restent faux ; `clock_accuracy_seconds` et `mid_exposure_utc` restent `null`. Le dossier indique qu’aucune preuve indépendante n’a été fournie à cette analyse ; il n’affirme pas qu’aucune preuve n’existe ailleurs.

## Commande et produits

```powershell
.\.venv\Scripts\python.exe -m gar time-evidence ".\local\lot\workset.json" --output ".\local\preuves-temps-01"
```

La destination doit être nouvelle. Produits : `time-evidence.json`, `cards.csv`, `time-evidence.svg`, `report.md`, `evidence-template.json` et `measurement-plan.md`. Le CSV protège les textes interprétables comme formules ; le JSON conserve la valeur originale. Les champs et commentaires réels peuvent être privés : tout reste sous `local/`. Les barres du SVG sont des comptages de déclarations qui se recouvrent, pas un niveau de confiance ou une précision.

Code **2** : dossier produit, temps non qualifié. Code **1** : entrée, intégrité ou production impossible. Aucun code 0 de certification dans cette version. Une erreur d’écriture peut laisser une sortie partielle ; choisir un nouveau dossier après résolution et ne pas annoncer ce dossier comme complet. La version et la révision enregistrées par la CLI identifient le logiciel de préparation, sans dater la précision de l’horloge du télescope.

Références normatives : [FITS 4.0, section 9 et table 35](https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf), [Rots et al., coordonnées temporelles FITS](https://arxiv.org/abs/1409.7583). API de lecture : [Astropy FITS](https://docs.astropy.org/en/stable/io/fits/api/files.html). Le choix de ne pas convertir ou certifier est une règle de preuve du projet ; le parseur limité n’est pas une définition de tout FITS.
