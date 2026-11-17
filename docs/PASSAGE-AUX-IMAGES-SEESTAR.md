# Quand essayer les images du Seestar S50 ?

**Le prochain jalon proposé est un essai exploratoire sur une série réelle copiée localement.** Il n’est pas nécessaire d’attendre la photométrie, les exports scientifiques ou l’application portable. Nous devons d’abord disposer d’une série compatible et adapter explicitement la recette aux images réelles. Aucune date fiable ne peut être annoncée avant cette vérification ; le nombre de tests logiciels n’est pas une date de disponibilité instrumentale.

![Trois jalons pour préparer le pilote réel puis les mesures scientifiques](images/passage-seestar-pilote.png)

*Schéma conceptuel, pas une mesure ou une capture d’écran. La préparation de série est le prochain travail proposé ; l’essai réel dépend de son résultat.*

## Ce qui utilise déjà les observations

Le projet a déjà utilisé des données Seestar pour l’inventaire, les diagnostics de métadonnées, le recalage et les comparaisons sur étoiles, avec rapports privés et fichiers sources préservés. L’échantillon de copies locales documenté comprend **trois poses individuelles et un empilement**. Ces essais ne constituent pas une recherche validée d’objets mobiles sur une série réelle ; ils sont décrits dans le [protocole pilote](VALIDATION-PILOTE.md).

Le lot de répartition des contrôles relit uniquement le manifeste local et la documentation pour cette préparation. Il n’ouvre aucun FITS réel et n’accède pas à la clé USB.

## Deux étapes concrètes pour arriver au premier essai réel

| Étape | Travail | Condition pour avancer |
|---|---|---|
| Prochain lot proposé : préparer la série | Examiner les manifestes locaux existants, identifier une séance et les copies disponibles, relever les manques | Série cohérente, accessible localement et avec provenance vérifiée ; sinon liste précise des copies à préparer |
| Pilote exploratoire réel | Adapter les entrées réelles, la voie de détection et l’ordre des images, puis exécuter et revoir les candidats | Rapports privés, originaux inchangés, alignement contrôlé et limites explicites ; un résultat sans candidat reste utile |

La première étape peut commencer après le lot de contrôles spatiaux, même si elle conclut que des données manquent. Le démarrage de la seconde dépend de la série et du traitement compatibles, pas d’une promesse de succès sur un objet astronomique.

## Série à préparer

Pour un premier essai, viser **au moins huit poses individuelles successives du même champ**, avec dimensions, mode et configuration compatibles, plutôt qu’un assemblage de belles images ou de seuls empilements. Huit est ici une cible de départ du projet, pas une norme scientifique. Le moteur d’association actuel exige au moins cinq détections temporelles pour former une trajectoire, et la recette fictive travaille avec huit images ; trois poses ne suffisent donc pas à reproduire cette chaîne.

Il faudra vérifier sur les copies locales :

- présence de toutes les poses sélectionnées, empreintes et intégrité ; doublons et images exclues conservés dans le rapport ;
- cohérence du champ et du repère, nombre et couverture des étoiles d’ajustement et de contrôle ;
- nature réelle des pixels : mosaïque Bayer, mono ou RGB, saturation et traitements déjà appliqués ; définir la voie de détection et le retour aux coordonnées natives ;
- ordre des prises de vue et cadences déclarées, interruptions, heures ambiguës et exclusions, sans inventer une heure de milieu de pose ;
- lecture des candidats en images successives, artefacts et objets connus, avant toute interprétation astronomique.

L’inventaire local peut indiquer qu’une séance plus complète existe dans les archives ; il ne prouve pas que ses fichiers soient déjà copiés et utilisables. Aucune source historique sur USB ne doit être ouverte automatiquement à partir d’un chemin mémorisé. Une éventuelle préparation de nouvelles copies doit être prévue dans un lot distinct, avec destination locale neuve et support source strictement en lecture seule, sans cache ou rapport sur celui-ci.

## Essai exploratoire et mesure scientifique sont deux usages différents

| Usage | Ce que l’on pourra examiner | Limites à garder |
|---|---|---|
| Exploration locale | Déplacements dans les images, candidats, faux signaux, positions en pixels et ordre de la série | Aucun candidat garanti ; origine du signal à revoir humainement |
| Mesures de vitesse et positions célestes destinées à la science | Astrométrie et chronologie qualifiées, incertitudes, calibration et traçabilité | Preuves temporelles indépendantes et budget d’erreur encore nécessaires |

Un premier essai peut exprimer un déplacement en pixels par image ou selon des intervalles **déclarés**, avec les réserves correspondantes. Il ne doit pas annoncer une vitesse physique ou une date UTC exacte à partir d’une horloge non qualifiée. La [campagne temporelle](CAMPAGNE-TEMPORELLE.md) reste nécessaire aux usages exigeant cette précision ; elle n’est pas remplacée par les essais fictifs.

La commande actuelle pour images synthétiques **ne doit pas recevoir de véritables observations réétiquetées**. Il faudra un chemin d’analyse réel distinct, avec provenance et limites adaptées ; ne pas ajouter `GARSYNTH` ou des temps fictifs aux fichiers Seestar pour contourner les protections. Le [bilan de contrôle spatial](CONTROLES-SPATIAUX.md) éclaire le recalage, mais ne valide pas Bayer, le bruit, les calibrations ou l’horloge du télescope.

## Ce que l’on décide après ce lot

Préparer la revue de faisabilité de la série réelle comme prochain lot, avec son plan avant code. Si des copies suffisantes sont présentes et compatibles, planifier le pilote exploratoire. Sinon, préciser ce qui manque et comment obtenir des copies locales en préservant les archives. Les rapports, coordonnées et images personnelles restent sous `local/` ; aucun envoi public d’observations n’est implicite.

L’autorisation de lecture seule USB demeure respectée. Le travail de contrôle spatial et ce document n’en ont pas fait usage.
