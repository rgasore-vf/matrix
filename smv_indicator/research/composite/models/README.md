# Modèles figés de la recherche composite

Modèles LightGBM et seuils de couverture (fixés sur la validation 2018-2019) utilisés par
`research/composite/final_eval.py`. Ils permettent de rejouer exactement le test final sans ré-entraîner.

- `model_y_1.0_1.0.pkl` : toutes heures, cible ±1 ATR (candidats C1a, C1b)
- `liquid/model_*.pkl` : heures liquides 1 h-19 h Paris (C3, C4, C6)

Contenu de chaque fichier (pickle) : `model` (LGBMClassifier), `feats` (ordre des variables),
`thresholds` (seuil de score par couverture), `tree` (arbre lisible).
Versions : lightgbm 4.7.0, scikit-learn 1.9.1. Un pickle ne doit être ouvert que s'il vient d'une source de confiance.

Rejouer : `python research/composite/final_eval.py DOSSIER_MATRICES research/composite/models`
