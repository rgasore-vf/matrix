# XAU_RESEARCH.md : sur l'or, quand la tendance H4 tient-elle, et les entrées M15 en profitent-elles ?

**Données** : XAUUSD M15, H4 et D1 du courtier, 2013 → mars 2022. Entraînement 2013-2017, validation 2018-2019, test 2020-2022.
**Réserve** : les tables par contexte des trois périodes ont été affichées ensemble avant que je choisisse la règle lisible ; le test 2020-2022 n'est donc pas vierge pour cette règle. Le modèle LightGBM, lui, n'a vu que 2013-2017 (arrêt précoce sur 2018-2019).

Correction de données : sur l'or, l'agrégation UTC depuis le M15 perdait une bougie H4 par jour et toutes les bougies D1, à cause de la pause quotidienne. Les bougies H4 et D1 du courtier sont utilisées à la place.

## 1. Persistance de la tendance H4 (course ±1 ATR H4, 24 h ; `research/xau/build_ctx.py`, `analyze_ctx.py`)

| | 2013-2017 | 2018-2019 | 2020-2022 |
|---|---|---|---|
| Sans condition | 52,3 % | 52,7 % | 50,0 % |
| D1 dans le même sens | 52,9 % | 53,5 % | 50,9 % |
| D1 aligné + volatilité H4 basse (≤ 0,95 x moyenne) + 6 h-14 h (Paris) + jour < 0,6 x l'amplitude moyenne | **54,8 %** | **55,7 %** | **55,1 %** |
| LightGBM, 10 % des moments les mieux notés | 70,6 % | 57,3 % | 56,9 % |

Ces pourcentages portent sur des observations toutes les 30 minutes, qui se recouvrent fortement : l'effectif réel est bien plus petit que le nombre de lignes.

## 2. Les entrées M15 dans ce contexte

Pour les BOS M15 dans le sens H4, avec entrée au retour sur la zone et stop sous la bougie qui prend l'argent (stop médian 1,6 à 2,2 $) : **elles ne s'améliorent pas dans le contexte favorable** (TP 2 R net : -0,22 / -0,58 / -0,27 R dans le contexte, contre -0,18 / -0,36 / -0,13 R en dehors). L'avantage directionnel se mesure à l'échelle d'un ATR H4 (environ 10 à 25 $). Avec un stop de 2 $, le bruit et le coût (0,15 à 0,28 R) dominent.

## 3. Le trade à l'échelle H4 (`research/xau/ctx_trade.py`)

Première bougie du jour où le contexte est vrai, entrée à l'ouverture suivante, stop 1 ATR H4, horizon 48 h, net du coût.

| | 2013-2017 | 2018-2019 | 2020-2022 |
|---|---|---|---|
| Règle lisible, TP 2 ATR (environ 80 trades par an) | +0,11 R | +0,04 R | +0,01 R |
| LightGBM top 10 %, TP 2 ATR | +0,41 R (entraînement) | +0,13 R | +0,02 R |

L'avantage décroît avec le temps : positif jusqu'en 2017, faible en 2018-2019, nul en 2020-2022, négatif en 2021-2022.

## 4. Conclusion

1. Sur l'or, la tendance H4 a tenu un peu plus que le hasard, surtout quand le D1 va dans le même sens et que la volatilité est calme. L'effet est faible et il s'est effacé après 2019 dans ces données.
2. Filtrer les entrées M15 par ce contexte n'améliore pas les entrées à stop serré : le scalping sur la structure M15 ne profite pas d'un avantage qui n'existe qu'à l'échelle H4.
3. La période 2022-2026, absente de ces données, a connu une tendance haussière exceptionnelle sur l'or. La règle lisible est figée ici ; seul un test sur cette période (coffre-fort MT5, sans réglage) dira si l'effet revient quand le marché tend.
