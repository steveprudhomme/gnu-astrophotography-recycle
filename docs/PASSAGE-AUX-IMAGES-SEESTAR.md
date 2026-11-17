# Quand essayer les images du Seestar S50 ?

**Le premier pilote sur huit poses Seestar réelles est maintenant terminé : sept alignements acceptés, recherche achevée avec zéro candidat, GIF réel avant/après publié sous CC0.** Le [lot 15](PREPARER-SERIE-SEESTAR.md) a préparé les copies et le [lot 16](PILOTE-MOBILES-SEESTAR.md) les a analysées avec une voie d'intensité adaptée et des contrôles réservés. Ce premier essai ne qualifie pas les performances de détection ni les mesures scientifiques.

![Trois jalons pour préparer le pilote réel puis les mesures scientifiques](images/passage-seestar-pilote.png)

*Schéma conceptuel, pas une mesure ou une capture d'écran. Les deux premières étapes ont maintenant été réalisées pour huit poses ; la qualification des mesures reste ouverte.*

## Ce qui utilise déjà les observations

Le projet a déjà utilisé des données Seestar pour l’inventaire, les diagnostics de métadonnées, le recalage et les comparaisons sur étoiles, avec rapports privés et fichiers sources préservés. L’échantillon antérieur de **trois poses et un empilement** reste conservé ; il est complété par une nouvelle série de **huit poses individuelles**. Ces préparations ne constituent pas une recherche validée d’objets mobiles ; les contrôles précédents sont décrits dans le [protocole pilote](VALIDATION-PILOTE.md).

Le lot 14 de répartition des contrôles n’avait lu que le manifeste et les documents. Le lot 15 a ensuite utilisé l’autorisation de lecture du support pour les huit copies sélectionnées ; les audits et aperçus ont travaillé sur ces copies, sans écrire sur le support.

## Deux étapes concrètes pour arriver au premier essai réel

| Étape | Travail | Condition pour avancer |
|---|---|---|
| Préparer la série — fait | Huit poses sélectionnées depuis le manifeste, copiées et contrôlées localement | Identité des octets et configuration observée vérifiées ; qualité scientifique non déduite |
| Pilote exploratoire réel — fait | Voie 2×2 d'intensité, alignement et recherche, GIF avant/après | Sept modèles acceptés ; zéro candidat aux seuils prévus, rapports privés et copies intactes |

La série préparée a permis ce premier essai sans accès USB supplémentaire. Aucun mobile n'a été détecté par cette recherche ; ce résultat ne démontre ni absence d'objet ni sensibilité suffisante pour tous les mobiles possibles.

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

La commande pour images synthétiques **ne doit pas recevoir de véritables observations réétiquetées**. Le nouveau chemin d'analyse réel est distinct, avec provenance et limites adaptées ; aucun `GARSYNTH` ou temps fictif n'est ajouté aux fichiers Seestar. Le [bilan de contrôle spatial](CONTROLES-SPATIAUX.md) éclaire le recalage, mais ne valide pas Bayer, le bruit, les calibrations ou l'horloge du télescope.

## Ce que l’on décide après ce lot

Conserver le premier essai et ses seuils. Le [lot 18](INJECTIONS-SEESTAR.md) a mesuré une récupération conditionnelle de 10/36 ajouts sur le fond des copies, avec témoin naturel inchangé. Le [lot 19](DIAGNOSTIC-MANQUES.md) explique maintenant l'étape limitante enregistrée pour les 26 manques : neuf hors vitesse et 17 avec moins de cinq images contenant une position proche dès les détections, aux deux voisinages. Il ne prouve pas une cause physique unique. Une future investigation des critères internes du détecteur ou d'autres profils devra être préenregistrée et vérifiée sur un jeu distinct, sans abaisser automatiquement les seuils sur ces résultats. Aucune nouvelle archive n'est consultée ; rapports, distances, dérivés, coordonnées, FITS et en-têtes restent locaux, avec les cinq médias réels autorisés toujours publiés sous CC0.

Le mainteneur a réaffirmé son autorisation de publier les images réelles comme exemples publics sous [CC0 1.0](images/reels/LICENCE.md), y compris le GIF du pilote et ses illustrations. Elles figurent dans le tutoriel, sans en-têtes ou métadonnées privées. Cette exception n’est pas une diffusion des archives FITS ou rapports. L’autorisation USB reste exclusivement en lecture pour les outils du projet ; aucun fichier source n’a été réécrit.
