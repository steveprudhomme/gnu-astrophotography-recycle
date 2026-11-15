# Tutoriel illustré — construire et utiliser l’inventaire

## 1. Planifier avant de coder

Le premier lot transforme le relevé exploratoire en une commande réutilisable. Les sous-étapes P1-A à P1-I sont consignées dans [ROADMAP.md](../ROADMAP.md). Le plan est enregistré dans un commit avant l’implémentation. Les règles de suivi figurent dans [AGENTS.md](../AGENTS.md).

![Schéma du traitement prévu, des archives en lecture seule aux rapports séparés](images/plan-inventaire.svg)

*Schéma d’architecture, pas une capture d’écran ni un résultat scientifique.*

Le futur inventaire parcourra les fichiers, calculera leurs empreintes, relèvera chaque HDU et produira des rapports dans un dossier distinct. Les heures resteront brutes tant que leur convention n’est pas validée. Les données personnelles ne font pas partie de ce tutoriel public.

## 2. Installation et exécution

À compléter après l’implémentation et la vérification des commandes. Ne pas supposer qu’un exécutable ou un paquet portable est déjà disponible.

## 3. Comprendre les résultats

À compléter avec un exemple synthétique réellement produit par le module et son illustration. Les résultats de l’archive personnelle restent locaux.

## 4. Vérifier et connaître les limites

À compléter avec les tests exécutés, la vérification du pilote et les limites observées. L’inventaire ne prouve ni l’exactitude de l’horloge, ni la validité d’une WCS, ni la qualité photométrique des pixels.
