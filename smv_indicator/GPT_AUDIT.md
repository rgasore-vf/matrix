# Audit indépendant de smv_indicator

Date : 1 octobre 2026. Objet audité : l’archive `matrix-main.zip` fournie après l’échec d’accès à `rgasore-vf/matrix`. Le SHA-256 de l’archive est `1310d5cb8d404574107636c96d860dc320829d8c1738979b74ea7ce430222bab`. Aucun commit Git ne peut être associé avec certitude à ce fichier.

## Verdict

La version reçue ne satisfait pas son contrat temporel sur tous les chemins. Des contre-exemples montrent une publication HTF avant disponibilité réelle, une deuxième fuite pendant une heure répétée à l’automne, des structures oubliées et des mesures de recherche utilisant une qualification future. Les corrections décrites ci-dessous sont incluses dans cette version.

Les **61 tests préexistants passent sur la version reçue**. Après ajout de 42 cas indépendants, la version reçue donne **39 échecs et 64 succès**. La version corrigée donne **103 succès**. Ces nombres comptent les cas paramétrés, pas 39 causes distinctes. Les preuves avant et après sont conservées dans `audit_evidence/`.

La fidélité à la formation SMV reste **non vérifiable**. L’archive contient uniquement 66 fichiers de `smv_indicator`, sans `Strategie/`, transcriptions originales, diapositives originales, ancien EA ni historique Git. Les références M1/5, M9/2, etc. dans les documents préexistants sont des assertions à vérifier, pas des sources accessibles. La compilation, l’exécution et la parité **native** de MT5 restent non réalisées.

| Comparaison | Conclusion |
| --- | --- |
| A, formation originale → B, formalisation | Bloquée : A absent de l’archive |
| B → C Python reçu | Réfutée sur plusieurs règles et contrats |
| B → C Python corrigé | Vérifiée sur les scénarios exécutés ; couverture partielle, propositions de B conservées |
| B → C MQL5 corrigé | Corrections écrites et relues ; validation native à faire |
| A → C, fidélité finale | Bloquée : aucune certification SMV possible |
| Performance de trading après corrections | Non mesurée : données brutes et provenance reproductible absentes |

## Méthode et périmètre

Le constat d’absence des sources a été consigné avant lecture approfondie de la spécification dérivée (`audit_evidence/SOURCE_GATE.md`). Je n’ai pas rempli cette lacune avec une définition SMC trouvée ailleurs. L’audit a ensuite séparé les garanties techniques, les propositions de formalisation et les affirmations attribuées à la formation. Les recherches officielles et les interprétations externes sont dans `GPT_RESEARCH.md`. La traçabilité et la comparaison finale avec le travail préexistant sont dans `GPT_STRATEGY_REVIEW.md`.

Tous les fichiers textuels de l’archive ont été examinés ; les JSON de résultats ont été parcourus, et le SVG synthétique a été inspecté puis rendu. Ce graphique ne constitue pas un exemple annoté du formateur. La carte des 66 fichiers et leurs rôles figure dans `audit_evidence/REPOSITORY_MAP.md`, avec tailles et empreintes dans `input_manifest.json`. Aucun Pine Script n’est présent : l’audit `request.security`, `barstate`, `varip` et limites TradingView est sans objet.

Les sévérités suivent votre définition. Un BLOCKER de validation indique aussi une condition empêchant l’acceptation demandée ; il ne signifie pas nécessairement qu’une erreur de compilation a été constatée. « Corrigé Python » signifie testé dans cet environnement. « Reporté MQL5 » signifie modification de source, encore non validée dans MetaTrader.

## Registre des constats

| ID | Sévérité | Constat | État |
| --- | --- | --- | --- |
| F01 | BLOCKER | Sources de formation et historique absents | Fidélité non vérifiable |
| F02 | BLOCKER | Une bougie source déborde sa période HTF | Corrigé Python |
| F03 | BLOCKER | Heure répétée : état HTF visible trop tôt | Corrigé Python |
| F04 | CRITICAL | BOS de continuation masque une prise du protégé | Corrigé Python, reporté MQL5 |
| F05 | CRITICAL | Premier LH/HL après BOS ignoré comme fail | Corrigé Python, reporté MQL5 |
| F06 | CRITICAL | Excursion de range masque l’autre borne | Corrigé Python, reporté MQL5 |
| F07 | CRITICAL | Un ancien IDM survit à des changements de tendance | Corrigé Python, reporté MQL5 |
| F08 | CRITICAL | Statistiques EQ qualifiées avec le futur | Script corrigé ; chiffres à recalculer |
| F09 | CRITICAL | Mesure mensuelle omet les jours 26 à fin du mois | Script corrigé ; chiffres à recalculer |
| F10 | MAJOR | Données et paramètres invalides admis | Corrigé Python, contrôles MQL5 renforcés |
| F11 | MAJOR | Charge utile du journal modifiable après émission | Corrigé Python |
| F12 | MAJOR | EQ au-delà de l’âge maximal | Corrigé Python, reporté MQL5 |
| F13 | MAJOR | Stop traversé par gap valorisé systématiquement à −1 R | Modèle corrigé Python, reporté MQL5 |
| F14 | MAJOR | Relecture graphique utilise des statuts futurs | Corrigé Python |
| F15 | MAJOR | Extrêmes mensuels tirés d’une bougie hors fenêtre | Corrigé Python, reporté MQL5 |
| F16 | MAJOR | Mélange aléatoire supprime les gaps | Script corrigé ; modèle nul limité |
| F17 | MAJOR | Chargement de recherche répare silencieusement l’OHLC | Corrigé Python |
| F18 | MAJOR | Étude étiquetée BM 0,6 exécutée à 0,7 | Configuration explicite corrigée |
| F19 | MAJOR | Plafond initial MT5 glissant au rechargement | Défaut passé à historique complet ; contexte limité documenté |
| F20 | MAJOR | Instances MT5 partagent le même espace d’objets | Isolation écrite ; test terminal à faire |
| F21 | MAJOR | Fenêtre de dessin MT5 ne supprime pas les anciens objets | Purge écrite ; test terminal à faire |
| F22 | MAJOR | Entrées MT5 invalides et MN1 traité comme durée fixe | Contrôles ajoutés ; test terminal à faire |
| F23 | MAJOR | Indépendance de N affirmée à tort, rotation annoncée absente | Errata documenté |
| F24 | MAJOR | Setups simplifiés présentés à côté de règles plus riches | Écart documenté ; sources requises |
| F25 | MAJOR | Inférence et reproductibilité des calibrages insuffisantes | Conclusions suspendues ; comptes de censure ajoutés |
| F26 | BLOCKER | Parité MT5 native non démontrée | Protocole fourni, non exécuté |
| F27 | MINOR | Versions et notices préexistantes désynchronisées | Documenté, pas de nouvelle version de produit inventée |
| F28 | INFO | Cache HTF MT5 et timestamps renforcés | Source corrigée, comportement terminal à vérifier |

### F01 — Formation originale inaccessible

- **Fichier / zone :** `README.md`, `docs/STRATEGY_SPEC.md §0.2`, archive entière. **Source :** critère d’acceptation A → B → C de votre demande.
- **Actuel :** des documents citent un corpus `../Strategie/` absent. Aucun historique n’atteste comment les règles ont été dérivées. **Attendu :** sources originales consultables, références exactes et exemples annotés.
- **Preuve :** inventaire exhaustif et empreintes de l’archive ; nouvel essai GitHub retourne 404. **Impact :** impossible de déclarer la stratégie reproduite, même avec un moteur déterministe.
- **Correction proposée :** confronter chaque ligne du registre de stratégie au corpus original quand il devient disponible. **Test :** annotations manuelles du formateur avec niveaux, sens, événements et instants de confirmation. Aucun substitut externe ne remplit ce test.

### F02 — Agrégation HTF avec publication prématurée

- **Fichier / fonction :** `smv/mtf.py::resample`. **Source :** R-MTF-01 et contrat de disponibilité des bougies closes.
- **Reçu :** une bougie de 15 minutes est agrégée dans une période de 7 minutes ; son high est publié à minute 7 alors qu’il n’est connu qu’à minute 15. Une heure avec ouverture ou bougie intermédiaire manquante est aussi déclarée complète si sa dernière clôture atteint la borne.
- **Attendu / preuve :** impossible de découper cet OHLC sans données plus fines. Tests `test_resample_rejects_a_bar_that_contains_future_of_its_bucket` et `test_resample_omits_missing_start_and_missing_middle` échouent avant correction. **Impact :** anticipation et OHLC HTF incomplet présenté comme complet.
- **Correction :** intervalle entièrement contenu, début exact, continuité, fin exacte ; refus d’un chevauchement, omission des périodes trouées. Grille alignée en UTC. Les gaps ne sont pas comblés artificiellement.

### F03 — Heure répétée et fuite d’un état HTF

- **Fichier / fonctions :** `smv/mtf.py::HtfView.at`, `smv/timing.py::SessionMarker.update`. **Source :** contrat temporel et documentation Python `datetime` citée dans `GPT_RESEARCH.md`.
- **Reçu :** avec le même objet `ZoneInfo`, les comparaisons peuvent ignorer `fold`. À New York le 1 novembre 2026, 01:00 à UTC−4 est pris pour 01:00 à UTC−5. L’état d’une bougie close à 06:00 UTC est renvoyé à 05:00 UTC. À Paris, une session du premier 02:00 peut disparaître et une fenêtre de 60 minutes peut durer deux heures réelles.
- **Attendu :** comparaison d’instants UTC ; durée ajoutée en UTC. **Preuve / tests :** les deux tests `dst_fold` échouent avant correction ; les résultats attendus sont obtenus par conversion manuelle des décalages. **Impact :** anticipation HTF et repères temporels incorrects.
- **Correction :** heures des vues, comparaisons de sessions et suivi de couverture mensuelle normalisés en UTC. Les heures locales restent utilisées pour définir les fenêtres et afficher les libellés.

### F04 — Deux faits simultanés, un seul événement

- **Fichier / fonction :** `smv/structure.py::_check_breaks`, `mt5/Include/SMV/Structure.mqh::CheckBreaks`. **Source :** R-ST-05 et R-ST-06.
- **Reçu :** avant la bougie 11, protégé = 10 et référence = 13. La bougie `(12,14,9,14)` ferme au-dessus de 13 et prend 10 en mèche. Le retour anticipé du BOS oublie `PROTECTED_SWEEP`.
- **Attendu :** les deux faits sont journalisés avec l’ancien état, sans supposer l’ordre des extrêmes à l’intérieur de la bougie. **Impact :** perte de liquidité et lecture incomplète des outside bars.
- **Correction / test :** tester le protégé avant mutation par continuation, puis émettre le BOS. `test_bos_and_old_protected_sweep_are_both_observable`, hausse et baisse par réflexion des prix.

### F05 — Fail après réinitialisation de la jambe

- **Fichier / fonction :** `structure.py::_integrate_pivot`, port MQL5 `IntegratePivot`. **Source :** R-ST-03 et R-ST-07 : premier pivot étiqueté LH en hausse, HL en baisse.
- **Reçu :** `_last_leg_pivot` est remis à zéro au BOS. Un premier pivot post-BOS déjà classé LH par le détecteur global n’a aucun prédécesseur local ; il n’émet pas FAIL.
- **Preuve :** high 20 confirmé au BOS 12, puis high 18 en 13 confirmé en 14 : le journal dit LH, sans fail. **Attendu :** FAIL confirmé à 14, ancré à 13. **Impact :** consolidation et setups possibles oubliés.
- **Correction / test :** utiliser l’étiquette du pivot confirmée selon R-ST-03, une fois par jambe. `test_first_lower_high_after_bos_is_a_fail`, avec cas baissier symétrique. Cela aligne C sur B ; cela ne prouve pas la règle de la formation.

### F06 — Une excursion en clôture cache la borne opposée

- **Fichier / fonction :** `ranges.py::update`, MQL5 `Ranges.mqh::Update`. **Source :** R-GS-02, épisodes par borne ; R-CE-01, acceptation en clôture.
- **Reçu :** les retours anticipés lors d’une clôture hors range et de sa récupération empêchent l’examen de l’autre mèche. Range `[9,11]`, bougie `(10,12,8,11.5)` : l’excursion haute attend sa confirmation, mais la prise basse est immédiatement observable à la clôture et disparaît.
- **Attendu :** suivre la sortie en attente et la borne opposée indépendamment ; à la récupération, traiter encore l’autre borne ; conserver le statut d’épisode pour éviter un double comptage.
- **Impact / correction / test :** décompte et qualification GOLDEN faussés. Traitement séparé écrit dans les deux moteurs. Les deux cas de `test_pending_range_excursion_does_not_hide_other_side` vérifient les listes exactes d’événements, sans ordre intra-bougie inventé.

### F07 — IDM ancien réutilisable après retournement

- **Fichier / fonction :** `setups.py::on_events`, MQL5 `Setups.mqh::OnEvents`. **Source :** R-SE-01b, inducement révélé et pris dans la tendance concernée.
- **Reçu :** un BOS_CHANGE efface `idm_taken_dir`, mais pas `idm_levels`. Un IDM haussier ancien peut être pris après un passage baissier puis un retour haussier et qualifier un CONCEPT.
- **Attendu :** le changement de contexte invalide les révélations non consommées. **Preuve / test :** journal manuel IDM → BOS_CHANGE baissier → BOS_CHANGE haussier → LIQ_CLEAN ; `test_old_inducement_does_not_survive_a_trend_change`.
- **Impact / correction :** faux contexte d’entrée. Effacement des IDM à TREND_INIT et BOS_CHANGE. Unité testée isolément ; les autres tests vérifient l’orchestration.

### F08 — Qualification EQ obtenue dans le futur

- **Fichier / fonction :** `research/study_outcomes.py::study_liquidity`. **Source :** commentaire du script : mesures après confirmation, sans anticipation du signal.
- **Reçu :** `eq_ids` est construit sur tout le journal ; un niveau créé à 0 devient EQ parce qu’une égalité survient à 5. La distance et l’horizon sont pourtant mesurés depuis 0.
- **Attendu :** niveau ordinaire à 0, exposition EQ seulement à 5. **Preuve :** prise à 6, horizon 3 : elle n’est pas dans le futur `[1,3]` du niveau initial, mais est dans `[6,8]` de l’EQ. Le test de recherche fixe ces deux résultats manuellement.
- **Impact / correction :** comparaison EQ/ordinaire biaisée. Expositions datées à la première révélation, niveaux déjà pris exclus, horizon incomplet exclu. Les expositions d’un même niveau restent corrélées : les intervalles Wilson ne constituent pas une inférence robuste. Q-07 doit être recalculée.

### F09 — Fin de mois retirée de la mesure mensuelle

- **Fichier / fonction :** `research/study_outcomes.py::month_paths`. **Source :** fenêtre annoncée `[26 précédent, fin du mois]` et Q-09.
- **Reçu :** chaque date ≥26 est affectée seulement au mois suivant. La mesure du mois courant s’arrête le 25. Un high le 27 ne peut plus invalider le high de sa fenêtre initiale.
- **Attendu / preuve :** le 27 février avec high 50 doit faire échouer `window_high_holds` pour février. `test_month_measurement_includes_the_last_days_of_the_month` échoue sur la version reçue.
- **Impact / correction :** conclusion sur le maintien des extrêmes biaisée. Les dates de fin de mois appartiennent au résultat de leur propre mois et au début de la fenêtre suivante ; mois tronqués aux bords de l’échantillon exclus. L’étude conserve ses journées UTC : elle n’établit toujours pas les extrêmes exacts d’une fenêtre Paris à partir d’OHLC journaliers UTC.

### F10 — Valeurs invalides admises avant calcul

- **Fichier / fonctions :** `context.py::append`, `config.py::__post_init__`, contrôles MQL5 correspondants. **Source :** domaine des paramètres et précondition d’un historique OHLC chronologique.
- **Reçu :** NaN/inf, doublons, intervalles qui se chevauchent et certains paramètres négatifs ou non entiers sont acceptés. NaN neutralise des comparaisons et se propage dans l’ATR.
- **Attendu :** rejet explicite avant mutation. Gaps légitimes admis, pas de bougies artificielles. **Preuve / tests :** trois prix non finis, doublon, chevauchement et neuf configurations invalides dans `test_gpt_adversarial.py`.
- **Impact / correction :** états silencieusement incohérents ou erreur tardive. Validations des prix, volume Python, bornes, temps avec fuseau, ordre UTC, comptes entiers et seuils finis. Le port MT5 ne possède pas de champ volume et n’a pas acquis de logique de volume.

### F11 — Un journal frozen contenant des listes mutables

- **Fichier / zone :** `types.py::Event.data`. **Source :** §0.5 et D-03, événements en ajout seul.
- **Reçu :** `@dataclass(frozen=True)` protège l’affectation des attributs, pas le dictionnaire ni la liste `targets`. Modifier le dictionnaire d’origine peut réécrire un événement déjà émis.
- **Attendu / preuve :** copie défensive et protection des conteneurs imbriqués ; les essais d’append et d’affectation doivent échouer. **Impact :** historique et relecture modifiables par un consommateur ordinaire.
- **Correction / tests :** conteneurs gelés compatibles JSON et `asdict`. `test_event_payload_cannot_change_after_emission`, `test_frozen_event_remains_serializable`. La garantie concerne l’API normale, pas une protection contre un code qui contourne volontairement les mécanismes Python.

### F12 — EQ trop ancien

- **Fichier / fonction :** `liquidity.py::on_pivots`, port MQL5 `OnPivots`. **Source :** R-LQ-03 et `eq_max_gap`.
- **Reçu :** le prix est comparé avant le contrôle d’âge ; un ancien niveau correspondant est accepté hors fenêtre. L’ordre de création mélange pivots retardés et signatures : il ne garantit pas l’ordre des ancrages.
- **Attendu :** vérifier l’âge avant l’égalité, continuer la recherche sans supposer cet ordre. **Preuve :** highs 5 en 1 et 4,999 en 9, âge maximal 3 ; `test_equal_highs_obey_maximum_age`.
- **Impact / correction :** faux EQ. Contrôle déplacé dans Python et MQL5 ; statut intact, côté et source restent requis. Le scan peut encore être coûteux sur beaucoup de niveaux survivants.

### F13 — Stop et prix d’exécution confondus

- **Fichier / fonction :** `setups.py::update`, `Setups.mqh::Update`. **Source :** arithmétique du R et distinction déclenchement/exécution, documentation officielle citée dans la recherche.
- **Reçu :** position déjà déclenchée, entrée 10, stop 9, ouverture suivante 7 : toujours −1 R. **Attendu :** exécution de référence à l’ouverture, soit `(7−10)/(10−9) = −3 R`, avec motif `stop_gap` et prix 7.
- **Preuve / test :** `test_stop_gap_is_not_reported_as_guaranteed_minus_one_r`. **Impact :** pertes sous-estimées sur des positions déjà ouvertes.
- **Correction :** champ `execution_price`, ouverture au-delà du stop pour ces positions ; stop nominal sinon. Cible 1 reste au prix limite nominal. Ce modèle OHLC n’est pas un moteur de courtier : gaps sur ordres encore en attente, spread, ordre réel des transactions et glissement restent non identifiables.

### F14 — Affichage daté avec statuts futurs

- **Fichier / fonction :** `render/primitives.py::build`. **Source :** `visible_from`, §0.5, séparation journal/visualisation.
- **Reçu :** un LIQ_CLEAN confirmé en 10 modifie déjà style et fin du niveau lors d’un `build(..., last_index=5)`. Une consolidation remplacée par un nouveau FAIL reste dessinée comme ouverte, faute de RANGE_EXIT.
- **Attendu :** seuls les événements confirmés jusqu’à 5 influencent la vue ; l’ancienne range se termine à la confirmation du remplacement. **Impact :** relecture trompeuse, différente de l’état interne.
- **Correction / tests :** filtrage interne à `build`, suivi des remplacements. `test_render_asof_does_not_use_future_status`, `test_render_range_ends_when_replaced`. Le SVG principal filtrait déjà les événements en amont ; le défaut temporel concernait l’API publique de primitives.

### F15 — Frontières mensuelles et historique partiel

- **Fichier / fonction :** `timing.py::MonthWindow.update`, port `Timing.mqh`. **Source :** R-OU-02, fenêtre Paris du 26 à minuit au 10 à minuit exclus.
- **Reçu :** toute bougie ouverte dans la fenêtre contribue son high/low complet, même si elle finit après la borne. Un lancement au milieu de la fenêtre annonce les extrêmes sans indiquer que le début manque.
- **Preuve :** bougie UTC du 9 janvier, high 99 : ce high peut appartenir à la dernière heure hors fenêtre Paris. **Attendu :** ne pas attribuer un extrême impossible à localiser ; signaler les observations partielles.
- **Correction / tests :** bougies entièrement contenues seulement, `coverage`, `excluded_boundary_bars`, contrôle de continuité UTC. Test de frontière et tests de couverture continue/trouée. `partial` est conservateur : un week-end non documenté ne prouve pas l’absence de données attendues. Sans aucune bougie entièrement contenue, aucun extrême n’est émis.

### F16 — Modèle nul sans gaps

- **Fichier / fonction :** `research/study_nulls.py::shuffled`, `month_null`. **Source :** promesse de conserver la distribution des bougies et validité de l’ATR utilisé ensuite.
- **Reçu :** chaque ouverture devient la clôture précédente ; volume perdu et gaps supprimés. **Preuve :** TR triés `[2,12,22,27]` deviennent `[2,3,3,3]` sur quatre bougies manuelles.
- **Attendu / correction :** première bougie conservée comme condition initiale ; permuter ensemble gap d’ouverture, corps, mèches et volume ; méthode également utilisée dans le nul mensuel. `test_null_preserves_gaps_true_range_and_volume`.
- **Impact :** volatilité et rapports en ATR comparés à un autre problème statistique. Le mélange détruit encore dépendance et saisonnalité : il ne devient pas un modèle réaliste de marché par cette correction.

### F17 — Réparation silencieuse de données de recherche

- **Fichier / fonction :** `research/marketdata.py::load`. **Source :** précondition OHLC et reproductibilité des données.
- **Reçu :** `max(high,open,close)` et `min(low,open,close)` masquent un high/low incohérent. **Attendu :** rejet avec l’erreur conservée, correction des données en amont explicitement justifiée.
- **Preuve / test :** CSV avec high inférieur au close dans `test_market_data_does_not_silently_repair_invalid_ohlc`. **Impact :** données modifiées sans compter ni publier les réparations.
- **Correction :** validation commune, sans réparation. Les hypothèses de fuseau serveur, échelle, arrondi et UTC pour D1 restent des hypothèses du chargeur ; elles ne sont pas attestées par les données absentes.

### F18 — Configuration BM mal attribuée

- **Fichier / zone :** `research/study_outcomes.py::main`, clé `zones_h1_bosorigin_bm0.6`. **Source :** provenance du paramètre dans la clé de résultat.
- **Reçu :** `Config()` vaut désormais 0,7 ; les lignes annoncées 0,6 et 0,7 exécutent le même seuil. **Attendu :** seuil 0,6 explicitement fourni pour la première ligne.
- **Preuve :** lecture du défaut dans `config.py` et de l’appel du script. **Impact :** résultats non reproductibles sous leur étiquette.
- **Correction / vérification :** `Config(bm_body_min=0.6)` et 0,7 explicites. Contrôle de source ; pas de nouveau backtest réel ni de résultats chiffrés inventés.

### F19 — Historique plafonné au lancement, contexte différent au rechargement

- **Fichier / fonction :** `SMV_Indicator.mq5::FullReset`, `InpMaxBars`. **Source :** déterminisme à données et configuration identiques, contrat de rechargement.
- **Reçu :** origine = `rates_total−1−20000` au reset, puis le moteur s’allonge sans appliquer ce maximum. Au rechargement après de nouvelles bougies, l’origine glisse. ATR, pivots, protégé et identifiants peuvent changer parce que le préfixe fourni au moteur a changé.
- **Attendu :** contexte d’entrée explicitement défini, pas de garantie universelle de résultat identique avec un autre préfixe. **Preuve :** formule et transitions de reset, non essai terminal.
- **Correction :** `InpMaxBars=0` par défaut pour tout l’historique disponible ; cap positif renommé dans le commentaire comme limite initiale. **Test :** protocole natif N04. Le chargement de données plus anciennes ou la correction des données peut toujours changer le résultat ; ceci n’est pas un futur lu dans le moteur.

### F20 — Collision entre instances graphiques MT5

- **Fichier / fonctions :** `SMV_Indicator.mq5::OnInit/OnDeinit`, `Draw.mqh::Reset`. **Source :** unicité par instance et documentation officielle des objets.
- **Reçu :** toutes les instances d’un graphique utilisent `SMV_<ChartID%100000>_`. Le reset ou retrait de l’une supprime les objets de l’autre. Avant allocation de préfixe, un échec d’initialisation pouvait conserver un préfixe trop général.
- **Attendu / correction :** propriétaire réservé par instance, préfixe vide avant allocation et nettoyage seulement du préfixe possédé. **Preuve :** comparaison des constructions de nom et du `ObjectsDeleteAll` ; pas de terminal exécuté.
- **Impact / test :** disparition ou remplacement de structures pourtant calculées correctement. N05 : deux instances, retrait de l’une, initialisation invalide ; aucune suppression chez l’autre.

### F21 — Accumulation d’objets hors fenêtre de dessin

- **Fichier / fonctions :** `Draw.mqh::DrawNew/Extend`. **Source :** contrat de `InpDrawBars`, priorité performance après justesse.
- **Reçu :** le filtre limite les nouvelles créations mais ne retire jamais les anciennes. Les objets ouverts continuent d’être étendus. **Attendu :** les objets dont la confirmation sort de la fenêtre sont supprimés et désenregistrés.
- **Correction :** noms compacts à index de journal et confirmation, purge par confirmation ; identifiants métier complets en info-bulle. La limite officielle de 63 caractères est respectée par cette construction ; les anciennes références concaténées pouvaient aussi croître avec l’historique.
- **Preuve / impact :** absence de suppression dans le chemin incrémental reçu ; croissance des objets malgré une fenêtre fixe. **Test :** N06 en terminal, durée longue avec petit `InpDrawBars`, contrôle du nombre d’objets et de leur propriétaire. Les appels synchrones d’objets restent un coût à mesurer.

### F22 — Paramètres de plate-forme hors domaine

- **Fichier / fonction :** `SMV_Indicator.mq5::OnInit`, `FullReset`. **Source :** validité des indices et des durées, documentation des périodes.
- **Reçu :** `InpMaxBars<0` peut produire `g_start` au-delà du tableau ; warmup et taille de dessin non contrôlés. MN1 est utilisé comme durée nominale fixe alors qu’un mois civil n’est pas toujours de cette durée.
- **Attendu / correction :** rejeter ces paramètres avant traitement ; refuser MN1 de base tant qu’une clôture calendaire n’est pas implémentée. **Preuve :** substitution d’une valeur négative dans la formule et variation de longueur des mois, sans exécution MT5.
- **Impact / test :** erreur d’indice ou dates de clôture incorrectes. N07 couvre paramètres négatifs, MN1, faible historique et changement d’UT.

### F23 — Structure sensible aux pivots, rotation absente

- **Fichiers / zones :** `STRATEGY_SPEC.md::R-ST-02`, `DECISIONS.md::D-05`, `CALIBRATION.md::Q-08`, `structure.py`, `config.py`. **Source :** assertions internes comparées au code.
- **Reçu :** la structure majeure est dite indépendante de N ; pourtant `ref` et FAIL dépendent des pivots. La rotation est annoncée comme marqueur, mais `rotation_legs` n’est pas consommé par le moteur et aucun événement de rotation n’existe.
- **Preuve :** même série de 17 closes, N=1 donne INIT en 6, BOS en 11, changement en 14 ; N=4 n’en donne aucun. Usage du paramètre limité à validation/provenance. **Impact :** fausse portée des réglages et couverture annoncée.
- **Attendu / correction proposée :** retirer l’affirmation d’indépendance et qualifier la rotation de non implémentée. Errata séparé ; pas de nouvel algorithme inventé. **Test :** comparaison de la série et recherche des consommateurs du paramètre, détaillées dans la revue de stratégie.

### F24 — Un sous-ensemble formalisé ne couvre pas les entrées décrites

- **Fichiers / fonctions :** `STRATEGY_SPEC.md::R-GS-03/§9/R-MTF-03`, `setups.py::_qualify`, `zones.py::build/update`. **Source :** déclarations de B ; A absent.
- **Reçu :** GOLDEN exige une zone de BOS après un sweep et omet le contexte décisionnel HTF. Le drapeau `decisional` est un proxy BOS_CHANGE. La cause peut accepter différents ordres, mais une intention antérieure au sweep ne qualifie pas une entrée sans nouveau BOS. Le breaker est toute zone rompue, sans démontrer le zéro-réaction et le BOS décrit dans B. CONCEPT est un sous-modèle nécessitant la continuation suivante.
- **Attendu :** distinguer explicitement ces heuristiques de la stratégie complète. **Impact :** un programme conforme à §10 peut manquer les exemples de §8/§9 ou accepter des contextes non enseignés.
- **Correction proposée / preuve / test :** formalisation à décider sur les transcriptions et exemples originaux ; aucun filtre ni séquence arbitraire ajouté. Lecture des prédicats, puis future comparaison à un jeu annoté, détaillée dans `GPT_STRATEGY_REVIEW.md`.

### F25 — Calibrage non certifiable et inférence trop forte

- **Fichiers / fonctions :** tous les `research/study_*.py`, `results_*.json`, `CALIBRATION.md::Q-01…Q-16`. **Source :** reproductibilité, distinction description/inférence, publication de Bailey et al. citée dans la recherche.
- **Reçu :** données hors archive, révision non épinglée, niveaux/trades et fenêtres qui se chevauchent, intervalles simples supposant une indépendance non démontrée. Le split 2019 n’est pas attesté comme jamais consulté lors du choix des paramètres. Les trades encore ouverts/en attente ne sont pas comptés. La rotation est sélectionnée sur une liste de pivots alternés construite rétrospectivement.
- **Attendu :** données et hash, heures attestées, règles figées avant évaluation, censure publiée et méthode adaptée aux dépendances. Un histogramme de corps ou une médiane d’ATR ne prouve pas une intention du formateur.
- **Impact / correction :** résultats descriptifs ne tranchent pas la fidélité ni une espérance réelle. Comptes des déclenchements, clôtures, ordres encore ouverts/en attente ajoutés au script de setups ; autres inférences suspendues. Les JSON préexistants restent inchangés et marqués obsolètes pour le moteur corrigé.
- **Test futur :** reproduction sur données identiques, audit des réparations interdites, validation temporelle hors sélection et analyse de sensibilité des règles. Aucun PBO chiffré ni backtest sur données absentes n’est prétendu.

### F26 — Validation native manquante

- **Fichiers / zones :** `mt5/`, `tests/test_mt5_parity.py`, `tools/mt5_parity.py`. **Source :** D-19 et critère d’acceptation du portage.
- **Reçu :** le comparateur est testé avec des exports produits par Python. Le commentaire du test le dit correctement ; ce n’est pas une validation du moteur MQL5. Le comparateur acceptait également un prix NaN comme égal, car `abs(NaN)>tol` vaut faux.
- **Attendu / correction :** rejet de tout numérique non fini dans la comparaison ; compilation MetaEditor puis journal réellement exporté de MT5 sur les mêmes bougies. **Preuve / test :** `test_parity_rejects_nan_event_price` corrigé ; aucun compilateur ni Wine disponible dans l’environnement.
- **Impact :** aucune déclaration « MT5 validé » possible. **Test futur :** N01 à N08 dans le rapport de tests, export natif obligatoire ; vérification distincte HTF car l’export courant porte seulement le moteur de base.

### F27 — Versions et présentation

- **Fichiers / zones :** `smv/__init__.py`, `tools/run_smv.py`, notices et SVG. **Source :** métadonnées cohérentes.
- **Reçu :** paquet 0.1.0 et titre SVG v0.1, README v0.2. Plusieurs étiquettes se superposent sur les graphiques denses. **Attendu :** version de produit décidée explicitement, légende de confirmation claire, filtres d’affichage adaptés.
- **Preuve / impact :** lecture des valeurs et rendu visuel du SVG original et du smoke test ; confusion limitée, aucune preuve de logique correcte tirée du dessin.
- **Correction proposée / test :** préparer une version après validation native ; comparer les métadonnées et contrôler le rendu. Le README reçoit un avertissement d’audit séparé ; les documents et SVG historiques ne sont pas remplacés silencieusement.

### F28 — Durcissement du cache HTF MT5

- **Fichier / fonctions :** `SMV_Indicator.mq5::HtfLoad/HtfFeedUntil/OnCalculate`. **Source :** documentation officielle CopyRates et séries.
- **Reçu :** admission fondée sur une clôture nominale et TimeCurrent ; pas d’exclusion explicite du bar zéro ni de contrôle de synchronisation. La clôture UTC est calculée par addition à l’ouverture UTC, sans reconversion de la borne serveur. L’échec du moteur HTF est ignoré.
- **Attendu / correction :** CopyRates appelé pour initier le chargement, puis série synchronisée ; exclusion de `iTime(...,0)`, indices ascendants explicites, conversion des deux bornes serveur et propagation de l’échec HTF.
- **Preuve / limites :** contrôle de code et documentation ; aucun scénario MT5 exécuté ne prouve un défaut de marché ni la justesse du correctif sur un broker. **Impact / test :** meilleure conformité au contrat de bougies closes ; N02/N03 doivent contrôler DST, week-ends, historique tardif, rechargement et cache. Les corrections historiques HTF seules, fuseaux non attestés et dates antérieures aux règles codées restent des limites.

## Architecture, automates et complexité

L’ordre général est pertinent : contexte → statuts des objets antérieurs → pivots et structure → nouvelles zones/liquidités → cause et setups → marqueurs. Un objet créé à la clôture i est suivi à partir de i+1. Cette organisation évite des consommations rétroactives et reste conservée.

Les graphes de `GPT_STRATEGY_REVIEW.md` montrent les transitions. Les états critiques observés étaient des contextes résiduels et des sorties anticipées, plutôt qu’une dépendance circulaire. Un trend inconnu sur un historique court n’est pas un état mort : aucune cassure confirmée ne l’a encore initialisé. L’absence de BOS dans une impulsion sans référence fixée est une proposition de B, pas une erreur démontrée. Range et trend peuvent coexister ; une sortie de range ne change pas automatiquement la structure majeure.

Le scan de tous les pivots à chaque continuation a été réduit à ceux postérieurs à la référence, en conservant l’ordre des événements. Les bornes de retracement et de retournement restent des scans de leur intervalle. L’égalité et les cibles parcourent des niveaux intacts ; les zones actives et liens ODF peuvent encore croître. Au pire, ces chemins peuvent tendre vers O(n²), notamment avec de nombreux objets survivants. Le journal, les bougies et les pivots conservent une mémoire O(n). MQL5 trie les cibles par insertion et examine tous les niveaux intacts : les performances Python ne valident pas celles de MT5.

Mesure indicative sur Python 3.12.14, mêmes réglages, série synthétique seed 6 : 5 000 bougies en 0,2305 s, 10 000 en 0,4850 s, 20 000 en 1,3336 s. RSS maximale cumulative du processus : environ 19, 30 et 49 Mio. Une seule exécution par taille, génération exclue ; aucune promesse de complexité linéaire, temps réel ou latence broker. Fichier brut : `audit_evidence/benchmark.json`.

## Ce qui est conservé et ce qui reste à accepter

La séparation ancrage/confirmation, le retard de pivot, la stricte clôture des cassures, la priorité au stop quand l’ordre intra-bougie est inconnu et le marquage provisoire Wyckoff sont de bonnes décisions techniques. Les tests existants vérifient plusieurs règles exactes et l’invariance de préfixe ; ils ne sont pas tous tautologiques. Le test streaming=batch est moins indépendant puisque `run` appelle `on_bar`. Le test de parité simulée vérifie un format et un comparateur, pas une plate-forme.

Les documents préexistants `STRATEGY_SPEC`, `RESEARCH`, `CALIBRATION`, `ARCHITECTURE`, `DECISIONS` et les cinq JSON de résultats sont conservés. Les divergences et les conclusions historiques suspendues sont consignées ici, sans réécrire leur provenance. Les réglages de stratégie n’ont pas été recalibrés sur des données synthétiques.

Pour accepter l’indicateur comme fidèle à SMV, il manque le corpus original et un jeu d’exemples annotés. Pour accepter le portage MT5, il manque la compilation et les essais natifs. Pour reprendre les conclusions statistiques, il manque les données épinglées, leur validation et une nouvelle étude après corrections. L’archive livrée rend ces travaux concrets et reviewables ; elle ne masque pas ces trois limites.
