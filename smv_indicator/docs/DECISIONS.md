# DECISIONS : décisions techniques et de lecture

Format : contexte, options, décision, conséquences, statut. Version 0.2 : le responsable de la stratégie a fixé la plateforme cible (MetaTrader 5) et a demandé que les autres questions soient tranchées par la recherche ; les statuts ci-dessous en tiennent compte (D-17). Les réponses restent révisables par lui.

## D-01 Le dépôt est la source de vérité, pas l'ancien EA ni ses analyses

- **Contexte** : le dépôt contient les transcriptions (source primaire), des analyses `.md` produites par un tiers et un EA dont l'audit déclare une conformité de 90 à 98 %.
- **Décision** : seules les transcriptions et diapositives font foi. L'EA et ses audits servent à repérer des écarts (STRATEGY_SPEC §12).
- **Conséquence** : plusieurs règles de l'EA ne sont pas reprises (seuil de BM à 70 %, 80/20 en filtre de prix, intact par clôture, kill zones filtrantes).
- **Statut** : acté.

## D-02 Cœur en Python pur, événementiel, bougie par bougie

- **Contexte** : besoin d'un code testable, réutilisable (indicateur, scanner, backtest) et portable ; l'environnement ne permet pas de compiler du MQL5.
- **Options** : MQL5 direct, Pine Script, bibliothèque vectorisée, cœur événementiel (ARCHITECTURE §2).
- **Décision** : cœur événementiel en Python standard, sans dépendance d'exécution ; adaptateurs d'affichage séparés.
- **Conséquences** : tests automatiques possibles ici ; le portage MT5 reste à faire et sera validé par comparaison des journaux.
- **Statut** : acté. Plateforme cible confirmée : MetaTrader 5 (D-19). Le cœur Python reste la référence testée ; l'indicateur MQL5 en est le portage.

## D-03 Journal d'événements en ajout seul, daté par confirmation

- **Contexte** : plusieurs notions du dépôt sont rétrospectives (pivots, inducement, SC/BC « après coup »).
- **Décision** : chaque événement porte `confirm_index` et `anchor_index` ; aucun événement n'est modifié ; un changement de statut est un nouvel événement.
- **Conséquences** : l'historique affiché est exactement ce qui était connu à chaque instant ; les retards sont visibles et assumés.
- **Statut** : acté.

## D-04 Test d'invariance par préfixe comme garde-fou permanent

- **Décision** : tout changement du moteur doit passer `tests/test_no_lookahead.py`.
- **Justification** : la bibliothèque publique étudiée (RESEARCH §2.3) montre qu'un look-ahead peut passer inaperçu dans un code populaire.
- **Statut** : acté.

## D-05 Pivots fractals de Williams pour les swings

- **Contexte** : le dépôt ne définit pas un « high » ou un « low » (R-ST-02).
- **Options** : pivot fractal à N bougies ; ZigZag à seuil (pourcentage ou ATR) ; swings définis uniquement par les cassures.
- **Décision** : pivot fractal (défaut 2/2) pour les swings de base, et automate de cassures pour la structure majeure. **Erratum (audit F23)** : la structure majeure dépend de N, car la référence de continuation et le fail sont des pivots.
- **Raisons** : définition objective, connue, sans repaint ; un ZigZag à seuil repeint tant que le seuil n'est pas atteint et ajoute un paramètre d'échelle.
- **Conséquence** : la sensibilité dépend de N.
- **Statut** : acté en v0.2 : N = 2 sur toutes les UT ; les jambes mesurées en ATR ont la même distribution de M15 à D1 (`CALIBRATION.md` Q-16).

## D-06 BOS par clôture stricte, sans marge

- **Décision** : `close > niveau` (ou `<`), `bos_eps = 0`. Une clôture égale au niveau n'est pas un BOS.
- **Source** : M1/10 (« le corps de la bougie se clôture au-dessus »).
- **Statut** : acté.

## D-07 Structure majeure : lecture A par défaut, lecture B disponible

- **Contexte** : contradiction R-ST-04 entre M1/M3/M9 (lecture A) et M5/M8 (lecture B).
- **Décision** : les deux sont implémentées (`major_mode`) ; A par défaut.
- **Conséquences mesurées** sur une série synthétique de 3 000 bougies : lecture A, 38 BOS de changement et 120 de continuation ; lecture B, 4 et 28. En lecture B, le niveau protégé reste loin du prix ; après un contre-mouvement, l'extrême de jambe n'est plus dépassé et la structure se fige. C'est une propriété de la lecture B, pas un bug ; elle illustre l'enjeu de l'arbitrage.
- **Mesure sur données réelles (v0.2)** : en lecture B, EURUSD H1 ne produit qu'un BOS de changement en sept ans (XAUUSD : quatre), contre 631 et 574 en lecture A.
- **Statut** : acté en v0.2 : lecture A (`CALIBRATION.md` Q-01). B reste disponible ; elle correspond plutôt à une lecture d'UT supérieure.

## D-08 Zones créées seulement à l'origine d'un BOS

- **Contexte** : le dépôt dit qu'il y a des zones « partout » mais qu'il faut les « décisionnelles » (R-OD-01, R-OD-02).
- **Décision** : `zones_on = "bos_origin"` par défaut ; `"all_pivots"` disponible (zones non validées).
- **Conséquence** : moins de zones, chacune justifiée par une cassure ; une zone « décisionnelle » est provisoirement celle d'un BOS de changement de tendance.
- **Mesure (v0.2)** : l'« excès » de réaction des zones de BOS (+0,11) apparaît aussi sur des bougies mélangées ; il vient de la méthode de mesure. Le choix repose donc sur le texte du dépôt, pas sur un avantage mesuré.
- **Statut** : acté en v0.2 sur la base du dépôt (`CALIBRATION.md` Q-04, Q-05).

## D-09 Zone du corps de la BM à la mèche de la BQA

- **Décision** : `zone_proximal = "body"` (diapositive M2) ; option `"wick"`.
- **Conséquence observée** : quand la BM est une grande bougie, la zone est haute (plusieurs ATR). C'est fidèle à la diapositive mais il faudra comparer avec les zones tracées par le formateur ; le raffinage (M10) répond en partie à ce problème.
- **Statut** : acté en v0.2 : corps ; l'écart de hauteur avec l'option mèche est inférieur à 0,1 ATR (`CALIBRATION.md` Q-03).

## D-10 Une touche de zone est un épisode, pas une bougie

- **Contexte** : la première version comptait une touche par bougie dans la zone (3 088 touches pour 158 zones, soit environ 20 par zone, sur 3 000 bougies synthétiques ; 409 après correction).
- **Décision** : une touche = le prix entre dans la zone après en être sorti.
- **Statut** : acté (cohérent avec « mitigé plusieurs fois »).

## D-11 Intact au sens strict : une mèche suffit à le retirer

- **Décision** : R-LQ-01 tel qu'énoncé (non manipulé). Conséquence : un double sommet dont le second dépasse le premier n'est pas un EQH (STRATEGY_SPEC R-LQ-03, cas limite).
- **Statut** : acté, y compris le cas limite EQH ; tolérance EQ de 0,1 ATR (`CALIBRATION.md` Q-07).

## D-12 Consolidation ouverte par le fail, fermée par acceptation

- **Contexte** : le dépôt ne donne pas de critère de « latéralisation ». Première version : fermeture à la première clôture hors bornes ; elle fermait la consolidation au moment même de l'intention, avant les prises de liquidité.
- **Décision** : ouverture au fail (bornes = climax et AR, comme le décompte Wyckoff du dépôt) ; fermeture après `range_accept_bars = 3` clôtures consécutives hors bornes ; une excursion plus courte est une prise ; une prise est un épisode.
- **Observation** : sur une marche aléatoire de 3 000 bougies, 36 sorties « confirment » le décompte attendu et 31 l'infirment (lecture A). C'est le niveau du hasard ; cela rappelle qu'un décompte qui se confirme souvent n'est pas une preuve d'avantage.
- **Statut** : expérimental ; `range_accept_bars = 3` appuyé sur les sources de praticiens Wyckoff (retour du spring en 1 à 5 bougies, `CALIBRATION.md` Q-11).

## D-13 Heures de tir : marqueurs, ancrages mesurés par défaut

- **Contexte** : deux heures du dépôt semblent fausses (Chicago, Tokyo ; RESEARCH §4) et l'heure US à Paris se décale pendant la désynchronisation des heures d'été.
- **Décision v0.1** : heures de Paris du dépôt, sans correction.
- **Décision v0.2** : ancrages dans le fuseau de chaque place (10:00 Tokyo, 08:00 Londres, 08:30 et 10:00 New York), qui correspondent aux pics de volatilité mesurés en hiver, en été et pendant les semaines désynchronisées. Les heures du dépôt restent disponibles (`session_mode = "repo"`). Toujours des marqueurs, jamais des filtres.
- **Statut** : acté en v0.2 (`CALIBRATION.md` Q-10).

## D-14 Pas de biais mensuel calculé

- **Décision** : la fenêtre du 26 au 9 est mesurée (plus haut, plus bas, horodatés à la fin de la fenêtre), mais aucun biais n'est déduit tant que la règle de choix n'est pas définie.
- **Mesure (v0.2)** : 89,9 % des mois ont un extrême dans la fenêtre, contre 87,2 % sous un modèle nul.
- **Statut** : acté : pas de biais (`CALIBRATION.md` Q-09).

## D-15 Concepts non implémentés volontairement

- Trendline de liquidité (le dépôt la déclare subjective), décompte en rotation, premium/discount, market shift, complexe pullback, vagues d'Elliott. (La couche Setups est implémentée en v0.2, D-18.)
- **Raison** : les coder imposerait des précisions que le dépôt ne donne pas. Ils sont spécifiés comme questions ouvertes.
- **Statut** : acté (v0.2 : Q-13 confirme l'absence de définition dans le dépôt).

## D-16 Pas de push sur le dépôt distant

- **Contexte** : la session n'a pas les droits d'écriture sur `rogshutter/matrix_indicator`.
- **Décision** : travail sur la branche locale `claude/smv-indicator-spec`, livré sous forme de fichiers ; le push se fera quand l'accès sera donné.
- **Statut** : en attente.

## D-17 Questions tranchées par la recherche et la mesure, pas par préférence

- **Contexte** : le responsable de la stratégie a fixé la plateforme cible (MetaTrader 5) et a demandé de trancher les autres questions par la recherche.
- **Décision** : chaque réponse combine le dépôt, des sources externes notées A à D et des mesures sur sept ans de données réelles (EURUSD, XAUUSD), toujours confrontées à deux modèles nuls (ruine du joueur, bougies mélangées). Quand la mesure ne distingue pas une option du hasard, le texte du dépôt décide.
- **Conséquences** : plusieurs affirmations du dépôt sont rapportées comme non vérifiées (« les EQ sautent toujours », biais mensuel, zones décisionnelles plus fiables). Le détail est dans `CALIBRATION.md`.
- **Statut** : acté.

## D-18 Couche Setups implémentée avec deux règles prudentes, affichée comme repère

- **Contexte** : le dépôt décrit l'entrée (golden entry, concept entry) avec des éléments discrétionnaires (raffinage, choix de la zone décisionnelle de l'UT supérieure).
- **Décision** : setups GOLDEN et CONCEPT déterministes (STRATEGY_SPEC §10) ; stop prioritaire si stop et cible dans la même bougie ; sur la bougie de déclenchement, seul le stop compte.
- **Incident** : sans la seconde règle, le backtest « gagnait » aussi sur des bougies mélangées (biais d'ordre intra-bougie). Corrigé avant toute conclusion.
- **Résultat** : pas d'espérance positive après coûts ; taux de réussite au niveau du modèle nul (`CALIBRATION.md` §4).
- **Conséquence** : les setups sont des repères de lecture, désactivables (`enable_setups`), et ne doivent pas piloter un robot sans validation supplémentaire.
- **Statut** : acté.

## D-19 Portage MetaTrader 5 : même modèle, même ordre, validation par parité

- **Contexte** : MT5 est la plateforme cible ; MetaEditor n'est pas disponible dans l'environnement de développement (pas de compilation possible ici).
- **Options** : (a) réécrire l'indicateur à partir de l'ancien EA ; (b) porter le cœur Python module par module ; (c) appeler Python depuis MT5.
- **Décision** : (b). Un fichier `.mqh` par module Python, mêmes noms d'événements, mêmes références, même ordre de traitement ; affichage séparé (`Draw.mqh`) ; tampons `DRAW_NONE` pour `iCustom` ; export du journal et des bougies, comparé au moteur Python par `tools/mt5_parity.py`. L'option (c) aurait fait dépendre l'indicateur d'une installation Python et d'une communication inter-processus ; l'option (a) aurait repris les écarts de l'EA (STRATEGY_SPEC §12).
- **Conséquence** : la parité doit être vérifiée sur un terminal (procédure dans `mt5/README.md`) ; tant que ce n'est pas fait, le code MQL5 est **non compilé et non validé**.
- **Statut** : implémenté ; validation sur terminal en attente.

## D-20 Heure du serveur : règle explicite, vérifiée par script

- **Contexte** : les heures de tir et la fenêtre mensuelle exigent l'heure UTC des bougies ; MQL5 ne donne que l'heure serveur et le décalage courant. Les courtiers suivent des conventions différentes (UTC+2/+3 selon l'heure d'été européenne ou américaine, ou décalage fixe). La donnée de calibrage s'est révélée suivre l'heure d'été européenne alors que l'hypothèse initiale était « New York + 7 ».
- **Décision** : paramètre `InpServerTz` explicite (EET/UE, New York + 7, fixe) et script `SMV_ServerTimeCheck.mq5` qui détermine la convention à partir de la dernière bougie du vendredi pendant les semaines désynchronisées.
- **Statut** : acté.

## D-21 Intégration de l'audit indépendant

- **Contexte** : audit externe (GPT, 1 octobre 2026), 28 constats, 42 cas de test adverses, corrections Python et MQL5.
- **Décision** : corrections intégrées sans modification après reproduction des échecs et relecture (commit séparé) ; études recalculées sur les données réelles ; erreurs reconnues (indépendance de N, rotation annoncée, ton des conclusions de calibrage). Changement de définition accepté : le fail est le premier pivot étiqueté LH/HL selon R-ST-03 (F05).
- **Conséquences** : 103 tests ; conclusions de fond inchangées ; statut des réponses Q-01 à Q-16 ramené à des choix de formalisation.
- **Statut** : acté. Ouverts : exemples annotés du formateur, validation MT5 native, validation statistique hors échantillon.
