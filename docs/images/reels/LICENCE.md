# Images Seestar réelles — CC0 1.0 Universal

À la demande et avec l’autorisation explicite de Steve Prud’Homme, mainteneur et fournisseur des observations, reçue le **17 novembre 2026**, les deux fichiers suivants sont mis à disposition sous **CC0 1.0 Universal** :

| Fichier couvert | Nature | SHA-256 du PNG publié |
|---|---|---|
| [seestar-serie-cc0.png](seestar-serie-cc0.png) | Montage de huit poses réelles Seestar S50 | `303a644bbde534637ba825106a73af51133d92cec4a47d0978bfe9c6f50e4b91` |
| [seestar-pose-01-cc0.png](seestar-pose-01-cc0.png) | Première pose de cette série, rendu gris | `4729c99aebfb0b7fa0be95bd7a4c5bd5a2dd91fa904307a1fa2a4b5ecd675459` |

Consulter le [résumé officiel CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) et son [texte juridique](https://creativecommons.org/publicdomain/zero/1.0/legalcode). CC0 est la dédicace Creative Commons au domaine public, dans la mesure permise par le droit applicable. Cette notice précise le périmètre des images ; elle ne modifie pas la licence GPL-3.0-or-later du code ni le régime des autres fichiers du dépôt.

## Provenance et rendu

Ces images proviennent de véritables poses Seestar S50 fournies par le mainteneur, copiées localement et vérifiées par empreintes contre l’inventaire et les sources avant/après copie. Elles ne sont pas synthétiques et ne sont pas des captures d’écran.

Le rendu applique une moyenne de blocs 2×2, puis un affichage gris avec étirement asinh. Les bornes sont calculées aux percentiles 5 et 99,7 de la première pose et partagées par les huit vues. Le fichier FITS n’est pas réécrit ; ce rendu n’est ni un dématriçage ou une calibration scientifique, ni une mesure photométrique. Les libellés ont été ajoutés pour l’apprentissage.

Les PNG sont réencodés en RGB sans EXIF, texte ou métadonnées d’image héritées. Aucun en-tête FITS, chemin privé, date d’observation ou coordonnée terrestre n’est fourni avec eux. Le champ d’étoiles est réel : la diffusion des pixels célestes est autorisée, sans promesse d’anonymisation du champ.

Les FITS exacts, en-têtes et rapports privés restent dans les répertoires ignorés. Leur diffusion ne fait pas partie de ces deux fichiers documentaires. Pour le contexte et les limites, lire [la préparation de série](../../PREPARER-SERIE-SEESTAR.md).
