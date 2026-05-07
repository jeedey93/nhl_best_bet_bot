# Hockey Pool — Guide de l'utilisateur
*Pour les commissaires et les participants — aucune connaissance technique requise*

---

## C'est quoi ?

Le Hockey Pool est une ligue de hockey de style fantaisie intégrée au site Parieur Discipliné. Une seule personne (le **commissaire**) gère tout — créer la ligue, choisir les joueurs pour toutes les équipes, gérer les échanges et les swaps tout au long de la saison, et regarder le classement se mettre à jour automatiquement chaque jour.

Pas d'application à télécharger. Pas de compte à créer. Tout se passe sur **parieurdiscipline.com/pool**.

---

## Comment ça fonctionne — Vue d'ensemble

1. Le commissaire **crée une ligue** et obtient un code de 4 lettres (ex. `MXQR`).
2. Avec ce code, le commissaire **construit le alignement de chaque équipe** en choisissant des joueurs NHL sous le plafond salarial.
3. Une fois la saison commencée, **les statistiques NHL se synchronisent automatiquement chaque matin** — aucune saisie manuelle requise.
4. Le **classement se met à jour en temps réel** selon les performances de chaque joueur depuis son ajout à une équipe.
5. Le commissaire peut **effectuer des mouvements** (swaps sur le banc, échanges entre équipes) tout au long de la saison.

---

## Les pages

### 🏠 Accueil — Hub de la ligue (`/pool`)

C'est le point de départ. De là, le commissaire peut :

- **Créer une nouvelle ligue** — entrer un nom de ligue (facultatif) et cliquer sur Créer. Un mot de passe est requis pour éviter les erreurs.
- **Rejoindre une ligue existante** — entrer un code de 4 lettres pour accéder à n'importe quelle ligue.
- **Voir toutes les ligues** — chaque ligue est listée avec des liens rapides vers sa page de repêchage, le classement et le gestionnaire d'équipe.
- **Supprimer une ligue** — supprime tout de façon permanente (nécessite le mot de passe et une confirmation).

Chaque carte de ligue affiche désormais un **nombre d'équipes** pour voir d'un coup d'œil combien d'équipes ont été repêchées sans avoir à naviguer dans la ligue.

---

### ✏️ Repêchage (`/pool/join`)

C'est ici que les équipes sont construites. Le commissaire remplit le alignement de chaque équipe avant — et pendant — la saison.

#### Structure du alignement

Chaque équipe a exactement **26 places** :

| Groupe | Places | Marque des points ? |
|---|---|---|
| Attaquants (F) | 12 | Oui |
| Défenseurs (D) | 6 | Oui |
| Gardiens (G) | 2 | Oui |
| Banc (B) | 6 | Non |
| **Total** | **26** | |

Les joueurs sur le banc font partie de l'équipe mais **ne marquent pas de points** tant qu'ils ne sont pas déplacés vers un poste actif.

#### Le plafond salarial

Chaque équipe a un **plafond salarial de 95,5 M$**. Seuls les 20 joueurs actifs (F/D/G) comptent dans le plafond — les joueurs sur le banc sont gratuits. Si l'ajout d'un joueur fait dépasser le plafond, l'ajout est bloqué.

La barre de plafond en haut de l'écran indique l'espace salarial restant. Si une équipe dépasse, elle clignote en rouge.

#### Trouver et ajouter des joueurs

Le bassin de joueurs à droite affiche tous les joueurs NHL, triés par salaire par défaut. Vous pouvez :

- **Chercher par nom** avec la barre de recherche
- **Filtrer par position** (F / D / G) avec les boutons de position
- **Filtrer par équipe NHL** avec la bande d'équipes en haut
- **Trier par** salaire, buts, passes, points, victoires, jeux blancs, % d'arrêts ou matchs joués en cliquant sur l'en-tête de colonne
- **Cliquer sur un joueur** pour voir ses statistiques complètes, puis l'ajouter à un poste

Les joueurs déjà réclamés par une autre équipe affichent un badge pour vous le signaler.

#### Gérer plusieurs équipes

Le **sélecteur d'équipe** en haut permet de passer d'une équipe à l'autre. Chaque pastille affiche le nom de l'équipe, une barre de remplissage et le nombre de places remplies sur 26. Quand une équipe est complète, la barre devient verte.

#### ⚡ Remplissage automatique (Ultimate Team)

Vous ne voulez pas choisir chaque joueur manuellement ? Le bouton **Ultimate Team** remplit automatiquement toutes les places vides avec les meilleurs joueurs disponibles qui respectent le plafond salarial restant. Il verrouille les joueurs déjà choisis et ne complète que ce qui manque. Un aperçu affiche les suggestions avant toute application.

#### Autres outils

- **Annuler** — annule la dernière action
- **Effacer l'équipe** — retire tous les joueurs d'une équipe et repart à zéro
- **Comparer** — épingler jusqu'à deux joueurs côte à côte pour comparer leurs statistiques
- **Partager** — copier un lien vers la vue du alignement actuel

---

### 📊 Classement (`/pool/standings`)

Le tableau de bord en direct de la ligue. Mis à jour automatiquement chaque matin, ou instantanément quand le commissaire appuie sur le bouton **Sync**.

#### Ce que les colonnes signifient

| Colonne | Ce qu'elle affiche |
|---|---|
| Rang | Position dans la ligue (👑 pour le 1er, médailles pour le 2e et 3e) |
| Équipe | Nom de l'équipe dans le pool |
| Pts/MJ | Points par match joué *depuis l'acquisition du joueur* |
| Eff. | Points du pool par tranche de 1 M$ de salaire — mesure le rapport qualité-prix |
| Pts | Total des points accumulés dans le pool |
| Écart | Nombre de points derrière le meneur |

#### Développer une ligne d'équipe

Cliquez sur n'importe quelle ligne d'équipe pour l'ouvrir et voir :
- Chaque joueur actif, ses points dans le pool et sa position
- Le meilleur pointeur de l'équipe mis en évidence

#### Onglet Meneurs du pool

Bascule vers une vue des **meilleurs joueurs individuels par position** dans toute la ligue — les meilleurs attaquants, défenseurs et gardiens, peu importe l'équipe qui les possède.

#### Statistiques et tendances

En dessous du classement, un résumé rapide affiche :
- Qui est en tête
- Qui a la meilleure efficacité (le plus de points par dollar)
- Qui remonte le plus vite sur le meneur actuel

#### Synchronisation des statistiques

Les statistiques se mettent à jour automatiquement chaque matin. Pour avoir les derniers chiffres en cours de journée, cliquez sur **Sync Stats**. L'heure de la dernière synchronisation est affichée en haut du classement pour toujours savoir à quelle date les données remontent.

---

### 🗂 Gestionnaire de équipe (`/pool/roster`)

C'est ici que le commissaire gère les mouvements pendant la saison — swaps entre actifs et banc, échanges entre équipes, et suivi de l'état de chaque équipe.

#### Voir une équipe

Utilisez le sélecteur d'équipe en haut pour passer d'une équipe à l'autre. Chaque équipe affiche :
- **Les joueurs actifs** (F, D, G) — ceux qui accumulent des points
- **Les joueurs sur le banc** — ceux qui n'accumulent pas de points tant qu'ils ne sont pas activés

Chaque ligne de joueur affiche le logo de son équipe NHL, son nom, son statut de blessure, les matchs joués, les buts, les passes, les points (ou victoires/jeux blancs pour les gardiens), le salaire et une **courbe de tendance** montrant les performances récentes. Sur mobile, la courbe est remplacée par un badge **▲ ▼ =** indiquant si le joueur est en feu, en baisse ou stable.

#### Comment les points fonctionnent — Le concept clé

Les points ne comptent **que lorsqu'un joueur est dans un poste actif**. C'est ce qui rend les swaps stratégiques :

- Quand vous **déplacez un joueur sur le banc**, ses points accumulés sont gelés.
- Quand vous **réactivez un joueur**, il recommence à accumuler des points à partir de ce moment — ses points gelés sont conservés et les nouveaux s'y ajoutent.
- Cela signifie qu'envoyer un joueur en baisse de forme au banc et activer un joueur en feu peut changer le classement.

#### Swaps de joueurs (Actif ↔ Banc)

Chaque équipe a une **limite de swaps** (par défaut : 5 par équipe pour la saison). Le compteur de swaps en haut du résumé de chaque équipe indique combien ont été utilisés, affiché sous forme de petits indicateurs — le dernier devient rouge en avertissement.

Pour effectuer un swap :
1. Cliquez sur **⬇ Banc** sur un joueur actif pour l'envoyer au banc.
2. Une fenêtre s'ouvre pour choisir quel joueur du banc activer à sa place.
3. Les deux joueurs doivent appartenir au même groupe de position (ex. impossible d'échanger un attaquant contre un défenseur).

Une **fenêtre d'annulation de 30 secondes** est disponible après chaque swap en cas d'erreur.

Le **mode swap en bloc** permet de sélectionner un joueur actif et un joueur sur le banc en même temps et d'exécuter le swap en une seule étape.

#### Échanges entre équipes

La page de équipe supporte également les **échanges entre équipes du pool** — déplacer un joueur d'une équipe à une autre. Cela compte comme un swap pour les deux équipes concernées.

Un **historique complet des échanges** est affiché pour chaque équipe, incluant qui a été déplacé, quand, et combien de points il avait accumulé à ce moment.

#### Agents libres

L'onglet **Agents libres** affiche tous les joueurs NHL qui ne font partie d'aucune équipe du pool. Vous pouvez les chercher et les filtrer de la même façon que dans la page de repêchage.

#### Bloc des échanges

N'importe quel joueur peut être placé sur le **Bloc des échanges** avec le bouton 📤 Lister. Cela signale aux autres gérants (ou au commissaire) que l'équipe est ouverte à bouger ce joueur.

---

## Comment le pointage fonctionne

Les points sont calculés selon les performances du joueur **depuis son ajout au alignement actif d'une équipe**.

| Position | Ce qui rapporte des points |
|---|---|
| Attaquant (C / AG / AD) | 1 pt par but ou passe |
| Défenseur | 1 pt par but, 1 pt par passe (configurable) |
| Gardien | 2 pts par victoire, 3 pts par jeu blanc (configurable) |

Le commissaire peut ajuster ces valeurs par ligue depuis la page des paramètres.

**Exemple :** Si un attaquant rejoint votre équipe après avoir déjà marqué 20 points cette saison, ces 20 points ne comptent pas pour votre équipe — seuls les points marqués à partir du jour de son repêchage sont pris en compte.

---

## Ce qui se passe automatiquement

Vous n'avez rien à faire pour les éléments suivants — ils se produisent d'eux-mêmes :

- **Les statistiques se mettent à jour chaque matin** vers 9h (heure de Montréal) via un processus automatisé connecté à l'API officielle NHL.
- **Les statuts de blessure** (Actif / Jour après jour / Liste des blessés / Hors liste) se mettent à jour avec les statistiques chaque matin.
- **Les données de tendance des joueurs** (les courbes) se mettent à jour avec les derniers résultats match par match.

---

## Fonctionnalités actuellement disponibles

| Domaine | Fonctionnalité | Disponible |
|---|---|---|
| Hub | Créer / supprimer des ligues | ✅ |
| Hub | Voir toutes les ligues avec le nombre d'équipes | ✅ |
| Repêchage | Construire les alignements de plusieurs équipes | ✅ |
| Repêchage | Respect du plafond salarial | ✅ |
| Repêchage | Remplissage automatique (Ultimate Team) | ✅ |
| Repêchage | Recherche, filtres et tri des joueurs | ✅ |
| Repêchage | Annuler, effacer l'équipe | ✅ |
| Repêchage | Comparaison de joueurs (épingler deux côte à côte) | ✅ |
| Classement | Tableau de bord en direct avec points, efficacité, écart | ✅ |
| Classement | Détail des joueurs par équipe | ✅ |
| Classement | Meneurs du pool par position | ✅ |
| Classement | Statistiques (meneur, meilleure efficacité, qui remonte) | ✅ |
| Classement | Bouton de sync manuel + badge de dernière synchro | ✅ |
| Équipe | Swaps actif ↔ banc avec limite de swaps | ✅ |
| Équipe | Mode swap en bloc | ✅ |
| Équipe | Annulation de 30 secondes après les swaps | ✅ |
| Équipe | Échanges entre équipes | ✅ |
| Équipe | Historique des échanges par équipe | ✅ |
| Équipe | Signal de performance (▲ ▼ =) par joueur | ✅ |
| Équipe | Badges de blessure | ✅ |
| Équipe | Onglet agents libres | ✅ |
| Équipe | Liste du bloc des échanges | ✅ |
| Stats | Synchronisation automatique quotidienne depuis l'API NHL | ✅ |
| Stats | Pointage par fenêtre active (points seulement quand actif) | ✅ |
| Stats | Pondération du pointage configurable par ligue | ✅ |

---

## Suggestions pour l'avenir

Ces améliorations rendraient le pool plus riche et plus facile à utiliser :

### Qualité de vie

| # | Fonctionnalité | Pourquoi ce serait utile |
|---|---|---|
| 1 | **Ajouter des joueurs directement depuis la page Équipe** | Présentement, il faut retourner dans la page de repêchage pour ajouter un agent libre — ce serait plus rapide depuis la même page que les swaps |
| 2 | **Libérer un joueur vers les agents libres** | Il n'y a pas de façon de relâcher complètement un joueur — l'envoyer au banc est la seule option, mais le joueur occupe quand même une place |
| 3 | **Verrouillage du repêchage une fois les alignements complets** | Empêcher les modifications accidentelles une fois que le repêchage est terminé |
| 4 | **Verrouiller des joueurs individuels** | Permettre au commissaire de marquer un joueur comme intouchable pour qu'il ne puisse pas être déplacé ou échangé par erreur |

### Classement et analyses

| # | Fonctionnalité | Pourquoi ce serait utile |
|---|---|---|
| 5 | **Flèches de mouvement au classement (↑ ↓)** | Montrer si chaque équipe a monté ou descendu depuis la dernière synchronisation — rend le classement plus dynamique |
| 6 | **Vue semaine par semaine** | Filtrer le classement pour voir qui a le mieux performé une semaine donnée, pas seulement sur toute la saison |
| 7 | **Graphique d'évolution des points par équipe** | Un graphique en courbe montrant comment le total de points de chaque équipe a progressé au fil de la saison |
| 8 | **Meilleur et pire mouvement de la semaine** | Mettre en évidence automatiquement le swap ou l'échange qui a rapporté ou coûté le plus de points cette semaine |
| 9 | **Classement final projeté** | Selon le rythme actuel, estimer où chaque équipe finira la saison |

### Gestion des équipes

| # | Fonctionnalité | Pourquoi ce serait utile |
|---|---|---|
| 10 | **Système de ballottage** | Un ordre de priorité pour réclamer des agents libres, afin que l'équipe dernière au classement ait la priorité |
| 11 | **Propositions d'échanges entre gérants** | Permettre aux participants de proposer des échanges entre eux plutôt que le commissaire décide de tout |
| 12 | **Synchronisation en soirée** | Une deuxième mise à jour automatique tard le soir pour capturer tous les matchs terminés dans la journée (la synchro actuelle se fait une fois le matin) |
| 13 | **Règles spéciales pour les séries** | Permettre de réduire le alignement actif ou d'utiliser un pointage différent pendant les séries éliminatoires |

### Outils du commissaire

| # | Fonctionnalité | Pourquoi ce serait utile |
|---|---|---|
| 14 | **Améliorations de la page des paramètres** | Présentement, le nombre max de swaps et les pondérations sont configurables — on pourrait ajouter la taille du alignement ou des règles de bris d'égalité personnalisées |
| 15 | **Journal des erreurs de synchronisation** | Si la synchro nocturne échoue, afficher une alerte visible sur la page de classement plutôt que ça passe inaperçu |
| 16 | **Notes du commissaire par équipe** | Un petit champ texte pour laisser des notes sur une équipe (ex. « en attente d'approbation d'un échange ») visibles uniquement en mode gestion |
| 17 | **Exporter le classement en image ou PDF** | Pratique pour partager les résultats hebdomadaires dans un groupe de discussion |
