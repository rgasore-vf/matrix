# RESEARCH : recherches externes, comparaison avec le dépôt, sources

Version 0.1, octobre 2026.

Rôle de ce document : vérifier, clarifier et comparer. Le dépôt reste la source de vérité de la stratégie (`STRATEGY_SPEC.md`). Une définition externe n'est reprise dans la spécification que si elle est étiquetée [RECHERCHE].

## 0. Méthode et limites

- Recherches menées le 1er octobre 2026 par moteur de recherche web, plus la lecture directe du code source d'une bibliothèque publique (section 2.3).
- **Limite d'accès** : la politique réseau de l'environnement bloque plusieurs domaines (stockcharts.com, wyckoffanalytics.com, tradingview.com, luxalgo.com, gist.github.com). Pour ces sources, je n'ai eu accès qu'aux extraits renvoyés par le moteur de recherche, pas aux pages complètes. Ces points sont marqués « extrait seulement ».
- **Fiabilité des sources**, notée de A à D :
  - **A** : publication à comité de lecture ou documentation officielle d'un organisme ou d'un éditeur de plateforme.
  - **B** : code source public lisible, ou ouvrage de référence du domaine.
  - **C** : site pédagogique ou commercial sérieux, sans revue.
  - **D** : blog, forum, page marketing d'un broker ou d'un vendeur d'indicateurs.
- Le vocabulaire SMC/ICT n'a **aucune norme** : il vient de vidéos et de cours privés (Inner Circle Trader, M. Huddleston) et de leurs reprises. Les définitions « SMC » ci-dessous sont donc des usages dominants, pas des standards.

## 1. Synthèse des écarts entre le dépôt et l'usage externe

| Concept | Dépôt (SMV) | Usage externe dominant | Écart et conséquence |
|---|---|---|---|
| Swing high/low | jamais défini ; choix visuel | pivot à N bougies de chaque côté (fractal de Williams, N = 2 ; bibliothèques SMC : N paramétrable, souvent 50) | le dépôt laisse ouvert ; je reprends le pivot fractal |
| BOS | clôture au-delà du dernier HH (continuation) | idem ; certaines implémentations acceptent la mèche (`close_break = False`) | aligné ; le dépôt tranche pour la clôture |
| CHoCH | **absent sous ce nom** ; l'équivalent est le « BOS de changement de tendance » | première cassure contre la tendance | renommage nécessaire |
| « Changement de caractère » | premier LH en hausse (ou HL en baisse), **sans cassure** | n/a (le terme SMC CHoCH exige une cassure) | **faux ami** : même mot, sens différent |
| MSS | absent | cassure avec déplacement (displacement), souvent après une prise de liquidité | non utilisé |
| Order block | « bougie qui a manipulé ou pris l'argent » ; forme indifférente | dernière bougie de couleur opposée avant l'impulsion | proche ; le dépôt ajoute la BQA (extrême du swing) |
| Zone | du corps de la BM à la mèche de la BQA | OB = haut/bas de la bougie, parfois le corps | le dépôt est plus précis que l'usage courant |
| FVG | « imbalance », « price delivery », bougies non connectées ; « on ne se focus pas dessus » | trou à 3 bougies entre la mèche de la 1re et de la 3e | le dépôt ne l'utilise que comme indice |
| Premium/discount | « Fibonacci SMC » cité une fois, jamais enseigné | demi-range d'une jambe, 50 % = équilibre | absent du dépôt |
| Inducement | tout LH/HL qui ne donne pas de BOS majeur ; rétrospectif | pullback mineur devant le vrai point d'intérêt, censé être balayé d'abord | proche ; le dépôt est explicite sur la rétrospection |
| EQH/EQL | « même niveau », sans tolérance | tolérance relative (pourcentage ou fraction d'ATR) | tolérance à choisir |
| Wyckoff | décompte des événements sans volume | décompte **avec volume** (effort/résultat) | écart méthodologique majeur |
| Sessions | heures de Paris, avec deux erreurs probables | heures UTC officielles des places | voir section 4 |

## 2. Structure de marché et SMC

### 2.1 Swing points

- Le fractal de Bill Williams (« Trading Chaos », 1995) est une définition objective à 5 bougies : un sommet strictement supérieur aux deux bougies de chaque côté. Il n'est connu que **deux bougies après** l'extrême ; il ne repeint pas, mais il est en retard. Source : LuxAlgo, *Williams Fractal* (C, extrait seulement) ; MQL5 Articles, *MQL5 Wizard Techniques Part 56: Bill Williams Fractals* (C).
- Conséquence pour la spécification : le moment de vérité d'un pivot est `p + n_right` (R-ST-02).

### 2.2 BOS, CHoCH, MSS, displacement

- Usage courant : BOS = cassure dans le sens de la tendance (continuation) ; CHoCH = cassure contre la tendance, premier signal de retournement. Source : LuxAlgo, *Smart Money Concepts (SMC)* (C, extrait seulement).
- MSS : présenté comme une variante du CHoCH qui exige un déplacement rapide ; les définitions varient d'un site à l'autre. Sources : innercircletrader.net, *ICT Market Structure Shift* (D) ; fxopen.com, *What Are the Main ICT Concepts?* (D).
- Displacement : suite de bougies à grands corps qui laisse souvent un FVG. Source : LuxAlgo, *Displacement* (C, extrait seulement).
- **Comparaison** : la notion la plus proche du « BOS trap » du dépôt dans l'usage SMC est le « liquidity sweep » ou « stop hunt » ; mais le dépôt le définit relativement à l'UT supérieure, ce que l'usage courant ne fait pas.

### 2.3 Lecture du code d'une bibliothèque publique : `smartmoneyconcepts` (Python)

Source : dépôt GitHub `joshyattridge/smart-money-concepts`, fichier `smartmoneyconcepts/smc.py`, version 0.0.27, lu en entier pour les fonctions citées (B).

Constats utiles :

1. `swing_highs_lows` détecte un pivot par `high == high.shift(-n).rolling(2n).max()` : la valeur au temps `t` utilise les `n` bougies **futures**. Aucun moment de confirmation n'est exposé.
2. `bos_choch` attribue l'événement à l'indice d'un swing **antérieur** puis **efface** a posteriori les BOS « non cassés » ou chevauchés par une cassure ultérieure (« remove the ones that aren't broken »). Le résultat sur l'historique dépend donc de bougies postérieures.
3. `fvg` utilise `shift(-1)` (bougie suivante) et place l'événement sur la bougie du milieu.
4. Le dépôt GitHub contient plusieurs demandes de correction intitulées « Fix look-ahead bias in swing_highs_lows » (PR #103, #108) et « add causal parameter to prevent lookahead bias » (PR #95).

Leçon retenue : même un outil populaire produit, s'il est utilisé tel quel en backtest, des signaux connus trop tôt. Notre architecture impose `confirm_index` sur chaque événement et un test d'invariance par préfixe (ARCHITECTURE.md §4).

### 2.4 Inducement

- Usage courant : pullback mineur situé devant un point d'intérêt, où les traders entrés trop tôt placent leurs stops ; il est censé être balayé avant que le prix n'atteigne la vraie zone. Sources : LuxAlgo, *Inducement* (C, extrait) ; innercircletrader.net, *What is Inducement* (D) ; equiti.com (D).
- **Comparaison** : cohérent avec M5. Le dépôt ajoute une règle de classement (absence de BOS majeur) et reconnaît que le statut n'est connu qu'après coup. L'usage externe ne donne pas de règle opérationnelle plus précise.

### 2.5 Premium / discount

- Usage courant : la jambe entre un swing bas et un swing haut est coupée à 50 % ; au-dessus = premium (vendre), en dessous = discount (acheter). Source : LuxAlgo, *Premium & Discount* (C, extrait).
- Le dépôt ne l'enseigne pas. Le seul indice est « la Fibonacci SMC » dans une liste d'outils (M9/1) et la mention « les 50 % de la bougie, moi personnellement je n'utilise pas » (M10/1). **Non repris.**

### 2.6 Fair value gap

- Définition ICT courante : sur trois bougies, haussière si `high[i-1] < low[i+1]`, la zone `[high[i-1], low[i+1]]` est le gap. Sources : LuxAlgo, *Fair Value Gap* (C, extrait) ; `smartmoneyconcepts.fvg` (B, code lu).
- Le dépôt parle d'« imbalance » et de « price delivery », dit que ça « va potentiellement se combler » mais « pas obligé », et « on ne se focus pas dessus ». Implémentation optionnelle, étiquetée externe, avec confirmation à la clôture de la 3e bougie (et non de la 2e comme dans la bibliothèque citée).

## 3. Wyckoff

### 3.1 Terminologie et schémas

- Accumulation, phases A à E : PS, SC, AR, ST (phase A) ; construction de la cause (phase B, avec ST en phase B, UA) ; Spring et Test (phase C) ; SOS et LPS, BU (phase D) ; markup (phase E). Deux schémas : n° 1 avec spring, n° 2 sans spring (creux montants). Sources : StockCharts ChartSchool, *The Wyckoff Method: A Tutorial* (A/B, extrait seulement) ; TrendSpider Learning Center (C) ; Wyckoff Analytics, *Wyckoff Schematics: Visual templates* (B, extrait seulement).
- UA = « upthrust action », dépassement temporaire de la résistance en accumulation ; mSOW = « minor sign of weakness » en distribution, phase B. Sources : extraits de recherche (C).
- **Correspondances avec le dépôt** : « MSO » = mSOW ; « STB » = ST en phase B ; « UTAC » = UTAD (erreur de transcription). Le dépôt fait de l'UA et du mSOW des **prises de liquidité de l'AR**, éventuellement accompagnées d'un BOS d'« intention ». C'est une relecture SMC de Wyckoff, pas la définition d'origine.

### 3.2 Les trois lois et le volume

- Lois de Wyckoff : offre et demande ; cause et effet (la cause construite dans le range détermine l'ampleur de l'effet, mesurée classiquement par comptage en point-and-figure) ; effort et résultat (le volume est l'effort, la variation de prix le résultat). Sources : tradingwithrayner.com, fxopen.com, ironcladresearch.com (C/D, concordants).
- **Écart majeur** : le dépôt n'utilise jamais le volume. Il garde la loi de cause et effet sous une forme qualitative (« plus la cause dure, plus l'effet est grand »), sans comptage. Sur le forex au comptant, il n'existe pas de volume centralisé ; seul le volume en ticks du courtier est disponible. Une version de la stratégie « avec volume » serait donc un ajout, pas une reconstruction.

### 3.3 Distribution

- PSY, BC, AR, ST, mSOW, UT, UTAD, LPSY (schéma n° 1). Le dépôt (diapositives M7) reproduit ces schémas.

## 4. Sessions, fixings et annonces

| Donnée | Valeur externe | Dépôt | Verdict |
|---|---|---|---|
| Londres | ouverture 08:00 UTC en hiver, 07:00 en été | 9 h / 8 h Paris | **cohérent** (Paris = UTC+1 / +2) |
| New York | 13:00 UTC en hiver, 12:00 en été | 14 h / 13 h Paris | cohérent avec l'ouverture « forex » conventionnelle ; correspond à 8 h ET, pas à l'ouverture des actions (9 h 30 ET = 15 h 30 Paris) |
| Chicago | fuseau Central = New York moins **1 h** | « décalage de 2 h entre New York et Chicago », d'où 16 h | **erreur factuelle** sur le décalage ; 16 h Paris = 10 h ET = 9 h CT |
| Tokyo | ouverture 09:00 JST = 00:00 UTC = 01 h Paris (hiver), pas d'heure d'été au Japon | « 4 h du matin, Tokyo » | **incohérent** avec l'ouverture ; 4 h Paris = 12 h JST |
| Asie « 2 h » | fixing de Tokyo à 9 h 55 JST = 01 h 55 Paris (hiver) | « 2 h, Sydney » | **hypothèse** : coïncide avec le fixing de Tokyo, pas avec Sydney (22:00 UTC en hiver nord) |
| Décalage des heures d'été | en 2026 : États-Unis et Europe désynchronisés du 8 au 29 mars et du 25 octobre au 1er novembre | non mentionné | pendant ces semaines, l'« heure US » tombe 1 h plus tôt à Paris |
| Fixing de Londres (WM/Reuters) | 16:00 heure de Londres, fenêtre de 1 min | non mentionné | — |
| NFP (Employment Situation) | 1er vendredi du mois, 8 h 30 ET | « premier vendredi du mois » | cohérent |
| FOMC | communiqué 14 h ET, conférence 14 h 30 ET | cité | cohérent |

Sources : compareforexbrokers.com, *Forex Market Hours* (D) ; Dukascopy, *Forex Market Hours* (C) ; Ito et Yamada, *Puzzles in the Tokyo Fixing*, NBER WP 22820 (A) ; Ito et Yamada, *Was the Forex Fixing Fixed?*, NBER WP 21518 (A) ; Kiplinger, financecalendar.com (D) pour le calendrier NFP ; federalreserve.gov (A) pour le FOMC.

## 5. Repainting, look-ahead et multi-UT

- **Bougie non close** : en MQL5, l'indice 0 désigne la bougie en formation ; ses valeurs changent à chaque tick ; tout signal fondé sur une bougie complète doit lire l'indice 1. Source : MQL5 Documentation, *Timeseries and Indicators Access*, *iClose* (A) ; MQL5 Articles, *Leak-Free Multi-Timeframe Engine with Closed-Bar Reads* (C).
- **Multi-UT** : sur TradingView, `request.security` avec `lookahead_on` sans décalage `[1]` produit sur l'historique des valeurs de l'UT haute avant leur disponibilité ; avec `lookahead_off`, la valeur de la bougie haute en cours change en temps réel. Le motif non repeignant est `lookahead_on` avec l'expression décalée de 1. Source : TradingView, *Pine Script User Manual, Concepts / Repainting* et *Other timeframes and data* (A, extrait seulement).
- **Indicateurs à pivots** : un pivot à `n` bougies à droite n'est connu qu'à `p + n` ; le dessiner à `p` n'est correct que si l'on n'utilise pas sa valeur avant `p + n` (section 2.1).
- **Principe retenu** (ARCHITECTURE.md) : événements horodatés par leur confirmation ; journal en ajout seul ; UT haute publiée à sa clôture ; test automatique d'invariance par préfixe.

## 6. Ce que dit la littérature sur l'efficacité

### 6.1 Analyse technique en général

- Park et Irwin (2007), *What do we know about the profitability of technical analysis?*, Journal of Economic Surveys 21(4), 786-826 (A) : sur 95 études « modernes », 56 positives, 20 négatives, 19 mitigées ; mais la plupart souffrent de data snooping, de sélection ex post des règles, et d'une mauvaise prise en compte du risque et des coûts.
- Lo, Mamaysky et Wang (2000), *Foundations of Technical Analysis*, Journal of Finance 55(4) (A) : propose une reconnaissance automatique des figures par régression à noyau et montre qu'elles apportent une information statistique (sur des actions américaines 1962-1996). Pertinent ici pour la méthode : formaliser un motif visuel avant de le tester.
- Bailey, Borwein, López de Prado et Zhu (2017), *The Probability of Backtest Overfitting* (A) : quand on teste beaucoup de configurations, la probabilité qu'un backtest optimisé soit sur-ajusté tend vers 1 ; propose la validation croisée combinatoire symétrique (CSCV).

### 6.2 Liquidité aux extrêmes : un appui empirique partiel

- Osler (2003), *Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis*, Journal of Finance 58(5), 1791-1819 (A) ; Osler (2005), *Stop-loss orders and price cascades in currency markets*, Journal of International Money and Finance 24(2) (A). À partir des ordres d'une grande banque de change : les ordres stop et take-profit se concentrent sur des niveaux ronds ; les stops sont déclenchés plutôt juste après le franchissement d'un niveau rond et amplifient le mouvement (cascades).
- **Portée pour la stratégie** : c'est l'appui empirique le plus proche de l'idée « il y a de la liquidité au-delà des sommets et des creux ». Mais Osler parle de **niveaux ronds**, pas de swings, et ne valide pas l'idée d'institutions qui « manipulent » volontairement le prix vers ces niveaux.

### 6.3 SMC / ICT

- Aucune étude académique évaluée par des pairs n'a été trouvée sur l'efficacité du cadre SMC/ICT ou de ses variantes. Les pages qui annoncent des résultats de backtest sont des blogs ou des vendeurs (statoasis.com, fxnx.com, medium.com) (D) ; leurs résultats vont d'« aucun avantage significatif » (t = 1,22 sur des order blocks en daily sur SPY, selon statoasis.com) à des taux de réussite de 50-65 % non vérifiables. Je ne les retiens pas comme preuves.
- Les justifications causales du dépôt (« algorithmes des banques qui valent des milliards », « 80 % des retails sont perdants », « ce qui marchait il y a 100 ans marche aujourd'hui ») sont des **affirmations non sourcées**.

### 6.4 Conséquence pour le projet

L'indicateur est un outil de **lecture** et de **mesure**. Il permet ensuite de tester la stratégie (fréquence des événements, taux de prise des liquidités, comportement après un BOS, etc.) avec un protocole sérieux : données hors échantillon, coûts réels, comparaison à des entrées aléatoires, contrôle du nombre de configurations testées (Bailey et al.).

## 7. Liste des sources

- [Smart Money Concepts (SMC) [LuxAlgo], TradingView](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/) (C, extrait seulement)
- [LuxAlgo, Smart Money Concepts (SMC)](https://www.luxalgo.com/library/indicator/smart-money-concepts-smc/) (C, extrait seulement)
- [LuxAlgo, Premium & Discount](https://www.luxalgo.com/library/concept/premium-and-discount/) (C, extrait seulement)
- [LuxAlgo, Inducement](https://www.luxalgo.com/library/concept/inducement/) (C, extrait seulement)
- [LuxAlgo, Fair Value Gap](https://www.luxalgo.com/library/concept/fair-value-gap/) et [Displacement](https://www.luxalgo.com/library/concept/displacement/) (C, extrait seulement)
- [LuxAlgo, Williams Fractal](https://www.luxalgo.com/library/concept/williams-fractal/) (C, extrait seulement)
- [joshyattridge/smart-money-concepts (GitHub)](https://github.com/joshyattridge/smart-money-concepts) (B, code lu) ; [PR #103](https://github.com/joshyattridge/smart-money-concepts/pull/103), [PR #108](https://github.com/joshyattridge/smart-money-concepts/pull/108), [PR #95](https://github.com/joshyattridge/smart-money-concepts/pull/95)
- [innercircletrader.net, ICT Market Structure Shift](https://innercircletrader.net/tutorials/ict-market-structure-shift/) ; [Inducement](https://innercircletrader.net/tutorials/what-is-inducement-in-forex/) (D)
- [fxopen.com, What Are the Main ICT Concepts?](https://fxopen.com/blog/en/what-are-the-inner-circle-trading-concepts/) (D)
- [StockCharts ChartSchool, The Wyckoff Method: A Tutorial](https://chartschool.stockcharts.com/table-of-contents/market-analysis/wyckoff-analysis-articles/the-wyckoff-method-a-tutorial) (A/B, extrait seulement)
- [Wyckoff Analytics, Wyckoff Schematics: Visual templates](https://www.wyckoffanalytics.com/wp-content/uploads/2019/09/WyckoffSchematics-VisualTemplatesForMarketTimingDecisions.pdf) (B, extrait seulement)
- [TrendSpider, Wyckoff Accumulation Pattern](https://trendspider.com/learning-center/chart-patterns-wyckoff-accumulation/) (C)
- [Rayner Teo, Wyckoff Theory](https://www.tradingwithrayner.com/wyckoff-theory/) ; [Ironclad Research, Wyckoff Method](https://www.ironcladresearch.com/learn/technical-analysis/wyckoff-method) (C/D)
- [Wikipedia, Doji](https://en.wikipedia.org/wiki/Doji) ; [StockCharts, Introduction to Candlesticks](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/candlestick-charts/introduction-to-candlesticks) (C)
- [MQL5 Documentation, Timeseries and Indicators Access](https://www.mql5.com/en/docs/series) ; [iClose](https://www.mql5.com/en/docs/series/iclose) (A)
- [MQL5 Articles, Leak-Free Multi-Timeframe Engine with Closed-Bar Reads](https://www.mql5.com/en/articles/22363) (C)
- [TradingView Pine Script, Concepts / Repainting](https://www.tradingview.com/pine-script-docs/concepts/repainting/) ; [Other timeframes and data](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/) (A, extrait seulement)
- [Compare Forex Brokers, Forex Market Hours](https://www.compareforexbrokers.com/trading/hours/) (D) ; [Dukascopy, Forex Market Hours](https://www.dukascopy.com/swiss/english/fx-market-tools/forex-market-hours/) (C)
- [Ito et Yamada, Puzzles in the Forex Tokyo Fixing, NBER WP 22820](https://www.nber.org/system/files/working_papers/w22820/w22820.pdf) ; [Was the Forex Fixing Fixed?, NBER WP 21518](https://www.nber.org/system/files/working_papers/w21518/w21518.pdf) (A)
- [Federal Reserve, FOMC meeting April 28-29, 2026](https://www.federalreserve.gov/monetarypolicy/fomcpresconf20260429.htm) (A) ; [financecalendar.com, US Jobs Report](https://www.financecalendar.com/us-jobs-report/) (D)
- [Park et Irwin (2007), Journal of Economic Surveys](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-6419.2007.00519.x) (A)
- [Lo, Mamaysky et Wang (2000), Journal of Finance](https://stuff.mit.edu/people/wangj/pap/LoMamayskyWang00.pdf) (A)
- [Bailey, Borwein, López de Prado et Zhu, The Probability of Backtest Overfitting](https://scholarworks.wmich.edu/math_pubs/42/) (A)
- [Osler (2003), Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588) ; [version Fed de New York, SR 125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf) (A)
- [Osler (2005), Stop-loss orders and price cascades in currency markets](https://ideas.repec.org/a/eee/jimfin/v24y2005i2p219-241.html) (A)
- [statoasis.com, I Backtested ICT / Smart Money Concepts](https://statoasis.com/overfit/research/ict-backtest-what-survives) ; [fxnx.com, Do Smart Money Concepts Work?](https://fxnx.com/en/blog/smart-money-concepts-work-backtest-evidence) (D, cités pour mémoire, non retenus comme preuves)

---

## 8. Addendum (v0.2) : recherches pour Q-01 à Q-16 et pour MetaTrader 5

Ces recherches complètent les sections précédentes pour répondre aux questions de `STRATEGY_SPEC.md` §13 ; les réponses et les mesures sont dans `CALIBRATION.md`. Même grille de fiabilité (§0). Plusieurs domaines (mql5.com notamment) étaient bloqués par le réseau de l'environnement : seuls les extraits fournis par le moteur de recherche ont pu être lus pour ces sources, signalés « extrait ».

### 8.1 Niveau protégé (Q-01)

- Usage SMC : « si un haut casse un bas, ce haut est protégé ; si un bas casse un haut, ce bas est protégé » ; en tendance haussière les bas sont protégés et les hauts sont des cibles. Source : tradethepool.com, *Smart Money Concepts Terminology* (D, extrait). Les autres sources consultées (strike.money, writofinance.com) vont dans le même sens (D).
- **Comparaison** : c'est la lecture A du dépôt (le niveau protégé est l'origine de la dernière cassure). La lecture B n'a pas d'équivalent dans l'usage externe consulté.

### 8.2 Invalidation d'un order block (Q-06)

- Usage ICT : le « mean threshold » est le milieu (50 %) du corps de la bougie d'order block ; une clôture au-delà de ce milieu, ou au-delà de l'extrême, invalide la zone. « Les mèches testent, les clôtures décident. » Certains indicateurs transforment alors la zone en breaker. Sources : ictkillzone.com, *ICT Order Block* (D, extrait) ; TradingView, *ICT Order Block Pro* (C, extrait).
- **Comparaison** : le dépôt invalide par clôture (cohérent avec « les clôtures décident ») mais ne parle jamais du milieu de la bougie et dit ne pas utiliser « les 50 % de la bougie » (M10/1). La règle du mean threshold n'est donc pas reprise.

### 8.3 Tolérance des EQH/EQL (Q-07)

- Des indicateurs SMC publics expriment la tolérance des égalités en fraction d'ATR, avec 0,10 par défaut, et conseillent de l'augmenter sur les marchés volatils. Sources : LuxAlgo / TradingView, *Smart Money Concepts [Quantum Algo]* (C, extrait) ; LuxAlgo, *Smart Money Concepts (SMC)* (C, extrait).
- **Comparaison** : le dépôt ne donne aucune tolérance (« au même niveau »). 0,1 ATR est donc un choix externe ; la mesure (`CALIBRATION.md` Q-07) indique qu'il reste sélectif (environ 8 % des paires de pivots).

### 8.4 OTE, équilibre, premium/discount (Q-13)

- Usage ICT : l'équilibre est le milieu (50 %) de la « dealing range » ; au-dessus = premium, au-dessous = discount ; l'« optimal trade entry » est la zone de retracement de 62 à 79 %, avec 70,5 % comme niveau central. Sources : forexbee.co, *ICT Optimal Trade Entry* (D) ; innercircletrader.net, *ICT Fibonacci Settings* (D) ; theinnercircletraders.com, *Premium and Discount Zones* (D). Concordants.
- **Comparaison** : le dépôt cite « la Fibonacci SMC » une fois sans l'enseigner. Non implémenté.

### 8.5 Displacement et bougie manipulatrice (Q-02)

- Usage ICT : une bougie de « displacement » ou bougie institutionnelle a un corps d'au moins 60 à 70 % de son amplitude ; au-dessus de 75 à 80 %, le déplacement est jugé net. Sources : FibAlgo, *ICT Displacement* (C, extrait) ; ictkillzone.com, *ICT Displacement* (D) ; smartmoneytrader.co (D). Concordants sur l'ordre de grandeur, pas sur le seuil exact.
- **Comparaison** : le dépôt dit « pleine ou presque pleine » sans chiffre. Le seuil retenu (70 %) est au milieu de la fourchette externe et correspond au quintile supérieur mesuré.

### 8.6 Spring et test Wyckoff (Q-11)

- Sources de référence (StockCharts, Wyckoff Analytics, TrendSpider) : un spring est un passage sous le support suivi d'un retour **rapide** dans la fourchette ; le test se fait sur volume plus faible et reste au-dessus du bas du spring. Aucune ne donne de nombre de bougies. Sources : TrendSpider, *Wyckoff Accumulation Pattern* (C) ; Wyckoff Analytics, *Identifying Wyckoff Springs with Algorithms* (B, extrait).
- Sources de praticiens et d'indicateurs : retour dans la fourchette en 1 à 5 bougies selon l'UT, souvent « 3 à 5 » ; plus de 5 clôtures dehors indiquent plutôt une vraie cassure ; une implémentation exige un retour en 3 bougies. Sources : LuxAlgo, *Spring* (C, extrait) ; tradingwyckoff.com, *Spring & Shakeout* (C/D, extrait) ; journalplus.co (D).
- **Limite** : aucune source vérifiée ne chiffre le délai entre le spring et son test. `test_max_bars = 10` est une PROPOSITION.

### 8.7 MetaTrader 5 (plateforme cible retenue)

- `OnCalculate` : le paramètre `prev_calculated` vaut ce que l'appel précédent a renvoyé ; le terminal le remet à 0 quand l'historique change (chargement d'un historique plus profond, trous comblés), ce qui impose un recalcul complet. Le schéma usuel renvoie `rates_total` et ne traite que `rates_total - prev_calculated` bougies. Sources : documentation MQL5, *OnCalculate* (A, extrait) ; *MQL5 Programming for Traders*, « Main indicator event: OnCalculate » (A, extrait) ; forum MQL5, fils 152462 et 326512 (C).
- Bougie en formation : dans une série inversée, l'indice 0 est la bougie courante, non terminée ; sans inversion, c'est l'indice `rates_total - 1`. `CopyRates` renvoie aussi la bougie en cours d'une autre UT. Sources : documentation MQL5, *CopyRates* et *Timeseries and Indicators Access* (A, extrait).
- Multi-UT : `iBarShift` et `CopyRates` permettent de synchroniser les UT ; il faut éviter de lire la bougie d'UT supérieure non close. Sources : MQL5 Articles, *Creating multi-symbol, multi-period indicators* (B, extrait) ; *MTF indicators as the technical analysis tool* (B, extrait) ; voir aussi §5.
- Fichiers : `FileOpen` travaille dans le bac à sable `<dossier de données>\MQL5\Files\` ; l'option `FILE_COMMON` utilise le dossier commun à tous les terminaux. Sources : documentation MQL5, *FileOpen* (A, extrait) ; MQL5 Articles, *MQL5 Programming Basics: Files* (B, extrait).
- Objets graphiques : interroger les propriétés d'objets est coûteux quand il y en a beaucoup ; il faut grouper les modifications et appeler `ChartRedraw` une fois. Source : forum MQL5, fil 158961 (C, extrait). D'où la limite `InpDrawBars` et la mise à jour de l'affichage seulement à la clôture d'une bougie.
- Heure du serveur : MQL5 ne fournit pas de base de fuseaux horaires ; `TimeTradeServer() - TimeGMT()` donne seulement le décalage **actuel**. Les règles d'heure d'été (UE, États-Unis) sont donc codées dans `Timing.mqh`, et la convention du courtier se vérifie avec le script `SMV_ServerTimeCheck.mq5` (méthode du §1 de `CALIBRATION.md`).

### 8.8 Palette graphique

- Couleurs de la marque Anthropic relevées en octobre 2026 : ardoise #141413, ivoire #FAF9F5, gris moyen #B0AEA5, gris clair #E8E6DC, orange #D97757, bleu #6A9BCC, vert #788C5D. Sources : shadcn.io, *Anthropic Design System* (D) ; getclaudeskills.com, *Brand Guidelines Anthropic* (D). Concordantes entre elles ; aucune source officielle d'Anthropic n'a pu être consultée.
- Usage : couleurs par défaut de l'indicateur (vert = haussier, orange = baissier, bleu = cibles, gris = neutre ; teintes claires pour les zones). Elles restent réglables.

### 8.9 Sources de l'addendum

- [tradethepool.com, Smart Money Concepts Terminology](https://tradethepool.com/technical-skill/smart-money-concepts-terminology/) ; [strike.money, Smart Money Concepts](https://www.strike.money/technical-analysis/smart-money-concepts) ; [writofinance.com, Structure Mapping](https://www.writofinance.com/structure-mapping-in-trading/) (D)
- [ictkillzone.com, ICT Order Block](https://www.ictkillzone.com/ict-order-block) ; [TradingView, ICT Order Block Pro](https://www.tradingview.com/script/oObsuObl-ICT-Order-Block-Pro/) (C/D)
- [TradingView, Smart Money Concepts [Quantum Algo]](https://www.tradingview.com/script/SRsr9SLs-Smart-Money-Concepts-Quantum-Algo/) ; [LuxAlgo, Smart Money Concepts](https://www.luxalgo.com/library/indicator/SRsr9SLs-smart-money-concepts/) (C)
- [forexbee.co, ICT OTE 62-79 %](https://forexbee.co/ict-optimal-trade-entry-ote-strategy/) ; [innercircletrader.net, ICT Fibonacci Settings](https://innercircletrader.net/tutorials/ict-fibonacci-levels/) ; [theinnercircletraders.com, Premium and Discount](https://www.theinnercircletraders.com/ict-premium-and-discount-zones/) (D)
- [FibAlgo, ICT Displacement](https://www.tradingview.com/script/9OYOAKNU-FibAlgo-ICT-Displacement/) ; [ictkillzone.com, ICT Displacement](https://www.ictkillzone.com/ict-displacement) ; [smartmoneytrader.co, Displacement candle](https://www.smartmoneytrader.co/blog/what-is-displacement-candle-ict) (C/D)
- [TrendSpider, Wyckoff Accumulation](https://trendspider.com/learning-center/chart-patterns-wyckoff-accumulation/) ; [Wyckoff Analytics, Identifying Wyckoff Springs with Algorithms](https://www.wyckoffanalytics.com/identifying-wyckoff-springs-with-algorithmic-trading-strategies/) ; [LuxAlgo, Spring](https://www.luxalgo.com/library/concept/spring/) ; [tradingwyckoff.com, Spring & Shakeout](https://tradingwyckoff.com/en/spring-shakeout/) ; [journalplus.co, Wyckoff Accumulation](https://journalplus.co/patterns/wyckoff-accumulation/) (B à D)
- [Documentation MQL5, OnCalculate](https://www.mql5.com/en/docs/event_handlers/oncalculate) ; [MQL5 Programming for Traders, OnCalculate](https://www.mql5.com/en/book/applications/indicators_make/indicators_oncalculate) ; [CopyRates](https://www.mql5.com/en/docs/series/copyrates) ; [FileOpen](https://www.mql5.com/en/docs/files/fileopen) ; [ObjectCreate](https://www.mql5.com/en/docs/objects/objectcreate) (A, extraits)
- [MQL5 Articles, Creating multi-symbol, multi-period indicators](https://www.mql5.com/en/articles/13578) ; [MTF indicators as the technical analysis tool](https://www.mql5.com/en/articles/2837) ; [MQL5 Programming Basics: Files](https://www.mql5.com/en/articles/2720) (B, extraits)
- [Forum MQL5, prev_calculated](https://www.mql5.com/en/forum/152462) ; [Max bars in chart](https://www.mql5.com/en/forum/326512) ; [performance des objets](https://www.mql5.com/en/forum/158961/page2) (C, extraits)
- [shadcn.io, Anthropic Design System](https://www.shadcn.io/design/anthropic) ; [getclaudeskills.com, Brand Guidelines Anthropic](https://www.getclaudeskills.com/skills/brand-guidelines-anthropic) (D)
