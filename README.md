# GNU Astrophotography Recycle

**Donner une seconde vie scientifique aux archives du Seestar S50.**

[Dépôt public et suivi du projet](https://github.com/steveprudhomme/gnu-astrophotography-recycle).

Projet de logiciel **libre, à distribution gratuite**, sous **GNU GPL version 3 ou ultérieure** ([texte intégral](COPYING), [application au projet](LICENSE-NOTICE.md)). La GPL permet aussi la redistribution commerciale.

**Statut : Alpha 0.3 — inventaire, séances candidates et diagnostic temporel depuis les sources. Les mesures astronomiques et la distribution portable restent à développer.**

## Mission

Permettre aux astronomes amateurs de réexaminer leurs poses FITS individuelles du ZWO Seestar S50 pour rechercher des objets mobiles et des variations stellaires. Chaque mesure devra être traçable, accompagnée de ses incertitudes et reproductible. Les originaux resteront intacts ; le traitement scientifique s’effectuera localement, sur Windows 11.

Le projet est indépendant et ne revendique aucune affiliation officielle au projet GNU, à ZWO, à l’AAVSO ou au Minor Planet Center.

## Fonctionnalités prévues

| Étape | Résultat attendu | État |
|---|---|---|
| Inventaire FITS | SHA-256, chaque HDU, anomalies, CSV/JSON et synthèse Markdown/SVG | Première version disponible, phase 1 |
| Séances candidates | Regroupement depuis un manifeste local, exclusions et résumés CSV/JSON/SVG | Première version disponible, phase 1 |
| Diagnostic temporel | Forme des dates, déclarations, cadence et anomalies depuis un manifeste local | Disponible ; ne certifie pas l’horloge, phase 2 |
| Alignement et contrôle qualité | Rotation, dérive, WCS et horodatages vérifiés | À développer, phase 2 |
| Objets mobiles | Trajectoires candidates, vitesses et GIF | Recherche, phase 3 |
| Photométrie différentielle | Courbes de lumière et budget d’incertitude | Recherche, phase 4 |
| Passerelles scientifiques | Exports AAVSO, MPC ADES et ALCDEF validés localement | Phase 5 |

## Limites

Une détection n’est pas une découverte confirmée. Un GIF ne constitue pas une mesure scientifique. La qualité des archives, des calibrations, des heures et des catalogues détermine les usages possibles. Le vert Bayer n’est pas automatiquement une mesure Johnson V. Aucun format d’export ni aucune acceptation par un organisme n’est garanti à ce stade. Aucune soumission automatique n’est prévue.

## Démarrer

Les documents sont lisibles immédiatement. L’inventaire a été testé avec Python 3.13.6, Astropy 7.2.0 et NumPy 2.4.1 sur Windows. Le lanceur `scripts/gar-inventory.bat` utilise votre Python ou l’environnement `.venv` du projet ; voir [INSTALL.md](INSTALL.md). Il n’est pas encore autonome.

1. Lire le [dossier de lancement](docs/DOSSIER-LANCEMENT.md).
2. Suivre la [feuille de route](ROADMAP.md) et le [protocole pilote](docs/VALIDATION-PILOTE.md).
3. Consulter [INSTALL.md](INSTALL.md) et [CONTRIBUTING.md](CONTRIBUTING.md).
4. Suivre le [tutoriel illustré](docs/TUTORIEL.md) pour produire un exemple synthétique et lire les rapports.

Depuis PowerShell, à la racine du projet, avec les dépendances installées :

```powershell
.\scripts\gar-inventory.bat "D:\ArchivesFITS" --output ".\local\premier-inventaire"
```

Choisir une sortie nouvelle et extérieure aux archives. Le calcul SHA-256 lit tous les fichiers et peut prendre du temps. Les rapports contiennent potentiellement des informations privées ; ils restent locaux. Voir le [contrat des sorties et codes de retour](docs/CONTRAT-INVENTAIRE.md).

Pour regrouper un manifeste déjà présent sur l’ordinateur, sans rouvrir les FITS :

```powershell
.\scripts\gar-sessions.bat ".\local\premier-inventaire\manifest.json" --output ".\local\seances-01"
```

Les dates déclarées et les configurations restent séparées ; les interruptions de plus de 30 minutes coupent un groupe par défaut. Les copies, empilements et dates inutilisables sont expliqués dans les exclusions. Le [contrat des séances](docs/CONTRAT-SEANCES.md) précise les limites et le code de retour `2`, qui peut signaler des exclusions attendues. Aucun fichier n’est déplacé. Choisir la destination locale indiquée pour ne rien écrire sur le support externe des observations.

Pour diagnostiquer les horodatages du même manifeste, sans rouvrir les observations :

```powershell
.\scripts\gar-timing.bat ".\local\premier-inventaire\manifest.json" --output ".\local\horodatages-01"
```

Le [diagnostic temporel](docs/CONTRAT-HORODATAGES.md) sépare résolution écrite et exactitude. Aucun milieu de pose n’est calculé ; les heures restent non qualifiées sans preuve indépendante. Le code `2` après production des rapports rappelle cette limite, même si la cadence ne présente aucune anomalie.

Les FITS personnels, coordonnées d’observation et paramètres locaux ne doivent pas être joints aux contributions publiques. Voir la [politique des données](docs/DONNEES.md).

## Contribuer et vérifier

Proposer un objectif, produire un changement limité, ouvrir une proposition de fusion, attendre la revue et itérer. Toute évolution scientifique doit préciser ses hypothèses, ses références et ses critères de validation. Les décisions sont consignées publiquement ; les données privées restent locales.

Voir [gouvernance](GOVERNANCE.md), [licences tierces](docs/LICENCES-TIERCES.md) et [sources](docs/SOURCES.md).
