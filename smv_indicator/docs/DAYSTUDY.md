# DAYSTUDY.md : journée par journée, où et pourquoi les entrées « dans le sens de la tendance » échouent

**Question du trader.** Avec un indicateur qui donne la direction (les 80 %), on ne prend que les signaux dans ce sens. Cela ne marche pas assez : on tombe souvent à la fin du mouvement. Pourquoi ? Étude centrée sur EURUSD (2018-2019), contrôlée sur EURUSD 2015-2017 et 2020-2021, et sur XAUUSD 2018-2019.

**Signal étudié** (`research/daystudy/build_day.py`) : tendance de la structure H4 = direction ; chaque BOS M15 dans ce sens crée une zone ; entrée en limite au retour sur la zone, stop sous la mèche de la bougie qui prend l'argent ; issues à TP 2 R et 3 R, MFE sur 24 h.

## 1. Ce que montrent les journées (`docs/daystudy/*.png`)

Environ 2 entrées par jour de signal. Sur les journées tracées, trois schémas reviennent :
1. **Entrées empilées sur la même jambe** (29/01/2019 : 4 achats entre 6 h et 10 h, sur les BOS M15 n° 2 à 5). Un seul retournement emporte plusieurs stops.
2. **Entrées au bout de la jambe H4** (24/07/2019 : ventes au plus bas de la jambe H4, position 1,0, BOS M15 n° 11 et 14 ; 18/10/2019 : achats au sommet, 5e BOS H4, vendredi soir).
3. **Stops de 2 à 7 pips posés en séance asiatique**, balayés à l'ouverture de Londres ou de New York ; le prix repart parfois ensuite dans le sens prévu.

## 2. Ce que les chiffres en disent

| Cause des pertes (EURUSD 2018-2019, 639 entrées) | Part des entrées |
|---|---|
| Gagnant ou neutre (atteint +1 R ou pas stoppé) | 50 % |
| Retour normal contre l'entrée, sans cause identifiable | 20 % |
| Entrée en fin de mouvement H4 (haut de jambe ou 3e BOS H4 et plus) | 18 % |
| Stop trop serré (≤ 5 pips, touché en moins d'une heure) | 10 % |
| Pas de place (liquidité H4 à moins de 1 R) | 2 % |

- **Fin de mouvement** : un peu pire que le reste sur EURUSD 2015-2019 et sur l'or (XAUUSD : -0,46 R contre -0,25 R à TP 2 R), identique en 2020-2021. **Une fois ces entrées retirées, le reste reste négatif sur toutes les périodes.**
- **Stop chassé, puis le prix part dans le bon sens** : vrai pour 54 % des trades stoppés. Mais le prix part **aussi souvent de la même distance dans l'autre sens** (58 %). C'est la volatilité, pas un chasseur de stops : un stop de 8 pips vaut environ 1/8 de l'amplitude d'une journée EURUSD.
- **Élargir le stop** (de 0,5 à 1,5 ATR M15) réduit un peu le coût en R, mais la part des trades qui atteignent +1 R reste à 46-49 %.

## 3. La cause de fond : la direction H4 ne tient pas à l'échelle de la journée sur EURUSD

À chaque quart d'heure, de 2015 à 2022, j'ai mesuré dans quelle proportion le prix atteint d'abord +1 ATR H4 dans le sens de la tendance H4, plutôt que -1 ATR H4 :

| | EURUSD | XAUUSD |
|---|---|---|
| Global | **48,1 %** (n = 40 300) | **51,4 %** (n = 36 700) |
| Années au-dessus de 50 % | 2 sur 8 | 7 sur 8 (2016-2022 : 51 à 55 %) |
| Selon l'âge du dernier BOS H4, le rang du BOS, la position dans la jambe ou l'heure | 45 à 50 % partout | 50 à 52 % partout |

« Suivre les 80 % » suppose que le sens de la tendance H4 prévoit la suite des prochaines heures. **Sur EURUSD, il ne la prévoit pas** : la probabilité est même légèrement inférieure à 50 %, ce qui confirme le léger retour à la moyenne déjà mesuré en M15 (MODULES_TEST). Aucun filtre d'entrée ne peut corriger une direction qui vaut pile ou face. Sur l'or, la tendance H4 tient un peu, de façon régulière : c'est l'instrument où l'idée de départ a une base.

## 4. Conséquences

1. Le problème n'est pas d'abord le timing de l'entrée. Sur EURUSD, la prémisse directionnelle elle-même est absente à l'échelle intrajournalière.
2. Pour un scalpeur qui suit la tendance, **XAUUSD est le bon terrain** (persistance faible mais stable sur sept ans).
3. La prochaine étape logique, sur l'or uniquement : chercher les contextes où la persistance dépasse 55 %, puis seulement ensuite placer entrée, stop (hors de la zone balayée) et sortie.
