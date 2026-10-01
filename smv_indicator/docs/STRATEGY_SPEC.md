# STRATEGY_SPEC : reconstruction formelle de la stratégie « Smart Money Vision » (UltraFX)

Version 0.2, octobre 2026. Document de référence pour l'implémentation de l'indicateur `smv_indicator`.

**Nouveautés de la v0.2** : réponses aux questions Q-01 à Q-16 (section 13 et `CALIBRATION.md`) ; couche Setups implémentée (section 10) ; heures de tir mesurées (R-OU-01) ; portage MetaTrader 5, plateforme cible retenue par le responsable de la stratégie (`ARCHITECTURE.md` §8).

## 0. Objet, périmètre et conventions

### 0.1 Objet

Ce document reconstruit la stratégie enseignée dans le dossier `Strategie/` du dépôt (10 modules, transcriptions `.txt` et captures `img/`), puis la traduit en règles déterministes. Il doit permettre à un développeur de coder la stratégie sans relire les sources. Il ne valide pas la stratégie : aucune règle de ce document n'a de performance démontrée (voir `RESEARCH.md`, section 6).

### 0.2 Corpus lu

| Élément | Contenu | Statut de lecture |
|---|---|---|
| `Strategie/Module 1` à `Module 10`, 41 fichiers `.txt` | transcriptions automatiques (TurboScribe) de vidéos théorie/pratique | lus intégralement |
| `Strategie/Module N/img`, 328 fichiers | diapositives et captures annotées | 23 planches contact sur 29 examinées ; toutes les diapositives théoriques vues ; 8 planches de captures de graphiques non examinées image par image |
| `Strategie/*.md` (analyses pédagogiques, plan) | documents produits par un tiers (assistant IA) à partir des modules | lus pour comparaison, **non utilisés comme source de vérité** |
| `RG_SMV_V2.mq5`, `Include/*.mqh`, `AUDIT_COMPLET_V2.md` | ancien EA MetaTrader 5 | lus ; utilisés uniquement pour identifier des écarts (section 12) |

Lacunes du corpus, constatées et non comblables depuis le dépôt :

- `Module 8/1- ACCUMULATION & DISTRIBUTION THEORIE` est une copie octet pour octet de `Module 7/1`. La vidéo théorique du « décompte neutre avancé » manque ; seules ses diapositives (images) et la pratique existent.
- Le Module 11 (études de cas), l'« e-book / ultra-book » de définitions, les « calls VIP » et l'« école suivie » sont cités mais absents.
- Plusieurs outils sont cités sans jamais être enseignés : « Fibonacci SMC », « complexe pullback », « market shift », « structure de rotation complexe ».
- `Module 5/img` contient 5 captures d'une console Google Cloud (facturation) sans rapport avec la stratégie, qui exposent des noms d'organisation et des identifiants de compte. Elles devraient être retirées du dépôt.

### 0.3 Étiquettes de statut

Chaque règle porte un statut, qui qualifie la **source** de la règle dans le dépôt :

| Étiquette | Signification |
|---|---|
| **EXPLICITE** | énoncée clairement dans une transcription ou une diapositive |
| **IMPLICITE** | non énoncée, mais nécessaire à la cohérence des énoncés explicites |
| **DÉDUITE** | tirée d'un ou plusieurs exemples sur graphique, sans énoncé général |
| **AMBIGUË** | énoncée, mais avec plusieurs lectures possibles, ou sans critère opérationnel |
| **CONTRADICTOIRE** | deux passages du dépôt donnent des règles incompatibles |
| **INCOMPLÈTE** | annoncée ou utilisée, mais jamais définie dans le dépôt |

Chaque choix de formalisation porte une **provenance** :

- **[DÉPÔT]** : le choix reprend le dépôt sans ajout.
- **[RECHERCHE]** : le choix reprend une définition externe documentée dans `RESEARCH.md`.
- **[PROPOSITION]** : le choix est le mien ; il est paramétrable et doit être validé par le responsable de la stratégie.

Références : `M3/2` signifie « Module 3, fichier 2 ». `M2/img` désigne les diapositives du module.

### 0.4 Notations

- Une bougie `i` d'une unité de temps (UT) donnée a `open[i]`, `high[i]`, `low[i]`, `close[i]`, `t_open[i]`, `t_close[i]`. Les indices croissent avec le temps (0 = plus ancienne bougie), contrairement à MQL5.
- `body[i] = |close[i] - open[i]|`, `range[i] = high[i] - low[i]`, `body_ratio[i] = body[i] / range[i]` (0 si `range[i] = 0`).
- Bougie haussière : `close > open` ; baissière : `close < open` ; neutre : `close = open`.
- `ATR[i]` : Average True Range de Wilder sur `atr_len` bougies **closes**, calculé sur l'UT considérée [RECHERCHE].
- « Moment de vérité » (`confirm_index`) : indice de la bougie **close** à la clôture de laquelle la règle devient vraie. Aucune règle ne devient vraie sur une bougie non close.
- « Ancrage » (`anchor_index`) : indice de la bougie où l'objet est dessiné (par exemple l'extrême d'un swing). On a toujours `anchor_index <= confirm_index`.

### 0.5 Principe général d'implémentation (contrat anti-repaint)

[PROPOSITION, fondée sur RESEARCH.md §5] Le moteur est un automate qui consomme les bougies **closes** une par une et émet un **journal d'événements en ajout seul**. Un événement n'est jamais modifié ni supprimé. Un changement de statut (par exemple un niveau intact qui devient « clean ») est un nouvel événement. Conséquence vérifiable : les événements produits sur les `k` premières bougies sont exactement ceux du calcul complet dont `confirm_index < k` (test d'invariance par préfixe, `tests/test_no_lookahead.py`).

---

## 1. Vue d'ensemble de la stratégie reconstruite

La stratégie est une lecture discrétionnaire du prix, sans indicateur technique classique (« RSI, MACD... à la poubelle », M1/1 ; « notre structure, c'est notre seul indicateur », M1/10). Elle s'organise en couches qui se conditionnent :

1. **Structure** (M1) : tendance haussière/baissière/consolidation par la suite des sommets et creux ; structure majeure et mineure ; cassures (BOS) de trois types ; fractalité entre UT.
2. **Bougies** (M2) : la bougie manipulatrice (BM) et la bougie qui prend l'argent (BQA) délimitent les zones ; signatures algorithmiques (doji signature, signature de liquidité).
3. **Offre et demande** (M3) : zones (OB = POI = offre/demande), order flow (ODF), breaker block.
4. **Cause et effet** (M4) : consolidation = cause ; détection du fail, de l'intention, des prises de liquidité ; cibles sur les intacts.
5. **Liquidité** (M5) : intacts, EQH/EQL, trendlines, signatures de liquidité, inducement ; « attendre les prises de liquidité avant d'entrer ».
6. **Outils de contexte** (M6) : heures de tir, high/low du mois.
7. **Golden setup** (M7, M8) : décompte Wyckoff (accumulation/distribution type 1 et 2), décompte neutre, décompte en rotation ; entrée en phase C sur le test de la prise de liquidité.
8. **Concept entry** (M9) : entrées hors golden setup (suivi du flot après inducement, ODF).
9. **Raffinage** (M10) : choix du point d'entrée (PE) et du stop (SL) par confluence multi-UT.

La logique de décision du formateur se résume ainsi (synthèse, M3/1, M4/3, M5/1, M7/1, M9/1) : identifier le biais directionnel par la structure de l'UT supérieure ; attendre que le prix atteigne une zone d'offre ou de demande « décisionnelle » ; y observer une cause (consolidation) ou une suite de structure ; attendre le changement de caractère, la ou les prises de liquidité, l'intention (BOS) ; entrer sur le test d'une zone créée par ce processus ; viser les liquidités opposées (intacts, EQH/EQL, signatures, inducements).

---

## 2. Couche Structure (Module 1)

### R-ST-01 Types de structure

- **Statut** : EXPLICITE (M1/1, M1/2, M1/img).
- **Énoncé du dépôt** : tendance haussière = suite de HH (high high) et HL (high low) ; baissière = LH et LL ; consolidation = highs et lows évoluant « dans une fourchette », « la direction n'a pas encore été donnée ».
- **Formalisation** : la tendance est l'état de l'automate de structure majeure (R-ST-04). La consolidation est traitée par la couche Cause (R-CE-01), car le dépôt n'en donne pas de critère de structure autonome. [DÉPÔT + PROPOSITION]

### R-ST-02 Points de swing (sommets et creux)

- **Statut** : AMBIGUË. Le dépôt ne dit jamais quel extrême local compte comme « un high » ou « un low ». Il utilise la dynamique « impulsion, retracement » (« une impulsion va toujours demander un retracement », M1/1) et choisit visuellement.
- **Formalisation** [RECHERCHE + PROPOSITION] : pivot fractal de Williams généralisé.
  - Pivot haut en `p` si `high[p] > high[p-j]` pour `j = 1..n_left` et `high[p] >= high[p+j]` pour `j = 1..n_right`. Pivot bas symétrique avec `low`.
  - Les égalités : à gauche strictes, à droite larges, pour qu'un double sommet strictement égal produise un seul pivot (le premier). [PROPOSITION]
  - **Moment de vérité** : `confirm_index = p + n_right`. Le pivot est inconnu avant. Il ne disparaît jamais ensuite.
  - Paramètres : `pivot_left`, `pivot_right` (défaut 2 et 2, valeur de Williams [RECHERCHE]).
- **Limite assumée** : un pivot fractal n'est pas le « swing significatif » du formateur. La significativité est portée par la structure majeure (R-ST-04), qui ne dépend pas de `n`.

### R-ST-03 Étiquetage HH / HL / LH / LL

- **Statut** : EXPLICITE pour la règle de comparaison ; EXPLICITE que la comparaison se fait sur l'extrême, mèche comprise : « même si la bougie ne clôture pas en dessous, le niveau est passé en dessous, du coup low-low » (M9/2) ; « on vient au-dessus, on donne un nouveau high-high, mais pour l'instant on n'a pas encore BOS la structure » (M1/10).
- **Formalisation** [DÉPÔT] : chaque pivot haut est comparé au pivot haut précédent : `HH` si plus haut, `LH` si plus bas, `EH` (égal) si égal. Idem pour les bas (`HL`, `LL`, `EL`).
- **Moment de vérité** : celui du pivot.

### R-ST-04 Structure majeure et mineure

- **Statut** : CONTRADICTOIRE entre deux familles de passages.
- **Lecture A** (M1/5, M1/6, M3/2, M9/2, diapositive M1 « Structure majeure & mineure ») : en tendance baissière, le LL majeur est le plus bas atteint ; le LH majeur est le **plus haut du retracement qui précède la clôture sous le LL majeur**. Il n'est majeur qu'une fois cette cassure produite : « il faut venir passer en dessous de ce niveau majeur pour le valider comme low high majeur » (M3/2). Tous les swings internes au retracement sont mineurs. Chaque cassure du LL (y compris un BOS de continuation) crée « une nouvelle structure majeure » (M1/5).
- **Lecture B** (M5/5, M5/6, M8/2, M9/1) : seul le LH d'où part le **BOS de changement de tendance** est majeur ; le LH d'où part une impulsion qui ne fait qu'un BOS de continuation est un « LH mineur », un **inducement** : « ce n'est pas lui qui est venu nous donner le BOS changement de tendance... c'est notre LH mineur, puisque c'est un LH d'inducement » (M5/5).
- **Pourquoi c'est une vraie contradiction** : sur une même tendance baissière à trois jambes, la lecture A place le niveau protégé (celui dont la cassure change la tendance) sur le dernier LH ; la lecture B le laisse sur le LH initial, beaucoup plus haut. Les deux lectures donnent des changements de tendance à des moments différents.
- **Interprétation possible** [PROPOSITION, non retenue comme vérité] : la lecture B décrit peut-être la structure d'une UT supérieure vue depuis l'UT inférieure (fractalité). Le dépôt ne le dit pas.
- **Formalisation** : les deux lectures sont implémentées, sélectionnées par le paramètre `major_mode ∈ {"A", "B"}`. Défaut `"A"` parce qu'elle est appuyée par davantage de passages et par la diapositive de référence. Ce défaut est une décision de lecture, pas une vérité (DECISIONS.md, D-07).

Automate de structure majeure (lecture A), décrit en tendance baissière ; la tendance haussière est symétrique :

- État : `trend = DOWN`, `prot_high` (LH majeur, niveau protégé), `leg_low` (plus bas atteint depuis l'origine de la jambe), `ref_low` (dernier LL **fixé**, niveau à casser pour un BOS de continuation).
- Fixation du LL [PROPOSITION] : `ref_low` prend la valeur du pivot bas confirmé qui est l'extrême de la jambe en cours (premier pivot bas confirmé égal au plus bas de la jambe). Sans retracement (pas de pivot), aucun BOS de continuation n'est possible : une baisse continue n'est qu'une impulsion.
- **BOS de continuation baissier** à la bougie `i` si `close[i] < ref_low - eps`. Alors : le nouveau LH majeur `prot_high` est le **plus haut entre la bougie de `ref_low` et `i`** (retracement) ; une nouvelle jambe commence.
- **BOS de changement de tendance (haussier)** à la bougie `i` si `close[i] > prot_high + eps`. Alors : `trend = UP` ; le HL majeur protégé devient le **plus bas entre la bougie de `prot_high` et `i`** (lecture A, symétrique) ; la jambe haussière commence.
- Lecture B : identique, sauf qu'au BOS de continuation `prot_high` **n'est pas déplacé** ; le LH du retracement est émis comme inducement (R-LQ-05).
- `eps` : marge de clôture, défaut 0 [DÉPÔT : « le corps de la bougie se clôture au-dessus », M1/10]. L'ancien EA utilisait 0,05 % du prix, choix non présent dans le dépôt.
- Initialisation [PROPOSITION] : `trend = UNDEFINED` jusqu'à ce qu'une première clôture dépasse le pivot haut confirmé le plus récent (donne `UP`) ou casse le pivot bas confirmé le plus récent (donne `DOWN`).

### R-ST-05 BOS : validation par clôture

- **Statut** : EXPLICITE. « On voit très clairement que le corps de la bougie structure au-dessus. Du coup, on a bien eu un BOS » ; « on prend la liquidité, la bougie, le corps ne se clôture pas au-dessus » (M1/10).
- **Formalisation** [DÉPÔT] : un BOS exige `close` au-delà du niveau. Un dépassement en mèche sans clôture est une **prise de liquidité** (R-LQ-01), pas un BOS.
- **Moment de vérité** : clôture de la bougie de cassure. Jamais sur la bougie en cours.

### R-ST-06 Trois types de BOS

| Type | Statut | Définition du dépôt | Formalisation |
|---|---|---|---|
| BOS classique / changement de tendance | EXPLICITE (M1/9, M1/10, diapositive) | cassure du HL (en hausse) qui « montre un arrêt de la tendance » ; la diapositive montre la cassure de deux HL successifs | clôture au-delà du niveau protégé `prot_low`/`prot_high` de R-ST-04 [DÉPÔT + PROPOSITION pour le choix du niveau] |
| BOS de continuation | EXPLICITE | clôture au-delà du dernier HH (en hausse) | clôture au-delà de `ref_high`/`ref_low` de R-ST-04 |
| BOS trap (fake BOS) | EXPLICITE dans l'intention, AMBIGUË dans le critère | BOS de continuation sur l'UT basse qui ne casse pas la structure majeure de l'UT supérieure et se produit dans une zone d'offre/demande de l'UT supérieure ; « il prend les liquidités mais ne casse pas la structure majeure » | voir R-MTF-03 ; non décidable sur une seule UT |

**Correspondance de vocabulaire** [RECHERCHE] : le « BOS de changement de tendance » de SMV correspond au **CHoCH** (change of character) du vocabulaire SMC/ICT courant ; le « changement de caractère » de SMV désigne autre chose (R-ST-07). L'indicateur emploie les termes du dépôt, avec l'équivalent SMC en info-bulle.

### R-ST-07 Changement de caractère SMV et « fail »

- **Statut** : EXPLICITE. « Le fail, c'est ce qui va construire notre liquidité et qui va nous montrer le premier signe du changement de caractère... high-high, high-low, high-high, high-low, low-high, et c'est ça votre fail » (M4/3). Symétrique en baisse : un HL dans une structure baissière (M1/2, M4/4).
- **Formalisation** [DÉPÔT + PROPOSITION pour le support] : en tendance majeure `UP`, le premier pivot haut confirmé étiqueté `LH` (R-ST-03) depuis le dernier BOS haussier émet `FAIL_BEARISH` ; son niveau `high[p]` devient un niveau de liquidité (R-LQ-01). Symétrique en `DOWN` avec un pivot bas `HL`.
- **Moment de vérité** : confirmation du pivot (`p + n_right`).
- **Remarque** : ce n'est pas le CHoCH du SMC courant, qui exige une cassure. Ici aucune cassure n'est requise.

### R-ST-08 Règle 80/20 (Pareto)

- **Statut** : EXPLICITE (M1/1, M1/3, M1/7). « 80 % continuité, 20 % correction » ; trader « les 80 % » = dans le sens de la tendance de l'UT considérée ; « les 20 % » = le retracement. Les 80/20 dépendent de l'UT (fractalité).
- **Ce que ce n'est pas** : ni une probabilité mesurée, ni une zone de prix. L'ancien EA l'a transformée en filtre « prix dans les 20 % extrêmes d'un range », ce qui n'est pas dans le dépôt.
- **Formalisation** [DÉPÔT] : étiquette informative de chaque jambe : `IMPULSE` si elle va dans le sens de `trend` de l'UT, `RETRACEMENT` sinon.

### R-ST-09 Structure de rotation

- **Statut** : AMBIGUË. Retracement « structuré » (structure interne opposée, « le drapeau » des retail) dont les impulsions « perdent en intensité » ; souvent avec une « zone de neutralité » ; deux familles (rotation de retracement, rotation « dans la tendance » de fin de tendance) ; une « rotation complexe » annoncée, jamais enseignée (M1/11, M1/12, M8/3, M8/4).
- **Pourquoi non formalisable en l'état** : « perte d'intensité » n'a pas de critère. Les exemples chiffrés du dépôt ne sont pas monotones : 73, 71, 55, 58 pips (M1/12) ; 320, 430, 208 pips (M8/4).
- **Proposition (non implémentée en v0.1)** : au moins 3 jambes d'impulsion consécutives de même sens dans le retracement, dont l'amplitude de la dernière est inférieure à `rot_decay` fois celle de la première. À valider sur des exemples annotés par le formateur avant tout codage.

### R-ST-10 Fractalité

- **Statut** : EXPLICITE (M1/7, M1/8, M4/7). Les mêmes règles s'appliquent à toutes les UT ; un retracement de l'UT haute est une tendance de l'UT basse ; quand l'UT basse atteint une zone décisionnelle de l'UT haute, on cesse de suivre l'UT basse.
- **Formalisation** : chaque UT a son propre moteur, avec les mêmes paramètres exprimés en unités relatives (ATR de l'UT). Couplage entre UT : R-MTF.

---

## 3. Couche Bougies (Module 2)

### R-CA-01 Bougie manipulatrice (BM)

- **Statut** : AMBIGUË pour le critère, EXPLICITE pour le rôle. « Une bougie qui est pleine ou presque pleine et qui viendra manipuler les retail traders à acheter leur résistance et à vendre leur support » (M2/1). En cas de doute entre deux bougies, « la bougie la plus pleine » (M3/2).
- **Ce qui est observable dans les diapositives** (M2/img) : pour une zone de demande, la BM est une grande bougie **baissière** ; pour une zone d'offre, une grande bougie **haussière**. La BM a donc la couleur **opposée** au départ qui suit.
- **Formalisation** [PROPOSITION] : la bougie `b` est candidate BM si `body_ratio[b] >= bm_body_min` (défaut 0,6) et si sa couleur est opposée au sens de la zone. Optionnel : `range[b] >= bm_range_atr * ATR[b-1]` (désactivé par défaut, car le dépôt ne mentionne aucune taille).
- Le dépôt ne donne aucun seuil. L'ancien EA utilisait 0,70 ; ce chiffre n'a pas de source.

### R-CA-02 Bougie qui prend l'argent (BQA)

- **Statut** : EXPLICITE. « La bougie qui a la mèche ou le corps le plus haut du sommet ou tout simplement du low » (M2/1) ; elle prend la liquidité des bougies et niveaux précédents.
- **Formalisation** [DÉPÔT] : la BQA d'une zone est la bougie qui porte l'extrême du swing qui ancre la zone (le pivot, ou l'extrême de jambe de R-ST-04). Une même bougie peut être BM et BQA (EXPLICITE, M2/2).

### R-CA-03 Ordre et adjacence BM / BQA

- **Statut** : DÉDUITE des diapositives (BM puis BQA adjacente, puis départ) et EXPLICITE pour le cas confondu.
- **Formalisation** [PROPOSITION] : on cherche la BM parmi `{bqa, bqa-1}` (dans cet ordre de préférence : d'abord la BQA elle-même si elle qualifie, sinon la bougie précédente). Paramètre `bm_search_back` (défaut 1). Si aucune ne qualifie, la zone est construite sur la BQA seule (R-OD-01, cas OB).

### R-CA-04 Doji signature

- **Statut** : AMBIGUË. Un doji « souvent placé juste avant des grandes impulsions, ou qui va être placé comme bougie qui prend l'argent » ; il sera « récupéré avec précision » (M2/3).
- **Formalisation** [RECHERCHE + PROPOSITION] : doji si `body_ratio <= doji_body_max` (défaut 0,1). Nison définit le doji par une ouverture « égale ou presque » à la clôture, sans pourcentage fixe [RECHERCHE]. « Doji signature » = doji qui est la BQA d'une zone validée, ou qui est l'une des `doji_window` (défaut 2) bougies précédant la bougie de BOS. L'ancien EA exigeait en plus « bougie suivante > 2 fois le range » : absent du dépôt.

### R-CA-05 Signature de liquidité

- **Statut** : EXPLICITE pour le sens, AMBIGUË pour la taille. Bougie à « grande mèche derrière son corps » ; ce n'est pas un rejet mais de la **liquidité en attente**, une **cible** (« potentiel target ») (M2/3, M2/img, M5/3). Diapositive : bougie haussière avec longue mèche haute = cible pour un acheteur ; bougie baissière avec longue mèche basse = cible pour un vendeur.
- **Formalisation** [DÉPÔT + PROPOSITION pour le seuil] : bougie haussière avec `(high - close) / range >= liqsig_wick_min` (défaut 0,5) ; niveau cible `high`. Symétrique.
- **Écart avec l'ancien audit** : l'audit de l'EA y voyait une zone d'entrée « contre la mèche ». Le dépôt dit le contraire : c'est une cible.

---

## 4. Couche Offre et demande (Module 3)

### R-OD-01 Zone d'offre / de demande (= OB = POI)

- **Statut** : EXPLICITE pour la construction, IMPLICITE pour la sélection.
- **Énoncé** : « OB/POI = offre et demande » (diapositive M3). Offre = zone délimitée **sur un high** par la BM et/ou la BQA ; demande = sur un low (M3/1). Diapositive M2 : la zone de demande va du **haut du corps de la BM** au **bas de la mèche de la BQA** ; la zone d'offre du **bas du corps de la BM** au **haut de la mèche de la BQA**. Pratique M2/2 : « on a pris le corps de la bougie, la mèche de la bougie manipulatrice et la mèche de la BQA » (lecture ambiguë du bord proximal).
- **Formalisation** [DÉPÔT + PROPOSITION] :
  - Demande : `distal = low[bqa]` ; `proximal = max(open[bm], close[bm])` si `zone_proximal = "body"` (défaut, conforme à la diapositive) ou `high[bm]` si `"wick"`. Si aucune BM : `proximal = high[bqa]` (zone = bougie OB entière, conforme à la diapositive POI).
  - Offre : symétrique (`distal = high[bqa]`, `proximal = min(open[bm], close[bm])` ou `low[bm]`).
- **Sélection (quelles zones créer)** : le dépôt dit qu'il existe des zones « un peu partout » et qu'il faut trouver les « décisionnelles » (M3/1), sans critère. [PROPOSITION] Une zone n'est **créée et validée** qu'au moment d'un BOS (continuation ou changement), ancrée sur l'extrême de jambe d'où part l'impulsion cassante : « quand le marché nous aura donné les cassures, on pourra revenir dessus » (M2/2). Paramètre `zones_on = "bos_origin"` (défaut) ou `"all_pivots"` (zones non validées sur tout pivot).
- **Moment de vérité** : clôture de la bougie de BOS.

### R-OD-02 Zone décisionnelle

- **Statut** : INCOMPLÈTE. Utilisée partout (« offre décisionnelle », « demande décisionnelle ») ; jamais définie. Indices donnés : zone de l'UT supérieure à l'origine de la structure majeure, d'où part le BOS majeur, sur laquelle une cause se forme.
- **Formalisation** [PROPOSITION] : une zone est `decisional = True` si elle est ancrée sur l'origine d'un **BOS de changement de tendance** (et non d'un simple BOS de continuation). Ce critère est discutable et doit être validé.

### R-OD-03 Mitigation et invalidation

- **Statut** : EXPLICITE pour la mitigation multiple (« un POI peut être mitigé plusieurs fois », diapositive M3) ; INCOMPLÈTE pour l'invalidation.
- **Formalisation** [PROPOSITION] :
  - Touche : une touche est le **début d'un épisode de contact** : à la clôture de la bougie `i > confirm`, `low[i] <= proximal` (demande) alors que la bougie précédente ne touchait pas la zone. On émet `ZONE_TOUCH` avec un compteur ; la zone reste active. Les bougies suivantes qui restent dans la zone n'ajoutent pas de touche. (Une première version comptait chaque bougie ; sur données synthétiques cela donnait environ 20 « touches » par zone, ce qui ne correspond pas à « mitigé plusieurs fois ».)
  - Rupture : `close[i] < distal` (demande) ; la zone passe `BROKEN` et devient candidate breaker (R-OD-05).
- L'ancien EA invalidait la zone à la première traversée en clôture ; c'est la même règle de rupture, mais il n'acceptait pas les touches multiples comme une propriété.

### R-OD-04 Order flow (ODF)

- **Statut** : EXPLICITE. « Des mitigations sur mitigations de l'offre ou de la demande. La nouvelle bougie manipulatrice ou qui prend l'argent vient récupérer le précédent » (diapositive M3, M3/3). Diapositive : chaque nouvelle zone a son extrême posé sur la ligne prolongée du bord proximal de la zone précédente, « comme un escalier ».
- **Formalisation** [DÉPÔT + PROPOSITION pour « récupérer »] : une nouvelle zone de demande `Z` est **liée** à la zone de demande active précédente `Z'` si la BQA de `Z` a touché `Z'` : `low[bqa(Z)] <= proximal(Z')` et `close[bqa(Z)] >= distal(Z')`. Une suite d'au moins `odf_min_len` (défaut 2) zones liées forme un ODF. L'ODF « saute » quand sa dernière zone passe `BROKEN` (EXPLICITE que l'ODF finit par sauter, M3/4 ; le moment n'est pas défini).

### R-OD-05 Breaker block (zone de polarité inversée)

- **Statut** : EXPLICITE pour le principe, AMBIGUË pour « zéro réaction ». Une offre traversée sans réaction, suivie d'un BOS et d'un retracement, devient une demande potentielle ; on ne la trade **qu'après** avoir observé une réaction (M3/5, M3/6).
- **Formalisation** [PROPOSITION] : à la rupture d'une zone (R-OD-03), on émet `BREAKER_CANDIDATE` de sens opposé, mêmes bornes. Le critère « zéro réaction avant la rupture » n'est pas codé (non mesurable sans seuil) : il est signalé comme ambiguïté. `BREAKER_REACTION` est émis quand une bougie touche le breaker puis clôture du bon côté (pour un breaker de demande : `low[i] <= proximal` et `close[i] > proximal`).

---

## 5. Couche Cause et effet (Module 4)

### R-CE-01 Consolidation (cause)

- **Statut** : EXPLICITE dans l'intention, AMBIGUË dans le critère. Cause = consolidation = marché « latéral », « neutre », « en équilibre » entre une fourchette haute et basse ; deux types : accumulation (achat) et distribution (vente), variantes réaccumulation et redistribution (M4/1 à M4/4).
- **Formalisation** [PROPOSITION, fondée sur le décompte Wyckoff du dépôt et sur RESEARCH.md §3] : une consolidation est **ouverte** quand un fail (R-ST-07) est confirmé.
  - Après une tendance `DOWN` : borne basse = plus bas de la jambe (SC) ; borne haute = plus haut entre le SC et le pivot du fail (AR) ; le fail lui-même est le ST.
  - Après une tendance `UP` : borne haute = plus haut de la jambe (BC) ; borne basse = plus bas entre le BC et le fail (AR) ; le fail est le ST.
  - Moment de vérité : confirmation du pivot de fail. Cela respecte l'énoncé « SC, on peut le définir qu'après coup » (M7/1).
- La consolidation est **fermée** quand `range_accept_bars` clôtures consécutives (défaut 3) se font du même côté hors des bornes ; l'événement de sortie est confirmé à la dernière de ces clôtures et ancré à la première. Une excursion en clôture qui revient dans la fourchette avant ce nombre est une **prise de liquidité**, pas une sortie : un UT, un UTAD ou un spring peuvent clôturer brièvement hors du range (RESEARCH §3.1). Une nouvelle consolidation remplace la précédente. [PROPOSITION ; une première version fermait la consolidation à la première clôture hors bornes, ce qui la fermait presque toujours au moment de l'intention ou du MSO, avant toute prise de liquidité.]

### R-CE-02 Contenu de la cause : fail, intention, prise de liquidité

- **Statut** : EXPLICITE pour la liste ; CONTRADICTOIRE pour l'ordre.
- **Énoncé** : « dans la cause on doit détecter le fail qui construit notre liquidité et qui est un des premiers signes du changement de caractère ; on doit repérer l'intention de vente ainsi que la prise de liquidité » (diapositive M4).
- **Ordre observé** : fail → intention (BOS) → prise de liquidité du fail (M4/3, exemple 1) ; fail → prise de liquidité → intention (M4/4, M4/8 : « l'intention de vente n'était pas encore présente... on vient prendre sa liquidité, et votre intention est ici »). Le Module 7 confirme : « le MSO peut venir soit avant, soit après la prise de liquidité ».
- **Formalisation** [DÉPÔT] : les trois éléments sont des événements indépendants ; une cause est « complète » quand les trois ont été observés, **dans n'importe quel ordre**. L'audit de l'ancien EA imposait l'ordre FAIL → BOS → LIQ ; c'est une sur-spécification.

### R-CE-03 Effet et proportionnalité

- **Statut** : EXPLICITE et qualitatif : « plus la cause prend du temps, plus l'effet est grand » ; exemple : 28 jours de cause, 1150 pips d'effet (M4/4).
- **Formalisation** : l'indicateur mesure la durée (en bougies) et la hauteur de la cause, et l'amplitude de l'effet ; il ne prédit aucune cible. Wyckoff mesure classiquement la cause par un comptage en point-and-figure [RECHERCHE] ; le dépôt ne le fait pas.

---

## 6. Couche Liquidité (Modules 4 et 5)

### R-LQ-01 Liquidité de swing, intact, clean, BOS

- **Statut** : EXPLICITE. « Sur chaque high et chaque low, il y a de la liquidité » (M5/1). Intact = « high ou low non manipulé », dont la liquidité n'a pas été prise ; deux issues : BOS (clôture au-delà) ou nettoyé « clean buyer / clean seller » (prise en mèche puis retour) (M4/5, M4/6, diapositives).
- **Formalisation** [DÉPÔT] : chaque pivot confirmé crée un niveau `LIQ` à `INTACT`. Pour un niveau haut `L`, à la clôture de `i > confirm` :
  - si `close[i] > L` : `BOS` (statut final) ;
  - sinon si `high[i] > L` : `CLEAN` (statut final ; événement « prise de liquidité »).
- Lows : symétrique.
- **Écart** : l'ancien EA considérait un niveau intact tant qu'aucune clôture ne le dépassait ; un dépassement en mèche le laissait « intact ». Le dépôt dit l'inverse.

### R-LQ-02 Cibles (targets)

- **Statut** : EXPLICITE. Acheteur : viser les intact sellers (highs intacts) ; vendeur : les intact buyers. T1, T2, T3 = intacts successifs (M4/5, M4/6). Autres cibles explicites : signature de liquidité, EQH/EQL, inducement, extrême du PS (« le high du PS va toujours sauter », M7/2 ; « le low du PSY », M8/2).
- **Formalisation** [DÉPÔT] : pour une position longue d'entrée `E`, la liste ordonnée des cibles est l'ensemble des niveaux `INTACT` au-dessus de `E` (pivots hauts, signatures de liquidité, EQH), triés par distance croissante. Le choix entre T1, T2, T3 et la gestion des partiels sont **discrétionnaires** (« chaque personne va manager son trade différemment », M4/6) et restent hors indicateur.

### R-LQ-03 EQH / EQL

- **Statut** : EXPLICITE pour le concept, AMBIGUË pour la tolérance. « Low ou high au même niveau, ce qui crée une ligne de liquidité à venir chasser » (diapositive M5) ; = « double top / double bottom » retail.
- **Formalisation** [PROPOSITION] : deux pivots de même type `p1 < p2`, `p1` encore intact au moment de la confirmation de `p2`, avec `|niveau(p1) - niveau(p2)| <= eq_tol_atr * ATR[p2]` (défaut 0,1 ATR, valeur usuelle d'outils SMC publics [RECHERCHE, non vérifiée dans le code source faute d'accès]). Moment de vérité : confirmation de `p2`. Le niveau EQ est le plus extrême des deux.
- **Cas limite assumé** : si le second sommet dépasse le premier, même d'un tick, il a pris la liquidité du premier (R-LQ-01) ; le premier n'est plus intact et **il n'y a pas d'EQH**, quelle que soit la tolérance. Seul un second sommet égal ou légèrement inférieur forme un EQH. C'est une conséquence de la combinaison R-LQ-01 + R-LQ-03 ; si le formateur considère qu'un « double top » légèrement dépassé reste un EQH, il faut l'arbitrer (Q-07).
- L'ancien EA utilisait 0,25 ATR, sans source dans le dépôt.

### R-LQ-04 Trendline de liquidité

- **Statut** : AMBIGUË de façon assumée par le dépôt : « les trendlines, ce n'est pas des choses précises, c'est selon la vision du retail » (M5/6).
- **Décision** : **non implémentée** en v0.1. Toute implémentation imposerait un choix de points, de tolérance et de nombre de touches que le dépôt refuse de fixer. Proposition à valider : au moins 3 pivots de même type alignés à `tl_tol_atr * ATR` près sur une droite, la dernière touche étant la 3e.

### R-LQ-05 Inducement

- **Statut** : EXPLICITE pour la règle générale, CONTRADICTOIRE pour son application (dépend de R-ST-04), et EXPLICITEMENT rétrospectif.
- **Énoncé** : « tout LH ou tout HL dans une structure qui ne donne pas BOS, c'est de l'inducement » ; « toujours venir chercher les inducements avant de partir » (M5/5). Et : « vous ne pouvez pas savoir que c'est l'inducement [au moment de l'entrée]... maintenant vous savez que le niveau n'a pas cassé la structure majeure, du coup ce niveau devient de l'inducement » (M5/6).
- **Formalisation** [DÉPÔT + PROPOSITION] :
  - Lecture A : un pivot mineur (pivot du retracement, hors extrême de jambe) est émis `INDUCEMENT` au moment où un BOS est produit par une autre origine que lui (il n'a « pas donné le nouveau LL », M9/2) ; concrètement, au BOS de continuation, tous les pivots du retracement autres que le LH majeur retenu sont émis inducement.
  - Lecture B : au BOS de continuation, le LH du retracement (origine de la continuation) est émis `INDUCEMENT` ; le niveau protégé ne bouge pas.
  - Statut ultérieur par R-LQ-01 (`CLEAN` ou `BOS`). « Inducement pris » = son niveau est dépassé.
- **Moment de vérité** : la bougie du BOS qui révèle le statut. Le pivot existe avant ; son statut d'inducement n'existe qu'à partir de là. C'est l'exemple type de règle qui reprendrait le passé si on la calculait naïvement.

---

## 7. Couche Outils (Module 6)

### R-OU-01 Heures de tir

- **Statut** : EXPLICITE pour les heures, AMBIGUË pour la durée et l'usage.
- **Énoncé** (heures de **France**) : Europe 9 h (hiver) / 8 h (été) ; US 14 h / 13 h ; Asie (Sydney) 2 h / 1 h ; « 16 h, Chicago » ; « 4 h, Tokyo ». « C'est l'heure où le marché a le plus de probabilité de partir... on peut trader avant comme après » (M6/11).
- **Points faibles vérifiés** [RECHERCHE] : le décalage New York–Chicago est d'**une** heure, pas de deux ; Tokyo ouvre à 9 h JST, soit 1 h (hiver) heure de Paris, pas 4 h ; les passages à l'heure d'été américain et européen ne coïncident pas (environ 3 semaines en mars, 1 semaine en octobre), ce qui décale l'« heure de tir US » d'une heure à Paris pendant ces périodes. Hypothèse non vérifiée : l'« heure de tir Asie » de 2 h correspond au fixing de Tokyo (9 h 55 JST).
- **Formalisation** : marqueur d'heure (pas un filtre) ; fenêtre de durée `session_window_min` (défaut 60 min) [PROPOSITION]. L'ancien EA en avait fait des « kill zones » filtrantes, ce que le dépôt n'autorise pas.
- **v0.2, réponse à Q-10** [MESURE] : par défaut (`session_mode = "measured"`), les ancrages sont exprimés dans le fuseau de chaque place : 10:00 Tokyo, 08:00 Londres, 08:30 et 10:00 New York. À Paris, cela donne 9 h toute l'année pour l'Europe, et 14 h 30 et 16 h pour les États-Unis (13 h 30 et 15 h pendant la désynchronisation des heures d'été). Ces heures correspondent aux pics de volatilité mesurés (`CALIBRATION.md` Q-10). Les heures du dépôt restent disponibles (`session_mode = "repo"`).

### R-OU-02 High / low du mois

- **Statut** : EXPLICITE pour la fenêtre, AMBIGUË pour l'usage. « Créé entre le 26 du mois précédent et le 9 du mois courant, il indique le biais directionnel du mois », « souvent après une secousse » (nettoyage de liquidité ou annonce : NFP, FOMC) ; un high/low de mi-mois (14 au 18) donne « soit la continuation, soit le retracement » (M6/13, M6/14).
- **Problème** : la fenêtre contient toujours un plus haut **et** un plus bas ; le dépôt ne dit pas lequel est « le » high/low du mois. La règle de mi-mois n'est pas falsifiable (les deux issues sont annoncées).
- **Formalisation** [PROPOSITION] : à la clôture de la dernière bougie du 9 (heure de Paris), émettre les deux extrêmes de la fenêtre, horodatés. **Aucun biais n'est calculé.** Le choix du biais reste au trader.
- **v0.2, réponse à Q-09** [MESURE] : l'un des deux extrêmes du mois tombe dans la fenêtre dans 89,9 % des mois, contre 87,2 % sous un modèle nul (loi de l'arcsinus). L'observation du dépôt est vraie mais n'apporte presque aucune information.

### R-OU-03 Annonces économiques

- **Statut** : EXPLICITE : les annonces sont « un accélérateur », pas un frein ; pas de filtre d'annonces dans le dépôt.
- **Formalisation** : aucune. Pas de calendrier intégré en v0.1.

---

## 8. Couche Golden setup (Modules 7 et 8)

### R-GS-01 Décompte Wyckoff du dépôt

- **Statut** : EXPLICITE pour les noms et rôles, EXPLICITEMENT rétrospectif.
- **Accumulation** (M7/1, diapositives) : PS (tente d'arrêter la baisse, échoue) ; SC (arrête la baisse, borne basse) ; AR (élargit, borne haute) ; ST (teste le SC sans le prendre, renforce sa liquidité) ; UA (prend la liquidité de l'AR, avec ou sans BOS ; avec BOS = intention d'achat) ; STB (1re prise de liquidité du SC-ST) ; Spring (2e prise, « brutale », optionnelle) ; Test ; LPS. Type 1 = STB + Spring ; type 2 = STB seul.
- **Distribution** : PSY, BC, AR, ST, MSO (= mSOW, prend la liquidité de l'AR ; avec BOS = intention de vente), UT, UTAD (type 1), test, LPSY.
- « SC-ST et BC-ST vont toujours sauter » : affirmation non démontrée, à ne pas coder comme certitude.
- « On ne peut définir SC, BC... qu'après coup » ; « PSY, BC, AR, ST toujours dans l'ordre ; le MSO peut venir avant ou après la prise de liquidité ; il faut rester flexible » (M7/1, M7/2).
- **Écart avec Wyckoff** [RECHERCHE] : la méthode Wyckoff repose sur le volume (loi effort/résultat) ; le dépôt n'utilise jamais le volume. Le spot forex n'a d'ailleurs pas de volume centralisé.

### R-GS-02 Formalisation du décompte

[PROPOSITION, implémentée de façon minimale et marquée expérimentale] Sur une consolidation ouverte (R-CE-01) :

- `RANGE_SWEEP` : une prise est un **épisode** : la première bougie qui dépasse une borne (en mèche, ou en clôture suivie d'un retour, voir R-CE-01) ; les bougies suivantes qui dépassent encore la même borne appartiennent au même épisode. On numérote les épisodes par borne (1, 2...).
- Libellés **provisoires** : contexte accumulation (tendance précédente `DOWN`) : 1er dépassement bas = `STB`, 2e = `SPRING` ; dépassement haut = `UA`. Contexte distribution : 1er dépassement haut = `UT`, 2e = `UTAD` ; dépassement bas = `MSO`.
- Les libellés sont émis comme « candidats » et peuvent être **requalifiés** par un événement ultérieur (jamais par modification) quand la consolidation se ferme : sortie dans le sens attendu = décompte confirmé ; sens opposé = décompte infirmé (par exemple une « accumulation » qui casse vers le bas était une redistribution).
- Décompte neutre (M8, diapositives « Wyckoff neutre/avancé ») : on compte les deux bornes (« liquidités externes ») et l'on attend que l'une saute avant de réagir. C'est le comportement par défaut de cette formalisation, qui n'attribue pas de sens a priori.

### R-GS-03 Golden entry (sniper entry)

- **Statut** : EXPLICITE dans le principe : entrer en phase C, sur le **test** de la (dernière) prise de liquidité (M7/1). Conditions nécessaires listées : arrêt de tendance, latéralisation, fourchettes, tests créant la liquidité, niveau d'offre/demande décisionnel, prise de liquidité, intention, puis entrée sur le test (M7/1, M9/1).
- **AMBIGU** : la définition du « test » (contact de la zone créée par la prise de liquidité ? retour au niveau du STB ?) ; l'heuristique « si le prix consolide sur le STB, la probabilité de spring diminue » n'est pas quantifiée.
- **v0.2** : implémenté comme setup GOLDEN (section 10, R-SE-01). Le « test » est le retour sur la zone créée par le BOS d'intention dans les `test_max_bars = 10` bougies [PROPOSITION, `CALIBRATION.md` Q-11].

### R-GS-04 Décompte en rotation

- **Statut** : AMBIGUË (dépend de R-ST-09). Non implémenté.

---

## 9. Couche Concept entry (Module 9)

- **Statut** : EXPLICITE dans le principe : entrées hors golden setup ; « on procède toujours de la même façon, avec tous les concepts et les outils de la SMV » (diapositive M9). Schéma type (M9/1, diapositive) : après une cause et l'intention, le prix fait impulsion, retracement, continuation sans BOS majeur ; l'origine de la continuation devient inducement ; on attend la prise de cet inducement ; on entre sur la zone (BQA/doji signature) sous l'inducement, dans le sens de la tendance.
- **AMBIGU** : « s'il y a du market shift on travaille avec le market shift, s'il y a du breaker... » : la sélection de l'outil est opportuniste.
- **v0.2** : implémenté comme setup CONCEPT (section 10, R-SE-01b).

---

## 10. Couche Setups, entrée, stop, cibles (Modules 4, 7, 9, 10)

Implémentée en v0.2 (`smv/setups.py`, `mt5/Include/SMV/Setups.mqh`). **Avertissement** : le backtest de cette couche sur EURUSD et XAUUSD 2015-2021 ne montre aucune espérance positive après coûts, et ses taux de réussite ne dépassent pas le modèle nul (`CALIBRATION.md` §4). Les setups sont des repères de lecture, pas des signaux de trading.

### R-SE-01 Setup « golden » (GOLDEN) [PROPOSITION fondée sur R-GS-02, R-GS-03]

À la clôture de la bougie `i`, un setup GOLDEN de sens `d` est créé si :
1. un BOS de sens `d` (changement ou continuation) crée une zone (R-OD-01) à `i` ;
2. une consolidation (R-CE-01) est ouverte avant `i` et n'est pas fermée, ou se ferme à `i` même (la sortie et l'intention peuvent coïncider) ;
3. au moins une prise (RANGE_SWEEP) a eu lieu sur la borne **opposée au trade** (borne basse pour un achat : STB/spring ; borne haute pour une vente : UT/UTAD).

Le libellé est celui de la dernière prise (STB, SPRING, UT, UTAD, MSO, UA, éventuellement suffixé « +n »). Délai de déclenchement : `test_max_bars`.

### R-SE-01b Setup « concept » (CONCEPT) [PROPOSITION fondée sur §9 et R-LQ-05]

Tendance `d` ; un inducement révélé dans cette tendance a été pris (LIQ_CLEAN ou LIQ_BOS) ; le BOS de **continuation** suivant de sens `d` crée une zone à `i`. Délai de déclenchement : `setup_expiry_bars`. Un seul setup CONCEPT par prise d'inducement.

### R-SE-01c Exécution et cycle de vie (commun)

- Entrée : ordre limite au bord proximal ; stop : bord distal (mèche de la BQA) ; cible 1 : premier niveau de liquidité intact au-delà de l'entrée au moment de la création (R-LQ-02), cibles 2 et 3 journalisées.
- Rejet à la création (journalisé avec son motif, non suivi) : risque nul ; risque supérieur à `sl_max_atr` x ATR (`sl_too_wide`) ; aucune cible (`no_target`).
- SETUP_TRIGGERED quand une bougie touche l'entrée ; SETUP_CLOSED au stop (-1 R) ou à la cible 1 (+RR) ; SETUP_EXPIRED si l'entrée n'est pas touchée avant le délai, ou si la tendance change avant le déclenchement.
- Ordre intra-bougie inconnu, deux règles prudentes : si une bougie touche le stop et la cible, le stop est retenu ; sur la bougie de déclenchement, seul le stop est évalué.
- Hors périmètre (dépôt discrétionnaire) : partiels, break-even (préférence personnelle, R-SE-03), raffinage (R-SE-04), filtre de zone décisionnelle de l'UT supérieure.

### R-SE-02 Stop loss

- **Statut** : EXPLICITE pour les options, DÉDUITE pour le plafond. Options montrées : SL sur la mèche de la BQA ; « raffiné » sur le corps de la BQA ou du doji ; sur la « confluence des corps » BM/BQA ; sur un niveau déjà nettoyé (M4/6, M5/2, M10/1, M10/2).
- Plafond implicite : « 20 pips, ça ne rentre pas dans la stratégie » ; 9 à 10 pips « rentrent » ; 16 pips « toujours dans la stratégie » (M9/2, M10/1). Unité « pip » non normalisée entre EURUSD et l'or.
- **v0.2, réponse à Q-12** [DÉPÔT + MESURE] : plafond `sl_max_atr = 2,5` ATR(14) de l'UT d'entrée ; sur EURUSD M15, 2,5 ATR médian ≈ 16,5 pips, ce qui reproduit l'exemple du dépôt. Stop implémenté : mèche de la BQA (bord distal).

### R-SE-03 Break-even

- **Statut** : EXPLICITE comme **préférence personnelle**, pas comme règle : « moi, pour mettre un BE, il faut que ce niveau-là soit BOS » (M7/2, M9/2).

### R-SE-04 Raffinage

- **Statut** : EXPLICITE dans le principe (« raffiner n'est pas affiner », M10/1 ; préférer la bougie qui a la même valeur sur plusieurs UT, y compris non standard : 6, 7, 8, 9, 11, 12, 13 min) ; AMBIGU pour le nombre d'UT requis.
- [PROPOSITION v0.2] Calculer, pour une liste d'UT, les zones dont les bornes coïncident à `refine_tol_atr` près ; le score = nombre d'UT concordantes.

---

## 11. Couche Multi-UT (transversale)

### R-MTF-01 Agrégation causale

[PROPOSITION, fondée sur RESEARCH.md §5] Les bougies d'UT supérieure sont construites à partir des bougies de l'UT de base. Une bougie d'UT supérieure n'est publiée qu'à sa clôture. Un moteur d'UT basse ne voit, à la clôture de sa bougie `j`, que les événements de l'UT haute dont la bougie de confirmation a `t_close <= t_close[j]`.

### R-MTF-02 Biais de l'UT supérieure

- **Statut** : EXPLICITE (fractalité, M1/7). « On suit les 80 % de l'UT haute. »
- **Formalisation** : biais = `trend` de l'automate de l'UT haute à cet instant.

### R-MTF-03 BOS trap

- **Statut** : EXPLICITE dans l'intention, AMBIGUË pour le critère, rétrospectif.
- **Formalisation** [PROPOSITION] : un BOS de continuation de l'UT basse est `TRAP_RISK` s'il est contraire au biais de l'UT haute et si son niveau reste en deçà du niveau protégé de l'UT haute. Il devient `TRAP_CONFIRMED` si l'UT basse produit ensuite un BOS de changement de tendance dans le sens de l'UT haute avant que le niveau protégé de l'UT haute ne soit cassé.
- Implémentation : `smv.mtf.bos_trap_risk` (Python) ; dans l'indicateur MT5, moteur complet sur l'UT supérieure (`InpHtf`, bougies closes seulement) et tampon `SMV_BosTrap`. `TRAP_CONFIRMED` n'est pas implémenté.

---

## 12. Écarts entre le dépôt et l'ancien EA (`RG_SMV_V2.mq5`)

| Sujet | Dépôt | Ancien EA | Conséquence |
|---|---|---|---|
| BOS | clôture au-delà | boucle jusqu'à la bougie 0 non close, marge 0,05 % | BOS sur bougie non close (repaint) |
| 80/20 | étiquette impulsion/retracement | filtre « prix dans les 20 % du range » | règle inventée |
| Intact | niveau non dépassé, même en mèche | non dépassé en clôture | statuts faux après une mèche |
| Signature de liquidité | cible | zone d'entrée « contre la mèche » (audit) | sens inversé |
| BM | « pleine ou presque », sans seuil | corps >= 70 % | seuil inventé |
| EQH/EQL | même niveau, sans tolérance | 0,25 ATR | tolérance inventée |
| Ordre fail/BOS/liquidité | variable | imposé | sur-spécification |
| Heures de tir | indicatives | filtre « kill zones » | règle inventée |
| Modules 6 à 10 | enseignés | fichiers présents mais non inclus dans l'EA | audit déclaratif |

---

## 13. Registre des ambiguïtés et des questions au responsable de la stratégie

Le responsable de la stratégie a répondu à une question : la plateforme cible est **MetaTrader 5**. Les autres ont reçu une réponse fondée sur le dépôt, la recherche externe et des mesures sur données réelles ; le détail et les chiffres sont dans `CALIBRATION.md` §2. Ces réponses restent révisables par le responsable de la stratégie.

| ID | Question | Règles | Réponse v0.2 | Provenance |
|---|---|---|---|---|
| Q-01 | Lecture A ou B de la structure majeure ? | R-ST-04, R-LQ-05 | A ; B dégénérée sur données réelles (1 changement en 7 ans sur EURUSD H1) | DÉPÔT + RECHERCHE + MESURE |
| Q-02 | Critère de bougie « pleine » ? | R-CA-01 | corps >= 70 % de l'amplitude | RECHERCHE + MESURE |
| Q-03 | Bord proximal : corps ou mèche ? | R-OD-01 | corps (écart < 0,1 ATR) | DÉPÔT + MESURE |
| Q-04 | Zone sans BOS ? | R-OD-01 | non ; aucun avantage mesuré pour l'une ou l'autre option | DÉPÔT (MESURE neutre) |
| Q-05 | Zone « décisionnelle » ? | R-OD-02 | origine d'un BOS de changement, marqueur descriptif | PROPOSITION (MESURE neutre) |
| Q-06 | Invalidation d'une zone ? | R-OD-03 | clôture au-delà du bord distal | DÉPÔT |
| Q-07 | Tolérance EQH/EQL ? | R-LQ-03 | 0,1 ATR ; « les EQ sautent toujours » non vérifié | RECHERCHE + MESURE |
| Q-08 | « Perte d'intensité » d'une rotation ? | R-ST-09 | 3 jambes décroissantes, marqueur seulement (effet ≈ 2 points) | PROPOSITION + MESURE |
| Q-09 | Quel extrême est « le high/low du mois » ? | R-OU-02 | aucun biais ; effet expliqué par la loi de l'arcsinus | MESURE |
| Q-10 | Heures de tir ? | R-OU-01 | ancrages mesurés dans le fuseau de chaque place | MESURE + RECHERCHE |
| Q-11 | « Test » en phase C ? | R-GS-03 | retour sur la zone d'intention dans 10 bougies | PROPOSITION ; acceptation de sortie 3 bougies (RECHERCHE) |
| Q-12 | Plafond de SL ? | R-SE-02 | 2,5 ATR(14) de l'UT d'entrée | DÉPÔT + MESURE |
| Q-13 | Market shift, Fibonacci SMC, complexe pullback ? | M9/1 | non implémentés ; définitions externes documentées | RECHERCHE |
| Q-14 | Théorie du décompte neutre ? | R-GS-02 | reconstruite depuis les diapositives M8 | DÉPÔT |
| Q-15 | Taille minimale de la BM ? | R-CA-01 | aucune (pas d'effet mesuré de la BM) | MESURE |
| Q-16 | N du pivot selon l'UT ? | R-ST-02 | 2 / 2 sur toutes les UT (structure auto-similaire en ATR) | RECHERCHE + MESURE |

---

## 14. Paramètres et provenance

La table de référence est `CALIBRATION.md` §3 ; elle est reproduite dans `smv/config.py` (`PROVENANCE`) et dans les entrées de `SMV_Indicator.mq5`. Principales évolutions par rapport à la v0.1 : `bm_body_min` passe de 0,6 à 0,7 ; `session_mode = "measured"` ; nouveaux paramètres `test_max_bars = 10`, `sl_max_atr = 2,5`, `setup_expiry_bars = 100`, `eq_max_gap = 500`.

## 15. Ce qui n'est pas dans cette spécification

- Premium/discount (Fibonacci 50 %) : cité une seule fois (« Fibonacci SMC ») et jamais enseigné ; non implémenté.
- Fair value gap au sens ICT : le dépôt parle d'« imbalance » et de « price delivery » (bougies « non connectées ») comme **indice** d'un mouvement algorithmique, et déclare « on ne se focus pas dessus » (M10/1). Implémenté comme marqueur optionnel avec la définition ICT à 3 bougies [RECHERCHE], clairement étiquetée externe.
- MSS (market structure shift) : terme absent du dépôt.
- Vagues d'Elliott : citées comme confluence de perte d'intensité ; non implémentées.
