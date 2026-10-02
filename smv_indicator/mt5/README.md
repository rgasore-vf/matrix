# SMV pour MetaTrader 5

Portage MQL5 du moteur `smv` (voir `../docs/ARCHITECTURE.md` §8). L'indicateur dessine la structure majeure, les zones d'offre et de demande, les breakers, les EQH/EQL, les consolidations et leur décompte, les setups, les heures de tir et la fenêtre du high/low du mois. Tout est calculé sur des **bougies closes** : rien n'est redessiné après coup.

> **État : non compilé, non validé sur terminal.** L'environnement de développement ne dispose pas de MetaEditor. Le code a été écrit pour être identique, événement par événement, au moteur Python testé, et un outil de comparaison est fourni. Suivre la procédure de validation ci-dessous avant tout usage réel.

## 1. Installation

1. Dans MetaTrader 5 : *Fichier > Ouvrir le dossier des données*.
2. Copier le contenu de `mt5/` dans `MQL5/` :
   - `mt5/Include/SMV/*.mqh` vers `MQL5/Include/SMV/`
   - `mt5/Indicators/SMV/SMV_Indicator.mq5` vers `MQL5/Indicators/SMV/`
   - `mt5/Scripts/SMV/SMV_ServerTimeCheck.mq5` vers `MQL5/Scripts/SMV/`
3. Ouvrir les deux fichiers `.mq5` dans MetaEditor et compiler (F7). Signaler toute erreur de compilation avec son message exact.

## 2. Régler l'heure du serveur (une fois par courtier)

Les heures de tir et la fenêtre mensuelle ont besoin de l'heure UTC des bougies. Exécuter le script `SMV_ServerTimeCheck` sur un graphique du symbole (onglet *Experts* du terminal pour le résultat). Il indique la convention probable :

- `SMV_SRV_EET_EU` : UTC+2 / UTC+3 avec l'heure d'été européenne (cas des données de calibrage) ;
- `SMV_SRV_NY7` : New York + 7 heures (clôture du vendredi à 00:00 serveur toute l'année) ;
- sinon, décalage fixe (`SMV_SRV_FIXED`, `InpServerFixedHours`).

Reporter la valeur dans l'entrée `InpServerTz` de l'indicateur. Une erreur d'une heure ne change pas la structure, les zones ni les setups ; elle décale seulement les marqueurs horaires.

## 3. Entrées principales

| Groupe | Entrée | Défaut | Référence |
|---|---|---|---|
| Moteur | `InpPivotLeft`, `InpPivotRight` | 2, 2 | CALIBRATION Q-16 |
| | `InpMajorMode` | A | Q-01 |
| | `InpBmBodyMin` | 0,7 | Q-02 |
| | `InpZoneProximal` | corps | Q-03 |
| | `InpZonesOn` | origines des BOS | Q-04 |
| | `InpEqTolAtr` | 0,1 | Q-07 |
| | `InpRangeAccept`, `InpTestMaxBars` | 3, 10 | Q-11 |
| | `InpSlMaxAtr` | 2,5 | Q-12 |
| | `InpEnableSetups` | oui | §4 de CALIBRATION : repères sans espérance démontrée |
| | `InpSessionMode` | mesurées | Q-10 |
| Ajustement (§7) | `InpGoldenSchemaOnly` | non | golden seulement dans le sens du schéma |
| | `InpFilterPD` | non | signal (tampons) seulement en discount à l'achat / premium à la vente de la jambe `InpHtf` ; l'étude utilise H4 |
| | `InpBeAtR` | 0 | break-even après N R ; testé, non retenu |
| Historique | `InpMaxBars` | 20 000 | bougies recalculées au chargement |
| | `InpHtf` | désactivée | UT supérieure pour le biais et le BOS trap |
| Affichage | couches, couleurs, police | | Lora si installée sous Windows, sinon substitution par le système |

Les couleurs par défaut reprennent la palette d'Anthropic relevée en octobre 2026 (RESEARCH §8.8) : vert #788C5D (haussier), orange #D97757 (baissier), bleu #6A9BCC (cibles), gris #B0AEA5 (neutre). Elles sont pensées pour un fond clair ; sur fond noir, éclaircir les teintes de zones.

## 4. Utilisation depuis un autre programme (`iCustom`)

```mql5
int h = iCustom(_Symbol, PERIOD_M15, "SMV\\SMV_Indicator");
double trend[1], dir[1], entry[1], stop[1], target[1];
// bougie close la plus récente = décalage 1 (le décalage 0 est la bougie en formation, vide)
CopyBuffer(h, 0, 1, 1, trend);
CopyBuffer(h, 2, 1, 1, dir);
CopyBuffer(h, 3, 1, 1, entry);
CopyBuffer(h, 4, 1, 1, stop);
CopyBuffer(h, 5, 1, 1, target);
```

Tampons : 0 tendance, 1 niveau protégé, 2 sens du setup créé sur la bougie (0 sinon), 3 entrée, 4 stop, 5 cible 1, 6 tendance de l'UT supérieure, 7 BOS trap.

Les setups n'ont pas d'espérance positive mesurée (CALIBRATION §4). Un robot qui les exécuterait sans autre filtre ne serait pas fondé sur un avantage démontré.

## 5. Validation de parité avec le moteur Python

1. Mettre `InpExport = true` et charger l'indicateur sur un graphique (par exemple EURUSD M15). L'onglet *Experts* affiche le chemin des fichiers écrits : `MQL5/Files/SMV/<SYMBOLE>_<UT>_events.tsv` et `..._bars.tsv`.
2. Copier ces deux fichiers dans un dossier accessible depuis Python, puis :

```bash
cd smv_indicator
python tools/mt5_parity.py chemin/vers/EURUSD_M15 --write-reference
```

3. Résultat attendu : `PARITÉ : journaux identiques`. Sinon l'outil liste les premières divergences (indice de l'événement, champ, valeur Python, valeur MT5). Le fichier `..._python.tsv` permet un `diff` texte ligne à ligne avec l'export MT5.

Points sensibles à vérifier en priorité en cas d'écart : ordre des événements dans une bougie, arrondis (`NormalizeDouble` contre `round`, tolérés à l'arrondi près), conversion d'heure (sessions), fenêtre `InpMaxBars` (le moteur MT5 commence à la bougie `rates_total - 1 - InpMaxBars`, l'export contient exactement les bougies traitées).

## 6. Limites connues

- Les règles d'heure d'été codées sont celles de l'UE et des États-Unis depuis 2007.
- L'UT supérieure utilise les bougies du courtier (`CopyRates`), alors que le moteur Python agrège les bougies de l'UT de base ; la parité ne couvre pas l'UT supérieure.
- MN1 n'est pas accepté comme UT supérieure (durée variable).
- Le recalcul complet est déclenché par tout changement d'historique ; sur 20 000 bougies, il doit rester bref, mais n'a pas été mesuré sur terminal.

## 7. Backtest de la version ajustée

Configuration étudiée dans `docs/CALIBRATION.md` §7 : `InpGoldenSchemaOnly = true`, `InpFilterPD = true`, `InpHtf = PERIOD_H4`, M15. Les tampons 2 à 5 ne portent alors que les setups qui passent les deux filtres ; les setups dessinés sur le graphique ne sont pas filtrés par le premium/discount.

Différences attendues avec l'étude Python : les bougies H4 du courtier sont alignées sur l'heure serveur, alors que l'étude agrège des H4 alignées sur UTC ; les coûts et l'exécution sont ceux du testeur. Pour une validation honnête, utiliser de préférence la période **postérieure à mars 2022**, jamais utilisée dans l'étude, et fixer les réglages avant de lancer le test.

## 8. EA du coffre-fort : `Experts/ASYM/ASYM_Vault.mq5`

Il teste les candidats figés A, B et C de `docs/ASYM_RESEARCH.md` sans aucun réglage de stratégie. Les critères de verdict sont fixés d'avance (§9 du même document).

> La v1.00 a compilé et tourné chez l'utilisateur (MetaTester build 6231), mais provoquait une violation d'accès au 13/05/2025 dans le moteur SMV complet ; la v1.10 n'en garde que l'ATR, les pivots et la structure. La v1.10 n'a pas encore été compilée sur terminal.

**Installation.**
- Copier `Experts/ASYM/ASYM_Vault.mq5` vers `MQL5/Experts/ASYM/`.
- Copier `Include/SMV/*.mqh` vers `MQL5/Include/SMV/`. L'EA utilise l'ATR de Wilder et la structure du moteur SMV.

**Réglages du testeur (identiques pour tous les tests).**

| Réglage | Valeur |
|---|---|
| Expert | `ASYM\ASYM_Vault` |
| Symbole, période | le symbole testé ; graphique **H4** pour A et B, **D1** pour C (une période de graphique supérieure à celle de la stratégie est refusée, surtout en mode « prix d'ouverture ») |
| Dates | du **01/01/2021** à aujourd'hui. Avant `InpTradeFrom` = 01/03/2022, l'EA ne fait que chauffer l'ATR et la structure. |
| Modélisation | **Chaque tick basé sur des ticks réels** (écarts réels). À défaut, « 1 minute OHLC ». Le shadow ne dépend pas de ce choix ; l'exécution réelle, si. |
| Dépôt | 10 000 USD, risque 1 %. Avec 500 $, le lot minimal fausse la taille sur l'or ; les R du journal n'en dépendent pas. |
| Compte | **hedging** (positions simultanées, comme dans la recherche). En netting, l'EA ignore en réel les signaux qui se chevauchent ; le shadow les garde. |
| Agents | **locaux uniquement** : les journaux sont écrits dans le dossier commun de la machine, pas sur le réseau MQL5 Cloud. |

**Douze instruments en une fois.** Graphique EURUSD, onglet *Paramètres* :
- `InpSymbolIdx` de 0 à 11, pas de 1 ;
- optimisation « Algorithme complet », sans forward.

`InpSymbolSuffix` ajoute le suffixe du courtier (par exemple `.m`). Faire une passe pour `InpStrategy = B`, puis une pour `C`. A est inclus dans le shadow de B (colonne `r_2`).

**Journaux** : `…/MetaQuotes/Terminal/Common/Files/ASYM/` (*Fichier > Ouvrir le dossier des données*, remonter d'un niveau, puis `Common/Files`).

| Fichier | Contenu |
|---|---|
| `*_shadow.csv` | un signal par ligne : R pour TP 1 à 4 selon les règles de la recherche, MFE, MAE, temps du stop, coût de recherche et écart au signal en R |
| `*_trades.csv` | exécution réelle : prix prévu et prix obtenu, glissement en R, écart, raison de sortie (sl, tp, timeout), R prix, R monétaire après commission et swap, MFE, MAE |
| `*_signals.csv` | contexte de chaque signal et action prise (ouvert, ignoré, erreur) |
| `*_bars.csv` | bougies transmises au moteur (contrôle de parité avec Python) |
| `*_log.csv` | paramètres, caractéristiques du symbole et du compte, avertissements, résumé final |

**Retour.** Envoyer tout le dossier `ASYM` compressé, avec si possible le rapport HTML du testeur. Analyse :

```bash
python research/asym/vault_report.py dossier_ASYM resultats.json
python research/asym/vault_replay.py parity B dossier_ASYM/B_..._EURUSD_..._bars.csv dossier_ASYM/B_..._EURUSD_..._shadow.csv
```
