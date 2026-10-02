# ASYM_RESEARCH.md : recherche d'une stratégie asymétrique rentable (RR ≥ 2)

**Objectif.** Trouver, sans chercher à défendre SMV, une stratégie dont l'**espérance après coûts** est positive, avec une géométrie d'au moins 1:2 et idéalement 1:3, robuste hors échantillon et stable entre instruments et années.

**Réponse.** **Aucune stratégie robuste trouvée** dans ces données (12 instruments forex et or, M15 à D1, 2012-2022, OHLC de courtier). Le meilleur candidat (B : expansion de volatilité en H4, TP 3 R) était positif chaque année de 2013 à 2019, puis **négatif en 2020-2021** (-0,12 R). Les modèles LightGBM n'ont rien trouvé de plus solide : ce qu'ils apprennent surtout, c'est à éviter les instruments chers. La conclusion principale porte donc sur la structure du problème (§5), pas sur une règle.

Scripts : `research/asym/`. Résultats bruts : `research/asym/results/`. Matrices non versionnées : `python research/asym/build_matrix2.py SYMBOLE SORTIE.parquet [m15|h1|h4|d1]`.

---

## 1. Protocole (fixé avant l'exploration)

| Période | Rôle |
|---|---|
| 2012-2016 | entraînement |
| 2017-2019 | validation ; walk-forward en 3 plis (≤2014→2015-16, ≤2016→2017-18, ≤2018→2019) |
| 2020-mars 2022 | **contaminée** par la recherche précédente ; contrôle secondaire des candidats figés seulement |
| mars 2022 → aujourd'hui | **coffre-fort** : inaccessible depuis cet environnement (Dukascopy, HistData, Yahoo, Kaggle bloqués) ; à ouvrir dans le testeur MT5 de l'utilisateur |

Contrôle des instruments : leave-one-symbol-out pour les modèles (entraîné sur 11 instruments, évalué sur le 12e). Intervalles par rééchantillonnage de jours. Coûts : 1 pip sur les majeures, davantage sur les croisées et l'or (`setup_dataset.COST`), testés à x1, x1,5 et x2.

## 2. Matrice v2 (1,63 million d'opportunités en M15, 0,46 million en H1, 0,17 million en H4, 54 000 en D1)

**Familles de déclencheurs** (une opportunité peut en avoir plusieurs) :

| Famille | Définition (sens d) |
|---|---|
| brk20, brk96 | clôture au-delà du plus haut (bas) des 20 / 96 bougies précédentes, suivre |
| fail20 | mèche au-delà de l'extrême des 20 bougies, clôture revenue dedans, sens inverse |
| mr5 | mouvement de 5 bougies ≥ 1,5 ATR, retour à la moyenne |
| volx | amplitude des 20 bougies précédentes ≤ 4 ATR, puis bougie ≥ 1,5 ATR, suivre |
| pull | tendance de l'UT supérieure d, clôture à l'extrême opposé des 10 bougies, entrer dans le sens d |
| sess | bougie contenant l'ouverture de Londres (8:00) ou de New York (9:30), deux sens |
| zone, sweep, bos_follow, bos_fade | déclencheurs SMV, pour comparaison |

**Exécution :**
- entrée à l'**ouverture de la bougie suivante** ;
- trois stops justifiés, risque borné entre 0,25 et 3 ATR : 1 ATR, dernier swing (10 bougies), extrême de la bougie de signal ;
- TP de 1 à 4 R, sortie à l'horizon (96 bougies, 20 en D1) ;
- un gap au-delà du stop est compté au prix d'ouverture ; si le stop et le TP tombent dans la même bougie, le stop l'emporte.

**Variables (environ 70)** :
- momentum à 1, 5, 20 et 96 bougies, ratio d'efficience ;
- compression, amplitude, corps et mèches, bougies précédentes, série de bougies de même sens ;
- ATR relatif, tendance de l'ATR ;
- distances aux extrêmes 20 et 96 ;
- range du jour et position, range asiatique et sa cassure ;
- structure de l'UT de base et des deux UT supérieures, momentum et volatilité des UT supérieures ;
- temps depuis les événements SMV, distances aux liquidités ;
- heure, jour, risque en ATR, coût en R.

**Issues** : R par TP, MFE avant stop, MAE, temps.

## 3. Résultats par famille (étape 1)

**M15 : toutes les familles sont négatives après coûts**, sur tous les instruments et toutes les années. Le coût vaut 0,2 à 0,5 R par trade, soit dix fois le meilleur avantage brut :

| Famille (stop 1 ATR) | Brut, TP 2 R | Coût |
|---|---|---|
| pull | +0,06 R | 0,24 R |
| bos_fade | +0,03 à +0,06 R | 0,22 R |
| mr5 | +0,02 R | 0,22 R |
| brk, bos_follow | -0,07 à -0,10 R | — |

**H1** : coût d'environ 0,11 R. Aucune famille n'est positive après coûts ; le meilleur net en validation est -0,06 R.

**H4** : coût d'environ 0,05 R. Seule l'**expansion de volatilité** est positive avant et après coûts sur les deux périodes, mais faiblement (TP 3 R : +0,03 R net en entraînement, 0,00 en validation). Les cassures 20 et 96 ne le sont pas.

**D1** : coût d'environ 0,02 R. L'expansion de volatilité s'inverse entre entraînement (-0,26 R) et validation (+0,17 R), ce qui signale un effet de régime. Le **BOS journalier lu à l'envers** est positif sur les deux périodes (+0,05 à +0,08 R, puis +0,13 à +0,17 R), avec de petits effectifs.

## 4. Modèles LightGBM (régression sur le R net)

| UT, stop, TP | Validation top 5 % / 2 % | Walk-forward top 2 % (3 plis) | Instruments jamais vus top 2 % |
|---|---|---|---|
| H4, 1 ATR, 2 R | -0,015 / -0,037 | -0,03 ; -0,06 ; -0,11 | -0,04 R (6/12) |
| H4, 1 ATR, 3 R | -0,049 / -0,118 | -0,14 ; +0,03 ; +0,07 | -0,07 R (7/12) |
| H4, 1 ATR, 4 R | -0,050 / -0,005 | -0,06 ; -0,12 ; -0,03 | -0,22 R (3/12) |
| H4, signal, 2 R | -0,026 / -0,052 | +0,05 ; +0,04 ; +0,01 | +0,03 R (7/12) |
| H1, 1 ATR, 2 R | +0,009 / +0,041 | -0,01 ; +0,08 ; -0,05 | -0,01 R (7/12) |
| H1, 1 ATR, 3 R | -0,018 / +0,001 | -0,01 ; +0,02 ; -0,05 | -0,04 R (6/12) |

L'arrêt précoce intervient après 2 à 58 arbres. La variable la plus importante est presque toujours le **coût relatif au risque**. Le modèle apprend à éviter les paires chères ; il ne trouve pas de structure de marché exploitable. La configuration « signal, 2 R » en H4 frôle zéro sur les instruments jamais vus, ce qui reste dans la variance.

## 5. Candidats figés et contrôle 2020-2022

Figés par hypothèse, sans optimisation, avant toute lecture de 2020-2022 pour ces règles (`research/asym/candidates.py`).

| Candidat | Développement 2013-19 : n, réussite (seuil), net | Années positives | Instruments positifs | Coûts x2 | **2020-2022 (contaminé)** |
|---|---|---|---|---|---|
| A : H4, compression ≤ 4 ATR puis bougie ≥ 2 ATR, suivre ; SL 1 ATR ; TP 2 R | 2 880, 36,1 % (33,3 %), +0,03 R | 5/7 | 9/12 | -0,02 R | **-0,08 R**, 4/12 |
| B : même règle, TP 3 R | 2 880, 28,6 % (25 %), **+0,09 R** (entraînement +0,12, validation +0,04) | **7/7** | 10/12 | +0,03 R | **-0,12 R** [-0,29 ; +0,04], 3/12 ; 2020 -0,17, 2021 -0,11 |
| C : D1, BOS journalier lu à l'envers ; SL 1 ATR ; TP 3 R | 723, 32,0 % (25 %), +0,10 R | 6/7 | 9/12 | +0,07 R | **-0,06 R**, 4/10 ; 2020 -0,36, 2021 +0,10 |

Asymétrie de B (développement) :
- réussite 28,6 % pour un seuil de 25 % ;
- **28 % des trades atteignent 3 R, 23 % atteignent 4 R, 10 % dépassent 8 R** avant le stop ;
- MFE médiane : 1,16 R.

La queue droite est épaisse, comme dans un suivi de tendance. Un tel profil ne paie que si les trades gagnants ne sont pas coupés trop tôt et si le régime de marché favorise les tendances. Ce n'était pas le cas en 2020-2021.

## 6. Classement

| Classe | Stratégies |
|---|---|
| **ROBUSTE** | aucune |
| **PROMETTEUR** | aucune |
| **EXPLORATOIRE** | B (expansion H4, 1:3) : sept années positives sur sept en développement, puis échec en 2020-2021 ; à départager sur le coffre-fort 2022-2026. C (BOS D1 lu à l'envers, 1:3) : petit effectif, échec en 2020. |
| **REJETÉ** | toutes les familles M15 et H1 ; A ; cassures 20/96 en H4 et D1 ; modèles LightGBM H1 et H4 ; séquence SMV (recherche précédente) ; C2 « rollover » 1:1 de la recherche précédente (dépend des coûts réels de nuit) |

## 7. Ce que la recherche enseigne

1. **Le coût décide de l'unité de temps.** En M15, le coût (0,2-0,5 R) dépasse tout avantage observé. Il faut au moins du H4 pour qu'un avantage de quelques centièmes de R survive.
2. **Les effets de prix courts sont faibles et changent de signe selon le régime.** L'expansion de volatilité, la seule famille positive sur sept ans, s'inverse dès 2020.
3. **Les concepts SMV n'apportent pas d'information propre** une fois les variables de prix et de volatilité présentes. La seule trace d'effet est le **BOS lu à l'envers**, à toutes les UT, et il est faible.
4. **Trouver une stratégie par trade dans ces données n'est pas réaliste.** La littérature sur le momentum de séries temporelles (Moskowitz, Ooi et Pedersen, *Time Series Momentum*, Journal of Financial Economics, 2012) situe l'avantage robuste à des horizons de plusieurs semaines à plusieurs mois, **diversifié sur de nombreux actifs** (devises, indices, matières premières, taux). Cet avantage se mesure au niveau d'un portefeuille, pas d'un trade isolé de quelques heures.

## 8. Prochaines étapes

1. **Coffre-fort (MT5, mars 2022 → aujourd'hui), sans aucun réglage :** tester B et C exactement comme définis ici. Si B est positif sur la majorité des instruments et des années, l'échec de 2020-2021 était un effet de régime ; sinon, B est rejeté.
2. **Changer d'univers et d'horizon** plutôt que de raffiner des filtres :
   - suivi de tendance D1 et W1 sur un panier large (devises, or, indices) ;
   - sorties suiveuses qui laissent courir la queue droite (MFE > 8 R dans 10 % des cas de B) ;
   - évaluation au niveau du portefeuille.
3. **Données :** des cotations avec écart réel (ticks) pour mesurer les coûts au lieu de les supposer.

## 9. Protocole du coffre-fort et critères pré-enregistrés

Rédigé le 2 octobre 2026, **avant toute lecture des données postérieures à mars 2022**. Ces critères ne seront pas modifiés après réception des résultats.

**Outil.** EA `mt5/Experts/ASYM/ASYM_Vault.mq5` : règles figées, sans paramètre de stratégie réglable. Il produit deux mesures :
- **shadow** : simulation bougie par bougie avec exactement les règles de la recherche. Le rejeu Python (`research/asym/vault_replay.py check`) reproduit à l'identique la matrice de recherche, avec zéro écart sur B (EURUSD, XAUUSD) et sur C (EURUSD, GBPJPY). Le code MQL5 suit ce rejeu ligne à ligne ;
- **exécution réelle** du testeur : écart, glissement, commission et swap réels.

Le rejeu de parité (`vault_replay.py parity`) recalcule les signaux à partir des bougies exportées par l'EA et vérifie que le shadow MT5 est identique.

**Mesure principale.** Espérance shadow au TP figé (3 R pour B et C), nette du coût nominal de la recherche. Elle porte sur tous les instruments regroupés, pour les signaux du 1er mars 2022 à la fin des données.

| Verdict | Condition |
|---|---|
| REJETÉ | espérance nette ≤ 0 |
| EXPLORATOIRE (inchangé) | espérance nette > 0, sans remplir les conditions suivantes |
| PROMETTEUR | espérance nette > 0 ; au moins 7 instruments sur 12 positifs ; au moins 3 années sur 5 positives (2022 partielle à 2026 partielle) ; espérance de l'exécution réelle (R monétaire, tous frais) > 0 |
| ROBUSTE | PROMETTEUR, et borne basse de l'IC 95 % (rééchantillonnage de jours) > 0, et espérance nette > 0 avec coûts doublés |

**Puissance attendue (estimation).** Environ 400 signaux par an pour B, soit 1 800 environ sur le coffre-fort. L'écart-type d'un trade à 3 R est d'environ 1,8 R, d'où une erreur standard d'environ 0,04 R. Seul un effet au moins égal à celui du développement (+0,09 R) pourrait donc atteindre ROBUSTE. Pour C (environ 450 signaux), l'erreur standard est d'environ 0,09 R : C ne peut guère dépasser PROMETTEUR, même s'il est réel.

**Interdit après ouverture.** Ne pas modifier les règles, ne pas filtrer les instruments ou les heures, ne pas choisir le TP a posteriori. Les R pour TP 1 à 4 sont journalisés à titre descriptif seulement.

## 10. Journal du coffre-fort

**2 octobre 2026, essai technique (pas un verdict).** B sur EURUSD seulement, compte Deriv-Demo, mode « prix d'ouverture ». L'EA v1.00 s'est arrêté le 13/05/2025 sur une violation d'accès dans le moteur SMV complet ; il a été corrigé en v1.10. Les 137 trades exécutés du 29/03/2022 au 09/05/2025, relus dans le journal du testeur, donnent :
- 29,9 % de réussite pour un seuil de 25 % ;
- **+0,20 R** par trade (R prix, écart inclus, swap exclu) ;
- par année : 2022 +0,22 ; 2023 +0,03 ; 2024 +0,31 ; 2025 (partielle) +0,23.

À titre de comparaison, EURUSD valait +0,13 R en développement (n = 274). Un seul instrument, avec n = 137, donne une erreur standard d'environ 0,16 R. Ce résultat va dans le bon sens mais ne permet aucune conclusion. Le verdict de §9 exige les 12 instruments et le shadow.
