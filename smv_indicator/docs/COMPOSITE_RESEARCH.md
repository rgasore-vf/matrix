# COMPOSITE_RESEARCH.md : recherche d'une stratégie composite à haute précision

**Question.** Existe-t-il une région de l'espace des états du marché où plusieurs informations faibles deviennent ensemble une information forte, avec une précision hors échantillon de 70 à 80 % ?

**Réponse courte.**
1. **Oui, une région existe.** Elle ne vient pas de la séquence SMV, mais d'un retour à la moyenne en fin de séance américaine. Sa précision est **stable hors échantillon autour de 64 à 67 %** sur une course symétrique ±1 ATR (le hasard donne 50 %). C'est le maximum robuste trouvé. **70-80 % n'a pas été atteint honnêtement** sur une géométrie symétrique.
2. **Son espérance dépend entièrement des coûts.** Elle est positive au coût nominal (+0,11 R par trade sur le test 2020-2022), nulle sur les instruments jamais vus, et négative dès que le coût double. Or l'écart achat-vente s'élargit justement à ces heures. **Elle n'est pas démontrée comme tradable** ; elle doit être vérifiée avec les vrais écarts (testeur MT5, ticks réels).
3. **La séquence SMV** (zone décisionnelle, sweep, prise de borne, zone fraîche, H1 aligné) monte à 54-58 % sur une centaine de cas et **s'effondre au test** (48 %).
4. **Un 70-80 % « facile » existe**, mais il est trompeur : avec TP 0,5 / SL 1, le hasard donne déjà 67 %. Le meilleur modèle y atteint 70-72 % hors échantillon, soit +4 à +5 points d'excès, et son espérance est négative après coûts.

Scripts : `research/composite/`. Résultats bruts : `research/composite/results/`. Matrices (1,54 million de lignes, non versionnées) : `python research/composite/build_matrix.py SYMBOLE SORTIE.parquet`.

---

## 1. Données et matrice événementielle

- 12 instruments M15 (EURUSD, XAUUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, EURGBP, EURCHF, USDJPY, EURJPY, GBPJPY, AUDJPY), novembre 2012 à mars 2022 ; H1 et H4 agrégés depuis le M15, bougies closes seulement.
- **Une ligne = une opportunité** (bougie i close, sens d), créée si un déclencheur survient à la clôture de i :
  - première touche d'une zone de sens d ;
  - liquidité opposée prise en mèche ;
  - BOS de sens -d, lu à l'envers ;
  - prise de borne de consolidation ;
  - prise du niveau protégé.
- **85 variables**, toutes connues à la clôture de i :
  - pour chaque type d'événement (BOS de continuation et de changement, sweep, LIQ_BOS, signature, fail, FVG, prise du protégé, EQH/EQL, breaker, zone, sortie de cause, cause complète, STB, Spring, UT, UTAD, UA, MSO), le nombre de bougies écoulées depuis le dernier, dans le même sens et dans le sens opposé ;
  - la qualité de la zone touchée : source, BM, doji, hauteur, âge, pénétration, distance au bord distal ;
  - l'amplitude du BOS ;
  - la structure M15, H1 et H4 relative au sens, le premium/discount M15, H1 et H4, la présence dans une zone H1 ou H4 ;
  - la distance aux liquidités intactes, côté cible et côté risque ;
  - le régime : ATR relatif, momentum à 5, 20 et 96 bougies, ratio d'efficience, compression, position dans le range de 24 h, corps et mèche de la bougie ;
  - la consolidation en cours, l'heure, le jour.
- **Issues** (jamais utilisées comme variables) : entrée à la clôture de i, courses TP/SL en ATR M15 pour six géométries (1/1, 1,5/1, 2/1, 1/0,5, 0,5/1, 2/2). Une bougie qui touche les deux bornes compte comme perte. S'y ajoutent la MFE, la MAE et le temps jusqu'à l'issue.

## 2. Protocole anti-surapprentissage (fixé avant l'exploration)

| Partie | Contenu | Usage |
|---|---|---|
| Entraînement | 9 instruments, 2012-2017 | découverte des règles et des modèles |
| Validation | 9 instruments, 2018-2019 | arrêt précoce, seuils de couverture, choix des candidats |
| Test temporel | 9 instruments, 2020-mars 2022 | **lu une seule fois**, candidats figés |
| Test instruments | USDCAD, EURCHF, GBPJPY, toute la période | **jamais vus** avant le test (équivalent leave-symbols-out) |

**Contrôles :**
- même recherche de règles sur des étiquettes **permutées** dans chaque instrument, pour mesurer la hauteur des « découvertes » dues au seul volume de recherche (402 conditions, conjonctions jusqu'à 4) ;
- intervalles par **rééchantillonnage de jours entiers**, car les opportunités d'un même jour sont corrélées ;
- coûts : 1 pip sur les majeures, davantage sur les croisées et l'or (`setup_dataset.COST`), testés à x0, x1, x2 et x3.

**Mesure du hasard selon la géométrie** : 1/(1 + TP/SL), soit 50 % pour 1/1, 33 % pour 2/1 et 67 % pour 0,5/1. Un taux de réussite ne se lit qu'en excès sur cette valeur.

## 3. Ce que la recherche a trouvé

### 3.1 Contrôle par permutation

| Recherche | Meilleur entraînement (borne basse) | Validation des meilleures règles |
|---|---|---|
| Étiquettes permutées | 56 % | 49 à 52 % ; les meilleures choisies en validation montent à 55-56 % par sélection |
| Étiquettes réelles, toutes heures | 68 % | 60 à 69 % |
| Étiquettes réelles, heures liquides (1 h-19 h) | 61 % | 47 à 56 %, **indiscernable du hasard** |

En heures liquides, aucune conjonction ne se distingue du bruit. Toutes les règles fortes contiennent `heure >= 21` (Paris).

### 3.2 Courbes précision / couverture (LightGBM, cible ±1 ATR, validation)

| Opportunités gardées | Toutes heures | Heures liquides |
|---|---|---|
| 100 % | 49,6 % | 49,5 % |
| 25 % | 53,4 % | 51,8 % |
| 10 % | 56,3 % | 53,2 % |
| 5 % | 58,2 % | 53,5 % |
| 2 % | 62,2 % | 53,3 % |
| 1 % | **65,7 %** | 52,4 % |

L'abstention fonctionne quand il existe un signal : toutes heures, la précision monte régulièrement avec la sélectivité. En heures liquides, elle plafonne à 53 %, ce qui reste en dessous du seuil de rentabilité à ±1 ATR avec les coûts (environ 56 à 60 % selon l'instrument et l'heure : seuil = (1 + coût/ATR) / 2).

### 3.3 La région trouvée : retour à la moyenne en fin de séance américaine

Carte probabiliste (entraînement / validation), conditions empilées dans les **mêmes** événements :

| Conditions simultanées | Entraînement n | Réussite | Validation n | Réussite | Instruments > 50 % (val) |
|---|---|---|---|---|---|
| Toutes opportunités | 635 761 | 49,7 % | 249 643 | 49,6 % | 1/9 |
| Heure 21 h-23 h (Paris) | 68 401 | 50,5 % | 27 422 | 49,8 % | 4/9 |
| + mouvement contre ≤ -1 ATR sur 5 bougies | 10 897 | 59,2 % | 4 532 | 61,1 % | 9/9 |
| + bougie pleine contre (corps ≤ -0,4 ATR) | 5 680 | 61,0 % | 2 289 | 63,1 % | 9/9 |
| + aucune mèche de rejet (≤ 0,15 ATR) | 2 455 | 64,7 % | 1 004 | 63,8 % | 9/9 |
| + touche de zone (toute source) | 1 523 | 65,1 % | 602 | 64,5 % | 9/9 |

Lecture : à la fin de la séance de New York, après une poussée de 5 bougies terminée par une bougie pleine sans rejet, le prix revient. La condition SMV (touche de zone) n'ajoute presque rien. L'absence de mèche de rejet compte, ce qui est l'inverse de la « réaction » attendue par la formation.

### 3.4 Concepts de la formation dans la recherche

- **Séquence SMV complète** (zone décisionnelle, sweep, prise de borne, zone fraîche, H1 aligné, faible pénétration) : 50,6 → 54,2 % en entraînement (n = 360), 57,6 % en validation (n = 118), **48,3 % au test** (n = 205). Rejetée.
- **BOS lu à l'envers** : 50,7 %, quelles que soient les conditions ajoutées (excès, zone, discount). La faiblesse du BOS suivi (47 %) ne devient pas un signal contrarien utilisable en heures liquides.
- **Variables les plus utiles au modèle** : heure, corps et mèche de la bougie, momentum 5 et 20, ATR relatif, position dans le range de 24 h, premium/discount H4, temps depuis le dernier BOS de continuation, distance aux liquidités. Les concepts SMV interviennent comme modulateurs secondaires, pas comme moteurs.

## 4. Classement final (candidats figés avant lecture du test)

R = distance du stop ; E1 = espérance au coût nominal, E2 = coût doublé ; IC = intervalle à 95 % par jours. Profit factor sans coût.

| Candidat | Cible | Entraînement | Validation | **Test 2020-22** (9 instr.) | **Instruments jamais vus** | E1 test / jamais vus | E2 test | PF test | Stabilité test |
|---|---|---|---|---|---|---|---|---|---|
| C1b ML toutes heures, top 1 % | ±1 ATR | 71,7 % (6 191) | 65,7 % (2 496) | **67,3 %** (2 942) [65,1-69,6] | **63,8 %** (4 324) | +0,11 / -0,01 | -0,13 | 2,06 | 9/9 instr., 3/3 ans ; jamais vus 3/3, 10/11 ans |
| C1a ML toutes heures, top 2 % | ±1 ATR | 69,7 % | 62,2 % | 63,5 % (5 717) | 62,0 % (8 222) | +0,04 / -0,05 | -0,20 | 1,74 | 9/9, 3/3 |
| C2 règle lisible « rollover » | ±1 ATR | 64,6 % (1 329) | 68,5 % (515) | 65,4 % (687) | 64,8 % (907) | +0,08 / +0,03 | -0,14 | 1,89 | 9/9, 3/3 ; 3/3, 10/11 |
| C4 ML heures liquides, top 1 % | TP 0,5 / SL 1 (hasard 67 %) | 79,1 % | 72,5 % | 70,3 % | 71,7 % | -0,18 / -0,21 | -0,41 | 1,19 | 7/9 |
| C6 ML heures liquides, top 5 % | 2 / 2 | 63,3 % | 53,1 % | 52,9 % | 54,9 % | -0,06 / -0,05 | -0,17 | 1,12 | 9/9 |
| C3 ML heures liquides, top 5 % | ±1 ATR | 60,6 % | 53,5 % | 52,7 % | 54,5 % | -0,18 / -0,20 | -0,42 | 1,11 | 9/9 |
| C5 séquence SMV | ±1 ATR | 54,2 % (360) | 57,6 % (118) | 48,3 % (205) | 53,6 % (252) | -0,24 / -0,22 | -0,44 | 0,93 | 4/9 |

**Règle C2 (figée avant le test) :** première touche d'une zone créée il y a au moins 18 bougies M15 ; heure de clôture ≥ 21 h (Paris) ; mèche de rejet de la bougie de touche ≤ 0,28 ATR(14). Entrée à la clôture dans le sens de la zone ; TP = SL = 1 ATR(14) M15.

**Classement demandé :**

| Catégorie | Candidats |
|---|---|
| 70-80 % seulement dans l'échantillon | C1b (71,7 % en entraînement) ; C4 (79 %, mais géométrie à 67 % de hasard) |
| 70-80 % en validation mais pas au test | aucun sur une géométrie symétrique |
| 70-80 % stable hors échantillon | **aucun honnêtement** : C4 atteint 70-72 % mais n'a que 4 à 5 points d'excès sur son hasard (67 %) et une espérance négative |
| Maximum robuste réellement atteint | **64-67 % à ±1 ATR (C1b, C2)**, stable sur 12 instruments et toutes les années, dans une seule région (21 h-minuit Paris) |
| Aucun résultat crédible | heures liquides (C3, C6), séquence SMV (C5) |

## 5. Pourquoi ce n'est pas encore une stratégie

1. **Coûts au mauvais moment.** L'ATR M15 de nuit est petit : le coût représente 0,21 à 0,25 ATR, donc 0,21 à 0,25 R. Le seuil de rentabilité à ±1 ATR est d'environ 61 % au coût nominal et 73 % au coût doublé. Or les écarts s'élargissent à l'approche du rollover de New York (23 h à Paris) et juste après. Les données utilisées n'ont pas d'écart réel : le coût de nuit est sous-estimé, d'un facteur inconnu.
2. **Artefact possible.** Une partie du retour à la moyenne de fin de journée peut venir des cotations elles-mêmes (pics sans liquidité qui reviennent aussitôt). Seules des données avec écart réel, ou des ticks réels, peuvent trancher.
3. **Exécution.** L'entrée à la clôture exacte n'inclut pas le glissement.
4. **Tests multiples.** Le protocole (test figé, instruments jamais vus, permutation) limite ce risque pour C1 et C2, mais leur stabilité de 2020 à 2022 ne garantit pas les années suivantes.

## 6. Enseignements sur la formation

- Les concepts SMV ne portent pas, dans ces données, d'information forte, ni seuls, ni combinés (séquence C5 rejetée).
- La seule région robuste est un **retour à la moyenne** : elle contredit l'idée de suivre la cassure et ne demande pas de « réaction » visible sur la bougie de touche.
- **Fausses idées confirmées :** suivre le BOS, les EQ ou l'inducement comme aimants, la séquence complète comme filtre de précision.
- **Information utile :** l'heure, l'excès de court terme et la forme de la bougie. Ce ne sont pas des concepts enseignés.

## 7. Prochaine étape décisive (à faire sur MT5)

Tester **C2 tel quel**, sans rien régler, dans le testeur MT5 en mode « chaque tick basé sur des ticks réels », chez le courtier visé, de mars 2022 à aujourd'hui (période jamais vue). Ordre au marché à la clôture de la bougie M15, TP = SL = ATR(14). Trois variantes figées d'avance :
- toutes heures ≥ 21 h ;
- 21 h-22 h seulement (avant l'élargissement des écarts) ;
- 22 h-23 h seulement.

Critère d'acceptation : espérance positive avec les écarts réels sur au moins 8 instruments sur 12 et sur chaque année. Sinon, la conclusion est que l'avantage est mangé par la microstructure.
