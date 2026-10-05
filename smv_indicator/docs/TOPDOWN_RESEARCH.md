# TOPDOWN_RESEARCH.md : méthode combinée des modules 1 à 5 (zone en grande UT, entrée en petite UT)

**Demande.** Tester la combinaison enseignée dans les modules 1 à 5, sans cible imposée ni filtre horaire : combien de R le prix donne en moyenne, et combien de trades par jour. Les décisions (cible, horaires) seront prises après.

**Réponse courte (exploratoire, 2012-2022, 12 instruments, entrée M15).**
- **Fréquence** : 0,5 à 0,9 trade par jour pour le panier de 12 instruments, et non 3 à 5. La petite UT M15 est le facteur limitant ; le M5 (données à exporter de MT5) donnerait plus d'occasions.
- **R atteints** : la part des trades qui atteignent k R avant le stop est **égale ou inférieure au hasard** pour tout k (1 R : 48 % contre 50 % ; 3 R : 21 % contre 25 %). MFE médiane : 0,9 R ; MFE moyenne : 2 R, tirée par une queue de grands mouvements que le hasard produit aussi.
- **Espérance** : brute proche de zéro pour tous les TP (-0,03 à +0,07 R) ; **nette de -0,10 à -0,20 R** avec un coût d'environ 0,13 R (stop médian de 12 pips).
- Aucune variante (prise de liquidité imposée, séquence complète fail puis prise) ni aucune heure ne donne un résultat stable entre 2012-2019 et 2020-2022.

## 1. Les règles codées (`research/topdown/build_td.py`, v1.1)

| Étape | Module | Règle |
|---|---|---|
| Biais | 1 | tendance de la structure majeure HTF (H4 ou H1, agrégées depuis le M15, bougies closes) |
| Zone | 2-3 | zone HTF active, décisionnelle (origine d'un BOS de changement), dans le sens du biais ; bord proximal = bougie manipulatrice, distal = mèche de la bougie qui prend l'argent |
| Armement | 3 | une bougie M15 touche la zone HTF sans la casser ; armement 16 h |
| Intention | 4 | BOS de changement de tendance M15 dans le sens du trade pendant l'armement |
| Fail, prise de liquidité | 4-5 | enregistrés (has_fail, has_sweep, strict = fail puis prise) et testés comme filtres |
| Entrée | 2-3, 5 | ordre limite au bord proximal de la zone M15 créée par ce BOS ; stop au bord distal ; ordre valable 16 h, annulé si la zone casse |
| Sortie | 4-5 | aucune cible : MFE avant stop, TP fixes 1 à 5 R, premier intact M15, premier intact HTF ; horizon 24 h |

Conventions prudentes : sur la bougie de remplissage seul le stop compte ; stop et cible dans la même bougie = stop ; un trade à la fois par instrument. Coût = écart nominal de la recherche (1 pip sur les majeures).

**Deux corrections faites pendant le test, documentées :**
- la séquence stricte imposée (fail, puis prise, puis BOS) ne donnait que 11 trades en 9 ans sur EURUSD : elle est devenue une variante mesurée ;
- la v1.0 annulait l'ordre si le prix atteignait +1 R avant l'entrée ; au moment du BOS, le prix est presque toujours déjà au-delà, et 85 % des ordres étaient annulés à tort.

Entonnoir (EURUSD, zone H1) : 901 touches de zone HTF, 186 BOS M15 pendant l'armement, 177 ordres, 104 remplis.

## 2. Résultats (2012-2019 ; 2020-2022 entre parenthèses)

| | Zone H4, entrée M15 | Zone H1, entrée M15 |
|---|---|---|
| Trades | 1 213 (519) | 1 020 (407) |
| Trades par jour, panier de 12 | 0,62 (0,92) | 0,54 (0,72) |
| Stop médian | 12 pips | 12,6 pips |
| P(MFE ≥ 1 / 2 / 3 / 5 R), hasard 50 / 33 / 25 / 17 % | 48 / 32 / 21 / 11 % | 48 / 29 / 20 / 10 % |
| Espérance brute TP 2 R / 3 R | +0,07 / +0,04 R (-0,03 / -0,03) | -0,02 / -0,01 R (+0,02 / -0,02) |
| Espérance nette TP 3 R | -0,13 R (-0,23) | -0,17 R (-0,20) |
| Premier intact M15 : distance médiane, atteint | 2,3 R, 34 % | 2,2 R, 32 % |
| Instruments positifs à TP 3 R (net) | 3/12 | 2/12 |

Variantes : imposer la prise de liquidité ne change rien. La séquence complète (fail puis prise) ne laisse que 0,07 trade par jour ; elle est négative en 2012-2019 (-0,05 R net à TP 3 R en H4) et positive en 2020-2022 sur 53 à 59 trades, ce qui reste dans le bruit.

Heures (Paris) : 20 à 100 trades par heure ; les heures positives d'une configuration sont négatives dans l'autre. Aucun créneau défendable.

Note : la référence « hasard » 1/(1+k) ignore l'horizon de 24 h ; pour k ≥ 4, le vrai hasard est un peu plus bas. Cela ne change pas la lecture pour k ≤ 3.

## 3. Lecture

1. Telle que codée, la combinaison zone HTF + intention M15 n'apporte pas d'information sur la suite du prix : les R atteints suivent la loi du hasard.
2. **Cette conclusion porte sur ma traduction en règles.** Une lecture discrétionnaire peut différer : choix de la zone, de la bougie manipulatrice, inducement, timing. Avant d'aller plus loin, il faut vérifier sur des graphiques que les trades codés sont ceux que le trader aurait pris.
3. La fréquence voulue (3 à 5 par jour) demande une entrée en M5, ou un panier plus large.

## 4. Suite proposée

1. **Audit visuel** : 20 trades tirés au hasard, tracés avec les zones et les événements, pour que le trader dise « je l'aurais pris » ou non, et pourquoi.
2. **Données M5** : `mt5/Scripts/SMV/SMV_ExportBars.mq5` exporte les bougies M5 et l'écart réel du courtier (Deriv, depuis 2018), pour tester l'entrée en M5 comme dans le cours.
3. Ajuster les règles **uniquement** sur les écarts constatés à l'audit, puis tester sur des données non utilisées.
