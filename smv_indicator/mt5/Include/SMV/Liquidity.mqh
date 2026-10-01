//+------------------------------------------------------------------+
//| SMV/Liquidity.mqh                                                |
//| R-LQ-01 à R-LQ-03 : niveaux de liquidité (intact, clean, BOS)    |
//| et EQH/EQL (portage de smv/liquidity.py).                        |
//|                                                                  |
//| Un niveau haut L est INTACT tant qu'aucune bougie ultérieure n'a |
//| dépassé L. À la première bougie i qui le dépasse : LIQ_BOS si    |
//| close[i] > L, LIQ_CLEAN sinon (statut final). Bas : symétrique.  |
//+------------------------------------------------------------------+
#ifndef SMV_LIQUIDITY_MQH
#define SMV_LIQUIDITY_MQH

#include "Pivots.mqh"

#define LQ_INTACT 0
#define LQ_CLEAN  1
#define LQ_BOS    2

struct SmvLevel
  {
   string lid;
   int    side;        // +1 haut, -1 bas
   double price;
   int    anchor;
   int    confirm;
   string source;      // PIVOT ou SIGNATURE
   int    status;
   int    taken;       // -1 = intact
  };

class CSmvLiquidity
  {
public:
   SmvLevel          lv[];
   int               nlv;
   int               intact[];   // indices des niveaux intacts, ordre de création
   int               nint;

                     CSmvLiquidity(void) { Reset(); }
   void              Reset(void) { nlv = 0; nint = 0; ArrayResize(lv, 0, 4096); ArrayResize(intact, 0, 4096); }

   //--- statuts des niveaux créés avant i ; événements dans l'ordre de création
   void              Update(const int i, const CSmvContext &ctx, CSmvLog &log)
     {
      SmvBar bar = ctx.bars[i];
      bool hit_any = false;
      for(int a = 0; a < nint; a++)
        {
         int k = intact[a];
         bool hit = lv[k].side > 0 ? lv[k].price < bar.high : lv[k].price > bar.low;
         if(!hit) continue;
         hit_any = true;
         bool closed;
         int d;
         if(lv[k].side > 0) { closed = bar.close > lv[k].price; d = SMV_BULL; }
         else               { closed = bar.close < lv[k].price; d = SMV_BEAR; }
         lv[k].status = closed ? LQ_BOS : LQ_CLEAN;
         lv[k].taken = i;
         string s = "";
         KvS(s, "level", lv[k].lid);
         KvS(s, "source", lv[k].source);
         int e = log.Add(closed ? K_LIQ_BOS : K_LIQ_CLEAN, i, lv[k].anchor, d, lv[k].price,
                         (closed ? "LB:" : "LC:") + lv[k].lid, s);
         log.ev[e].s1 = lv[k].lid;
        }
      if(hit_any)
        {
         int m = 0;
         for(int a = 0; a < nint; a++)
            if(lv[intact[a]].status == LQ_INTACT) intact[m++] = intact[a];
         nint = m;
         ArrayResize(intact, nint, 4096);
        }
     }

   void              OnPivots(const int i, const SmvPivot &newp[], const int nnew, const SmvConfig &cfg,
                              const CSmvContext &ctx, CSmvLog &log)
     {
      for(int k = 0; k < nnew; k++)
        {
         // R-LQ-03 : niveau intact de même côté le plus récent sous la tolérance
         double tol = cfg.eq_tol_atr * ctx.atr[newp[k].index];
         int match = -1;
         for(int a = nint - 1; a >= 0; a--)
           {
            int m = intact[a];
            if(lv[m].side == newp[k].side && lv[m].source == "PIVOT" && lv[m].anchor < newp[k].index)
               if(MathAbs(lv[m].price - newp[k].price) <= tol) { match = m; break; }
            if(newp[k].index - lv[m].anchor > cfg.eq_max_gap) break;
           }
         AddLevel(PivotRef(newp[k]), newp[k].side, newp[k].price, newp[k].index, i, "PIVOT", log);
         if(match >= 0)
           {
            double ext = newp[k].side > 0 ? MathMax(lv[match].price, newp[k].price)
                                          : MathMin(lv[match].price, newp[k].price);
            string sd = SideStr(newp[k].side);
            string s = "";
            KvS(s, "side", sd);
            KvS(s, "first", lv[match].lid);
            KvS(s, "second", PivotRef(newp[k]));
            KvD(s, "tolerance", tol);
            log.Add(K_EQUAL_LEVELS, i, lv[match].anchor, SMV_NONE, ext,
                    "EQ" + sd + ":" + IntegerToString(lv[match].anchor) + ":" + IntegerToString(newp[k].index), s);
           }
        }
     }

   //--- signatures de liquidité émises à la bougie i (événements [from, to))
   void              OnSignatures(const int i, const int from, const int to, CSmvLog &log)
     {
      for(int k = from; k < to; k++)
        {
         if(log.ev[k].kind != K_LIQ_SIGNATURE) continue;
         int side = log.ev[k].s1 == "H" ? 1 : -1;
         AddLevel(log.ev[k].ref, side, log.ev[k].price, log.ev[k].anchor, i, "SIGNATURE", log);
        }
     }

   //--- R-LQ-02 : niveaux intacts au-delà de l'entrée, du plus proche au plus lointain
   //--- (tri stable : à prix égal, ordre de création)
   int               IntactTargets(const double entry, const int dir, int &out[]) const
     {
      int n = 0;
      ArrayResize(out, 0, 64);
      for(int a = 0; a < nint; a++)
        {
         int k = intact[a];
         bool ok = dir == SMV_BULL ? (lv[k].side > 0 && lv[k].price > entry)
                                   : (lv[k].side < 0 && lv[k].price < entry);
         if(!ok) continue;
         ArrayResize(out, n + 1, 64);
         // insertion stable
         int j = n;
         while(j > 0 && (dir == SMV_BULL ? lv[out[j - 1]].price > lv[k].price
                                          : lv[out[j - 1]].price < lv[k].price))
           { out[j] = out[j - 1]; j--; }
         out[j] = k;
         n++;
        }
      return n;
     }

private:
   void              AddLevel(const string lid, const int side, const double price, const int anchor,
                              const int confirm, const string source, CSmvLog &log)
     {
      ArrayResize(lv, nlv + 1, 4096);
      lv[nlv].lid = lid; lv[nlv].side = side; lv[nlv].price = price;
      lv[nlv].anchor = anchor; lv[nlv].confirm = confirm; lv[nlv].source = source;
      lv[nlv].status = LQ_INTACT; lv[nlv].taken = -1;
      ArrayResize(intact, nint + 1, 4096);
      intact[nint++] = nlv;
      nlv++;
      string s = "";
      KvS(s, "side", SideStr(side));
      KvS(s, "source", source);
      log.Add(K_LIQ_LEVEL, confirm, anchor, SMV_NONE, price, lid, s);
     }
  };

#endif
