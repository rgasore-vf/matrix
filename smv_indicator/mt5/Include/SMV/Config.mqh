//+------------------------------------------------------------------+
//| SMV/Config.mqh                                                   |
//| Paramètres du moteur (portage de smv/config.py).                 |
//| Les valeurs par défaut et leur provenance (DEPOT, RECHERCHE,     |
//| MESURE, PROPOSITION) sont documentées dans docs/CALIBRATION.md.  |
//+------------------------------------------------------------------+
#ifndef SMV_CONFIG_MQH
#define SMV_CONFIG_MQH

#include "Types.mqh"

struct SmvConfig
  {
   int    pivot_left;
   int    pivot_right;
   string major_mode;        // "A" ou "B" (R-ST-04, D-07)
   double bos_eps;
   int    atr_len;
   double bm_body_min;
   double bm_range_atr;      // <= 0 : désactivé (None en Python)
   int    bm_search_back;
   double doji_body_max;
   int    doji_window;
   double liqsig_wick_min;
   string zone_proximal;     // "body" ou "wick"
   string zones_on;          // "bos_origin" ou "all_pivots"
   int    odf_min_len;
   double eq_tol_atr;
   int    eq_max_gap;
   int    range_accept_bars;
   int    test_max_bars;
   double sl_max_atr;
   int    setup_expiry_bars;
   bool   golden_schema_only; // golden seulement dans le sens du schéma (CALIBRATION §7)
   double be_at_r;            // break-even après be_at_r R ; 0 = désactivé (None en Python)
   bool   enable_setups;
   bool   enable_imbalance;
   bool   enable_sessions;
   string session_mode;      // "measured" ou "repo"
   int    session_window_min;
  };

void SmvConfigDefaults(SmvConfig &c)
  {
   c.pivot_left         = 2;
   c.pivot_right        = 2;
   c.major_mode         = "A";
   c.bos_eps            = 0.0;
   c.atr_len            = 14;
   c.bm_body_min        = 0.7;
   c.bm_range_atr       = 0.0;
   c.bm_search_back     = 1;
   c.doji_body_max      = 0.1;
   c.doji_window        = 2;
   c.liqsig_wick_min    = 0.5;
   c.zone_proximal      = "body";
   c.zones_on           = "bos_origin";
   c.odf_min_len        = 2;
   c.eq_tol_atr         = 0.1;
   c.eq_max_gap         = 500;
   c.range_accept_bars  = 3;
   c.test_max_bars      = 10;
   c.sl_max_atr         = 2.5;
   c.setup_expiry_bars  = 100;
   c.golden_schema_only = false;
   c.be_at_r            = 0.0;
   c.enable_setups      = true;
   c.enable_imbalance   = false;
   c.enable_sessions    = false;
   c.session_mode       = "measured";
   c.session_window_min = 60;
  }

//--- contrôle des valeurs (mêmes règles que Config.__post_init__)
bool SmvConfigValid(const SmvConfig &c, string &err)
  {
   err = "";
   if(!MathIsValidNumber(c.bos_eps) || !MathIsValidNumber(c.bm_body_min) ||
      !MathIsValidNumber(c.bm_range_atr) || !MathIsValidNumber(c.doji_body_max) ||
      !MathIsValidNumber(c.liqsig_wick_min) || !MathIsValidNumber(c.eq_tol_atr) ||
      !MathIsValidNumber(c.sl_max_atr)) err = "paramètres numériques finis exigés";
   else if(c.bos_eps < 0 || c.eq_tol_atr < 0 || c.bm_range_atr < 0) err = "marges >= 0";
   else if(c.bm_search_back < 0 || c.doji_window < 0 || c.eq_max_gap < 0) err = "fenêtres >= 0";
   else if(c.odf_min_len < 1 || c.session_window_min < 1) err = "odf_min_len, session_window_min >= 1";
   else if(c.pivot_left < 1 || c.pivot_right < 1) err = "pivot_left et pivot_right doivent être >= 1";
   else if(c.major_mode != "A" && c.major_mode != "B") err = "major_mode doit valoir A ou B";
   else if(c.zone_proximal != "body" && c.zone_proximal != "wick") err = "zone_proximal: body ou wick";
   else if(c.zones_on != "bos_origin" && c.zones_on != "all_pivots") err = "zones_on: bos_origin ou all_pivots";
   else if(c.session_mode != "measured" && c.session_mode != "repo") err = "session_mode: measured ou repo";
   else if(c.bm_body_min < 0 || c.bm_body_min > 1 || c.doji_body_max < 0 || c.doji_body_max > 1 ||
           c.liqsig_wick_min < 0 || c.liqsig_wick_min > 1) err = "seuils de bougie dans [0, 1]";
   else if(c.range_accept_bars < 1 || c.test_max_bars < 1 || c.setup_expiry_bars < 1 || c.atr_len < 1)
      err = "range_accept_bars, test_max_bars, setup_expiry_bars, atr_len >= 1";
   else if(c.sl_max_atr <= 0) err = "sl_max_atr > 0";
   else if(c.be_at_r < 0 || !MathIsValidNumber(c.be_at_r)) err = "be_at_r >= 0 (0 = désactivé)";
   return err == "";
  }

//--- en-tête d'export, relu par tools/mt5_parity.py pour reconstruire Config(**kw)
string SmvConfigHeader(const SmvConfig &c)
  {
   string s = "";
   KvI(s, "pivot_left", c.pivot_left);
   KvI(s, "pivot_right", c.pivot_right);
   KvS(s, "major_mode", c.major_mode);
   KvD(s, "bos_eps", c.bos_eps);
   KvI(s, "atr_len", c.atr_len);
   KvD(s, "bm_body_min", c.bm_body_min);
   if(c.bm_range_atr > 0) KvD(s, "bm_range_atr", c.bm_range_atr); else KvNone(s, "bm_range_atr");
   KvI(s, "bm_search_back", c.bm_search_back);
   KvD(s, "doji_body_max", c.doji_body_max);
   KvI(s, "doji_window", c.doji_window);
   KvD(s, "liqsig_wick_min", c.liqsig_wick_min);
   KvS(s, "zone_proximal", c.zone_proximal);
   KvS(s, "zones_on", c.zones_on);
   KvI(s, "odf_min_len", c.odf_min_len);
   KvD(s, "eq_tol_atr", c.eq_tol_atr);
   KvI(s, "eq_max_gap", c.eq_max_gap);
   KvI(s, "range_accept_bars", c.range_accept_bars);
   KvI(s, "test_max_bars", c.test_max_bars);
   KvD(s, "sl_max_atr", c.sl_max_atr);
   KvI(s, "setup_expiry_bars", c.setup_expiry_bars);
   KvB(s, "golden_schema_only", c.golden_schema_only);
   if(c.be_at_r > 0) KvD(s, "be_at_r", c.be_at_r); else KvNone(s, "be_at_r");
   KvB(s, "enable_setups", c.enable_setups);
   KvB(s, "enable_imbalance", c.enable_imbalance);
   KvB(s, "enable_sessions", c.enable_sessions);
   KvS(s, "session_mode", c.session_mode);
   KvI(s, "session_window_min", c.session_window_min);
   return s;
  }

#endif
