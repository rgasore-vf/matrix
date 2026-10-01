//+------------------------------------------------------------------+
//| SMV/Setups.mqh                                                   |
//| R-SE-01 à R-SE-03, R-GS-03, §9 : golden entry et concept entry   |
//| (portage de smv/setups.py).                                      |
//|                                                                  |
//| SETUP -> SETUP_TRIGGERED -> SETUP_CLOSED (stop ou cible 1)       |
//|       ou SETUP_EXPIRED (délai, retournement de tendance).        |
//| Entrée : bord proximal (limite) ; stop : bord distal ; cible :   |
//| première liquidité intacte au-delà de l'entrée.                  |
//| Ordre intra-bougie inconnu : stop prioritaire si stop et cible   |
//| sur la même bougie ; sur la bougie de déclenchement, seul le     |
//| stop est évalué.                                                 |
//|                                                                  |
//| AVERTISSEMENT (docs/CALIBRATION.md §7) : sur EURUSD et XAUUSD    |
//| 2015-2021, ces setups n'ont pas d'espérance positive mesurée     |
//| après coûts. Ce sont des repères de lecture, pas des signaux.    |
//+------------------------------------------------------------------+
#ifndef SMV_SETUPS_MQH
#define SMV_SETUPS_MQH

#include "Liquidity.mqh"
#include "Ranges.mqh"

struct SmvSetup
  {
   string sid;
   string kind;        // GOLDEN ou CONCEPT
   int    dir;
   double entry;
   double stop;
   double t1;
   int    created;
   int    deadline;
   string zone;
   string label;
   int    triggered;   // -1 : non déclenché
   double mfe_r;
  };

class CSmvSetups
  {
public:
   SmvSetup          act[];
   int               nact;
   string            idm_ref[];
   int               idm_dir[];
   int               nidm;
   int               idm_taken_dir;
   string            sw_rid[2];   // dernière prise par côté : [0] = H, [1] = L
   int               sw_at[2];

                     CSmvSetups(void) { Reset(); }
   void              Reset(void)
     {
      nact = 0; ArrayResize(act, 0, 64);
      nidm = 0; ArrayResize(idm_ref, 0, 256); ArrayResize(idm_dir, 0, 256);
      idm_taken_dir = 0;
      sw_rid[0] = ""; sw_rid[1] = ""; sw_at[0] = -1; sw_at[1] = -1;
     }

   //--- suivi des setups créés avant i
   void              Update(const int i, const CSmvContext &ctx, CSmvLog &log)
     {
      SmvBar bar = ctx.bars[i];
      int m = 0;
      for(int a = 0; a < nact; a++)
        {
         bool keep = true;
         if(act[a].created < i)
           {
            int d = act[a].dir;
            double risk = MathAbs(act[a].entry - act[a].stop);
            bool skip_rest = false;
            if(act[a].triggered < 0)
              {
               bool touched = d == SMV_BULL ? bar.low <= act[a].entry : bar.high >= act[a].entry;
               if(!touched)
                 {
                  if(i >= act[a].deadline)
                    {
                     string x = ""; KvS(x, "reason", "not_triggered");
                     Ev(K_SETUP_EXPIRED, i, act[a], x, log);
                     keep = false;
                    }
                  skip_rest = true;
                 }
               else
                 {
                  act[a].triggered = i;
                  Ev(K_SETUP_TRIGGERED, i, act[a], "", log);
                 }
              }
            if(!skip_rest)
              {
               bool stop_hit = d == SMV_BULL ? bar.low <= act[a].stop : bar.high >= act[a].stop;
               if(stop_hit)
                 {
                  bool gap = act[a].triggered < i && (d == SMV_BULL ? bar.open < act[a].stop : bar.open > act[a].stop);
                  double fill = gap ? bar.open : act[a].stop;
                  Close(i, act[a], d * (fill - act[a].entry) / risk, gap ? "stop_gap" : "stop", fill, log);
                  keep = false;
                 }
               else if(act[a].triggered != i)
                 {
                  double fav = d == SMV_BULL ? bar.high - act[a].entry : act[a].entry - bar.low;
                  act[a].mfe_r = MathMax(act[a].mfe_r, fav / risk);
                  bool hit = d == SMV_BULL ? bar.high >= act[a].t1 : bar.low <= act[a].t1;
                  if(hit)
                    { Close(i, act[a], MathAbs(act[a].t1 - act[a].entry) / risk, "target1", act[a].t1, log); keep = false; }
                 }
              }
           }
         if(keep) { if(m != a) act[m] = act[a]; m++; }
        }
      nact = m;
      ArrayResize(act, nact, 64);
     }

   //--- création à partir des événements de la bougie i (journal [from, to))
   void              OnEvents(const int i, const int from, const int to, const SmvConfig &cfg,
                              const CSmvContext &ctx, const int trend, const CSmvLiquidity &liq,
                              const CSmvRanges &rng, CSmvLog &log)
     {
      for(int e = from; e < to; e++)
        {
         string kind = log.ev[e].kind;
         if(kind == K_RANGE_SWEEP)
           {
            int sd = log.ev[e].s2 == "H" ? 0 : 1;
            sw_rid[sd] = log.ev[e].s1; sw_at[sd] = i;
           }
         else if(kind == K_INDUCEMENT)
            IdmSet(log.ev[e].s1, log.ev[e].i1);
         else if(kind == K_LIQ_CLEAN || kind == K_LIQ_BOS)
           {
            int d = IdmPop(log.ev[e].s1);
            if(d != 0 && d == trend) idm_taken_dir = d;
           }
         else if(kind == K_BOS_CHANGE || kind == K_TREND_INIT)
           {
            idm_taken_dir = 0;
            nidm = 0;
            ArrayResize(idm_ref, 0, 256); ArrayResize(idm_dir, 0, 256);
            // retournement : les setups non déclenchés dans l'autre sens expirent
            int m = 0;
            for(int a = 0; a < nact; a++)
              {
               if(act[a].triggered < 0 && act[a].dir != log.ev[e].dir)
                 {
                  string x = ""; KvS(x, "reason", "trend_change");
                  Ev(K_SETUP_EXPIRED, i, act[a], x, log);
                  continue;
                 }
               if(m != a) act[m] = act[a];
               m++;
              }
            nact = m;
            ArrayResize(act, nact, 64);
           }
        }
      for(int e = from; e < to; e++)
        {
         if(log.ev[e].kind != K_ZONE) continue;
         string src = log.ev[e].s1;
         if(src != K_BOS_CHANGE && src != K_BOS_CONTINUATION) continue;
         int d = log.ev[e].dir;
         string skind, label;
         int deadline;
         if(!Qualify(i, d, src, cfg, rng, skind, label, deadline)) continue;
         double entry = log.ev[e].d1, stop = log.ev[e].d2;
         double risk = MathAbs(entry - stop);
         double atr = ctx.atr[i];
         int tg[];
         int nt = liq.IntactTargets(entry, d, tg);
         string reject = "";
         if(risk <= 0) reject = "zero_risk";
         else if(risk > cfg.sl_max_atr * atr) reject = "sl_too_wide";
         else if(nt == 0) reject = "no_target";
         string zref = log.ev[e].ref;
         string sid = StringSubstr(skind, 0, 1) + IntegerToString(i) + ":" + zref;
         string tl = "", rl = "";
         for(int k = 0; k < nt && k < 3; k++)
           {
            double tp = liq.lv[tg[k]].price;
            if(k > 0) { tl += "|"; rl += "|"; }
            tl += FmtD(tp);
            if(risk > 0) rl += FmtD(NormalizeDouble(MathAbs(tp - entry) / risk, 2));
           }
         if(risk <= 0) rl = "";
         string s = "";
         KvS(s, "setup", sid);
         KvS(s, "type", skind);
         KvS(s, "label", label);
         KvS(s, "zone", zref);
         KvD(s, "stop", stop);
         KvD(s, "risk", risk);
         if(atr > 0) KvD(s, "risk_atr", NormalizeDouble(risk / atr, 3)); else KvNone(s, "risk_atr");
         KvS(s, "targets", tl);
         KvS(s, "rr", rl);
         KvS(s, "rejected", reject);
         KvI(s, "deadline", deadline);
         int ne = log.Add(K_SETUP, i, log.ev[e].anchor, d, entry, sid, s);
         log.ev[ne].d1 = stop;
         log.ev[ne].d2 = nt > 0 ? liq.lv[tg[0]].price : 0.0;
         log.ev[ne].s1 = skind;
         log.ev[ne].s2 = reject;
         log.ev[ne].i1 = deadline;
         if(reject == "")
           {
            ArrayResize(act, nact + 1, 64);
            act[nact].sid = sid; act[nact].kind = skind; act[nact].dir = d;
            act[nact].entry = entry; act[nact].stop = stop; act[nact].t1 = liq.lv[tg[0]].price;
            act[nact].created = i; act[nact].deadline = deadline; act[nact].zone = zref;
            act[nact].label = label; act[nact].triggered = -1; act[nact].mfe_r = 0.0;
            nact++;
            if(skind == "CONCEPT") idm_taken_dir = 0;
           }
        }
     }

private:
   bool              Qualify(const int i, const int d, const string src, const SmvConfig &cfg,
                             const CSmvRanges &rng, string &skind, string &label, int &deadline)
     {
      if(rng.cur >= 0)
        {
         int k = rng.cur;
         string side = d == SMV_BULL ? "L" : "H";
         if(rng.r[k].open_index < i)
           {
            int sd = side == "H" ? 0 : 1;
            bool swept = sw_rid[sd] == rng.r[k].rid && sw_at[sd] >= 0 && sw_at[sd] <= i;
            bool open_or_just_closed = !rng.r[k].closed || rng.r[k].exit_index == i;
            if(swept && open_or_just_closed)
              {
               int n = side == "H" ? rng.r[k].sweeps_h : rng.r[k].sweeps_l;
               skind = "GOLDEN";
               label = rng.Label(k, side, n);
               deadline = i + cfg.test_max_bars;
               return true;
              }
           }
        }
      if(idm_taken_dir == d && src == K_BOS_CONTINUATION)
        {
         skind = "CONCEPT"; label = "IDM"; deadline = i + cfg.setup_expiry_bars;
         return true;
        }
      return false;
     }

   void              Ev(const string kind, const int i, const SmvSetup &s, const string extra, CSmvLog &log)
     {
      string d = "";
      KvS(d, "setup", s.sid);
      KvS(d, "type", s.kind);
      if(StringLen(extra) > 0) d += ";" + extra;
      log.Add(kind, i, s.created, s.dir, s.entry, kind + ":" + s.sid, d);
     }

   void              Close(const int i, const SmvSetup &s, const double r, const string reason,
                           const double execution_price, CSmvLog &log)
     {
      string x = "";
      KvS(x, "reason", reason);
      KvD(x, "r", NormalizeDouble(r, 4));
      KvD(x, "execution_price", execution_price);
      KvI(x, "bars_in_trade", i - (s.triggered >= 0 ? s.triggered : i));
      KvD(x, "mfe_r", NormalizeDouble(s.mfe_r, 4));
      Ev(K_SETUP_CLOSED, i, s, x, log);
     }

   void              IdmSet(const string ref, const int dir)
     {
      for(int k = 0; k < nidm; k++)
         if(idm_ref[k] == ref) { idm_dir[k] = dir; return; }
      ArrayResize(idm_ref, nidm + 1, 256);
      ArrayResize(idm_dir, nidm + 1, 256);
      idm_ref[nidm] = ref; idm_dir[nidm] = dir; nidm++;
     }

   int               IdmPop(const string ref)
     {
      for(int k = 0; k < nidm; k++)
         if(idm_ref[k] == ref)
           {
            int d = idm_dir[k];
            for(int j = k; j < nidm - 1; j++) { idm_ref[j] = idm_ref[j + 1]; idm_dir[j] = idm_dir[j + 1]; }
            nidm--;
            ArrayResize(idm_ref, nidm, 256);
            ArrayResize(idm_dir, nidm, 256);
            return d;
           }
      return 0;
     }
  };

#endif
