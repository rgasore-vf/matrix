# ARCHITECTURE de l'indicateur SMV

Version 0.1, octobre 2026.

## 1. Objectifs d'architecture

1. **Séparer le calcul de l'affichage.** Le moteur produit des événements ; l'affichage les lit. Le même moteur doit servir à un indicateur, un scanner, un backtest ou une stratégie automatique.
2. **Rendre le look-ahead et le repaint impossibles par construction**, et le vérifier automatiquement.
3. **Rendre chaque règle traçable** vers la spécification (identifiants R-xx) et chaque paramètre vers sa provenance (dépôt, recherche, proposition).
4. **Rester portable** : la logique du cœur doit pouvoir être réécrite en MQL5 ou en Pine Script sans changer de modèle de données.

## 2. Alternatives envisagées

| Option | Avantages | Inconvénients | Verdict |
|---|---|---|---|
| A. Indicateur MQL5 directement (comme l'ancien EA) | exécution native sur MT5 | pas de tests automatisés dans cet environnement (pas de MetaEditor) ; logique et dessin mélangés dans l'ancien code ; réutilisation difficile pour un backtest externe | rejetée pour la v0.1 |
| B. Pine Script (TradingView) | diffusion facile | modèle d'exécution par bougie avec `request.security` source classique de repaint ; tests unitaires quasi impossibles ; pas de réutilisation hors TradingView | rejetée comme référence |
| C. Bibliothèque vectorisée (pandas) | calcul rapide sur l'historique | les opérations vectorisées utilisent facilement des données futures (`shift(-n)`, voir RESEARCH §2.3) ; difficile à porter en MQL5 | rejetée |
| **D. Cœur événementiel en Python pur, bougie par bougie, puis adaptateurs** | même code en historique et en temps réel ; invariance par préfixe testable ; aucune dépendance ; structure directement transposable en MQL5 (une classe par module, une méthode `update(i)`) | plus lent qu'un calcul vectorisé (acceptable : environ 40 000 bougies/s sur série synthétique et 20 000 bougies/s sur EURUSD M15 réel, configuration par défaut, machine de test) | **retenue** |

La décision est consignée en DECISIONS.md (D-01, D-02).

## 3. Vue d'ensemble

```
            bougies CLOSES (une à une)
                      │
                      ▼
 ┌──────────────────────────── smv.Engine.on_bar(bar) ───────────────────────────┐
 │ 1. Context.append      : historique + ATR de Wilder (causal)                  │
 │ 2. objets antérieurs   : LiquidityBook.update, ZoneBook.update,               │
 │                          RangeTracker.update, SetupTracker.update             │
 │ 3. nouveautés de i     : PivotDetector → StructureTracker → ZoneBook          │
 │                          → LiquidityBook (pivots, EQ) → CandleScanner         │
 │                          → LiquidityBook (signatures) → RangeTracker          │
 │                          → SetupTracker                                       │
 │ 4. marqueurs           : ImbalanceScanner, SessionMarker, MonthWindow         │
 └───────────────────────────────────────┬───────────────────────────────────────┘
                                         │ list[Event] (confirm_index == i)
                                         ▼
                         journal d'événements (ajout seul)
                     ┌───────────────┼─────────────────┬──────────────────┐
                     ▼               ▼                 ▼                  ▼
              render.primitives   scanner         backtest           export JSON
              → render.svg        (à faire)       research/          tools/run_smv.py
                                                  study_setups.py
   portage MQL5 (mt5/) : même chaîne, journal exporté → tools/mt5_parity.py
```

### 3.1 Modules du cœur (`smv/`)

| Fichier | Rôle | Règles |
|---|---|---|
| `types.py` | `Bar`, `Event`, constantes `Kind` | §0.4 |
| `config.py` | paramètres immuables, validation, table de provenance | §14 |
| `context.py` | historique des bougies closes, ATR, plus haut / plus bas sur intervalle | §0.4 |
| `pivots.py` | pivots fractals, étiquettes HH/HL/LH/LL | R-ST-02, R-ST-03 |
| `structure.py` | automate de structure majeure, BOS, fail, inducement, prise du niveau protégé | R-ST-04 à R-ST-07, R-LQ-05 |
| `candles.py` | doji, bougie manipulatrice, signature de liquidité | R-CA-01 à R-CA-05 |
| `zones.py` | zones (BM/BQA), touches, rupture, breaker, order flow | R-OD-01 à R-OD-05 |
| `liquidity.py` | niveaux intact / clean / BOS, EQH/EQL, cibles | R-LQ-01 à R-LQ-03 |
| `ranges.py` | consolidation, prises externes, intention, sortie (expérimental) | R-CE-01, R-CE-02, R-GS-02 |
| `setups.py` | setups GOLDEN et CONCEPT : création, rejet, déclenchement, stop, cible, expiration | R-SE-01 à R-SE-02, R-GS-03, §9 |
| `timing.py` | heures de tir, fenêtre mensuelle, imbalance (définition externe) | R-OU-01, R-OU-02, §15 |
| `mtf.py` | agrégation d'UT, vue datée de l'UT haute, risque de BOS trap | R-MTF-01 à R-MTF-03 |
| `engine.py` | orchestration et contrôle `confirm_index == i` | §0.5 |
| `data.py` | lecture CSV, séries synthétiques, constructeurs de tests | — |

### 3.2 Couche d'affichage (`render/`)

- `primitives.py` convertit le journal en `Segment`, `Box`, `Marker`. Chaque primitive porte `visible_from`, ce qui permet une relecture bougie par bougie fidèle à ce qui était connu.
- `svg.py` dessine ces primitives (outil de vérification, pas un produit). Police déclarée : Lora, avec repli `serif` si elle n'est pas installée sur la machine de lecture.
- L'indicateur MT5 a sa propre couche d'affichage (`mt5/Include/SMV/Draw.mqh`), qui lit le journal du moteur MQL5. Aucune règle de stratégie ne doit être écrite dans une couche d'affichage.

## 4. Contrat temporel (anti-repaint, anti look-ahead)

1. **Entrée** : uniquement des bougies closes. L'appelant ne transmet jamais la bougie en formation. (En MQL5, sans série inversée : bougies d'indice `0` à `rates_total - 2` ; la bougie `rates_total - 1` est en formation.)
2. **Lecture** : aucune fonction du cœur ne lit un indice supérieur à la bougie courante. `Context` n'expose pas le futur.
3. **Datation** : chaque événement a `confirm_index` (vrai à la clôture de cette bougie) et `anchor_index <= confirm_index` (où il est dessiné). `Engine.on_bar` vérifie que tout événement émis a `confirm_index == i`.
4. **Journal en ajout seul** : un changement de statut est un nouvel événement (`LIQ_CLEAN`, `ZONE_BROKEN`, `RANGE_EXIT`...). Les libellés rétrospectifs (inducement, décompte Wyckoff) sont émis au moment où ils deviennent connus, jamais réécrits.
5. **Ordre déterministe** dans une bougie : statuts des objets antérieurs, puis nouveautés. Un objet créé à la clôture de `i` n'est mis à jour qu'à partir de `i + 1`.
6. **Multi-UT** : une bougie d'UT haute n'existe qu'une fois close ; `HtfView.at(t)` ne renvoie que l'état dont la clôture est `<= t`.
7. **Vérification** : `tests/test_no_lookahead.py` exécute le moteur sur des préfixes de séries aléatoires et exige que les événements soient exactement ceux du calcul complet ayant `confirm_index < k`, pour plusieurs configurations. Il vérifie aussi que le traitement en flux et le traitement en lot sont identiques, et que le retard des pivots vaut `pivot_right`.

Les retards qui en résultent sont **voulus** et visibles : un pivot apparaît `pivot_right` bougies après son extrême ; une zone n'existe qu'au BOS qui la valide ; un inducement n'est connu qu'au BOS qui le révèle ; une sortie de consolidation n'est validée qu'après `range_accept_bars` clôtures.

## 5. Modèle d'événement

```python
Event(kind, confirm_index, anchor_index, direction, price, ref, data)
```

- `kind` : une constante de `Kind`, avec la règle de spécification en commentaire.
- `direction` : `+1` haussier, `-1` baissier, `0` neutre.
- `price` : niveau principal (niveau cassé, bord proximal, niveau de liquidité...).
- `ref` : identifiant stable de l'objet (`PH:123`, `ZD:118:131`, `R:140`...), utilisé pour relier les événements (statuts, liens ODF, consolidation).
- `data` : détails (origine du BOS, bornes de zone, libellé candidat...).

`Event.key()` donne une identité comparable, utilisée par les tests.

## 6. Paramètres

`Config` est immuable et validé. `Config.describe()` renvoie, pour chaque paramètre documenté, sa valeur, sa provenance, la règle concernée et une note. Les défauts sont listés dans STRATEGY_SPEC §14.

## 7. Tests

| Fichier | Couvre |
|---|---|
| `test_pivots.py` | confirmation retardée, égalités, étiquettes |
| `test_structure.py` | série de référence calculée à la main ; lectures A et B ; mèche sans clôture ; clôture égale au niveau ; fail et consolidation ; prise du niveau protégé |
| `test_zones.py` | bornes de zone (corps/mèche, BM précédente, absence de BM) ; rupture et breaker ; épisodes de touche ; lien ODF |
| `test_liquidity.py` | intact / clean / BOS ; EQH et cas limite ; classificateurs de bougies ; signature comme cible |
| `test_ranges.py` | libellés par contexte ; épisodes de prise ; sortie par acceptation ; décompte infirmé |
| `test_timing.py` | heures d'hiver et d'été à Paris ; désynchronisation des heures d'été ; fenêtre mensuelle |
| `test_mtf.py` | agrégation, vue datée de l'UT haute, règle de BOS trap |
| `test_setups.py` | qualification GOLDEN / CONCEPT ; rejets ; déclenchement, cible, stop prioritaire ; pas de cible sur la bougie de déclenchement ; expirations ; cohérence du cycle de vie sur 4 000 bougies |
| `test_mt5_parity.py` | outil de parité MT5 : lecture du format, reconstruction de la configuration, détection d'une divergence |
| `test_no_lookahead.py` | invariance par préfixe (setups compris), flux = lot, retard des pivots |

Commande : `python -m pytest -q tests` depuis `smv_indicator/` (pytest est la seule dépendance, pour les tests).

## 8. Portage vers MetaTrader 5 (v0.2)

MetaTrader 5 est la plateforme cible (DECISIONS D-19). Le portage reprend le cœur Python module par module.

```
mt5/
├── Indicators/SMV/SMV_Indicator.mq5   entrées, OnCalculate (bougies closes), tampons, export
├── Include/SMV/
│   ├── Types.mqh       SmvBar, SmvEvent, CSmvLog (journal), constantes K_*      ← types.py
│   ├── Config.mqh      SmvConfig, défauts, validation, en-tête d'export          ← config.py
│   ├── Context.mqh     bougies closes, ATR de Wilder                             ← context.py
│   ├── Pivots.mqh      pivots fractals                                           ← pivots.py
│   ├── Structure.mqh   automate de structure majeure                             ← structure.py
│   ├── Zones.mqh       classificateurs de bougies, zones, ODF, breakers          ← candles.py, zones.py
│   ├── Liquidity.mqh   niveaux, EQH/EQL, cibles                                  ← liquidity.py
│   ├── Ranges.mqh      consolidation et décompte (expérimental)                  ← ranges.py
│   ├── Setups.mqh      GOLDEN, CONCEPT                                           ← setups.py
│   ├── Timing.mqh      fuseaux et heure d'été, sessions, fenêtre 26-9, FVG       ← timing.py
│   ├── Engine.mqh      orchestration, même ordre que engine.py
│   └── Draw.mqh        affichage (objets graphiques), sans règle de stratégie
└── Scripts/SMV/SMV_ServerTimeCheck.mq5  convention horaire du courtier
```

**Choix de portage.**
- Indices croissants dans le moteur ; l'indice moteur `k` correspond à l'indice graphique `g_start + k`.
- Les événements portent la même chaîne `kind`, les mêmes `confirm`, `anchor`, `dir`, `price`, `ref`, et une charge utile `data` sérialisée « clé=valeur » avec les mêmes clés que le dictionnaire Python. Les modules consommateurs lisent des champs typés (`i1`, `d1`, `s1`...) documentés dans `Types.mqh`.
- Recalcul complet quand `prev_calculated == 0`, quand la première bougie traitée a changé (historique tronqué à gauche) ou quand la dernière bougie traitée ne correspond plus (historique modifié). Sinon, seules les nouvelles bougies closes sont traitées ; l'affichage n'est mis à jour qu'à ce moment-là.
- UT supérieure : second moteur alimenté par `CopyRates` ; une bougie d'UT supérieure n'est conservée que terminée (`time + période <= TimeCurrent()`) et n'est transmise que si sa clôture nominale précède la clôture de la bougie courante.
- Heure : conversion serveur → UTC par règle explicite (`InpServerTz`), règles d'heure d'été UE et États-Unis codées (valables depuis 2007).

**Tampons** (`iCustom`, fenêtre de données ; valeur sur chaque bougie close, `EMPTY_VALUE` sur la bougie en formation) :

| Indice | Nom | Valeur |
|---|---|---|
| 0 | SMV_Trend | tendance majeure après la bougie (+1, -1, 0) |
| 1 | SMV_Protected | niveau protégé |
| 2 | SMV_SetupDir | sens d'un setup non rejeté créé sur la bougie, sinon 0 |
| 3 à 5 | SMV_SetupEntry, SMV_SetupStop, SMV_SetupTarget | entrée, stop, cible 1 de ce setup |
| 6 | SMV_HtfTrend | tendance de l'UT supérieure connue à la clôture de la bougie |
| 7 | SMV_BosTrap | sens d'un BOS de continuation à risque de BOS trap (R-MTF-03), sinon 0 |

**Validation.** Le code MQL5 n'a pas pu être compilé dans l'environnement de développement (pas de MetaEditor). La procédure de validation est décrite dans `mt5/README.md` : compilation, export du journal (`InpExport = true`), puis `python tools/mt5_parity.py <dossier>/<SYMBOLE>_<UT>`. L'outil rejoue les mêmes bougies dans le moteur Python et compare les deux journaux événement par événement. L'outil lui-même est testé (`tests/test_mt5_parity.py`).

**Performances attendues** (non mesurées sur terminal) : le moteur est en O(n) par bougie pour la plupart des modules ; deux parcours sont proportionnels au nombre d'objets actifs (niveaux de liquidité intacts, zones actives). `InpMaxBars` (20 000 par défaut) borne le recalcul complet et `InpDrawBars` (3 000) le nombre d'objets graphiques.

## 9. Ce qui reste à construire

1. Validation de parité sur un terminal MT5 (compilation, export, `tools/mt5_parity.py`) ; corriger toute divergence côté MQL5 ou côté Python.
2. Test hors échantillon du setup CONCEPT et filtre de contexte multi-UT défini avant de regarder les résultats (`CALIBRATION.md` §5).
3. Moteur multi-UT complet côté Python (plusieurs UT simultanées, BOS trap confirmé).
4. Scanner multi-instruments à partir du même moteur.
