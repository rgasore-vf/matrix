//+------------------------------------------------------------------+
//| SMV/Pivots.mqh                                                   |
//| R-ST-02 / R-ST-03 : pivots fractals et étiquetage HH/HL/LH/LL    |
//| (portage de smv/pivots.py). Un pivot en p n'est connu qu'à la    |
//| clôture de p + pivot_right.                                      |
//+------------------------------------------------------------------+
#ifndef SMV_PIVOTS_MQH
#define SMV_PIVOTS_MQH

#include "Config.mqh"
#include "Context.mqh"

struct SmvPivot
  {
   int    side;        // +1 = haut ("H"), -1 = bas ("L")
   int    index;       // bougie de l'extrême
   double price;
   int    confirm;
   string label;       // HH, LH, EH, HL, LL, EL ou ""
  };

string PivotRef(const SmvPivot &p) { return "P" + SideStr(p.side) + ":" + IntegerToString(p.index); }

class CSmvPivots
  {
public:
   SmvPivot          highs[];
   SmvPivot          lows[];
   int               nh, nl;

                     CSmvPivots(void) { Reset(); }
   void              Reset(void) { nh = 0; nl = 0; ArrayResize(highs, 0, 2048); ArrayResize(lows, 0, 2048); }

   //--- remplit newp (0, 1 ou 2 pivots, haut avant bas) et journalise les événements
   int               Update(const int i, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log,
                            SmvPivot &newp[])
     {
      ArrayResize(newp, 0);
      int nlft = cfg.pivot_left, nrgt = cfg.pivot_right;
      int p = i - nrgt;
      if(p - nlft < 0) return 0;
      int cnt = 0;
      //--- haut : strictement au-dessus à gauche, >= à droite
      double h = ctx.bars[p].high;
      bool ok = true;
      for(int j = 1; j <= nlft && ok; j++) if(!(h > ctx.bars[p - j].high)) ok = false;
      for(int j = 1; j <= nrgt && ok; j++) if(!(h >= ctx.bars[p + j].high)) ok = false;
      if(ok)
        {
         SmvPivot pv;
         pv.side = 1; pv.index = p; pv.price = h; pv.confirm = i;
         pv.label = "";
         if(nh > 0)
           {
            double prev = highs[nh - 1].price;
            pv.label = h > prev ? "HH" : (h < prev ? "LH" : "EH");
           }
         ArrayResize(highs, nh + 1, 2048); highs[nh] = pv; nh++;
         ArrayResize(newp, cnt + 1); newp[cnt] = pv; cnt++;
        }
      //--- bas
      double lo = ctx.bars[p].low;
      ok = true;
      for(int j = 1; j <= nlft && ok; j++) if(!(lo < ctx.bars[p - j].low)) ok = false;
      for(int j = 1; j <= nrgt && ok; j++) if(!(lo <= ctx.bars[p + j].low)) ok = false;
      if(ok)
        {
         SmvPivot pv;
         pv.side = -1; pv.index = p; pv.price = lo; pv.confirm = i;
         pv.label = "";
         if(nl > 0)
           {
            double prev = lows[nl - 1].price;
            pv.label = lo > prev ? "HL" : (lo < prev ? "LL" : "EL");
           }
         ArrayResize(lows, nl + 1, 2048); lows[nl] = pv; nl++;
         ArrayResize(newp, cnt + 1); newp[cnt] = pv; cnt++;
        }
      for(int k = 0; k < cnt; k++)
        {
         string d = "";
         KvS(d, "label", newp[k].label);
         log.Add(newp[k].side > 0 ? K_PIVOT_HIGH : K_PIVOT_LOW, i, newp[k].index, SMV_NONE,
                 newp[k].price, PivotRef(newp[k]), d);
        }
      return cnt;
     }
  };

#endif
