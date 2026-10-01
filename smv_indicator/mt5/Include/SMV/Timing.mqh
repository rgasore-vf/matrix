//+------------------------------------------------------------------+
//| SMV/Timing.mqh                                                   |
//| Fuseaux horaires, heures de tir (R-OU-01), fenêtre du high/low   |
//| du mois (R-OU-02) et imbalance ICT optionnelle (§15).            |
//| Portage de smv/timing.py.                                        |
//|                                                                  |
//| MQL5 n'a pas de base de fuseaux : les règles d'heure d'été sont  |
//| codées ici (UE depuis 1996, États-Unis depuis 2007). Elles ne    |
//| sont donc pas valables pour un historique antérieur à 2007.      |
//| Les ancrages des sessions sont des MARQUEURS, pas des filtres.   |
//+------------------------------------------------------------------+
#ifndef SMV_TIMING_MQH
#define SMV_TIMING_MQH

#include "Context.mqh"
#include "Config.mqh"

#define TZ_UTC     0
#define TZ_PARIS   1
#define TZ_LONDON  2
#define TZ_NY      3
#define TZ_TOKYO   4
#define TZ_ATHENS  5

//--- date (00:00 UTC) du n-ième dimanche du mois ; n = -1 : dernier dimanche
datetime SundayOf(const int year, const int month, const int n)
  {
   MqlDateTime t;
   ZeroMemory(t);
   t.year = year; t.mon = month; t.day = 1;
   datetime first = StructToTime(t);
   MqlDateTime f;
   TimeToStruct(first, f);
   if(n > 0)
     {
      int delta = (7 - f.day_of_week) % 7;            // premier dimanche
      return first + (delta + 7 * (n - 1)) * 86400;
     }
   // dernier dimanche : partir du premier jour du mois suivant
   MqlDateTime u;
   ZeroMemory(u);
   u.year = month == 12 ? year + 1 : year; u.mon = month == 12 ? 1 : month + 1; u.day = 1;
   datetime next = StructToTime(u);
   MqlDateTime g;
   TimeToStruct(next - 86400, g);                      // dernier jour du mois
   return next - 86400 - g.day_of_week * 86400;
  }

int YearOf(const datetime t) { MqlDateTime s; TimeToStruct(t, s); return s.year; }

//--- UE : du dernier dimanche de mars 01:00 UTC au dernier dimanche d'octobre 01:00 UTC
bool IsEuDst(const datetime utc)
  {
   int y = YearOf(utc);
   return utc >= SundayOf(y, 3, -1) + 3600 && utc < SundayOf(y, 10, -1) + 3600;
  }

//--- États-Unis : du 2e dimanche de mars 02:00 EST (07:00 UTC) au 1er dimanche de novembre 02:00 EDT (06:00 UTC)
bool IsUsDst(const datetime utc)
  {
   int y = YearOf(utc);
   return utc >= SundayOf(y, 3, 2) + 7 * 3600 && utc < SundayOf(y, 11, 1) + 6 * 3600;
  }

int TzStd(const int tz)
  {
   switch(tz)
     {
      case TZ_PARIS:  return 3600;
      case TZ_LONDON: return 0;
      case TZ_NY:     return -5 * 3600;
      case TZ_TOKYO:  return 9 * 3600;
      case TZ_ATHENS: return 2 * 3600;
     }
   return 0;
  }

bool TzDst(const int tz, const datetime utc)
  {
   if(tz == TZ_PARIS || tz == TZ_LONDON || tz == TZ_ATHENS) return IsEuDst(utc);
   if(tz == TZ_NY) return IsUsDst(utc);
   return false;
  }

int TzOffset(const int tz, const datetime utc) { return TzStd(tz) + (TzDst(tz, utc) ? 3600 : 0); }

//--- heure locale -> UTC (heures ambiguës : première occurrence, comme zoneinfo fold=0)
datetime LocalToUtc(const datetime local, const int tz)
  {
   datetime u_dst = local - TzStd(tz) - 3600;
   if(TzDst(tz, u_dst)) return u_dst;
   return local - TzStd(tz);
  }

//--- format ISO 8601 avec décalage, identique à datetime.isoformat() de Python
string IsoLocal(const datetime utc, const int tz)
  {
   int off = TzOffset(tz, utc);
   MqlDateTime s;
   TimeToStruct(utc + off, s);
   int a = MathAbs(off);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02d%s%02d:%02d", s.year, s.mon, s.day, s.hour, s.min, s.sec,
                       off < 0 ? "-" : "+", a / 3600, (a % 3600) / 60);
  }

datetime DayStart(const datetime t) { return t - (t % 86400); }

//+------------------------------------------------------------------+
//| Conversion heure serveur -> UTC                                   |
//+------------------------------------------------------------------+
enum ENUM_SMV_SERVER_TZ
  {
   SMV_SRV_EET_EU = 0,   // UTC+2/+3, heure d'été européenne (Europe/Athens)
   SMV_SRV_NY7    = 1,   // New York + 7 h (UTC+2/+3, heure d'été américaine)
   SMV_SRV_FIXED  = 2    // décalage fixe (heures)
  };

datetime ServerToUtc(const datetime srv, const ENUM_SMV_SERVER_TZ mode, const int fixed_hours)
  {
   if(mode == SMV_SRV_FIXED) return srv - fixed_hours * 3600;
   datetime cand = srv - 3 * 3600;
   bool dst = mode == SMV_SRV_EET_EU ? IsEuDst(cand) : IsUsDst(cand);
   return dst ? cand : srv - 2 * 3600;
  }

//+------------------------------------------------------------------+
//| Heures de tir                                                     |
//+------------------------------------------------------------------+
class CSmvSessions
  {
public:
   void              Update(const int i, const SmvConfig &cfg, const CSmvContext &ctx, CSmvLog &log)
     {
      datetime a = ctx.bars[i].t_open, b = ctx.bars[i].t_close;
      string names[]; datetime starts[]; int tzs[];
      int n = 0;
      for(datetime day = DayStart(a - 86400); day <= DayStart(b + 86400); day += 86400)
        {
         if(cfg.session_mode == "measured")
           {
            Try(day, "ASIA", TZ_TOKYO, 10, 0, a, b, names, starts, tzs, n);
            Try(day, "EUROPE", TZ_LONDON, 8, 0, a, b, names, starts, tzs, n);
            Try(day, "US_DATA", TZ_NY, 8, 30, a, b, names, starts, tzs, n);
            Try(day, "US_10H", TZ_NY, 10, 0, a, b, names, starts, tzs, n);
           }
         else
           {
            bool summer = IsEuDst(LocalToUtc(day + 12 * 3600, TZ_PARIS));
            Try(day, "ASIA", TZ_PARIS, summer ? 1 : 2, 0, a, b, names, starts, tzs, n);
            Try(day, "ASIA_TOKYO", TZ_PARIS, 4, 0, a, b, names, starts, tzs, n);
            Try(day, "EUROPE", TZ_PARIS, summer ? 8 : 9, 0, a, b, names, starts, tzs, n);
            Try(day, "US", TZ_PARIS, summer ? 13 : 14, 0, a, b, names, starts, tzs, n);
            Try(day, "US_CHICAGO", TZ_PARIS, summer ? 15 : 16, 0, a, b, names, starts, tzs, n);
           }
        }
      for(int k = 0; k < n; k++)
        {
         string s = "";
         KvS(s, "name", names[k]);
         KvS(s, "start", IsoLocal(starts[k], TZ_PARIS));
         KvS(s, "end", IsoLocal(starts[k] + cfg.session_window_min * 60, TZ_PARIS));
         KvS(s, "mode", cfg.session_mode);
         log.Add(K_SESSION, i, i, SMV_NONE, ctx.bars[i].open,
                 "SES:" + names[k] + ":" + IsoLocal(starts[k], tzs[k]), s);
        }
     }

private:
   //--- ajoute la session si son début tombe dans [a, b) ; tri stable par heure de début
   void              Try(const datetime day, const string name, const int tz, const int h, const int m,
                         const datetime a, const datetime b, string &names[], datetime &starts[], int &tzs[],
                         int &n)
     {
      datetime start = LocalToUtc(day + h * 3600 + m * 60, tz);
      if(!(a <= start && start < b)) return;
      ArrayResize(names, n + 1); ArrayResize(starts, n + 1); ArrayResize(tzs, n + 1);
      int j = n;
      while(j > 0 && starts[j - 1] > start)
        { names[j] = names[j - 1]; starts[j] = starts[j - 1]; tzs[j] = tzs[j - 1]; j--; }
      names[j] = name; starts[j] = start; tzs[j] = tz;
      n++;
     }
  };

//+------------------------------------------------------------------+
//| Fenêtre [26 du mois précédent 00:00, 10 du mois 00:00) Paris      |
//+------------------------------------------------------------------+
struct SmvMonthState
  {
   int    year;
   int    mon;
   double high;
   int    hi_idx;
   double low;
   int    lo_idx;
   bool   done;
   bool   has_data;
   datetime first;
   datetime last;
   bool   continuous;
   int    excluded;
  };

class CSmvMonthWindow
  {
public:
   SmvMonthState     st[];
   int               ns;

                     CSmvMonthWindow(void) { Reset(); }
   void              Reset(void) { ns = 0; ArrayResize(st, 0, 64); }

   void              Update(const int i, const CSmvContext &ctx, CSmvLog &log)
     {
      SmvBar bar = ctx.bars[i];
      MqlDateTime la;
      TimeToStruct(bar.t_open + TzOffset(TZ_PARIS, bar.t_open), la);
      int y = 0, m = 0;
      if(la.day >= 26) { y = la.mon == 12 ? la.year + 1 : la.year; m = la.mon == 12 ? 1 : la.mon + 1; }
      else if(la.day <= 9) { y = la.year; m = la.mon; }
      if(m == 0)
        {
         TimeToStruct(bar.t_close - 1 + TzOffset(TZ_PARIS, bar.t_close - 1), la);
         if(la.day >= 26) { y = la.mon == 12 ? la.year + 1 : la.year; m = la.mon == 12 ? 1 : la.mon + 1; }
         else if(la.day <= 9) { y = la.year; m = la.mon; }
        }
      if(m > 0)
        {
         int k = Find(y, m);
         if(k < 0)
           {
            ArrayResize(st, ns + 1, 64);
            k = ns++;
            st[k].year = y; st[k].mon = m; st[k].done = false;
            st[k].has_data = false; st[k].first = 0; st[k].last = 0;
            st[k].continuous = true; st[k].excluded = 0;
            st[k].high = 0; st[k].low = 0; st[k].hi_idx = 0; st[k].lo_idx = 0;
           }
         if(!st[k].done)
           {
            if(bar.t_open < WindowStart(y, m) || bar.t_close > WindowEnd(y, m)) st[k].excluded++;
            else
              {
               if(!st[k].has_data) st[k].first = bar.t_open;
               else if(st[k].last != bar.t_open) st[k].continuous = false;
               st[k].last = bar.t_close;
               if(!st[k].has_data || bar.high > st[k].high) { st[k].high = bar.high; st[k].hi_idx = i; }
               if(!st[k].has_data || bar.low < st[k].low) { st[k].low = bar.low; st[k].lo_idx = i; }
               st[k].has_data = true;
              }
           }
        }
      for(int k = 0; k < ns; k++)
        {
         if(st[k].done || !st[k].has_data || bar.t_close < WindowEnd(st[k].year, st[k].mon)) continue;
         st[k].done = true;
         string month = StringFormat("%d-%02d", st[k].year, st[k].mon);
         string s = "";
         KvS(s, "month", month);
         KvD(s, "high", st[k].high);
         KvI(s, "high_index", st[k].hi_idx);
         KvD(s, "low", st[k].low);
         KvI(s, "low_index", st[k].lo_idx);
         bool complete = st[k].first == WindowStart(st[k].year, st[k].mon) &&
                         st[k].last == WindowEnd(st[k].year, st[k].mon) && st[k].continuous && st[k].excluded == 0;
         KvS(s, "coverage", complete ? "complete" : "partial");
         KvI(s, "excluded_boundary_bars", st[k].excluded);
         log.Add(K_MONTH_WINDOW, i, (st[k].hi_idx < st[k].lo_idx ? st[k].hi_idx : st[k].lo_idx), SMV_NONE, st[k].high, "MW:" + month, s);
        }
     }

private:
   int               Find(const int y, const int m) const
     {
      for(int k = ns - 1; k >= 0; k--) if(st[k].year == y && st[k].mon == m) return k;
      return -1;
     }
   datetime          WindowEnd(const int y, const int m) const
     {
      MqlDateTime t; ZeroMemory(t);
      t.year = y; t.mon = m; t.day = 10;
      return LocalToUtc(StructToTime(t), TZ_PARIS);
     }
   datetime          WindowStart(const int y, const int m) const
     {
      MqlDateTime t; ZeroMemory(t);
      t.year = m == 1 ? y - 1 : y; t.mon = m == 1 ? 12 : m - 1; t.day = 26;
      return LocalToUtc(StructToTime(t), TZ_PARIS);
     }
  };

//--- fair value gap ICT à 3 bougies (définition EXTERNE), confirmé à la 3e bougie
void ImbalanceScan(const int i, const CSmvContext &ctx, CSmvLog &log)
  {
   if(i < 2) return;
   SmvBar b0 = ctx.bars[i - 2], b2 = ctx.bars[i];
   string s = "";
   if(b0.high < b2.low)
     {
      KvD(s, "top", b2.low); KvD(s, "bottom", b0.high); KvS(s, "definition", "ICT-3-candles");
      log.Add(K_IMBALANCE, i, i - 1, 1, b2.low, "IMB:" + IntegerToString(i - 1), s);
     }
   else if(b0.low > b2.high)
     {
      KvD(s, "top", b0.low); KvD(s, "bottom", b2.high); KvS(s, "definition", "ICT-3-candles");
      log.Add(K_IMBALANCE, i, i - 1, -1, b2.high, "IMB:" + IntegerToString(i - 1), s);
     }
  }

#endif
