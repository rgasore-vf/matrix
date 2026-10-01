# Rapport de tests et limites de validation

Date : 1 octobre 2026. Environnement : Linux, Python **3.12.14**, pytest **9.1.1**. Plugins pytest externes désactivés pour isoler la suite. Pas de MetaEditor, de terminal MT5 ni de Wine disponible. Aucun test Pine : pas de fichier Pine dans l’archive.

## Résultats exécutés

| Version et suite | Résultat | Preuve brute |
| --- | --- | --- |
| Archive reçue, 61 tests préexistants | **61 passent**, 2,26 s | `audit_evidence/baseline-tests.txt` |
| Archive reçue + les 42 nouveaux cas définitifs | **39 échouent, 64 passent**, 2,34 s | `audit_evidence/all-adversarial-original.txt` |
| Version corrigée, suite complète | **103 passent**, 2,60 s | `audit_evidence/regression-current.txt` |
| Première série de contre-exemples avant correction | 27 échecs | `audit_evidence/adversarial-before.txt` |
| Recherche, avant correction des scripts | 4 échecs | `audit_evidence/research-before.txt` |
| Heures répétées DST, avant leur correction | 2 échecs | `audit_evidence/dst-before.txt` |

Les 42 nouveaux cas proviennent de `tests/test_gpt_adversarial.py` et `tests/test_gpt_research.py`. Trois vérifient un comportement déjà correct de la version reçue : double pivot sur outside bar, première occurrence d’un plateau égal et sérialisation du payload. Les autres réfutent la version reçue ; plusieurs paramétrisations représentent la même cause. Le nombre d’échecs n’est pas le nombre de défauts distincts.

La comparaison avant/après utilise une seconde extraction du ZIP original avec **uniquement les nouveaux fichiers de tests copiés**, sans remplacer les modules de production. Les résultats attendus n’ont pas été ajustés pour faire passer la correction.

Commande pour rejouer la suite :

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests
```

## Oracles indépendants

| Scénario / test | Résultat déterminé avant correction | Niveau de test |
| --- | --- | --- |
| BOS + protected sweep, hausse/baisse | Les deux faits sur bar 11, avec l’ancien protégé 10 ; miroir à 30 | OHLC → Engine → événements |
| Premier LH/HL après BOS | High 20 puis high 18 en 13 : FAIL ancré 13, confirmé 14 ; miroir HL | OHLC → Engine → événements |
| EQ et âge maximal | Ancres 1 et 9 ne sont pas dans un écart maximal 3 | OHLC → Engine → événements |
| Range en sortie haute avec wick basse | Sweep bas dès close 1, sweep haut à récupération 2 | Module de range, état initial explicite |
| Retour d’excursion avec wick opposée | Sweep récupéré et nouveau sweep opposé à la même clôture | Module de range, état initial explicite |
| Sweeps via moteur complet, hausse/baisse | Prelude crée réellement FAIL/range ; sweep opposé en 13, récupéré en 14 | OHLC → toutes les couches |
| Bar 15 min vers période 7 min | Refus : high non disponible à minute 7 | Agrégation / disponibilité |
| Heure sans début ou milieu | Pas de bougie HTF complète ; prochaine heure entière admise | Agrégation / gaps |
| NaN/inf, doublon, chevauchement | Refus avant modification de `bars` et `atr` | Préconditions du contexte |
| Neuf configurations hors domaine | ValueError à construction | Préconditions de configuration |
| Payload partagé et listes imbriquées | Copie indépendante, append et affectation interdits | Contrat du journal |
| Position ouverte, entrée 10/stop 9/open 7 | R = −3, prix de référence 7 | Unité de simulation, calcul arithmétique |
| IDM → bear → bull → prise ancienne | Aucun contexte IDM pris utilisable | Journal manuel de contexte |
| Render en 5 avec prise en 10 | Niveau intact jusqu’à 5, pas statut futur | Projection du journal |
| Nouvelle range en 4 | Ancienne range terminée en 4, remplacée | Projection du journal |
| Export événement à prix NaN | Comparateur signale une divergence | Outil de parité, pas moteur MT5 |
| Fenêtre Paris chevauchée par D1 UTC | High hors fenêtre exclu ; high observé 2 et couverture partielle | OHLC → Engine → marqueur |
| HTF au fold NY de novembre | État close 06:00 UTC invisible à 05:00 UTC | Conversion d’instants / vue HTF |
| Session au fold Paris d’octobre | 02:00 +02 puis fin 02:00 +01, une heure réelle | OHLC → Engine → session |
| Fenêtre entière / heure manquante | Complete seulement dans le premier cas | OHLC → marqueur, continuité |
| Outside bar centrale | Pivot haut et bas ancrés 1, confirmés 2 | OHLC → Engine ; comportement conservé |
| Plateau 3/3/3 | Unique pivot haut au premier 3 | OHLC → Engine ; comportement conservé |
| EQ connu en 5, prise en 6, horizon 3 | Échec de prise dans `[1,3]`, succès dans `[6,8]` | Journal manuel, statistiques |
| High 50 le 27 février | Fin de mois incluse ; high de fenêtre ne tient pas | Bougies quotidiennes, statistiques |
| Mélange de quatre bougies avec gaps | TR triés `[2,12,22,27]` conservés et volume conservé | Modèle nul, calcul indépendant |
| CSV high sous le close | Refus, pas réparation silencieuse | I/O de recherche |

Le préambule des cas de structure est `[10,11,12,11,10,11,12.5,13,12,11.5,12]`, open = close précédent, sans wick. Il fournit un protégé 10 et une référence 13. Les ajouts du cas fail sont explicitement décrits dans le fichier de test, pas tirés d’un second algorithme. Pour les cas symétriques, la réflexion de prix est `(o,h,l,c) → (40−o,40−l,40−h,40−c)`.

Les tests unitaires de range et de contexte IDM isolent une précondition. Ils ne prouvent pas la reconnaissance d’une accumulation depuis une formation. Les deux nouveaux cas de sweeps via le moteur entier complètent les unités de range avec un état réellement construit par le pipeline. Le journal manuel de recherche sert à contrôler la causalité du calcul statistique sans le confondre avec la justesse de détection de pivots.

## Audit des tests préexistants

Les tests de pivots, structure, zones, liquidité et range contiennent plusieurs valeurs attendues explicites et utiles. Ils passent encore après correction. Les tests d’invariance par préfixe couvrent trois seeds, quatre configurations et quatre coupures ; ils sont un garde-fou temporel réel. Ils ne prouvent pas que toutes les séries, tous les alignements HTF ou tous les paramètres respectent le contrat. Une branche jamais exercée peut rester incorrecte.

La comparaison streaming=batch est moins indépendante puisque `Engine.run` appelle `on_bar`. Les tests de parité exportent un journal **Python** dans un format MT5 puis le relisent : ils contrôlent format, paramètres et détection de divergences, sans exécuter une ligne de MQL5. Le commentaire original le reconnaît ; le rapport ne transforme pas ces trois tests en validation native.

La suite reçue manquait notamment les non-diviseurs de période, HTF troué, fold DST, première LH après reset, deux bornes prises pendant une excursion, héritage IDM après retournements, mutation profonde du journal, stop gappé, projection à une date passée et études statistiques causales. Les nouvelles assertions ciblent ces trous sans recopier l’implémentation comme oracle.

## Autres vérifications exécutées

- `python -m compileall -q smv render research tools tests` : succès. C’est une vérification syntaxique Python, pas une preuve de stratégie.
- CLI avec 1 500 bougies synthétiques seed 1, sessions et FVG : **3 417 événements**, export JSON et SVG réussi. XML des SVG original et généré valide ; rendus inspectés avec Inkscape. Les libellés restent denses et la version du titre préexistant est v0.1.
- Script de setups sur 5 000 bougies synthétiques seed 6 : 21 créés, 9 déclenchés/clos, 10 expirés sans trigger et 2 expirés sur tendance. Les comptes de clôture, expiration et censure s’équilibrent. Aucune performance sur ces données synthétiques n’est utilisée pour recalibrer la stratégie.
- Mesure de temps et mémoire sur 5 000 / 10 000 / 20 000 bougies : données dans `audit_evidence/benchmark.json`. Une exécution par taille, pas un test de charge MT5.
- Contrôle de délimiteurs des sources `.mqh/.mq5` : équilibrés. Les classes et leurs champs ont été relus pour les modifications. Ce contrôle ne vérifie ni le typage MQL5, ni les API natives, ni le rendu.

## Vérifications MT5 à exécuter

Un script natif à résultats attendus manuels est livré :
`mt5/Scripts/SMV/SMV_GptAuditCheck.mq5`.
Il traite de fausses bougies closes UTC directement dans le moteur MQL5, dans les deux sens, et contrôle BOS+sweep, premier fail, double borne de range, gap de position ouverte et frontière mensuelle. Il n’envoie aucun ordre et ne dessine pas d’objets. **Il n’a pas été compilé ni exécuté ici.** Un succès doit montrer zéro FAIL dans le journal ; cela ne remplace pas les essais d’adaptateur et de parité suivants.

| ID | Essai natif | Critère d’acceptation |
| --- | --- | --- |
| N01 | Copier les Include/Indicators/Scripts dans MQL5, compiler l’indicateur, le script d’audit et le script horaire avec MetaEditor | Zéro erreur ; examiner chaque warning ; exécuter l’audit natif et garder le journal sans FAIL |
| N02 | M15/H1 et H1/H4, bar haut en formation, arrivée d’un nouveau bar, historique HTF initialement absent | Aucun état de bar zéro ; chargement initié/repris ; dernière close HTF ≤ close LTF ; erreurs non ignorées |
| N03 | DST Europe et États-Unis, désynchronisation, week-end, serveurs EET/NY7/fixe | Comparer conversions, sessions, durées et alignements à des bougies UTC attestées ; ne pas supposer le fuseau du broker |
| N04 | Même historique fixé, ajout de bougies, rechargement ; puis cap positif et chargement d’histoire plus ancienne | Journal identique sur le préfixe réellement identique ; documenter divergence lorsqu’un autre préfixe est fourni ; défaut MaxBars=0 |
| N05 | Deux instances sur le même graphique, retrait/reset de l’une, init invalide de l’autre | Objets de chaque instance conservés indépendamment ; aucun nettoyage au préfixe général |
| N06 | Petit DrawBars, nombreuses bougies et objets, toutes couches puis couches désactivées | Objets anciens purgés, propriétaires réservés, objets ouverts désenregistrés ; noms ≤63 ; mémoire et latence mesurées |
| N07 | InpMaxBars négatif, DrawBars=0, warmup négatif, MN1, faible historique, changements d’UT/symbole | Refus explicite des paramètres invalides ; pas d’indice hors tableau ; réinitialisation correcte |
| N08 | Export natif `InpExport` et comparaison Python sur les mêmes OHLC et configuration | `python tools/mt5_parity.py <préfixe>` sans divergence ; conserver bars/events/config/version terminal |

Utiliser des dossiers d’export différents pour des instances à configurations différentes. Le nom d’export courant n’identifie pas la configuration dans le chemin et peut être écrasé si deux instances partagent le dossier.

N08 valide le moteur **de base** exporté. Le biais/trap HTF et la couche graphique nécessitent N02 à N06 séparément : l’export existant ne contient pas leurs séries et buffers complets. Aucune comparaison de messages Python produits par Python ne remplit N08.

## Ce qui n’est pas établi

Les tests ne certifient pas une fidélité à la formation absente, la définition discrétionnaire du swing, la zone décisionnelle HTF, la séquence complète GOLDEN, les interprétations A/B, le zéro-réaction d’un breaker ni une rentabilité. Ils ne reproduisent pas sept ans de marché. Les données brutes, leur version et leurs transformations sont absentes ; les chiffres JSON restent inchangés et suspendus pour la version corrigée.

L’anti-repainting vérifié concerne l’API recevant des bougies closes sur les cas exécutés. Une correction de l’historique par un fournisseur, un autre début d’historique ou un autre alignement de bougies constitue une autre entrée. Le moteur ne garantit pas que des entrées différentes donnent le même journal. Le prochain critère fort de fidélité reste un jeu de décisions du formateur, annoté avec les informations effectivement disponibles à chaque clôture.
