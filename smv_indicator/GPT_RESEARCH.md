# Recherche technique indépendante

Recherche effectuée le 1 octobre 2026, indépendamment des conclusions numériques préexistantes. Les liens ci-dessous ont été recherchés ou ouverts pendant cet audit. Les sources officielles décrivent une plate-forme ; les pages d’auteurs d’indicateurs décrivent leurs propres conventions. Aucune ne prouve le contenu de la formation SMV absente de l’archive.

## Sources retenues et portée

| Source de première main | Apport vérifié | Limite pour SMV |
| --- | --- | --- |
| [MetaQuotes, Fractals](https://www.metatrader5.com/en/terminal/help/indicators/bw_indicators/fractals) | Fractal usuel sur au moins cinq bougies, sommet central et deux hauts inférieurs de chaque côté ; symétrie pour les creux | Ne définit pas les swings discrétionnaires SMV ; la gestion asymétrique des égalités du projet est une proposition |
| [LuxAlgo, Market Structure](https://docs.luxalgo.com/platform/algos/price-action-concepts/market-structures) | BOS de continuation, CHoCH de rupture opposée ; variantes CHoCH et CHoCH+ ; swings affichés rétrospectivement | Convention d’un auteur de logiciel, pas norme universelle ni formation UltraFX |
| [LuxAlgo, Market Structure with Inducements & Sweeps](https://www.luxalgo.com/library/indicator/market-structure-with-inducements-sweeps/) | Autre modèle du même auteur : niveau de swing pour CHoCH, extrême suivi pour BOS, rôle conditionnel de l’inducement, sweeps de mèches | Les conditions de BOS ne sont pas interchangeables avec un simple franchissement du dernier pivot |
| [LuxAlgo, Volumetric Order Blocks](https://docs.luxalgo.com/platform/algos/price-action-concepts/order-blocks) | Zones à proximité des swings ; breakers après rupture ; mitigations par close, wick ou moyenne ; métriques requérant du volume | Ne démontre pas que BM/BQA, bornes de corps et zéro-réaction SMV sont identiques |
| [LuxAlgo, Imbalance Concepts](https://docs.luxalgo.com/platform/algos/price-action-concepts/imbalances) | FVG trois bougies ; gap bullish low courant > high deux bougies avant, miroir bearish ; gap d’ouverture distinct | La variante minimale n’implique pas un déplacement suffisant, une entrée profitable ni une règle enseignée dans SMV |
| [Wyckoff Analytics, tutoriel de méthode, PDF](https://www.wyckoffanalytics.com/wp-content/uploads/2020/02/Wyckoff_Analytics_Wyckoff-Method_English.pdf) | Volume et spread dans SC/ST/SOS/tests ; spring et UTAD non obligatoires ; phases et cause point-and-figure | Tutoriel écrit par ses auteurs, pas texte original de la formation SMV ; un compteur de sweeps ne reproduit pas ces phases |
| [MetaQuotes, OnCalculate](https://www.mql5.com/en/docs/event_handlers/oncalculate) | `prev_calculated` remis à zéro lorsque l’historique change ; sens des tableaux à définir explicitement | Déterminisme sous un historique fixé ne garantit pas le même résultat avec un historique modifié |
| [MetaQuotes, CopyRates](https://www.mql5.com/en/docs/series/copyrates) | Position zéro = bougie courante non terminée ; copie physique chronologique ; historique absent peut déclencher chargement | Une seule comparaison à TimeCurrent ne remplace pas un contrat explicite sur les bars admis |
| [MetaQuotes, SeriesInfoInteger](https://www.mql5.com/en/docs/series/seriesinfointeger) | Interroger les propriétés de série, dont la synchronisation | N’atteste ni l’absence de révisions historiques ni le fuseau du broker |
| [MetaQuotes, ObjectCreate](https://www.mql5.com/en/docs/objects/objectcreate) | Nom unique dans un graphique, longueur maximale 63 ; création asynchrone, succès d’enfilement distinct du succès effectif | Le nombre de tests Python n’atteste pas le dessin effectif de MT5 |
| [MetaQuotes, ObjectsTotal](https://www.mql5.com/en/docs/objects/objectstotal), [ObjectName](https://www.mql5.com/en/docs/objects/objectname), [ObjectFind](https://www.mql5.com/en/docs/objects/objectfind) | Interrogations synchrones et coût potentiel avec beaucoup d’objets | Une purge peut borner la rétention sans garantir une latence terminal faible |
| [Python, datetime](https://docs.python.org/3/library/datetime.html) | Quand deux datetimes partagent le même tzinfo, comparaison de leurs valeurs locales pouvant ignorer fold ; addition sans conversion de fuseau | Un horodatage avec fuseau n’assure pas à lui seul une comparaison d’instants corrects |
| [Python, dataclasses](https://docs.python.org/3/library/dataclasses.html) | `frozen` protège les attributs de la dataclass ; transformation récursive `asdict` | Les conteneurs mutables d’un attribut ne deviennent pas immuables automatiquement |
| [CME, Futures Order Types](https://www.cmegroup.com/education/courses/futures-trading-mechanics-and-regulation/futures-order-types) | Déclenchement d’un stop et modalités d’exécution/protection sont distincts | Exemple de marché à terme, pas contrat d’exécution de votre broker Forex ; ouverture utilisée ici comme modèle de référence |
| [Bailey, Borwein, López de Prado et Zhu, The Probability of Backtest Overfitting, PDF d’auteur](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | Risque de sélection de stratégies par backtests ; nécessité de tenir compte des essais et du protocole de sélection | Ne fournit aucun verdict chiffré sur ce dépôt ; aucun PBO n’a été calculé |

La vidéo [The Inner Circle Trader, 2022 Mentorship Episode 6](https://www.youtube.com/watch?v=Bkt8B3kLATQ) a été identifiée, mais son contenu intégral n’a pas été visionné ni authentifié avec une transcription dans cet audit. Je ne l’utilise pas comme preuve d’un seuil précis ou d’une règle SMV. Les résumés tiers et les pages de discussions trouvés dans la recherche ne servent pas à trancher les règles techniques.

## Comparaison des définitions

| Terme | Variantes réellement différentes | Conséquence pour cet audit |
| --- | --- | --- |
| Swing | Fractal fixe confirmé après bougies de droite ; swing à lookback configurable ; pivot choisi visuellement selon impulsion/retracement dans B | Le 2/2 et la priorité au premier égal sont des choix formels ; il faut les confronter aux exemples originaux |
| BOS | Cassure du swing précédent ; continuation après changement de structure ; rupture d’un extrême suivi avec condition d’IDM ; changement de tendance aussi appelé BOS dans B | Ne pas importer un prédicat externe sous une étiquette familière |
| CHoCH / MSS | Rupture d’un swing opposé ; variante avec fail préalable ; dans le vocabulaire SMV revendiqué par B, changement de caractère = premier LH/HL sans cassure | Une correspondance de nom n’est pas une équivalence algorithmique |
| Liquidité / sweep | Franchissement de niveau par wick, sans close au-delà ; excursion clôturée dehors puis récupérée ; phase spring avec tests/contextes | Un état INTACT/CLEAN est une convention de prix, pas une observation directe de stops ou d’ordres institutionnels |
| EQH/EQL | Égalité exacte ; tolérance de prix ou volatilité ; deux niveaux encore intacts ; fenêtres de lookback variables | La tolérance, l’âge, le délai et la disponibilité du deuxième pivot sont tous des éléments de règle |
| OB / POI / offre-demande | Bougie d’origine ; dernière bougie opposée ; zone proche d’un swing ; métriques de volume ; proximal de corps contre distal de wick | Les frontières et invalidations doivent être tracées vers la formation ; elles ne se déduisent pas du mot OB |
| Breaker | Zone précédente rompue ; candidat de polarité inverse ; dans B, zéro-réaction puis BOS et réaction | Une simple rupture suffit au candidat C, mais pas à toutes les descriptions revendiquées |
| FVG / imbalance / displacement | Gap strict entre bougies extérieures ; filtre de taille ; contexte impulsif ; gap d’ouverture différent | Le code implémente seulement la géométrie trois bougies, optionnelle et non utilisée pour les setups |
| Spring / UTAD | Phase et test contextuels dans Wyckoff ; deuxième prise de borne dans le compteur C | Les deux usages doivent rester distincts ; aucune phase complète validée par un simple numéro |
| Cause et effet | Comptage point-and-figure chez Wyckoff ; durée/hauteur de range dans B/C | Une durée ne détermine pas automatiquement une cible ou un rendement |

L’absence de définition universelle ne permet pas de choisir celle qui semble produire les meilleurs chiffres. Avec A absent, la bonne conclusion est « plusieurs modèles compatibles avec les mots, fidélité non déterminée ».

## Résultats techniques indépendants

Les défauts d’anticipation sont prouvés par les temps disponibles, sans invoquer une théorie de marché. Une bougie `(open 00:00, close 00:15)` ne révèle pas son high à 00:07. Deux 01:00 locales avec UTC−4 et UTC−5 représentent des instants espacés d’une heure. L’exposition à un événement EQ confirmé en 5 ne commence pas en 0. Une high de bougie journalière chevauchant une borne ne peut pas être localisée dans l’une des deux sous-périodes par le seul OHLC. Ces quatre arguments fondent F02, F03, F08 et F15.

Les politiques stop avant cible et absence de gain sur la bougie d’entrée limitent une forme d’optimisme intrabar ; elles ne reconstituent pas le trajet réel. La correction d’un gap de position ouverte utilise le prix d’ouverture comme référence, sans promettre ce prix d’exécution réel. Les limites encore en attente et les coûts de broker demandent une autre source de données pour une simulation exacte.

Le contrat graphique requiert une distinction entre ancrage et disponibilité. Dessiner à p un pivot confirmé à p+2 est acceptable si l’apparition et la relecture commencent à p+2. Montrer au temps 5 le statut d’un niveau pris en 10 ne l’est pas. La beauté du SVG original ne valide donc aucune transition de la machine.

## Sessions : conversion et sélection de stratégie

Les ancrages measured du code produisent les heures Paris ci-dessous avec les règles de fuseaux utilisées. Il s’agit de conversions des réglages reçus, pas d’une recommandation de sessions ni d’une vérification des heures de la formation.

| Réglage du code | Hiver Paris | Été synchronisé Paris | Semaine US été / Europe hiver |
| --- | --- | --- | --- |
| Tokyo 10:00 | 02:00 | 03:00 | 02:00 |
| Londres 08:00 | 09:00 | 09:00 | 09:00 |
| New York 08:30 | 14:30 | 14:30 | 13:30 |
| New York 10:00 | 16:00 | 16:00 | 15:00 |

La notice de recherche préexistante rapproche des heures UTC d’ouverture et des horaires repo Paris 9/8 ou 14/13. L’addition des décalages ne justifie pas cette équivalence : 08:00 UTC en hiver +1 et 07:00 UTC en été +2 donnent tous deux 09:00 Paris. Le mode repo conserve un autre calendrier. Remplacer ses heures par celles mesurées est une décision de modèle qui doit être validée contre A.

MQL5 code des règles UE et américaines, sans base IANA complète. Ses règles de sessions et le mode serveur New York ne couvrent pas fidèlement tout historique ancien ; le fichier préexistant annonce cette restriction. Le test de l’heure serveur actuelle ne prouve pas le fuseau de toute la série passée. HTF natif broker et HTF resamplé UTC peuvent aussi avoir des ouvertures différentes. La parité du moteur sur un export LTF ne valide pas ce second alignement.

## Ce que les données reçues ne permettent pas de conclure

Les cinq JSON sont des résultats dérivés sans bougies brutes, commit du fournisseur, hash de chaque fichier ni manifeste de transformations. Le chemin `SMV_DATA` attendu est absent. Les études n’ont donc pas été reproduites sur EURUSD/XAUUSD ni sur sept années pendant cet audit.

Les corrections de classification EQ, horizon, fin de mois, gaps du modèle nul et logique du moteur rendent nécessaire un nouveau calcul. Même après cela, les fenêtres et trades qui se chevauchent, les expositions multiples d’un niveau, la saisonnalité détruite par permutation et la sélection de paramètres sur des années potentiellement consultées empêchent de lire les intervalles naïfs comme une preuve forte. La liste alternée utilisée pour l’étude de rotation est reconstruite après coup et doit être redéfinie avant toute prétention à un signal causal.

Un protocole défendable doit fixer les sources, fuseaux et règles avant l’évaluation, publier les données exclues et les cas non résolus, isoler réellement l’évaluation de la sélection et traiter les dépendances. Une validation en blocs temporels et une analyse de sensibilité seraient des voies possibles, à définir selon l’hypothèse étudiée. Cela reste une proposition de méthode, pas une analyse statistique déjà exécutée.

Les études descriptives peuvent expliquer la distribution d’un paramètre ; elles ne peuvent pas transformer une règle ambiguë de formation en règle explicite. Je ne confirme donc ni une espérance positive, ni une espérance négative de la stratégie SMV originale, ni les réponses Q-01 à Q-16 comme vérité du corpus.
