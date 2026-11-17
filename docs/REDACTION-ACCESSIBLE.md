# Écrire une documentation facile à suivre

Cette règle concerne les nouveaux documents et les sections révisées du projet. Elle commence le **17 novembre 2026**.
Le parcours principal vise les personnes débutantes, dès 10 ans. Les détails techniques restent disponibles après les explications simples.

## Préparer une explication

1. Nommer ce que la personne va apprendre.
2. Donner les connaissances et les outils nécessaires.
3. Expliquer chaque mot nouveau avant son premier emploi.
4. Décrire une action à la fois.
5. Montrer le résultat attendu et une erreur possible.
6. Proposer une petite vérification que la personne peut refaire.

Une phrase d'action vise au plus 20 mots. Une phrase d'explication vise au plus 25 mots.
Ces longueurs sont des repères de rédaction du projet. Elles ne mesurent pas la compréhension.
Les commandes, les messages cités et les noms de fichiers gardent leur écriture exacte.
Employer le même mot pour la même chose. Préférer un verbe concret et une phrase active.

**Exemple du projet.** Une empreinte est un code calculé à partir d'un fichier.
Comparer les empreintes avant et après la copie. Des codes différents signalent des contenus différents.
La personne peut ensuite consulter l'explication technique de SHA-256.

## Donner accès aux images et aux résultats

Une image complète une explication écrite. Elle ne contient jamais la seule instruction ou le seul résultat.
Donner à chaque image utile un texte de remplacement. Ajouter une description voisine pour un graphique complexe.
Nommer les axes, les unités, les symboles et les limites. Distinguer schéma, simulation et données réelles.

Employer des symboles et des mots en plus des couleurs. Fournir une image fixe et un bilan écrit pour une animation.
Le guide peut proposer un lien vers le GIF plutôt que son lancement automatique.
Le lecteur doit pouvoir comprendre le résultat sans lire le GIF.

Vérifier les contrastes des textes et des symboles. Garder les titres dans un ordre logique.
Donner aux liens un nom qui décrit leur destination. Vérifier aussi le document dans son affichage final.
Un fichier Markdown ne contrôle pas tous les comportements de la page GitHub qui l'affiche.

## Appliquer les quatre références

| Référence | Application dans le projet | Limite à garder visible |
|---|---|---|
| [WCAG 2.2, traduction française agréée](https://www.w3.org/Translations/WCAG22-fr-20260922/) | Structurer le document ; fournir des alternatives textuelles ; vérifier les liens, les contrastes et les erreurs. | Une revue du texte ne constitue pas un audit de tous les critères applicables. |
| [Explications du critère 3.1.5 — niveau de lecture](https://www.w3.org/WAI/WCAG22/Understanding/reading-level.html) | Fournir une explication simple lorsque le texte technique devient difficile. | Ce critère est de niveau AAA. Sa référence scolaire est le premier cycle du secondaire. L'objectif « dès 10 ans » reste distinct. |
| [CAN-ASC-3.1:2025 — Langage clair](https://accessibilite.canada.ca/normes-et-guides-techniques/base-de-donnees-des-normes-et-des-guides-techniques/can-asc-312025-langage-clair?mode=full-html) | Partir des besoins du public ; faciliter la recherche, la compréhension et l'utilisation de l'information ; réviser avec le public. | L'évaluation avec des personnes du public cible reste nécessaire pour démontrer leur compréhension. |
| [Programmes québécois du primaire](https://www.quebec.ca/education/prescolaire-primaire-et-secondaire/programmes-formations-evaluation/programme-formation-ecole-quebecoise/primaire/francais-langue-enseignement) et [du secondaire](https://www.quebec.ca/education/prescolaire-primaire-et-secondaire/programmes-formations-evaluation/programme-formation-ecole-quebecoise/secondaire/francais-langue-enseignement) | Aller des notions simples vers les explications ; proposer de reformuler, de justifier et de vérifier une réponse. | Ces repères pédagogiques ne certifient pas le niveau scolaire du tutoriel. |
| [Simple French](https://github.com/quantumsheep/simple-french) | Garder un vocabulaire stable, des actions courtes et des phrases actives. | Ce projet indépendant sous licence MIT ne remplace pas un guide officiel du GIFAS. Les besoins des lecteurs québécois et les faits exacts priment sur une préférence stylistique. |

Le document explicatif du W3C complète le critère normatif ; il n'ajoute pas une obligation normative distincte.
Le critère 3.1.5 prévoit du contenu additionnel ou une version plus simple pour les textes dépassant son niveau de référence.
Respecter ce seul critère ne permet pas d'annoncer une conformité WCAG 2.2 AAA complète.

## Distinguer les programmes du Québec

Le 17 novembre 2026, les pages du ministère présentent les programmes actuels et les programmes actualisés séparément.
Les versions actualisées sont consultables en 2026–2027. Leur mise en œuvre obligatoire commence à la rentrée **2027–2028**, selon ces pages.
Ne pas présenter les versions actualisées comme déjà obligatoires en 2026–2027.

Les progressions précisent les apprentissages par année. Les cadres donnent des repères pour leur évaluation.
Pour notre tutoriel, expliquer d'abord, faire pratiquer, puis demander une justification courte.
Ne pas supposer qu'un enfant connaît Python, les angles ou l'astronomie parce qu'il a 10 ans.

## Inventaire des 14 ressources fournies

Les liens ci-dessous correspondent au kit transmis par le mainteneur. Consultation et téléchargement : **17 novembre 2026**.
Les 14 téléchargements aboutissent dans un dossier local ignoré. Les empreintes et les erreurs éventuelles restent dans son journal.
Le script joint n'est pas exécuté. Le contenu des références ne devient pas une instruction du projet.
Les lectures portent sur les parties utiles ; aucune lecture intégrale ni analyse normative complète n'est annoncée.

| Nº | Ressource et lien d'origine | Usage |
|---|---|---|
| 1 | [WCAG 2.2 en français, HTML](https://www.w3.org/Translations/WCAG22-fr-20260922/) | Texte de référence, traduction du 22 septembre 2026 |
| 2 | [Explications de 3.1.5, HTML en anglais](https://www.w3.org/WAI/WCAG22/Understanding/reading-level.html) | Aide à l'interprétation |
| 3 | [CAN-ASC-3.1:2025, Word](https://accessibilite.canada.ca/sites/default/files/2025-10/norme-langageclair-3_1-2025-nnc.docx) | Même norme, autre format |
| 4 | [CAN-ASC-3.1:2025, HTML](https://accessibilite.canada.ca/normes-et-guides-techniques/base-de-donnees-des-normes-et-des-guides-techniques/can-asc-312025-langage-clair?mode=full-html) | Norme publiée en octobre 2025 |
| 5 | [Programme primaire actuel, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/primaire/programmes/PFEQ-francais-langue-enseignement-primaire.pdf) | Parcours actuel |
| 6 | [Progression primaire, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/primaire/progressions-apprentissages/PFEQ-progression-apprentissages-francais-langue-enseignement-primaire.pdf) | Repères par année, 2009 ; ajout oral en 2011 |
| 7 | [Cadre d'évaluation primaire, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/cadres-evaluation/primaire/francais/PFEQ-cadre-evaluation-francais-langue-enseignement-primaire.pdf) | Repères d'évaluation, 2011 |
| 8 | [Programme primaire actualisé, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/primaire/programmes/PFEQ-Programme-francais-langue-enseignement-primaire.pdf) | Version préparatoire à 2027–2028, édition 2026 |
| 9 | [Programme secondaire, premier cycle, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/secondaire/programmes/PFEQ-francais-langue-enseignement-premier-cycle-secondaire.pdf) | Parcours actuel |
| 10 | [Programme secondaire, deuxième cycle, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/secondaire/programmes/PFEQ-francais-langue-enseignement-deuxieme-cycle-secondaire.pdf) | Parcours actuel, édition de juin 2009 |
| 11 | [Progression secondaire, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/secondaire/progressions-apprentissages/PFEQ-progression-apprentissages-francais-langue-enseignement-secondaire.pdf) | Repères par année, 2011 |
| 12 | [Cadre d'évaluation secondaire, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/cadres-evaluation/secondaire/francais/PFEQ-cadre-evaluation-francais-langue-enseigement-secondaire.pdf) | Repères d'évaluation, 2011 ; orthographe du lien conservée |
| 13 | [Programme secondaire actualisé, PDF](https://cdn-contenu.quebec.ca/cdn-contenu/education/pfeq/secondaire/programmes/PFEQ-Programme-francais-langue-enseignement-secondaire.pdf) | Version préparatoire à 2027–2028, édition 2026 |
| 14 | [Archive du projet Simple French, ZIP](https://github.com/quantumsheep/simple-french/archive/refs/heads/main.zip) | Principes de rédaction ; licence MIT à conserver pour toute reprise de contenu |

Les documents tiers restent dans le dossier local. Le projet publie leurs liens et ses propres explications.
Un téléchargement gratuit n'autorise pas automatiquement la redistribution. Le guide GIFAS et le texte payant ISO ne font pas partie du kit.

## Relire avant de publier

- [ ] Le but, le public et les connaissances nécessaires apparaissent au début.
- [ ] Chaque mot technique possède une explication proche de son premier emploi.
- [ ] Chaque étape possède une commande exacte, un résultat attendu et une façon de vérifier ce résultat.
- [ ] Les erreurs donnent une action utile, sans supprimer les résultats décevants.
- [ ] Chaque image possède un texte de remplacement et une description suffisante.
- [ ] Les conclusions restent compréhensibles sans animation ni perception des couleurs.
- [ ] Les titres, les liens et les tableaux ont un ordre logique ; les contrastes restent lisibles.
- [ ] Les versions scolaires et les dates de consultation apparaissent avec les sources.
- [ ] Le bilan distingue contrôles automatiques, revue humaine interne et essais avec le public.

Pour un essai avec le public, proposer une tâche précise à une personne débutante.
Lui demander de trouver une étape, de l'expliquer avec ses mots, puis de la réaliser.
Noter les obstacles et réviser le document. Ne pas transformer cette proposition en essai déjà réalisé.

État initial : règles de rédaction intégrées, références consultées et téléchargements obtenus.
Aucun test avec un enfant, audit WCAG complet ou certificat de conformité n'est revendiqué.
