# Les seize vraies poses des séries 3 et 4

Ces observations Seestar S50 sont fournies par Steve Prud’Homme.
Elles visent le champ d’IC 342, le 20 septembre 2025 selon les dates des en-têtes.
Chaque pose dure 10 secondes. Chaque image mesure 1080 × 1920 pixels natifs.
Le fichier [manifest.json](manifest.json) donne les noms d’origine, les dates, les tailles et les empreintes SHA-256.
Les seize FITS occupent ensemble **66 447 360 octets**.

Les noms publics courts vont de `S03-01.fit` à `S03-08.fit`, puis de `S04-01.fit` à `S04-08.fit`.
Le renommage des copies ne change aucun octet du contenu FITS.
Les dates sont déclarées par l’appareil ; elles ne sont pas qualifiées par une horloge indépendante.

La référence stellaire CSV garde les fins de ligne LF du dépôt.
Son empreinte publiée a été corrigée après détection d’une différence LF/CRLF dans le premier environnement Windows.
Les positions stellaires et les pixels FITS n’ont pas changé.
La [nouvelle preuve de reproduction](../../../journal/reproduction-verification.json) compare le CSV aux octets du commit Git.

## Droits et autorisation

Le 18 novembre 2026, le fournisseur a expressément autorisé la publication de ces seize FITS et de leurs en-têtes.
Cela rend publics leurs dates, coordonnées célestes et coordonnées terrestres, y compris le site inscrit dans les fichiers.
Cette autorisation ne couvre pas ses autres archives.
Les fichiers de ce dossier créés par le projet sont dédiés au domaine public sous **CC0-1.0**.
Voir le [texte juridique CC0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.fr).
Le code reste sous GPL-3.0-or-later. Les catalogues orbitaux tiers ne deviennent pas CC0.

## Ce que contiennent les autres fichiers

| Fichier | Rôle | Limite |
|---|---|---|
| `calibration.json` | Carte WCS reliant les pixels de référence aux directions célestes | Étalonnage fourni ; erreur absolue complète non établie |
| `reference-stars.csv` | 696 centres d’étoiles issus d’un empilement de référence | Les centres sont fournis ; le FITS empilé n’est pas publié |
| `review-selection.json` | Quatre lignes choisies à l’œil avant le nouveau rapprochement orbital | Reproduction guidée ; aucune sélection aveugle |
| `orbital-provenance.json` | Date, service et empreinte du catalogue historique | Le catalogue brut doit être obtenu auprès du service |
| `expected-results.json` | Réponses historiques pour la vérification finale | Ne sert pas au classement des orbites |

Le [tutoriel détaillé](../../../docs/REPRODUIRE-SATELLITES.md) explique chaque étape.
Il recalcule les alignements et les rapprochements, avec cet étalonnage fourni.
Il ne reconstruit pas indépendamment la première solution astrométrique à partir d’un catalogue d’étoiles.
Les heures, le site réel exact et les orbites restent des sources d’incertitude.
