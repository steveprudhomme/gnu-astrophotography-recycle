# Installation et utilisation sur Windows 11

## Ce qui fonctionne aujourd’hui

Cette version contient la documentation de lancement. Ouvrir `README.md` avec un lecteur Markdown ou un éditeur de texte. Aucun paquet à installer pour la lire. Aucun programme de traitement des FITS n’est livré.

## Environnement de développement prévu

Après la sélection d’une combinaison Python/Astropy/Photutils vérifiée sous Windows 11 x64 :

1. Installer Python pour l’utilisateur courant, sans installation système ni droits administrateur.
2. Créer un environnement virtuel dans le dossier de travail.
3. Installer les versions verrouillées et leurs dépendances à partir du futur fichier de verrouillage avec empreintes.
4. Exécuter les contrôles automatisés sur des images synthétiques ; les instructions exactes seront publiées avec le premier module exécutable.
5. Placer les archives originales en dehors du dépôt ; choisir un autre dossier pour les sorties.

Les versions et commandes d’installation applicative ne sont pas encore publiées : aucun `requirements.txt`, paquet PyPI ou exécutable ne doit être supposé disponible.

## Distribution portable prévue

Une archive autonome devra embarquer un interpréteur redistribuable, les bibliothèques, leurs avis de licence et les moyens d’obtenir le code source correspondant. Les lanceurs `.bat` utiliseront des chemins relatifs et des arguments correctement cités. Rien ne devra écrire dans les originaux ou exiger un service système.

Validation obligatoire sur un compte standard Windows 11 : extraction dans un chemin avec espaces et accents, lancement sans Python installé, réseau désactivé, traitement du pilote, sortie contrôlée en cas de disque plein ou d’absence de droits d’écriture. L’objectif « portable » ne sera annoncé comme acquis qu’après ces essais.

L’installation initiale peut nécessiter Internet. L’analyse scientifique devra fonctionner sans réseau ; catalogues, index astrométriques et tables temporelles nécessaires seront préparés explicitement à l’avance, avec licences et provenance.
