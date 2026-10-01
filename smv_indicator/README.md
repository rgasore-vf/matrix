# smv_indicator

Reconstruction formelle, calibrage et implémentation de référence de la stratégie « Smart Money Vision » (UltraFX) décrite dans `../Strategie/`, avec un portage pour MetaTrader 5.

**État : v0.2.**
- Couches Structure, Bougies, Offre/Demande, Liquidité, Outils, Multi-UT et Setups implémentées et testées en Python (61 tests).
- Couche Cause/Wyckoff expérimentale.
- Questions Q-01 à Q-16 tranchées par la recherche et par des mesures sur sept ans de données réelles (`docs/CALIBRATION.md`).
- Indicateur MetaTrader 5 écrit (`mt5/`) mais **non compilé ici** ; outil de parité fourni.
- **Aucune performance n'est revendiquée** : le backtest des setups ne montre pas d'espérance positive après coûts (`docs/CALIBRATION.md` §4).

## Lire dans cet ordre

1. `docs/STRATEGY_SPEC.md` : la stratégie reconstruite, règle par règle, avec le statut de chaque règle (explicite, ambiguë, contradictoire...) et la provenance de chaque choix. Section 13 : les questions et leurs réponses.
2. `docs/CALIBRATION.md` : réponses argumentées à Q-01 à Q-16, mesures, modèles nuls, backtest des setups, limites.
3. `docs/RESEARCH.md` : définitions externes (SMC/ICT, Wyckoff, sessions, MQL5), littérature, sources notées A à D.
4. `docs/ARCHITECTURE.md` : moteur événementiel, contrat anti-repaint, modules, tests, portage MT5.
5. `docs/DECISIONS.md` : décisions techniques et de lecture (D-01 à D-20).
6. `mt5/README.md` : installation, réglage de l'heure du serveur, `iCustom`, validation de parité.

## Utilisation (Python)

```bash
cd smv_indicator
python -m pytest -q tests                      # 61 tests (pytest requis)
python tools/run_smv.py --synthetic 1500 --seed 1 --out out/demo
python tools/run_smv.py --csv eurusd_m15.csv --tf 15 --out out/eurusd --from 500 --to 900
python tools/mt5_parity.py MQL5/Files/SMV/EURUSD_M15     # comparaison avec un export MT5
```

Le CSV attendu a un en-tête `time,open,high,low,close[,volume]`, avec l'heure d'ouverture des bougies (ISO 8601 ou epoch ; UTC par défaut).

```python
from smv import Engine, Config
from smv.data import load_csv

eng = Engine(Config())                           # défauts de docs/CALIBRATION.md §3
for bar in load_csv("eurusd_m15.csv", 15):      # bougies CLOSES uniquement
    for ev in eng.on_bar(bar):                    # événements devenus vrais à cette clôture
        print(ev.kind, ev.confirm_index, ev.anchor_index, ev.price, ev.data)
```

## Reproduire les mesures

Les scripts de `research/` utilisent le dépôt public `ejtraderLabs/historical-data`, cloné hors du projet (variable `SMV_DATA`, défaut `/home/user/mktdata/ej`). Résultats versionnés : `research/results_*.json`.

```bash
python research/study_basic.py    > research/results_basic.json
python research/study_outcomes.py > research/results_outcomes.json
python research/study_nulls.py    > research/results_nulls.json
python research/study_sessions.py > research/results_sessions.json
python research/study_setups.py EURUSD m15        # un instrument, une UT ; ajouter un entier pour une série mélangée
```

## Garanties

- Le moteur ne lit jamais une bougie future ; chaque événement est daté par la bougie close qui le rend vrai (`confirm_index`).
- Le journal est en ajout seul : rien n'est réécrit, les changements de statut sont de nouveaux événements.
- `tests/test_no_lookahead.py` vérifie ces propriétés sur plusieurs configurations, setups compris.

## Exemple

`docs/img/demo_chart.svg` : 140 bougies synthétiques (lecture A). La police déclarée est Lora ; elle ne s'affiche que si elle est installée sur la machine qui ouvre le fichier.
