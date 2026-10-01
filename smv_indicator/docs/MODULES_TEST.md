# MODULES_TEST.md : chaque concept de la stratégie testé séparément

Objet : vérifier, concept par concept, si ce que la formation fait attendre se produit plus souvent que le hasard. Ce n'est pas un backtest de trading : c'est un test des idées.

Scripts : `research/modules.py`, `research/modules_report.py`. Résultats bruts : `research/results_modules.json`. Données : 12 instruments (EURUSD, XAUUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, EURGBP, EURCHF, USDJPY, EURJPY, GBPJPY, AUDJPY), M15 et H1, novembre 2012 à mars 2022 (`research/DATA_MANIFEST.json`).

## Méthode

**Signaux directionnels.** À la clôture de la bougie qui confirme l'événement, on « entre » dans le sens que la formation attribue au concept. On regarde si le prix atteint +1 ATR avant -1 ATR (et +2 avant -2), dans les 300 bougies. Si le concept n'apporte rien, le taux de réussite est de 50 %. Une bougie qui touche les deux bornes compte pour 0,5. Aucun coût.

**Contrôle.** Les mêmes calculs sur la même série de bougies mélangée donnent entre 48,8 et 52 % pour tous les concepts observés plus de 1 000 fois : la méthode ne fabrique pas d'effet. L'intervalle ± est un intervalle binomial à 95 % qui suppose des observations indépendantes ; elles ne le sont pas toutes (événements proches dans le temps), donc il est optimiste. La colonne « instruments » compte sur combien des 12 le concept dépasse 50 % : c'est le critère de robustesse le plus parlant.

**Limites.** L'entrée à la clôture de confirmation n'est pas l'entrée enseignée (ordre limite sur zone, raffinage) ; le test mesure l'information contenue dans le concept au moment où il devient connu. Les zones sont calculées sur tous les pivots pour pouvoir comparer « avec BOS » et « sans BOS ».

## Résultats : signaux directionnels (course ±1 ATR)

Verdicts : **FAUX** = le marché fait l'inverse de ce qui est attendu, de façon cohérente ; **SANS EFFET** = indiscernable du hasard ; **FAIBLE** = effet réel mais petit (1 à 2 points), régulier sur la plupart des instruments ; tous restent inférieurs aux coûts de transaction en M15.

| Module | Concept (sens attendu) | M15 : réussite (instruments > 50 %) | H1 | Verdict |
|---|---|---|---|---|
| M1 | Suivre un BOS de changement | 47,6 % (1/12) | 49,3 % (4/12) | **FAUX en M15**, sans effet en H1 |
| M1 | Suivre un BOS de continuation | 47,4 % (0/12) | 48,3 % (2/12) | **FAUX** |
| M1/M5 | Mèche sous le protégé sans clôture = reprise de tendance | 49,8 % (5/12) | 50,3 % | SANS EFFET |
| M2 | Zone avec bougie manipulatrice (vs sans) | 50,9 % (10/12) contre 50,3 % | 50,9 % contre 49,6 % | FAIBLE |
| M2 | Doji signature (vs sans) | 50,6 % contre 50,4 % | 49,8 % contre 50,0 % | SANS EFFET |
| M2 | Signature de liquidité : le prix va vers la mèche | 50,7 % (11/12) | 50,7 % (11/12) | FAIBLE, très régulier |
| M3 | 1re touche d'une zone décisionnelle (BOS de changement) | **51,8 % (11/12)** | 50,6 % (9/12) | FAIBLE, le meilleur de la structure |
| M3 | 1re touche d'une zone de continuation | 49,8 % (3/12) | 49,6 % | SANS EFFET |
| M3 | 1re touche d'une zone sans BOS | 50,4 % (12/12) | 50,1 % | quasi nul |
| M3 | Order flow (nouvelle zone liée) | 49,9 % | 49,7 % | SANS EFFET |
| M3 | Breaker : la zone cassée change de polarité | 48,2 % (1/12) | 49,6 % | **FAUX en M15** |
| M3 | Réaction sur breaker | 48,3 % (0/12) | 49,1 % | **FAUX en M15** |
| M4 | Fail = changement de caractère (retournement) | 49,9 % (4/12) | 49,4 % | SANS EFFET |
| M4 | Cause complète : suivre l'intention | 47,5 % (1/12) | 49,2 % | **FAUX en M15** |
| M4 | Suivre la sortie de consolidation (« effet ») | 48,1 % (1/12) | 48,3 % (1/12) | **FAUX** |
| M4 | Intact cassé en clôture = continuation | 47,9 % (0/12) | 49,0 % | **FAUX en M15** |
| M5 | Liquidité prise en mèche = retournement | 49,9 % | 50,1 % | SANS EFFET |
| M7 | Spring / STB : achat après la prise basse | STB 52,2 % (11/12), Spring 50,3 % | STB 50,6 %, Spring 49,5 % | FAIBLE pour STB, sans effet pour Spring |
| M7 | UT / UTAD : vente après la prise haute | 50,2 % / 51,5 % | 51,6 % / 52,1 % | FAIBLE, peu d'observations |
| M7 | Imbalance / FVG : suivre le déséquilibre | 48,2 % (0/12) | 49,3 % | **FAUX en M15** |
| M7/M9 | Setups GOLDEN / CONCEPT déclenchés | 50,1 % / 52,2 % | 48,9 % / 50,0 % | SANS EFFET (CONCEPT : n = 984, ±3 points) |

**Ce que ces chiffres disent ensemble.** Tous les concepts qui consistent à **suivre une cassure** (BOS, intact cassé, sortie de cause, intention, FVG, breaker) font **moins bien que le hasard** en M15, sur presque tous les instruments. Les quelques effets positifs (zone décisionnelle touchée, STB, signature de liquidité) sont des entrées **à contre-mouvement**, après un repli. Le marché des changes en M15 est légèrement **retour-à-la-moyenne** : une cassure est plus souvent suivie d'un repli que d'une poursuite. En H1 l'effet s'atténue et presque tout devient indiscernable du hasard.

## Résultats : affirmations sur la liquidité

Part des niveaux pris dans les 200 bougies, selon la distance au prix quand le niveau devient connu (M15, 12 instruments ; H1 identique à ±1 point).

| Niveau | Distance < 1 ATR | 1 à 3 ATR | > 3 ATR |
|---|---|---|---|
| Pivot ordinaire (référence) | 95,0 % | 86,5 % | 66,0 % |
| M5 EQH/EQL, « doivent toujours sauter » | 95,5 % | 87,4 % | 68,1 % |
| M5 Inducement, « toujours pris avant de partir » | 92,9 % (n = 56) | 82,6 % | 61,0 % |
| M2 Signature de liquidité, « cible » | 96,0 % | 89,2 % | 63,8 % |

**Verdict : FAUX en tant que règle spéciale.** Un EQH/EQL, un inducement ou une signature ne sont pas pris plus souvent qu'un sommet ou un creux ordinaire à la même distance. « Toute liquidité finit par sauter » est vrai pour les niveaux proches, mais c'est vrai de **n'importe quel** niveau proche : c'est une propriété de la volatilité, pas un signal. Un inducement éloigné n'est pris que 6 fois sur 10.

## Résultats : cause et effet (M4)

« Plus la cause dure, plus l'effet est grand. » Amplitude du mouvement dans les 50 bougies après la sortie, en ATR :

| | Corrélation de rang durée / effet | Tiers des causes les plus courtes | Tiers des plus longues |
|---|---|---|---|
| M15 réel | +0,07 | 3,5 ATR | 4,5 ATR |
| M15 mélangé | -0,01 | 4,3 ATR | 4,4 ATR |
| H1 réel | -0,01 | 3,8 ATR | 4,0 ATR |

**Verdict : partiellement vrai en M15, faiblement** (corrélation 0,07, effet +1 ATR pour les causes longues) ; **sans effet en H1**.

## Synthèse : fausses idées et idées utiles

**Fausses idées (contredites par les données) :**
1. Suivre une cassure de structure (BOS de continuation ou de changement) en M15.
2. « Intact cassé en clôture » ou « sortie de cause » comme signal de continuation.
3. Le breaker comme zone de polarité inversée.
4. L'imbalance / FVG comme direction du prix.
5. Les EQH/EQL, l'inducement et la signature de liquidité comme niveaux qui « sautent toujours » plus que les autres.

**Idées sans effet mesurable :** le fail comme signal de retournement, la prise de liquidité en mèche comme retournement, l'order flow, le doji signature, le spring.

**Idées avec un effet faible mais régulier :** la première touche d'une zone décisionnelle (origine d'un BOS de changement), la zone avec bougie manipulatrice, l'achat après un STB, la direction de la mèche d'une signature, la durée de la cause en M15. Ce sont toutes des idées de **retour vers une zone**, pas de poursuite de cassure.

**Portée pour le trading.** Le meilleur effet (zone décisionnelle, +1,8 point sur une course de ±1 ATR) vaut environ 0,04 R par trade avant coûts. En M15, les coûts représentent environ 0,1 à 0,2 ATR, donc 0,1 à 0,2 R : ils effacent l'effet. Aucun concept, pris seul, n'est exploitable tel quel.

**Pistes fondées sur ces résultats (à tester sur des données neuves) :**
- conserver l'architecture « attendre le retour sur zone » et retirer tout ce qui suit une cassure ;
- n'utiliser que les zones décisionnelles (origine d'un BOS de changement) ;
- passer à une UT où les coûts pèsent moins (H1, H4), en vérifiant que l'effet y subsiste ;
- tester l'inverse des idées fausses en M15 (s'opposer à la cassure), en sachant que l'avantage brut (environ 2 points) reste inférieur aux coûts habituels.
