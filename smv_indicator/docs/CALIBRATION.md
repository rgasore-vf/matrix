# CALIBRATION.md : réponses aux questions Q-01 à Q-16, mesures et provenance

> **Errata après audit (voir §6 et `CLAUDE_REVIEW_OF_GPT_AUDIT.md`).** Les chiffres des sections 2 et 4 sont ceux de la v0.2, avant les corrections de l'audit. Les valeurs recalculées sont au §6. Les réponses sont des choix de formalisation argumentés, pas la reconstitution certaine des règles de la formation.

Ce document répond aux seize questions ouvertes de `STRATEGY_SPEC.md` §13. Le responsable de la stratégie a tranché une seule question : la plateforme cible est MetaTrader 5. Les quinze autres réponses viennent de trois sources, toujours signalées :

| Étiquette | Sens |
|---|---|
| **DÉPÔT** | énoncé ou montré dans `Strategie/` (transcriptions, diapositives) |
| **RECHERCHE** | définition ou résultat externe documenté dans `RESEARCH.md` |
| **MESURE** | résultat obtenu ici sur données réelles, reproductible avec `research/` |
| **PROPOSITION** | choix de formalisation sans appui suffisant ; à revoir avec de meilleures données |

Une réponse MESURE n'est pas une preuve d'avantage. Plusieurs mesures ci-dessous montrent au contraire que l'effet supposé par le dépôt n'est pas distinguable du hasard. Ces résultats sont rapportés tels quels.

---

## 1. Données et méthode

**Données.** Dépôt public `ejtraderLabs/historical-data` (GitHub), cloné hors du projet et non versionné. EURUSD et XAUUSD en M15, H1, H4 et D1 ; dix autres paires en D1 pour la fenêtre mensuelle. Période de calibrage : 2015-01-01 à 2022-01-01 (173 889 bougies M15 EURUSD, 164 494 XAUUSD). Fiabilité : données de courtier, volumes en ticks, non auditées ; elles suffisent pour des distributions de formes de bougies et des courses de prix, pas pour estimer des coûts d'exécution.

**Horodatage.** Heure serveur EET/EEST (règles européennes, fuseau `Europe/Athens`), déduite de la clôture hebdomadaire et vérifiée sur les pics de volatilité (ouverture de Londres, chiffres américains de 8 h 30 ET). Une première hypothèse « New York + 7 h » décalait d'une heure les semaines où les heures d'été européenne et américaine sont désynchronisées ; elle a été rejetée (`research/marketdata.py`).

**Modèles nuls.** Deux références sont utilisées systématiquement :
1. **ruine du joueur** : sur une marche aléatoire sans dérive, une course entre une distance favorable `k` et une distance défavorable `h` est gagnée avec la probabilité `h / (h + k)`. Un taux de réussite n'a de sens qu'en excès sur cette valeur ;
2. **bougies mélangées** : même série de bougies (corps, mèches, amplitudes) dans un ordre aléatoire. La dépendance temporelle disparaît, la distribution des formes reste. Un « excès » qui subsiste sur la série mélangée vient de la méthode de mesure, pas du marché.

**Intervalles.** Proportions : intervalle de Wilson à 95 %. Moyennes de R : ±1,96 écart-type / √n.

**Limites communes.** Deux instruments, sept ans, un seul courtier. Les tests sont nombreux : un résultat isolé significatif à 95 % est attendu par hasard environ une fois sur vingt. Aucune optimisation de paramètres n'a été faite sur les issues des trades ; les seuils ont été fixés à partir de distributions descriptives ou de la recherche, avant le backtest.

---

## 2. Réponses

### Q-01 Lecture A ou B de la structure majeure (R-ST-04)

**Réponse : lecture A par défaut** (niveau protégé = origine du dernier BOS). Lecture B conservée en option.

- **DÉPÔT** : A est soutenue par M1, M3 et M9 et par la diapositive « structure majeure et mineure » ; B par M5 et M8 (DECISIONS D-07).
- **RECHERCHE** : les définitions SMC courantes (« si un bas casse un haut, ce bas est protégé ») placent le niveau protégé à l'origine de la dernière cassure ; c'est la lecture A (RESEARCH §8.1).
- **MESURE** (H1, 2015-2021) : en lecture B, EURUSD ne produit qu'un BOS de changement de tendance en sept ans et XAUUSD quatre (A : 631 et 574). La structure B se fige dès que le prix s'éloigne du niveau protégé initial. Elle ne peut pas servir de lecture de structure à l'UT de travail.
- **Interprétation (PROPOSITION)** : B ressemble à une lecture de l'UT supérieure faite sur l'UT basse ; c'est cohérent avec la fractalité du dépôt (M1/7). Pour cet usage, l'indicateur offre la lecture A sur une UT supérieure (`InpHtf`).

### Q-02 Critère de bougie « pleine ou presque pleine » (R-CA-01)

**Réponse : corps ≥ 70 % de l'amplitude** (`bm_body_min = 0.7`).

- **RECHERCHE** : les définitions de « displacement » et de bougie d'impulsion citent un corps de 60 à 80 % de l'amplitude (RESEARCH §8.5).
- **MESURE** : 70 % correspond environ au quintile supérieur des bougies M15 (percentile 75 : 0,68 ; percentile 90 : 0,83 sur EURUSD), donc à « une des bougies les plus pleines » sans être exceptionnel.
- **MESURE (portée)** : la présence d'une BM ne change pas la réaction de la zone (H1 EURUSD, seuil 0,7 : 0,690 avec BM, 0,692 sans ; XAUUSD : 0,679 et 0,696). Le seuil ne sert donc qu'à reproduire le tracé du dépôt (bord proximal), pas à filtrer.

### Q-03 Bord proximal : corps ou mèche de la BM (R-OD-01)

**Réponse : corps** (`zone_proximal = "body"`).

- **DÉPÔT** : la diapositive M2 trace la zone du corps de la BM à la mèche de la BQA.
- **MESURE** : l'écart de hauteur médiane entre les deux options est inférieur à 0,1 ATR (M15 2019-2020 EURUSD : 1,34 contre 1,38 ATR). Le choix est sans conséquence pratique ; le dépôt tranche.

### Q-04 Une zone doit-elle exister sans BOS (R-OD-01)

**Réponse : non**, zones à l'origine des BOS seulement (`zones_on = "bos_origin"`). L'option `all_pivots` reste disponible.

- **DÉPÔT** : la zone n'est « valide » qu'après les cassures (M2, M3).
- **MESURE** : course « +1 ATR avant clôture au-delà du bord distal » après la première touche. Zones de BOS (H1) : 0,691 de réussite contre 0,580 attendu sous la ruine du joueur, soit +0,11. **Mais la même mesure sur bougies mélangées donne +0,09 à +0,11** (EURUSD et XAUUSD, deux tirages). L'excès vient de l'asymétrie de la course (cible touchée en mèche, invalidation en clôture), pas d'une propriété des zones. Les zones de tous les pivots ne montrent aucun excès (+0,01 réel, -0,02 mélangé).
- **Conclusion** : le choix repose sur le texte du dépôt. Les données ne montrent pas que les zones de BOS « tiennent » mieux que le hasard.

### Q-05 Zone « décisionnelle » (R-OD-02)

**Réponse : provisoirement, origine d'un BOS de changement de tendance** (champ `decisional`), sans effet sur le calcul.

- **DÉPÔT** : « la zone à l'origine du swing majeur », non définie plus précisément.
- **MESURE** : BOS de changement 0,712 (H1 EURUSD) contre 0,681 pour les continuations, avec des attendus nuls différents (0,607 et 0,566) ; l'excès est le même (+0,10 et +0,12). Pas de différence mesurable.
- Statut : marqueur descriptif, à confirmer par le responsable de la stratégie.

### Q-06 Invalidation d'une zone (R-OD-03)

**Réponse : clôture au-delà du bord distal.** Une zone peut être touchée plusieurs fois avant cela.

- **DÉPÔT** : « un POI peut être mitigé plusieurs fois » (M3) ; le BOS se valide en clôture (M1/10), et la même logique est appliquée au bord distal.
- **RECHERCHE** : ICT invalide souvent un order block à la clôture au-delà de son « mean threshold » (50 %). C'est une règle plus stricte, documentée en option future (RESEARCH §8.2) et non retenue parce que le dépôt ne l'enseigne pas.

### Q-07 Tolérance des EQH/EQL (R-LQ-03)

**Réponse : 0,1 ATR** (`eq_tol_atr = 0.1`), même côté, niveau encore intact, au plus 500 bougies d'écart.

- **RECHERCHE** : des indicateurs SMC publics proposent une tolérance réglable en ATR, avec 0,10 par défaut (RESEARCH §8.3).
- **MESURE** : avec 0,1 ATR, 8,4 % (EURUSD) et 7,2 % (XAUUSD) des paires de pivots consécutifs de même côté sont « égaux ». Le seuil reste sélectif.
- **MESURE (affirmation du dépôt)** : « les EQH/EQL devront toujours sauter » n'est pas vérifié. À distance égale, un niveau EQ n'est pas pris plus souvent qu'un pivot ordinaire dans les 200 bougies H1 (distance < 1 ATR : 0,913 contre 0,954 sur EURUSD ; 0,901 contre 0,951 sur XAUUSD). Les EQ sont un marqueur de lecture, pas une cible privilégiée.
- **Cas limite** : un second sommet qui dépasse le premier n'est pas un EQH, c'est une prise de liquidité (DECISIONS D-11). Conservé.

### Q-08 « Perte d'intensité » d'une rotation (R-ST-09)

**Réponse : marqueur seulement** ; trois impulsions d'amplitude strictement décroissante (`rotation_legs = 3`), sans effet sur les autres couches.

- **DÉPÔT** : exemples de mesures en pips, non strictement décroissantes (73, 71, 55, 58).
- **MESURE** : probabilité d'un BOS de changement de tendance dans les 40 bougies H1 après trois jambes décroissantes : 0,297 à 0,321 (EURUSD), contre 0,289 à 0,291 sans décroissance ; XAUUSD : 0,288 à 0,296 contre 0,272 à 0,273. L'effet est de l'ordre de 2 points, à la limite des intervalles. Il ne justifie pas une règle.

### Q-09 Quel extrême est « le high/low du mois » (R-OU-02)

**Réponse : aucun biais calculé.** L'indicateur trace le plus haut et le plus bas de la fenêtre du 26 au 9 (heure de Paris), confirmés à la fin de la fenêtre.

- **MESURE** (D1, 12 instruments, 1 321 mois) : l'un des deux extrêmes du mois tombe dans la fenêtre dans 89,9 % des mois. Sous le modèle nul (rendements journaliers permutés dans chaque mois), la proportion est déjà de 87,2 %.
- **Explication (RECHERCHE)** : loi de l'arcsinus. Pour une marche aléatoire, les extrêmes se concentrent près des bords de l'intervalle ; une fenêtre qui couvre le début du mois les contient souvent par construction. L'observation du dépôt est vraie, mais elle ne contient presque aucune information.

### Q-10 Heures de tir (R-OU-01)

**Réponse : ancrages mesurés, exprimés dans le fuseau de chaque place** (`session_mode = "measured"`). Les heures du dépôt restent disponibles (`"repo"`).

| Session | Ancrage (heure locale) | Heure de Paris | Appui |
|---|---|---|---|
| ASIA | 10:00 Tokyo | 2 h (hiver), 3 h (été) | MESURE ; fixing de Tokyo à 9 h 55 (RECHERCHE) |
| EUROPE | 08:00 Londres | 9 h toute l'année | MESURE |
| US_DATA | 08:30 New York | 14 h 30 ; 13 h 30 pendant la désynchronisation | MESURE ; publications américaines (RECHERCHE) |
| US_10H | 10:00 New York | 16 h ; 15 h pendant la désynchronisation | MESURE |

- **MESURE** (M15 2015-2021, volatilité relative par quart d'heure) : les pics sont 14:30, 16:00 et 16:45 à Paris en hiver comme en été, et 13:30 pendant les semaines désynchronisées ; 9:00 est un pic toute l'année. Le pic de 9 h ne change pas d'heure en été, contrairement au « 8 h l'été » du dépôt. 4 h (« Tokyo ») n'est pas un pic.
- **DÉPÔT (erreurs factuelles)** : le décalage New York / Chicago est d'une heure, pas de deux (RESEARCH §4).
- Ces heures sont des **marqueurs**. Le dépôt dit qu'on peut trader avant comme après ; aucune heure n'est un filtre.

### Q-11 Définition opérationnelle du « test » (R-GS-03)

**Réponse : retour sur la zone créée par le BOS d'intention dans les 10 bougies** (`test_max_bars = 10`) ; sinon le setup golden expire.

- **RECHERCHE** (sources de praticiens, fiabilité C/D, RESEARCH §8.6) : un spring valide revient dans la fourchette en 1 à 5 bougies, le plus souvent citées « 3 à 5 » ; au-delà de 5 clôtures dehors, il s'agit plutôt d'une vraie cassure. Les sources de référence (Wyckoff Analytics, StockCharts) disent seulement « rapidement », sans nombre. Cette fourchette fonde `range_accept_bars = 3`.
- **PROPOSITION** : aucune source vérifiée ne chiffre le délai du **test** après le spring. 10 bougies = deux fois la fenêtre de récupération la plus longue citée. La mesure est faite en bougies de l'UT d'analyse. À revoir avec des exemples du formateur.

### Q-12 Plafond de stop (R-SE-02)

**Réponse : 2,5 ATR(14) de l'UT d'entrée** (`sl_max_atr = 2.5`). Un setup dont le risque dépasse ce plafond est journalisé avec `rejected = "sl_too_wide"` ; il n'est ni tracé ni suivi.

- **DÉPÔT** : « 16 pips, toujours dans la stratégie » ; « 20 pips, ça ne rentre pas » (M9, M10), sans unité normalisée entre l'EURUSD et l'or.
- **MESURE** : ATR(14) M15 médian de l'EURUSD = 6,6 pips ; 2,5 ATR ≈ 16,5 pips. Le plafond exprimé en ATR reproduit l'exemple du dépôt et s'adapte à la volatilité et à l'instrument.

### Q-13 « Market shift », « Fibonacci SMC », « complexe pullback »

**Réponse : non implémentés.** Ces notions sont citées dans M9 mais jamais enseignées dans le dépôt.

- **RECHERCHE** (définitions externes, RESEARCH §2.2, §2.5 et §8.4) : market structure shift (ICT) = variante du CHoCH qui exige un déplacement rapide, avec des définitions qui varient selon les sources ; « Fibonacci SMC » = premium/discount autour de l'équilibre à 50 % de la jambe et zone OTE de 62 à 79 %. Pour « complexe pullback », aucune définition sourcée n'a été trouvée ; l'usage oral le plus fréquent (retracement en plusieurs jambes) reste une interprétation non vérifiée.
- **DÉPÔT (déduit d'un exemple, M9)** : « market shift » y semble désigner le retour sur un niveau de swing cassé, suivi d'une réaction (changement de polarité).
- Coder l'une de ces définitions imposerait une lecture que le dépôt ne donne pas. Elles restent documentées.

### Q-14 Théorie du décompte neutre

**Réponse : reconstruite à partir des diapositives M8**, la vidéo théorique M8/1 étant un doublon de M7/1. Bornes BC (haut) et SC (bas) = liquidité externe ; UT au-dessus, STB en dessous ; entrée sur le test après la prise de liquidité externe. Implémentation : `RangeTracker`, qui compte les prises par côté et étiquette les candidats (STB, SPRING, UA ; UT, UTAD, MSO). Le statut reste **expérimental**.

### Q-15 Critère de taille de la BM

**Réponse : aucun** (`bm_range_atr` désactivé). Voir Q-02 : la BM n'a pas d'effet mesuré sur la réaction ; un seuil de taille ajouterait un paramètre sans appui.

### Q-16 Pivots : combien de bougies de chaque côté selon l'UT

**Réponse : 2 à gauche et 2 à droite, sur toutes les UT** (fractal de Williams).

- **RECHERCHE** : fractal de Bill Williams (2 + 2).
- **MESURE** : la distribution des jambes entre pivots exprimée en ATR est presque identique de M15 à D1 pour un même N (N = 2 : jambe médiane 2,21 ATR en M15, 2,40 en H4, 2,25 en D1 ; 4,5 à 4,7 bougies par jambe). La structure étant auto-similaire en unités d'ATR, il n'y a pas de raison de changer N avec l'UT. Retard de confirmation d'un pivot : 2 bougies.

---

## 3. Paramètres retenus

Les valeurs ci-dessous sont celles de `smv/config.py` et des entrées de `SMV_Indicator.mq5`.

| Paramètre | Valeur | Provenance | Question |
|---|---|---|---|
| `pivot_left`, `pivot_right` | 2, 2 | RECHERCHE + MESURE | Q-16 |
| `major_mode` | A | DÉPÔT + RECHERCHE + MESURE | Q-01 |
| `bos_eps` | 0 | DÉPÔT | — |
| `atr_len` | 14 | RECHERCHE | — |
| `bm_body_min` | 0,7 | RECHERCHE + MESURE | Q-02 |
| `bm_range_atr` | désactivé | MESURE | Q-15 |
| `zone_proximal` | corps | DÉPÔT + MESURE | Q-03 |
| `zones_on` | origines des BOS | DÉPÔT | Q-04 |
| `eq_tol_atr` | 0,1 | RECHERCHE + MESURE | Q-07 |
| `eq_max_gap` | 500 | PROPOSITION | Q-07 |
| `range_accept_bars` | 3 | RECHERCHE (praticiens) | Q-11 |
| `test_max_bars` | 10 | PROPOSITION | Q-11 |
| `sl_max_atr` | 2,5 | DÉPÔT + MESURE | Q-12 |
| `setup_expiry_bars` | 100 | PROPOSITION | — |
| `rotation_legs` | 3 | PROPOSITION + MESURE | Q-08 |
| `session_mode` | measured | MESURE | Q-10 |
| `doji_body_max` | 0,1 | RECHERCHE (Nison) + MESURE (décile inférieur) | — |
| `doji_window`, `liqsig_wick_min`, `odf_min_len`, `session_window_min` | 2 ; 0,5 ; 2 ; 60 | PROPOSITION | — |

---

## 4. Backtest des setups (couche R-SE)

**Question.** Les setups produits par le moteur ont-ils une espérance positive après coûts, et font-ils mieux que le hasard ?

**Protocole.**
- Setups GOLDEN (consolidation ouverte, prise sur la borne opposée au trade, BOS dans le sens du trade, test de la zone dans les 10 bougies) et CONCEPT (inducement pris dans la tendance, BOS de continuation, retour sur la zone dans les 100 bougies).
- Entrée limite au bord proximal, stop au bord distal, sortie totale sur la première liquidité intacte au-delà de l'entrée.
- Ordre intra-bougie inconnu, deux règles prudentes : stop prioritaire si le stop et la cible sont dans la même bougie ; sur la bougie de déclenchement, seul le stop est évalué.
- Coûts (HYPOTHÈSES de compte ECN, à remplacer par ceux du courtier) : 1,0 pip aller-retour sur EURUSD, 0,35 $ sur l'or.
- Échantillon 2015-2021, découpé en 2015-2018 et 2019-2021. Résultats complets : `research/results_setups.json`.

**Résultats** (R moyen par trade ; ± = demi-largeur de l'intervalle à 95 %) :

| Série | n | Taux de réussite | Attendu (ruine du joueur) | R brut | R net |
|---|---|---|---|---|---|
| EURUSD M15 réel | 321 | 0,296 | 0,321 | -0,02 ± 0,20 | -0,17 |
| EURUSD M15 mélangé (1) | 294 | 0,313 | 0,382 | -0,15 ± 0,20 | -0,25 |
| EURUSD M15 mélangé (2) | 310 | 0,329 | 0,354 | -0,07 ± 0,17 | -0,17 |
| XAUUSD M15 réel | 246 | 0,268 | 0,307 | -0,12 ± 0,22 | -0,33 |
| XAUUSD M15 mélangé (1) | 242 | 0,368 | 0,366 | +0,08 ± 0,22 | -0,08 |
| XAUUSD M15 mélangé (2) | 260 | 0,435 | 0,369 | +0,13 ± 0,19 | -0,03 |
| EURUSD H1 réel | 121 | 0,273 | 0,334 | -0,29 ± 0,24 | -0,36 |
| XAUUSD H1 réel | 70 | 0,300 | 0,355 | -0,21 ± 0,34 | -0,31 |

**Lecture.**
1. Aucune série réelle ne montre d'espérance positive après coûts. Les taux de réussite réels sont **au niveau ou en dessous** du modèle nul de la ruine du joueur.
2. Les séries mélangées, sans aucune structure de marché, ne font pas moins bien que les séries réelles. Rien n'indique que les setups exploitent une propriété du marché.
3. Seul sous-groupe positif : CONCEPT sur EURUSD M15 réel (n = 51, +0,52 ± 0,60 R brut, +0,41 net), positif sur les deux sous-périodes. L'intervalle contient zéro ; le même sous-groupe est négatif sur XAUUSD (-0,22 R) et parmi une vingtaine de sous-groupes examinés, un résultat de cette taille est attendu par hasard. **Ce n'est pas une preuve** ; c'est la seule piste qui mérite un test hors échantillon sur d'autres instruments et une autre période.
4. Une première version du backtest comptait la cible sur la bougie de déclenchement. Elle « gagnait » sur les séries mélangées (84 % de réussite pour un attendu de 64 % dans la tranche RR < 1). Le biais d'ordre intra-bougie a été corrigé avant les résultats ci-dessus. Cet incident montre pourquoi chaque mesure doit être confrontée à un modèle nul.

**Portée.** Ce backtest évalue **une formalisation mécanique** de la stratégie, pas la pratique discrétionnaire du formateur. Le dépôt insiste sur la sélection du contexte (zone décisionnelle de l'UT supérieure, confluences multi-UT, raffinage) que le moteur ne reproduit pas. La conclusion honnête est double : (a) les règles explicites du dépôt, codées telles quelles, ne suffisent pas à produire un avantage mesurable ; (b) s'il existe un avantage, il réside dans des éléments discrétionnaires qui restent à formaliser et à tester.

**Conséquence pour l'indicateur.** Les setups sont affichés comme des **repères de lecture** et sont désactivables. Ils ne doivent pas être utilisés comme signaux automatiques sans validation supplémentaire.

---

## 5. Ce qu'il faudrait pour aller plus loin

| Priorité | Travail | Pourquoi |
|---|---|---|
| 1 | Test hors échantillon de CONCEPT (EURUSD) sur 2022-2025 et sur d'autres paires, avec les coûts réels du courtier | seule piste positive, non confirmée |
| 2 | Filtre de contexte multi-UT (zone de l'UT supérieure, biais de l'UT supérieure) appliqué aux setups, défini AVANT de regarder les résultats | c'est l'élément discrétionnaire que le dépôt juge essentiel |
| 3 | Comparaison avec des setups tracés par le formateur sur les mêmes dates | mesurer l'écart entre la formalisation et la pratique |
| 4 | Données à ticks pour l'ordre intra-bougie | lever les deux hypothèses prudentes du backtest |
| 5 | Correction pour comparaisons multiples (par exemple Benjamini-Hochberg) et probabilité de surapprentissage (Bailey et al.) dès que des paramètres sont optimisés | éviter de retenir un sous-groupe chanceux |

---

## 6. Errata et valeurs recalculées après l'audit indépendant

Les études ont été relancées sur les mêmes données (`research/DATA_MANIFEST.json`) avec le moteur et les scripts corrigés. Détail et lecture : `CLAUDE_REVIEW_OF_GPT_AUDIT.md` §4.

| Question | Valeur v0.2 | Valeur recalculée | Effet sur la réponse |
|---|---|---|---|
| Q-04 | excès +0,11 réel, +0,09 à +0,11 mélangé | +0,10 à +0,12 réel, +0,08 à +0,09 mélangé (nul avec gaps) | réponse inchangée ; écart résiduel de 2 à 3 points à confirmer |
| Q-07 | EQ pris moins souvent (0,913 contre 0,954) | EQ pris aussi souvent (0,952 contre 0,948 EURUSD ; 0,941 contre 0,946 XAUUSD) | « les EQ sautent toujours » reste non vérifié ; l'ancien écart était un artefact |
| Q-08 | « marqueur seulement » | aucun marqueur n'existe dans le moteur | **la rotation n'est pas implémentée** ; `rotation_legs` n'est consommé par aucun module |
| Q-09 | 0,899 contre 0,872 | 0,853 contre 0,813 | excès de 4 points, dépendances non traitées ; toujours aucun biais |
| Q-12 | 2,5 ATR « reproduit » 16 pips | inchangé | la correspondance porte sur une médiane ; elle ne prouve pas que la règle du formateur est en ATR |
| Q-16 | « structure indépendante de N » | faux | la structure majeure dépend de N par la référence de continuation et le fail |
| §4 | EURUSD M15 -0,02 R brut ; CONCEPT +0,52 R | EURUSD M15 -0,05 R brut ; CONCEPT +0,52 R mais +0,72 R sur une série mélangée | aucune piste positive retenue |

---

## 7. Ajustement de la stratégie à partir des pertes (protocole avec validation)

**Objectif.** Trouver où la formalisation perd et l'ajuster, sans fabriquer une stratégie qui ne gagne que sur l'historique (surapprentissage). Scripts : `research/setup_dataset.py` et `research/adjust/`.

**Protocole, fixé avant les résultats.**
1. Développement : EURUSD et XAUUSD M15, 2012 à 2018. Diagnostic, hypothèses, choix.
2. Gel des règles.
3. Validation 1 : EURUSD et XAUUSD, 2019 à mars 2022. Période partiellement vue, car ses résultats agrégés avaient été consultés en v0.2.
4. Validation 2 : dix paires jamais regardées (GBPUSD, AUDUSD, USDCAD, USDCHF, EURGBP, EURCHF, USDJPY, EURJPY, GBPJPY, AUDJPY), 2012 à 2022, coûts hypothétiques de compte ECN (`setup_dataset.COST`).

**Diagnostic (développement, 459 trades, -0,32 R net par trade).**
- Les setups GOLDEN étiquetés UA (-0,77 R, 15 % de réussite pour 28 % attendus au hasard) et MSO (-0,17 R) sont des ventes dans une accumulation et des achats dans une distribution, **contraires au schéma** du dépôt (M7/1 : achat après STB/spring en accumulation, vente après UT/UTAD en distribution). C'était un écart de formalisation.
- Achat dans la moitié haute de la jambe H4, ou vente dans la moitié basse : -0,51 R ; dans le bon sens : -0,03 R.
- 25 % des perdants avaient atteint +1 R avant le stop.

**Hypothèses testées en développement.**

| Variante | Trades | R net par trade |
|---|---|---|
| base | 459 | -0,32 |
| H1 golden selon le schéma | 183 | -0,01 |
| H2 premium/discount H4 | 185 | -0,03 |
| H3 break-even à +1 R | 459 | -0,25 |
| H1 + H2 (**retenu**) | 90 | **+0,32 ± 0,51** |
| H1 + H2 + H3 | 90 | +0,14 |

Le break-even améliore la base mais dégrade la meilleure combinaison : il n'est pas retenu (option `be_at_r`, désactivée par défaut).

**Validation.**

| Jeu | Base : trades, R net | Ajusté : trades, R net | Ajusté, R brut |
|---|---|---|---|
| EURUSD + XAUUSD 2019-2022 | 303, -0,13 | 55, **-0,17 ± 0,50** | — |
| 10 paires jamais vues | 4 254, -0,21 ± 0,06 | 796, **-0,09 ± 0,13** | +0,11 ± 0,13 |

**Lecture.**
- Le gain du développement (+0,32 R) **ne se confirme pas** : c'était en partie du surapprentissage, comme le protocole permettait de le détecter.
- Les deux ajustements réduisent néanmoins les pertes de façon cohérente sur les dix paires jamais vues : -0,09 R au lieu de -0,21 R par trade, cinq fois moins de trades, perte totale de 74 R au lieu de 877 R.
- Avant coûts, la version ajustée est légèrement positive (+0,11 R), mais pas significativement. Les coûts (environ 0,2 R par trade, car les stops M15 sont serrés) suffisent à la rendre perdante.

**Capital de 500 $ à 1 % par trade (2012-2022)** : la version ajustée termine entre 331 $ et 650 $ selon l'instrument, contre 75 $ à 411 $ pour la base. Elle est au-dessus de 500 $ sur EURUSD (650 $, dans l'échantillon de développement), USDJPY (596 $), AUDJPY (545 $) et GBPUSD (513 $), en dessous ailleurs. La baisse maximale passe de 34 à 86 % à 9 à 34 %.

**Conclusion.** L'ajustement est une amélioration réelle mais **pas une stratégie gagnante démontrée**. Options : `golden_schema_only` (moteur, Python et MQL5) et filtre premium/discount (`smv.mtf.premium_discount_ok`, entrée `InpFilterPD` de l'indicateur, exige une UT supérieure). Elles sont désactivées par défaut.

**Prochaines hypothèses, à tester sur des données neuves (backtest MT5 de mars 2022 à aujourd'hui), pas sur celles-ci :**
1. Réduire le poids des coûts : n'accepter que les setups dont le risque vaut au moins 8 à 10 fois le coût aller-retour, ou travailler en M30 et H1 avec le même filtre.
2. Cible minimale de 1,5 R avant la première liquidité.
3. Contexte de zone de l'UT supérieure (non concluant en développement, à reformuler avec le formateur).
