//+------------------------------------------------------------------+
//| SMV/Structure.mqh                                                |
//| R-ST-04 à R-ST-07 et R-LQ-05 : automate de structure majeure     |
//| (portage de smv/structure.py ; mêmes règles, même ordre).        |
//|                                                                  |
//| Tendance haussière (la baisse est symétrique) :                  |
//|  prot    : niveau protégé ; clôture au-delà = BOS de changement  |
//|  ref     : HH fixé ; clôture au-delà = BOS de continuation       |
//|  leg_ext : extrême courant de la jambe                           |
//| Ordre pour la bougie i : cassures (état de i-1), extrême de      |
//| jambe, puis pivots confirmés à la clôture de i.                  |
//+------------------------------------------------------------------+
#ifndef SMV_STRUCTURE_MQH
#define SMV_STRUCTURE_MQH

#include "Pivots.mqh"

class CSmvStructure
  {
public:
   int               trend;
   bool              has_prot;
   double            prot_p;
   int               prot_i;
   bool              has_ref;
   double            ref_p;
   int               ref_i;
   bool              has_leg;
   double            leg_p;
   int               leg_i;
   int               leg_start;
   bool              fail_done;
   bool              prot_swept;
   bool              has_ph, has_pl, has_last_leg;
   SmvPivot          last_ph, last_pl, last_leg;

                     CSmvStructure(void) { Reset(); }
   void              Reset(void)
     {
      trend = SMV_NONE;
      has_prot = false; has_ref = false; has_leg = false;
      prot_p = 0; prot_i = 0; ref_p = 0; ref_i = 0; leg_p = 0; leg_i = 0;
      leg_start = 0; fail_done = false; prot_swept = false;
      has_ph = false; has_pl = false; has_last_leg = false;
     }

   bool              Beyond(const double price, const double level, const int d, const SmvConfig &cfg) const
     {
      return d == SMV_BULL ? price > level + cfg.bos_eps : price < level - cfg.bos_eps;
     }

   void              Update(const int i, const SmvPivot &newp[], const int nnew, const SmvConfig &cfg,
                            const CSmvContext &ctx, const CSmvPivots &piv, CSmvLog &log)
     {
      const double close = ctx.bars[i].close;
      if(trend == SMV_NONE) TryInit(i, close, cfg, ctx, log);
      else                  CheckBreaks(i, cfg, ctx, piv, log);
      //--- 2. extrême de jambe
      if(trend == SMV_BULL && has_leg && ctx.bars[i].high > leg_p) { leg_p = ctx.bars[i].high; leg_i = i; }
      else if(trend == SMV_BEAR && has_leg && ctx.bars[i].low < leg_p) { leg_p = ctx.bars[i].low; leg_i = i; }
      //--- 3. pivots confirmés à la clôture de i
      for(int k = 0; k < nnew; k++)
        {
         if(newp[k].side > 0) { last_ph = newp[k]; has_ph = true; }
         else                 { last_pl = newp[k]; has_pl = true; }
         if(trend != SMV_NONE) IntegratePivot(i, newp[k], ctx, log);
        }
     }

private:
   void              StartLeg(const int d, const double pp, const int pi, const int start, const int i,
                              const CSmvContext &ctx)
     {
      trend = d;
      has_prot = true; prot_p = pp; prot_i = pi;
      has_ref = false;
      leg_start = start;
      ctx.Ext(d, start, i, leg_p, leg_i); has_leg = true;
      fail_done = false;
      prot_swept = false;
      has_last_leg = false;
     }

   void              TryInit(const int i, const double close, const SmvConfig &cfg, const CSmvContext &ctx,
                             CSmvLog &log)
     {
      for(int k = 0; k < 2; k++)
        {
         int d = k == 0 ? SMV_BULL : SMV_BEAR;
         bool has = k == 0 ? has_ph : has_pl;
         if(!has) continue;
         SmvPivot pv;
         if(k == 0) pv = last_ph; else pv = last_pl;
         if(!Beyond(close, pv.price, d, cfg)) continue;
         double op; int oi;
         ctx.Ext(-d, pv.index, i, op, oi);
         StartLeg(d, op, oi, oi, i, ctx);
         string s = "";
         KvI(s, "origin_index", oi);
         KvD(s, "origin_price", op);
         int e = log.Add(K_TREND_INIT, i, pv.index, d, pv.price, "INIT:" + IntegerToString(i), s);
         log.ev[e].i1 = oi; log.ev[e].d1 = op;
         return;
        }
     }

   void              CheckBreaks(const int i, const SmvConfig &cfg, const CSmvContext &ctx,
                                 const CSmvPivots &piv, CSmvLog &log)
     {
      const int d = trend;
      const SmvBar bar = ctx.bars[i];
      //--- BOS de changement : clôture au-delà du niveau protégé
      if(Beyond(bar.close, prot_p, -d, cfg))
        {
         double bp = prot_p; int bi = prot_i;
         double np; int ni;
         ctx.Ext(d, bi, i, np, ni);     // extrême de l'ancienne tendance = origine
         string s = "";
         KvI(s, "origin_index", ni);
         KvD(s, "origin_price", np);
         KvS(s, "major_mode", cfg.major_mode);
         int e = log.Add(K_BOS_CHANGE, i, bi, -d, bp, "BOSC:" + IntegerToString(i), s);
         log.ev[e].i1 = ni; log.ev[e].d1 = np;
         StartLeg(-d, np, ni, ni, i, ctx);
         return;
        }
      // Both facts use the old protected level, before a continuation updates it.
      bool crossed = d == SMV_BULL ? bar.low < prot_p : bar.high > prot_p;
      if(crossed && !prot_swept)
        {
         prot_swept = true;
         string s = "";
         KvI(s, "trend", d);
         log.Add(K_PROTECTED_SWEEP, i, prot_i, -d, prot_p, "PSW:" + IntegerToString(i), s);
        }
      //--- BOS de continuation : clôture au-delà du dernier extrême fixé
      if(has_ref && Beyond(bar.close, ref_p, d, cfg))
        {
         double rp = ref_p; int ri = ref_i;
         double op; int oi;
         ctx.Ext(-d, ri, i, op, oi);
         string s = "";
         KvI(s, "origin_index", oi);
         KvD(s, "origin_price", op);
         KvS(s, "major_mode", cfg.major_mode);
         int e = log.Add(K_BOS_CONTINUATION, i, ri, d, rp, "BOS:" + IntegerToString(i), s);
         log.ev[e].i1 = oi; log.ev[e].d1 = op;
         //--- R-LQ-05 : pivots du retracement qui n'ont pas donné le BOS
         int side = d == SMV_BULL ? -1 : 1;
         int np = side < 0 ? piv.nl : piv.nh;
         int begin = np;
         while(begin > 0)
           {
            int anchor = side < 0 ? piv.lows[begin - 1].index : piv.highs[begin - 1].index;
            if(anchor <= ri) break;
            begin--;
           }
         for(int k = begin; k < np; k++)
           {
            SmvPivot p;
            if(side < 0) p = piv.lows[k]; else p = piv.highs[k];
            if(!(ri < p.index && p.index <= i && p.confirm <= i)) continue;
            if(cfg.major_mode == "A" && p.index == oi) continue;
            string t = "";
            KvS(t, "level_ref", PivotRef(p));
            KvS(t, "side", SideStr(side));
            KvI(t, "trend", d);
            int ei = log.Add(K_INDUCEMENT, i, p.index, SMV_NONE, p.price, "IDM:" + PivotRef(p), t);
            log.ev[ei].s1 = PivotRef(p); log.ev[ei].i1 = d;
           }
         if(cfg.major_mode == "A") { prot_p = op; prot_i = oi; }
         has_ref = false;
         leg_start = oi;
         ctx.Ext(d, oi, i, leg_p, leg_i); has_leg = true;
         fail_done = false;
         prot_swept = false;
         has_last_leg = false;
         return;
        }
     }

   void              IntegratePivot(const int i, const SmvPivot &pv, const CSmvContext &ctx, CSmvLog &log)
     {
      const int d = trend;
      int trend_side = d == SMV_BULL ? 1 : -1;
      if(pv.side != trend_side || pv.index < leg_start) return;
      bool is_extreme = d == SMV_BULL ? pv.price >= leg_p : pv.price <= leg_p;
      if(is_extreme) { has_ref = true; ref_p = pv.price; ref_i = pv.index; }
      //--- R-ST-07 : premier sommet plus bas (creux plus haut) de la jambe
      if(!fail_done)
        {
         bool failed = pv.label == (d == SMV_BULL ? "LH" : "HL");
         if(failed)
           {
            fail_done = true;
            double cp; int ci;
            ctx.Ext(d, leg_start, pv.index, cp, ci);   // BC (hausse) / SC (baisse)
            double ap; int ai;
            ctx.Ext(-d, ci, pv.index, ap, ai);         // AR
            string s = "";
            KvI(s, "prior_trend", d);
            KvI(s, "climax_index", ci);
            KvD(s, "climax_price", cp);
            KvI(s, "ar_index", ai);
            KvD(s, "ar_price", ap);
            KvS(s, "st_ref", PivotRef(pv));
            int e = log.Add(K_FAIL, i, pv.index, -d, pv.price, "FAIL:" + PivotRef(pv), s);
            log.ev[e].i1 = d; log.ev[e].i2 = ci; log.ev[e].i3 = ai;
            log.ev[e].d1 = cp; log.ev[e].d2 = ap; log.ev[e].s1 = PivotRef(pv);
           }
        }
      last_leg = pv;
      has_last_leg = true;
     }
  };

#endif
