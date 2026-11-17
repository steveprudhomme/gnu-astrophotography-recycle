# Images Seestar réelles — CC0 1.0 Universal

À la demande et avec l'autorisation explicite de Steve Prud'Homme, mainteneur et fournisseur des observations, reçue puis réaffirmée le **17 novembre 2026**, les cinq fichiers suivants sont mis à disposition sous **CC0 1.0 Universal**. L'autorisation réaffirmée couvre le GIF du pilote et ses illustrations, en plus des deux PNG initiaux.

| Fichier couvert | Nature | SHA-256 du média publié |
|---|---|---|
| [seestar-serie-cc0.png](seestar-serie-cc0.png) | Montage de huit poses réelles Seestar S50 | `303a644bbde534637ba825106a73af51133d92cec4a47d0978bfe9c6f50e4b91` |
| [seestar-pose-01-cc0.png](seestar-pose-01-cc0.png) | Première pose de cette série, rendu gris | `4729c99aebfb0b7fa0be95bd7a4c5bd5a2dd91fa904307a1fa2a4b5ecd675459` |
| [seestar-pilote-cc0.gif](seestar-pilote-cc0.gif) | Huit poses réelles, brut et affichage aligné ; 600 ms par vue, boucle | `cbc427e3a9c274ce1c3c7715387a75d8dd795c9fab70da1ab7c86424cae614f3` |
| [seestar-pilote-premiere-vue-cc0.png](seestar-pilote-premiere-vue-cc0.png) | Première vue de cette animation réelle | `2360751cf8e3938376ed7cd6873168da0259f3b2e6ab2ea326bcc6175154ddf5` |
| [seestar-pilote-controles-cc0.png](seestar-pilote-controles-cc0.png) | Graphique réel des étoiles réservées au contrôle du recalage | `bc403f43705fbc75e71cd9455bdf430900fb72c400cedf33d29854099b83dd4f` |

Consulter le [résumé officiel CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) et son [texte juridique](https://creativecommons.org/publicdomain/zero/1.0/legalcode). CC0 est la dédicace Creative Commons au domaine public, dans la mesure permise par le droit applicable. Cette notice précise le périmètre des images ; elle ne modifie pas la licence GPL-3.0-or-later du code ni le régime des autres fichiers du dépôt.

## Provenance et rendu

Ces images proviennent de véritables poses Seestar S50 fournies par le mainteneur, copiées localement et vérifiées par empreintes contre l’inventaire et les sources avant/après copie. Elles ne sont pas synthétiques et ne sont pas des captures d’écran.

Le rendu applique une moyenne de blocs 2×2, puis un affichage gris avec étirement asinh. Les bornes sont calculées aux percentiles 5 et 99,7 de la première pose et partagées par les huit vues. Le fichier FITS n’est pas réécrit ; ce rendu n’est ni un dématriçage ou une calibration scientifique, ni une mesure photométrique. Les libellés ont été ajoutés pour l’apprentissage.

Les PNG sont réencodés en RGB sans EXIF, texte ou métadonnées d’image héritées. Aucun en-tête FITS, chemin privé, date d’observation ou coordonnée terrestre n’est fourni avec eux. Le champ d’étoiles est réel : la diffusion des pixels célestes est autorisée, sans promesse d’anonymisation du champ.

Le GIF et ses deux illustrations viennent du [pilote du lot 16](../../PILOTE-MOBILES-SEESTAR.md), reproduit depuis le commit `80ada2e` sur les mêmes copies vérifiées. Le [plan du lot 17](../../../ROADMAP.md#lot-17--diffuser-le-gif-et-les-illustrations-réels-autorisés-sous-cc0) précède le mode de diffusion. À gauche, les poses brutes ; à droite, l'affichage aligné par les sept modèles acceptés. L'interpolation linéaire concerne seulement cet affichage : elle ne sert pas à mesurer les positions. La cadence de 600 ms par vue est artificielle, sans vitesse physique déduite. Le résultat reste **zéro candidat aux seuils prévus**, sans preuve d'absence de tout mobile. Le graphique représente les résidus et effectifs des véritables étoiles de contrôle, pas des valeurs inventées.

Le GIF n'inclut ni commentaire, EXIF, XMP ou profil hérité ; il conserve les informations nécessaires à ses dimensions, couleurs, huit vues, durées et boucle. Les deux PNG initiaux sont inchangés. Les journaux privés d'export, empreintes des FITS et modèles complets ne sont pas joints aux médias publics.

Les FITS exacts, en-têtes et rapports privés restent dans les répertoires ignorés. Leur diffusion ne fait pas partie de ces cinq médias documentaires. Pour le contexte et les limites, lire [la préparation de série](../../PREPARER-SERIE-SEESTAR.md) et [le tutoriel de diffusion](../../TUTORIEL.md#23-publier-les-exemples-réels-autorisés-sous-cc0).
