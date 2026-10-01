//+------------------------------------------------------------------+
//| SMV/Ranges.mqh                                                   |
//| R-CE-01, R-CE-02, R-GS-02 : consolidation (cause) et décompte de |
//| liquidité externe (portage de smv/ranges.py). EXPÉRIMENTAL : les |
//| libellés Wyckoff sont des CANDIDATS, confirmés ou infirmés à la  |
//| sortie (RANGE_EXIT.outcome). Rien n'est réécrit dans le passé.   |
//+------------------------------------------------------------------+
#ifndef SMV_RANGES_MQH
#define SMV_RANGES_MQH

#include "Pivots.mqh"

struct SmvRange
  {
   string rid;
   int    prior_trend;
   double low;
   double high;
   int    open_index;
   int    climax_index;
   string st_ref;
   int    sweeps_h;
   int    sweeps_l;
   int    intention;
   bool   fail_taken;
   bool   complete;
   bool   closed;
   int    exit_index;       // -1 : pas de sortie validée (ou remplacée par un FAIL)
   bool   has_pending;
   int    pend_dir;
   int    pend_start;
   double pend_ext;
   bool   outside_h;
   bool   outside_l;
  };

//--- libellés par contexte et par côté, dans l'ordre des prises successives
string RangeLabel(const int prior_trend, const string side, const int n)
  {
   string seq[];
   if(prior_trend == SMV_BEAR)
     {
      if(side == "L") { ArrayResize(seq, 2); seq[0] = "STB"; seq[1] = "SPRING"; }
      else            { ArrayResize(seq, 1); seq[0] = "UA"; }
     }
   else
     {
      if(side == "H") { ArrayResize(seq, 2); seq[0] = "UT"; seq[1] = "UTAD"; }
      else            { ArrayResize(seq, 1); seq[0] = "MSO"; }
     }
   int len = ArraySize(seq);
   if(n <= len) return seq[n - 1];
   return seq[len - 1] + "+" + IntegerToString(n - len);
  }

class CSmvRanges
  {
public:
   SmvRange          r[];
   int               nr;
   int               cur;        // indice de la consolidation courante, -1 si aucune

                     CSmvRanges(void) { Reset(); }
   void              Reset(void) { nr = 0; cur = -1; ArrayResize(r, 0, 256); }

   string            Label(const int k, const string side, const int n) const
     {
      return RangeLabel(r[k].prior_trend, side, n);
     }

   //--- sortie validée après range_accept_bars clôtures consécutives hors bornes ;
   //--- une excursion qui revient avant validation compte comme une prise
   void              Update(const int i, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
     {
      if(cur < 0) return;
      int k = cur;
      if(r[k].closed || r[k].open_index >= i) return;
      SmvBar bar = ctx.bars[i];
      int beyond = bar.close > r[k].high ? SMV_BULL : (bar.close < r[k].low ? SMV_BEAR : SMV_NONE);
      string resolved = "";
      if(r[k].has_pending)
        {
         int d = r[k].pend_dir, start = r[k].pend_start;
         double ext = r[k].pend_ext;
         if(beyond == d)
           {
            ext = d == SMV_BULL ? MathMax(ext, bar.high) : MathMin(ext, bar.low);
            r[k].pend_ext = ext;
           }
         else
           {
            r[k].has_pending = false;
            resolved = d == SMV_BULL ? "H" : "L";
            bool outside = resolved == "H" ? r[k].outside_h : r[k].outside_l;
            if(!outside) Sweep(k, i, resolved, start, ext, log);
            if(resolved == "H") r[k].outside_h = bar.high > r[k].high;
            else r[k].outside_l = bar.low < r[k].low;
           }
        }
      if(beyond != SMV_NONE && !r[k].has_pending)
        {
         r[k].has_pending = true;
         r[k].pend_dir = beyond;
         r[k].pend_start = i;
         r[k].pend_ext = beyond == SMV_BULL ? bar.high : bar.low;
        }
      // une prise = un épisode (première bougie qui dépasse la borne en mèche)
      if(resolved != "H" && !(r[k].has_pending && beyond == SMV_BULL))
        {
         bool ch = bar.high > r[k].high;
         if(ch && !r[k].outside_h) Sweep(k, i, "H", i, bar.high, log);
         r[k].outside_h = ch;
        }
      if(resolved != "L" && !(r[k].has_pending && beyond == SMV_BEAR))
        {
         bool cl = bar.low < r[k].low;
         if(cl && !r[k].outside_l) Sweep(k, i, "L", i, bar.low, log);
         r[k].outside_l = cl;
        }
      if(r[k].has_pending && i - r[k].pend_start + 1 >= cfg.range_accept_bars)
        { Exit(k, i, r[k].pend_dir, r[k].pend_start, ctx, log); return; }
      CheckComplete(k, i, log);
     }

   //--- événements de la bougie i (journal [from, to))
   void              OnEvents(const int i, const int from, const int to, CSmvLog &log)
     {
      int k = cur;
      for(int e = from; e < to; e++)
        {
         string kind = log.ev[e].kind;
         if(kind == K_FAIL)
           {
            int d = log.ev[e].i1;
            double lo, hi;
            if(d == SMV_BULL) { lo = log.ev[e].d2; hi = log.ev[e].d1; }
            else              { lo = log.ev[e].d1; hi = log.ev[e].d2; }
            if(k >= 0 && !r[k].closed) r[k].closed = true;
            ArrayResize(r, nr + 1, 256);
            int n = nr; nr++;
            r[n].rid = "R:" + IntegerToString(i);
            r[n].prior_trend = d; r[n].low = lo; r[n].high = hi; r[n].open_index = i;
            r[n].climax_index = log.ev[e].i2;
            r[n].st_ref = log.ev[e].s1;
            r[n].sweeps_h = 0; r[n].sweeps_l = 0; r[n].intention = SMV_NONE;
            r[n].fail_taken = false; r[n].complete = false; r[n].closed = false; r[n].exit_index = -1;
            r[n].has_pending = false; r[n].pend_dir = 0; r[n].pend_start = 0; r[n].pend_ext = 0;
            r[n].outside_h = false; r[n].outside_l = false;
            cur = n;
            string s = "";
            KvD(s, "low", lo);
            KvD(s, "high", hi);
            KvI(s, "prior_trend", d);
            KvI(s, "climax_index", log.ev[e].i2);
            KvI(s, "ar_index", log.ev[e].i3);
            KvS(s, "st_ref", log.ev[e].s1);
            KvS(s, "context", d == SMV_BEAR ? "accumulation?" : "distribution?");
            log.Add(K_RANGE_OPEN, i, log.ev[e].i2, -d, hi, r[n].rid, s);
            k = n;
           }
         else if(k >= 0 && !r[k].closed && r[k].open_index < i)
           {
            if((kind == K_BOS_CHANGE || kind == K_BOS_CONTINUATION) && r[k].intention == SMV_NONE)
              {
               r[k].intention = log.ev[e].dir;
               string s = "";
               KvS(s, "range", r[k].rid);
               KvS(s, "bos", log.ev[e].ref);
               log.Add(K_RANGE_INTENTION, i, log.ev[e].anchor, log.ev[e].dir, log.ev[e].price,
                       "RI:" + r[k].rid, s);
               CheckComplete(k, i, log);
              }
            else if((kind == K_LIQ_CLEAN || kind == K_LIQ_BOS) && log.ev[e].s1 == r[k].st_ref)
              {
               if(!r[k].fail_taken) { r[k].fail_taken = true; CheckComplete(k, i, log); }
              }
           }
        }
     }

private:
   void              Sweep(const int k, const int i, const string side, const int anchor, const double price,
                           CSmvLog &log)
     {
      int n;
      if(side == "H") n = ++r[k].sweeps_h; else n = ++r[k].sweeps_l;
      string s = "";
      KvS(s, "range", r[k].rid);
      KvS(s, "side", side);
      KvI(s, "count", n);
      KvS(s, "label_candidate", Label(k, side, n));
      int e = log.Add(K_RANGE_SWEEP, i, anchor, side == "H" ? SMV_BULL : SMV_BEAR, price,
                      "RS:" + r[k].rid + ":" + side + IntegerToString(n), s);
      log.ev[e].s1 = r[k].rid; log.ev[e].s2 = side;
     }

   void              Exit(const int k, const int i, const int d, const int start, const CSmvContext &ctx,
                          CSmvLog &log)
     {
      int expected = -r[k].prior_trend;
      r[k].closed = true;
      r[k].exit_index = i;
      r[k].has_pending = false;
      // type 1 : deux prises sur la borne opposée à la sortie ; type 2 : une seule
      int nopp = d == SMV_BULL ? r[k].sweeps_l : r[k].sweeps_h;
      string wtype = nopp >= 2 ? "type1" : (nopp == 1 ? "type2" : "none");
      string s = "";
      KvS(s, "range", r[k].rid);
      KvI(s, "expected", expected);
      KvS(s, "outcome", d == expected ? "confirmed" : "invalidated");
      KvI(s, "sweeps_high", r[k].sweeps_h);
      KvI(s, "sweeps_low", r[k].sweeps_l);
      KvS(s, "wyckoff_type", wtype);
      KvI(s, "duration", i - r[k].open_index);
      log.Add(K_RANGE_EXIT, i, start, d, ctx.bars[i].close, "RX:" + r[k].rid, s);
     }

   void              CheckComplete(const int k, const int i, CSmvLog &log)
     {
      bool took = r[k].fail_taken || (r[k].sweeps_h + r[k].sweeps_l) > 0;
      if(!r[k].complete && took && r[k].intention != SMV_NONE)
        {
         r[k].complete = true;
         string s = "";
         KvS(s, "range", r[k].rid);
         log.Add(K_CAUSE_COMPLETE, i, r[k].open_index, r[k].intention, 0.0, "CC:" + r[k].rid, s);
        }
     }
  };

#endif
