# Prototype de mobiles synthétiques — contrat 1.0

`gar moving-synthetic` est un banc d’essai expérimental sur images **déclarées fictives**, monoplans, déjà dans un repère commun. Les temps sont des secondes relatives inventées. Aucun recalage réel, Bayer, catalogue céleste, correction d’horloge ou export scientifique n’est réalisé par cette commande. Pour commencer sans connaissance technique, suivre le [parcours illustré](DEMARRER-DE-ZERO.md).

## Entrées et protections

```powershell
.\.venv\Scripts\python.exe examples/make_moving_demo.py local/demo-mobiles-input
.\.venv\Scripts\python.exe -m gar moving-synthetic local/demo-mobiles-input/manifest.json --truth local/demo-mobiles-input/truth.json --output local/demo-mobiles-report
```

Toutes les entrées et sorties doivent rester dans `local/`, sans lien ni jonction, avec destination nouvelle. Les chemins hors de ce périmètre sont refusés avant sondage. Le manifeste 1.0 déclare `synthetic: true`, `time_kind: fictitious_relative_seconds` et des séquences distinctes avec `local_copy`, SHA-256 et temps croissants. Chaque FITS doit porter `GARSYNTH = T` et un `SYNCTIME` correspondant au manifeste. Ces marqueurs ne prouvent pas l’origine d’un fichier réel arbitrairement réétiqueté ; ils limitent le périmètre déclaré de ce prototype.

Limites de ressources : au plus 64 séquences, 5 à 64 images par séquence, images 2D d’au plus 1 048 576 pixels, 500 détections sélectionnées par image et 100 000 hypothèses. Un dépassement arrête l’analyse au lieu de tronquer silencieusement le résultat. Dimensions constantes par séquence et chemins d’images distincts sont requis. Fichiers ouverts en lecture seule, empreintes de toutes les entrées avant/après, aucun accès réseau ou support USB. Aucun FITS n’est modifié ou rééchantillonné.

## Algorithme préenregistré

Plan préalable `a072ff1`, 17 novembre 2026. Détection DAO à 5 écarts-types robustes, FWHM initiale 3 pixels, séparation 5 pixels, marge 8 pixels, exclusion des valeurs non finies ou ≥65 000 ADU. Une source trouvée à moins de 2 pixels dans au moins la moitié des images est retirée comme stationnaire. Ce filtre peut aussi retirer des mobiles lents ou confondus avec une étoile ; ce risque fait partie des résultats de sensibilité.

Les paires de détections sur images séparées d’un ou deux pas créent des hypothèses rectilignes, vitesses de 0,1 à 1,5 pixel par seconde fictive. Association au plus proche dans 1,5 pixel, au plus une détection par image ; au moins cinq images et une couverture temporelle fictive de 40 s. Un premier ajustement linéaire est suivi d’une réassociation, puis d’un ajustement final. Conditions : RMS ≤0,75 pixel et P95 ≤1,5 pixel. Les candidats partageant au moins trois identités image/détection sont dédoublonnés de façon déterministe, en privilégiant l’effectif puis le RMS.

Le rayon et les filtres sélectionnent les associations observables ; ils ne rendent pas le résultat exempt de confusion. Des trajectoires se croisant, accélérées, très lentes, longues traces ou des défauts cohérents peuvent échouer ou produire de faux candidats. Les images sont supposées dans un repère commun, et aucune correction des défauts de repérage n’est ajustée ici. Les vitesses sont des coordonnées de pixels sur des temps fictifs, pas des vitesses célestes mesurées.

## Vérité distincte et évaluation

La vérité contient les positions et vitesses injectées, visibilité par image, identifiants distincts et l’empreinte du manifeste correspondant. Son fichier est haché avant traitement, mais ses coordonnées sont lues **après gel de tous les candidats** ; aucune vérité n’est passée à la détection ou à l’association. Les tests vérifient que changer la vérité change le bilan, sans modifier les candidats.

Un appariement un-à-un associe candidat et injection sur au moins cinq positions visibles communes, avec RMS d’erreur ≤1 pixel et erreur vectorielle de vitesse ≤0,05 pixel/s. Les injections non associées sont manquées ; les candidats non associés sont des faux candidats. Le rapport conserve erreurs de position et de vitesse, rappels, objets manqués, faux candidats et taux par image, mégapixel-image et heure fictive. Ce dernier taux utilise la durée entre premier et dernier échantillon, pas une durée d’exposition réelle.

Les trois graines 17, 23, 41 et six scénarios forment 18 séquences de huit images 256×256 espacées de 10 s fictives : nominal (deux mobiles brillants isolés), contrôle sans mobile avec pixels chauds/flashs indépendants/trace transitoire, mobile absent sur deux images, mobile faible et mobile très lent, mélange près d’une étoile et défaut commun de repérage jusqu’à 0,35 pixel. Fond gaussien 100 ADU, bruit sigma 2, PSF sigma 1,3 pixel. Les cas nominaux sont isolés par construction ; aucun réalisme exhaustif de capteur n’est revendiqué. Pas de Bayer, bruit de photons calibré, traînée intra-exposition ou budget d’incertitude complet.

Critères principaux fixés avant mesure : les six injections nominales et trois intermittentes retrouvées, zéro faux candidat sur les trois contrôles, P95 de position ≤0,75 pixel et erreur vectorielle maximale de vitesse ≤0,03 pixel/s sur les mobiles récupérés de ces cas. La suite doit être complète pour porter ce verdict. Les scénarios faible/lent, mélange et défaut de repérage sont descriptifs ; ils ne sont ni supprimés ni transformés en garantie par le verdict principal.

## Résultats de ce lot et limites

Sur la suite publiée : 6/6 nominaux et 3/3 intermittents retrouvés, zéro faux candidat sur les contrôles ; P95 principal voisin de 0,075 pixel, erreur vectorielle maximale de vitesse voisine de 0,0012 pixel/s fictive. Au total, 16/21 injections sont retrouvées ; cinq sont manquées dans le scénario faible/lent. Les témoins ne prouvent pas un taux universel de faux positifs nul et trois graines ne constituent pas un étalonnage exhaustif de sensibilité.

Le premier générateur de témoin plaçait ses flashs distincts suivant une ligne ; il a été corrigé pour utiliser des positions indépendantes. Les sorties initiales ont été conservées localement et l’évaluation rapportée utilise la suite corrigée, avec les mêmes seuils. Aucun paramètre n’a été modifié pour embellir le résultat.

## Sorties et images

`moving.json`, `candidates.csv`, `moving.svg` et `report.md` décrivent les candidats et l’évaluation. Le CSV protège les identifiants de séquence interprétables comme formules. Codes : 0 si les critères de la suite complète sont satisfaits ; 2 si le rapport produit ne les satisfait pas ou utilise un sous-ensemble ; 1 si l’analyse est impossible. Une erreur d’écriture peut laisser un dossier incomplet ; résoudre la cause puis choisir une nouvelle sortie.

Les figures PNG et GIF sont facultatives, avec les outils de `requirements/figures-tested.txt` :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements/figures-tested.txt
.\.venv\Scripts\python.exe examples/plot_moving_demo.py local/demo-mobiles-input/manifest.json local/demo-mobiles-report/moving.json local/demo-mobiles-figures
```

Le tracé lit les pixels synthétiques et les candidats gelés ; il produit bilan, image et GIF de huit images, sans modifier les entrées. Le générateur graphique vérifie correspondance du manifeste et empreintes des images illustrées. Les images publiques indiquent leur nature fictive ; aucune capture d’écran n’est fabriquée. `clock_qualified`, `real_data_performance_validated` et `scientific_submission_certified` restent faux.

Bibliothèques utilisées : [Photutils DAOStarFinder](https://docs.astropy.org/projects/photutils/en/stable/api/photutils.detection.DAOStarFinder.html), [SciPy, appariement un-à-un](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html). Les choix de filtres, trajectoires et critères sont propres à ce prototype du projet.

## Expérience complémentaire sur les limites

Le [lot de limites](LIMITES-DETECTEUR.md), plan publié `6f3e6c5`, réutilise ce moteur sans changement sur 120 séquences fictives et cinq nouvelles graines. Les quatre lots ne satisfont pas la définition de la suite initiale complète : les deux verdicts natifs restent faux, et l’agrégation distincte est descriptive. Les cas non alignés sont des stress hors domaine, sans exécution du recalage ; les étoiles entraînées peuvent devenir des faux candidats. Le contrat initial et ses seuils restent inchangés. Le [parcours pédagogique](DEMARRER-DE-ZERO.md#13-bis-mission--trouver-les-limites-du-chercheur) explique la différence avec des images et un GIF.

Le [lot recalage puis recherche](RECALAGE-MOBILES-SYNTHETIQUES.md), plan publié `286af43`, relie les fonctions existantes dans une recette distincte, sans modifier `moving.py` ou ses paramètres. Les mêmes détections sont recherchées avant/après transformation rigide des coordonnées, sans rééchantillonnage des FITS. La vérité n’est lue qu’après les modèles et candidats ; une séquence refusée n’a pas de bilan après disponible. Les critères exploratoires de cette expérience restent non tous satisfaits et ne remplacent pas le verdict de la suite initiale de ce contrat.
