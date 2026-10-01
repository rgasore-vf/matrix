//+------------------------------------------------------------------+
//| SMV/Zones.mqh                                                    |
//| R-CA-01 à R-CA-05 (bougies) et R-OD-01 à R-OD-05 (zones, ODF,    |
//| breaker). Portage de smv/candles.py et smv/zones.py.             |
//|                                                                  |
//| Zone de demande (BULL) : distal = plus bas de la BQA ;           |
//| proximal = haut du corps de la BM (« body ») ou plus haut de la  |
//| BM (« wick ») ; sans BM, plus haut de la BQA. Offre : symétrique.|
//+------------------------------------------------------------------+
#ifndef SMV_ZONES_MQH
#define SMV_ZONES_MQH

#include "Pivots.mqh"

//--- R-CA-04 : doji (une bougie sans amplitude est un doji)
bool IsDoji(const SmvBar &b, const SmvConfig &cfg)
  {
   return BarRange(b) == 0.0 || BarBodyRatio(b) <= cfg.doji_body_max;
  }

//--- R-CA-01 : bougie manipulatrice (pleine, de couleur opposée au départ de la zone)
bool IsManipulative(const SmvBar &b, const int zone_dir, const SmvConfig &cfg, const bool has_atr,
                    const double atr_prev)
  {
   if(BarColor(b) != -zone_dir) return false;
   if(BarBodyRatio(b) < cfg.bm_body_min) return false;
   if(cfg.bm_range_atr > 0 && has_atr && BarRange(b) < cfg.bm_range_atr * atr_prev) return false;
   return true;
  }

//--- R-CA-05 : signature de liquidité (mèche derrière le corps)
int LiquiditySignature(const SmvBar &b, const SmvConfig &cfg)
  {
   double r = BarRange(b);
   if(r <= 0) return SMV_NONE;
   if(BarColor(b) == SMV_BULL && (b.high - b.close) / r >= cfg.liqsig_wick_min) return SMV_BULL;
   if(BarColor(b) == SMV_BEAR && (b.close - b.low) / r >= cfg.liqsig_wick_min) return SMV_BEAR;
   return SMV_NONE;
  }

//--- émet LIQ_SIGNATURE à la clôture de la bougie i
void CandleScan(const int i, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
  {
   int sig = LiquiditySignature(ctx.bars[i], cfg);
   if(sig == SMV_NONE) return;
   double price = sig == SMV_BULL ? ctx.bars[i].high : ctx.bars[i].low;
   string s = "";
   KvS(s, "side", sig == SMV_BULL ? "H" : "L");
   int e = log.Add(K_LIQ_SIGNATURE, i, i, sig, price, "LS:" + IntegerToString(i), s);
   log.ev[e].s1 = sig == SMV_BULL ? "H" : "L";
  }

struct SmvZone
  {
   string zid;
   int    dir;
   double proximal;
   double distal;
   int    bqa;
   int    bm;            // -1 = pas de BM
   int    confirm;
   string source;        // BOS_CHANGE, BOS_CONTINUATION, PIVOT, BREAKER
   bool   decisional;
   bool   doji_sig;
   bool   validated;
   bool   active;
   int    touches;
   int    broken;        // -1 = non cassée
   int    odf_len;
   bool   reacted;
   bool   inside;
  };

class CSmvZones
  {
public:
   SmvZone           z[];
   int               nz;
   int               act[];     // indices des zones actives, ordre de création
   int               nact;

                     CSmvZones(void) { Reset(); }
   void              Reset(void) { nz = 0; nact = 0; ArrayResize(z, 0, 1024); ArrayResize(act, 0, 1024); }

   //--- construction ; renvoie false si la zone est dégénérée
   bool              Build(const int dir, const int bqa, const int i, const string source, const bool decisional,
                           const bool validated, const SmvConfig &cfg, const CSmvContext &ctx, SmvZone &out)
     {
      int bm = -1;
      for(int b = bqa; b >= bqa - cfg.bm_search_back; b--)
        {
         if(b < 0) break;
         bool has_atr = b >= 1;
         double atr_prev = has_atr ? ctx.atr[b - 1] : 0.0;
         if(IsManipulative(ctx.bars[b], dir, cfg, has_atr, atr_prev)) { bm = b; break; }
        }
      SmvBar q = ctx.bars[bqa];
      double proximal, distal;
      if(dir == SMV_BULL)
        {
         distal = q.low;
         if(bm < 0) proximal = q.high;
         else if(cfg.zone_proximal == "body") proximal = MathMax(ctx.bars[bm].open, ctx.bars[bm].close);
         else proximal = ctx.bars[bm].high;
        }
      else
        {
         distal = q.high;
         if(bm < 0) proximal = q.low;
         else if(cfg.zone_proximal == "body") proximal = MathMin(ctx.bars[bm].open, ctx.bars[bm].close);
         else proximal = ctx.bars[bm].low;
        }
      if((dir == SMV_BULL && proximal <= distal) || (dir == SMV_BEAR && proximal >= distal))
        {
         proximal = dir == SMV_BULL ? q.high : q.low;
         bm = -1;
         if(proximal == distal) return false;
        }
      bool doji = IsDoji(q, cfg);
      for(int k = (i - cfg.doji_window > 0 ? i - cfg.doji_window : 0); k < i && !doji; k++)
         if(IsDoji(ctx.bars[k], cfg)) doji = true;
      out.zid = "Z" + (dir == SMV_BULL ? "D" : "S") + ":" + IntegerToString(bqa) + ":" + IntegerToString(i);
      out.dir = dir; out.proximal = proximal; out.distal = distal;
      out.bqa = bqa; out.bm = bm; out.confirm = i; out.source = source;
      out.decisional = decisional; out.doji_sig = doji; out.validated = validated;
      out.active = true; out.touches = 0; out.broken = -1; out.odf_len = 1;
      out.reacted = false; out.inside = false;
      return true;
     }

   //--- zones issues des BOS de la bougie i (événements [from, to) du journal)
   void              OnStructure(const int i, const int from, const int to, const SmvConfig &cfg,
                                 const CSmvContext &ctx, CSmvLog &log)
     {
      for(int k = from; k < to; k++)
        {
         string kind = log.ev[k].kind;
         if(kind != K_BOS_CHANGE && kind != K_BOS_CONTINUATION) continue;
         SmvZone nzn;
         if(Build(log.ev[k].dir, log.ev[k].i1, i, kind, kind == K_BOS_CHANGE, true, cfg, ctx, nzn))
            Add(nzn, cfg, ctx, log);
        }
     }

   void              OnPivots(const int i, const SmvPivot &newp[], const int nnew, const SmvConfig &cfg,
                              const CSmvContext &ctx, CSmvLog &log)
     {
      if(cfg.zones_on != "all_pivots") return;
      for(int k = 0; k < nnew; k++)
        {
         int d = newp[k].side < 0 ? SMV_BULL : SMV_BEAR;
         SmvZone nzn;
         if(Build(d, newp[k].index, i, "PIVOT", false, false, cfg, ctx, nzn))
            Add(nzn, cfg, ctx, log);
        }
     }

   //--- cycle de vie des zones créées avant i
   void              Update(const int i, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
     {
      SmvBar bar = ctx.bars[i];
      SmvZone breakers[];
      int nb = 0;
      bool removed = false;
      for(int a = 0; a < nact; a++)
        {
         int k = act[a];
         if(z[k].confirm >= i) continue;
         bool broken, touched, reaction;
         if(z[k].dir == SMV_BULL)
           {
            broken = bar.close < z[k].distal;
            touched = bar.low <= z[k].proximal;
            reaction = touched && bar.close > z[k].proximal;
           }
         else
           {
            broken = bar.close > z[k].distal;
            touched = bar.high >= z[k].proximal;
            reaction = touched && bar.close < z[k].proximal;
           }
         if(broken)
           {
            z[k].active = false;
            z[k].broken = i;
            removed = true;
            string s = "";
            KvS(s, "zone", z[k].zid);
            KvS(s, "source", z[k].source);
            log.Add(K_ZONE_BROKEN, i, z[k].bqa, z[k].dir, z[k].distal, "ZB:" + z[k].zid, s);
            if(z[k].source != "BREAKER")
              {
               ArrayResize(breakers, nb + 1);
               breakers[nb].zid = "BRK:" + z[k].zid;
               breakers[nb].dir = -z[k].dir;
               breakers[nb].proximal = z[k].distal;
               breakers[nb].distal = z[k].proximal;
               breakers[nb].bqa = z[k].bqa;
               breakers[nb].bm = z[k].bm;
               breakers[nb].confirm = i;
               breakers[nb].source = "BREAKER";
               breakers[nb].decisional = false;
               breakers[nb].doji_sig = z[k].doji_sig;
               breakers[nb].validated = false;
               breakers[nb].active = true;
               breakers[nb].touches = 0;
               breakers[nb].broken = -1;
               breakers[nb].odf_len = 1;
               breakers[nb].reacted = false;
               breakers[nb].inside = false;
               nb++;
              }
           }
         else if(touched && !z[k].inside)
           {
            // R-OD-03 : une touche = début d'un épisode de contact
            z[k].inside = true;
            z[k].touches++;
            string s = "";
            KvS(s, "zone", z[k].zid);
            KvI(s, "touch", z[k].touches);
            KvS(s, "source", z[k].source);
            log.Add(K_ZONE_TOUCH, i, z[k].bqa, z[k].dir, z[k].proximal,
                    "ZT:" + z[k].zid + ":" + IntegerToString(z[k].touches), s);
           }
         else if(!touched)
            z[k].inside = false;
         // R-OD-05 : réaction = contact puis clôture du bon côté du bord proximal
         if(!broken && z[k].source == "BREAKER" && reaction && !z[k].reacted)
           {
            z[k].reacted = true;
            z[k].validated = true;
            string s = "";
            KvS(s, "zone", z[k].zid);
            log.Add(K_BREAKER_REACTION, i, z[k].bqa, z[k].dir, z[k].proximal, "BR:" + z[k].zid, s);
           }
        }
      if(removed)
        {
         int m = 0;
         for(int a = 0; a < nact; a++)
            if(z[act[a]].active) act[m++] = act[a];
         nact = m;
         ArrayResize(act, nact, 1024);
        }
      for(int b = 0; b < nb; b++)
         Add(breakers[b], cfg, ctx, log);
     }

private:
   void              ZoneEvent(const int k, CSmvLog &log)
     {
      int anchor = (z[k].bm >= 0 && z[k].bm < z[k].bqa) ? z[k].bm : z[k].bqa;
      string s = "";
      KvD(s, "proximal", z[k].proximal);
      KvD(s, "distal", z[k].distal);
      KvI(s, "bqa_index", z[k].bqa);
      if(z[k].bm >= 0) KvI(s, "bm_index", z[k].bm); else KvNone(s, "bm_index");
      KvS(s, "source", z[k].source);
      KvB(s, "decisional", z[k].decisional);
      KvB(s, "doji_signature", z[k].doji_sig);
      KvB(s, "validated", z[k].validated);
      int e = log.Add(z[k].source != "BREAKER" ? K_ZONE : K_BREAKER, z[k].confirm, anchor, z[k].dir,
                      z[k].proximal, z[k].zid, s);
      log.ev[e].d1 = z[k].proximal; log.ev[e].d2 = z[k].distal; log.ev[e].s1 = z[k].source;
     }

   //--- R-OD-04 : la BQA de la nouvelle zone a « récupéré » la zone précédente de même sens
   void              LinkOdf(const int k, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
     {
      SmvBar q = ctx.bars[z[k].bqa];
      for(int p = nz - 1; p >= 0; p--)
        {
         if(p == k || z[p].dir != z[k].dir || z[p].source == "BREAKER") continue;
         if(z[p].bqa >= z[k].bqa || z[p].confirm > z[k].bqa) continue;
         if(z[p].broken >= 0 && z[p].broken <= z[k].bqa) continue;
         bool linked;
         if(z[k].dir == SMV_BULL) linked = q.low <= z[p].proximal && q.close >= z[p].distal;
         else                     linked = q.high >= z[p].proximal && q.close <= z[p].distal;
         if(linked)
           {
            z[k].odf_len = z[p].odf_len + 1;
            string s = "";
            KvS(s, "from", z[p].zid);
            KvS(s, "to", z[k].zid);
            KvI(s, "chain_len", z[k].odf_len);
            KvB(s, "is_odf", z[k].odf_len >= cfg.odf_min_len);
            log.Add(K_ODF_LINK, z[k].confirm, z[k].bqa, z[k].dir, z[k].proximal,
                    "ODF:" + z[p].zid + ">" + z[k].zid, s);
           }
         return;   // seule la zone précédente de même sens est considérée
        }
     }

   void              Add(const SmvZone &zn, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
     {
      ArrayResize(z, nz + 1, 1024);
      z[nz] = zn;
      int k = nz;
      nz++;
      ArrayResize(act, nact + 1, 1024);
      act[nact++] = k;
      ZoneEvent(k, log);
      if(z[k].source != "BREAKER") LinkOdf(k, cfg, ctx, log);
     }
  };

#endif
