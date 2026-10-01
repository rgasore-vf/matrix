//+------------------------------------------------------------------+
//| SMV/Context.mqh                                                  |
//| Historique des bougies closes et ATR de Wilder                   |
//| (portage de smv/context.py). Aucune lecture au-delà du dernier   |
//| indice ajouté.                                                   |
//+------------------------------------------------------------------+
#ifndef SMV_CONTEXT_MQH
#define SMV_CONTEXT_MQH

#include "Types.mqh"

class CSmvContext
  {
public:
   int               atr_len;
   SmvBar            bars[];
   double            tr[];
   double            atr[];
   int               n;
   double            tr_sum;   // somme des TR pendant la chauffe (même ordre d'addition que Python)

                     CSmvContext(void) { Init(14); }

   void              Init(const int len)
     {
      atr_len = len;
      n = 0;
      tr_sum = 0.0;
      ArrayResize(bars, 0, 8192);
      ArrayResize(tr, 0, 8192);
      ArrayResize(atr, 0, 8192);
     }

   int               Last(void) const { return n - 1; }

   bool              Append(const SmvBar &b)
     {
      if(b.index != n)
        { PrintFormat("SMV: index attendu %d, reçu %d", n, b.index); return false; }
      if(!MathIsValidNumber(b.open) || !MathIsValidNumber(b.high) || !MathIsValidNumber(b.low) ||
         !MathIsValidNumber(b.close) ||
         b.high < b.low || b.high < MathMax(b.open, b.close) || b.low > MathMin(b.open, b.close))
        { PrintFormat("SMV: bougie %d incohérente", b.index); return false; }
      if(b.t_close <= b.t_open || (n > 0 && b.t_open < bars[n - 1].t_close))
        { PrintFormat("SMV: bougie %d intervalle invalide ou chevauchant", b.index); return false; }
      ArrayResize(bars, n + 1, 8192);
      ArrayResize(tr, n + 1, 8192);
      ArrayResize(atr, n + 1, 8192);
      bars[n] = b;
      double t;
      if(n == 0)
         t = b.high - b.low;
      else
        {
         double pc = bars[n - 1].close;
         t = MathMax(b.high - b.low, MathMax(MathAbs(b.high - pc), MathAbs(b.low - pc)));
        }
      tr[n] = t;
      int cnt = n + 1;
      if(cnt <= atr_len)
        {
         // chauffe : moyenne simple des TR disponibles (PROPOSITION)
         tr_sum += t;
         atr[n] = tr_sum / cnt;
        }
      else
         atr[n] = (atr[n - 1] * (atr_len - 1) + t) / atr_len;
      n = cnt;
      return true;
     }

   //--- plus haut sur [a, b] inclus ; à égalité, première occurrence
   void              Highest(int a, int b, double &price, int &idx) const
     {
      if(a < 0) a = 0;
      if(b > n - 1) b = n - 1;
      price = bars[a].high;
      idx = a;
      for(int i = a + 1; i <= b; i++)
         if(bars[i].high > price) { price = bars[i].high; idx = i; }
     }

   void              Lowest(int a, int b, double &price, int &idx) const
     {
      if(a < 0) a = 0;
      if(b > n - 1) b = n - 1;
      price = bars[a].low;
      idx = a;
      for(int i = a + 1; i <= b; i++)
         if(bars[i].low < price) { price = bars[i].low; idx = i; }
     }

   //--- extrême dans le sens d (BULL : plus haut, BEAR : plus bas)
   void              Ext(const int d, const int a, const int b, double &price, int &idx) const
     {
      if(d == SMV_BULL) Highest(a, b, price, idx);
      else              Lowest(a, b, price, idx);
     }
  };

#endif
