//+------------------------------------------------------------------+
//| XAU_Context.mq5                                                  |
//| Coffre-fort 2022 -> aujourd'hui de la règle FIGÉE de             |
//| docs/XAU_RESEARCH.md (research/xau/ctx_trade.py). Aucun          |
//| paramètre de stratégie réglable.                                 |
//|                                                                  |
//| Contexte (évalué à la clôture de chaque bougie M15) :            |
//|  - tendance de la structure SMV H4 d (bougies H4 du courtier),   |
//|    niveau protégé et extrême de jambe connus ;                   |
//|  - tendance de la structure SMV D1 dans le même sens ;           |
//|  - ATR H4 (Wilder 14) <= 0,95 x moyenne des 100 dernières ATR H4;|
//|  - heure de Paris de la bougie M15 entre 6 h et 14 h incluses ;  |
//|  - amplitude du jour (Paris) < 0,6 x moyenne des 20 jours        |
//|    précédents (au moins 5 jours connus).                         |
//| Trade : première bougie du jour où le contexte est vrai ; entrée |
//| à l'ouverture suivante ; stop 1 ATR H4 ; TP 2 ATR H4 ; sortie    |
//| après 192 bougies M15 (48 h). Un signal par jour au maximum.     |
//| Journal : shadow (règles exactes de la recherche, TP 1/1,5/2/3)  |
//| + exécution réelle ; Common/Files/XAUCTX/*.csv                   |
//+------------------------------------------------------------------+
#property copyright   "smv_indicator"
#property version     "1.00"
#property description "Coffre-fort XAUUSD : tendance H4 + D1 alignée, volatilité calme, 6 h-14 h Paris ; stop 1 ATR H4, TP 2 ATR H4."

#include <Trade/Trade.mqh>
#include <SMV/Structure.mqh>
#include <SMV/Timing.mqh>

input group "=== Instrument et heure du serveur ==="
input string             InpSymbol           = "";               // Symbole (vide = graphique)
input ENUM_SMV_SERVER_TZ InpServerTz         = SMV_SRV_FIXED;    // Fuseau du serveur (Deriv : fixe UTC+0)
input int                InpServerFixedHours = 0;                // Décalage fixe UTC+h
input group "=== Exécution ==="
input bool     InpTrade        = true;                 // Exécuter réellement (sinon shadow seulement)
input datetime InpTradeFrom    = D'2022.03.07 00:00';  // Signaux à partir de (après la fin des données de recherche)
input double   InpRiskPct      = 1.0;                  // Risque par trade (% du solde)
input double   InpFixedLots    = 0.0;                  // Lots fixes (0 = risque en %)
input int      InpDeviationPts = 50;                   // Glissement maximal (points)
input long     InpMagic        = 2610051;              // Numéro magique
input string   InpLogTag       = "";                   // Étiquette des fichiers

#define NTP 4
double g_tps[NTP] = {1.0, 1.5, 2.0, 3.0};
const double MAIN_TP = 2.0;
const int    HZ = 192;
const double RESEARCH_COST = 0.35;

//--- noyau SMV minimal pour une UT (contexte, pivots, structure)
class CTfCore
  {
public:
   ENUM_TIMEFRAMES   tf;
   SmvConfig         cfg;
   CSmvContext       ctx;
   CSmvPivots        piv;
   CSmvStructure     st;
   CSmvLog           log;
   datetime          last_fed;

   void              Init(const ENUM_TIMEFRAMES t)
     {
      tf = t;
      SmvConfigDefaults(cfg);
      cfg.enable_setups = false;
      ctx.Init(cfg.atr_len); piv.Reset(); st.Reset(); log.Reset();
      last_fed = 0;
     }
   bool              Feed(const MqlRates &r)
     {
      SmvBar b;
      b.index = ctx.n; b.t_srv = r.time; b.t_open = r.time; b.t_close = r.time + PeriodSeconds(tf);
      b.open = r.open; b.high = r.high; b.low = r.low; b.close = r.close;
      if(!ctx.Append(b)) return false;
      log.Reset();
      SmvPivot newp[];
      int nn = piv.Update(b.index, cfg, ctx, log, newp);
      st.Update(b.index, newp, nn, cfg, ctx, piv, log);
      last_fed = r.time;
      return true;
     }
   //--- transmet toutes les bougies closes jusqu'à t_close_max (clôture <= borne)
   int               Sync(const string sym, const datetime t_close_max, const int init_bars)
     {
      MqlRates rr[];
      ArraySetAsSeries(rr, false);
      int got;
      if(last_fed == 0) got = CopyRates(sym, tf, 1, init_bars, rr);
      else got = CopyRates(sym, tf, last_fed + 1, t_close_max, rr);
      if(got <= 0) return 0;
      int fed = 0;
      for(int k = 0; k < got; k++)
        {
         if(rr[k].time <= last_fed) continue;
         if(rr[k].time + PeriodSeconds(tf) > t_close_max) break;   // bougie pas encore close
         if(!Feed(rr[k])) return -1;
         fed++;
        }
      return fed;
     }
   double            Atr(void) const { return ctx.n > 0 ? ctx.atr[ctx.n - 1] : 0.0; }
   double            AtrMean(const int len) const
     {
      int a = MathMax(0, ctx.n - len);
      double s = 0; int c = 0;
      for(int k = a; k < ctx.n; k++) { s += ctx.atr[k]; c++; }
      return c > 0 ? s / c : 0.0;
     }
  };

struct Shadow
  {
   string   id;
   datetime t_sig;
   int      d;
   double   atr;
   double   E;
   int      rel;        // bougies M15 traitées après le signal
   bool     stopped;
   bool     hit[NTP];
   double   r[NTP];
   double   mfe;
   double   mae;
   double   volr, day_used;
   int      hour;
   bool     done;
  };

struct XTrade
  {
   string   id;
   ulong    pos_id;
   int      d;
   datetime t_sig, t_open;
   double   planned, fill, sl, tp, atr, vol, risk_money, spread_pts;
   int      bars;
   bool     open, timeout_sent;
  };

CTfCore  g_h4, g_d1;
CTrade   g_trade;
Shadow   g_sh[];
XTrade   g_tr[];
string   g_sym, g_prefix;
int      g_fh_ctx = INVALID_HANDLE, g_fh_sh = INVALID_HANDLE, g_fh_tr = INVALID_HANDLE, g_fh_log = INVALID_HANDLE;
datetime g_last_m15 = 0;
bool     g_ready = false;
bool     g_hedging = false;
//--- jour de Paris
datetime g_day = 0;
double   g_dhi = 0, g_dlo = 0;
double   g_ranges[];
datetime g_signal_day = 0;
int      g_nsig = 0;

string Fx(const double v, const int dg = 4) { return DoubleToString(v, dg); }
string Ts(const datetime t) { return TimeToString(t, TIME_DATE | TIME_MINUTES); }

void XLog(const string what)
  {
   if(g_fh_log != INVALID_HANDLE) { FileWriteString(g_fh_log, Ts(TimeCurrent()) + "," + what + "\n"); FileFlush(g_fh_log); }
   Print("XAUCTX: ", what);
  }

int OpenCsv(const string kind, const string header)
  {
   int h = FileOpen(g_prefix + "_" + kind + ".csv", FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h != INVALID_HANDLE) { FileWriteString(h, header + "\n"); FileFlush(h); }
   else PrintFormat("XAUCTX: impossible d'ouvrir %s (%d)", kind, GetLastError());
   return h;
  }

datetime ParisOf(const datetime srv)
  {
   datetime utc = ServerToUtc(srv, InpServerTz, InpServerFixedHours);
   return utc + TzOffset(TZ_PARIS, utc);
  }

int OnInit()
  {
   g_sym = StringLen(InpSymbol) > 0 ? InpSymbol : _Symbol;
   if(!SymbolSelect(g_sym, true)) { Print("XAUCTX: symbole introuvable ", g_sym); return INIT_PARAMETERS_INCORRECT; }
   if(PeriodSeconds(_Period) > PeriodSeconds(PERIOD_M15))
     { Print("XAUCTX: lancer sur un graphique M15 ou inférieur"); return INIT_PARAMETERS_INCORRECT; }
   g_h4.Init(PERIOD_H4);
   g_d1.Init(PERIOD_D1);
   g_hedging = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   MqlDateTime now; TimeToStruct(TimeLocal(), now);
   FolderCreate("XAUCTX", FILE_COMMON);
   g_prefix = "XAUCTX\\" + g_sym + (StringLen(InpLogTag) > 0 ? "_" + InpLogTag : "") +
              StringFormat("_%04d%02d%02d_%02d%02d%02d", now.year, now.mon, now.day, now.hour, now.min, now.sec);
   g_fh_log = OpenCsv("log", "time_srv,message");
   g_fh_ctx = OpenCsv("context", "time_srv,paris,hour,h4_trend,d1_trend,atr4,volr4,day_used,ctx,signal");
   g_fh_sh  = OpenCsv("shadow", "id,sig_time_srv,year,dir,atr4,entry_E,r_1,r_1.5,r_2,r_3,r_main,mfe_R,mae_R,volr4,day_used,hour,research_cost_R");
   g_fh_tr  = OpenCsv("trades", "id,pos_id,sig_time_srv,year,dir,open_time,planned_E,fill,slip_R,sl,tp,atr4,volume,risk_money,spread_pts_entry,"
                      "close_time,close_price,exit_reason,R_price,profit,commission,swap,fee,net_money,R_money");
   if(g_fh_log == INVALID_HANDLE || g_fh_ctx == INVALID_HANDLE || g_fh_sh == INVALID_HANDLE || g_fh_tr == INVALID_HANDLE)
      return INIT_FAILED;
   XLog(StringFormat("start;symbol=%s;server_tz=%s;fixed=%d;trade=%s;risk=%.2f;hedging=%s;server=%s",
                    g_sym, EnumToString(InpServerTz), InpServerFixedHours, InpTrade ? "yes" : "no", InpRiskPct,
                    g_hedging ? "yes" : "no", AccountInfoString(ACCOUNT_SERVER)));
   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpDeviationPts);
   g_trade.SetTypeFillingBySymbol(g_sym);
   EventSetTimer(60);
   return INIT_SUCCEEDED;
  }

//--- mise à jour du jour de Paris avec une bougie M15 close
void DayUpdate(const MqlRates &r)
  {
   datetime p = ParisOf(r.time);
   datetime day = p - (p % 86400);
   if(day != g_day)
     {
      if(g_day != 0)
        {
         int n = ArraySize(g_ranges);
         ArrayResize(g_ranges, n + 1, 512);
         g_ranges[n] = g_dhi - g_dlo;
        }
      g_day = day; g_dhi = r.high; g_dlo = r.low;
     }
   g_dhi = MathMax(g_dhi, r.high);
   g_dlo = MathMin(g_dlo, r.low);
  }

double DayUsed(void)
  {
   int n = ArraySize(g_ranges);
   if(n < 5) return -1.0;
   double s = 0; int c = 0;
   for(int k = MathMax(0, n - 20); k < n; k++) { s += g_ranges[k]; c++; }
   return s > 0 ? (g_dhi - g_dlo) / (s / c) : -1.0;
  }

void Process(void)
  {
   datetime cur = iTime(g_sym, PERIOD_M15, 0);
   if(cur <= 0) return;
   if(!g_ready)
     {
      if(g_h4.Sync(g_sym, cur, 3000) < 0 || g_d1.Sync(g_sym, cur, 800) < 0) { ExpertRemove(); return; }
      if(g_h4.ctx.n < 120 || g_d1.ctx.n < 30) return;              // historique pas encore prêt
      MqlRates rr[];
      ArraySetAsSeries(rr, false);
      int got = CopyRates(g_sym, PERIOD_M15, 1, 3000, rr);              // ~30 jours pour l'amplitude moyenne
      if(got <= 0) return;
      for(int k = 0; k < got; k++) DayUpdate(rr[k]);
      g_last_m15 = rr[got - 1].time;
      g_ready = true;
      XLog(StringFormat("ready;h4=%d;d1=%d;m15_init=%d;jours=%d", g_h4.ctx.n, g_d1.ctx.n, got, ArraySize(g_ranges)));
      return;
     }
   if(cur <= g_last_m15) return;
   MqlRates nr[];
   ArraySetAsSeries(nr, false);
   int got = CopyRates(g_sym, PERIOD_M15, g_last_m15 + 1, cur - 1, nr);
   if(got < 0) return;
   for(int k = 0; k < got; k++)
     {
      if(nr[k].time <= g_last_m15 || nr[k].time >= cur) continue;
      datetime t_close = nr[k].time + PeriodSeconds(PERIOD_M15);
      if(g_h4.Sync(g_sym, t_close, 3000) < 0 || g_d1.Sync(g_sym, t_close, 800) < 0) { ExpertRemove(); return; }
      OnM15(nr[k], k == got - 1);
      g_last_m15 = nr[k].time;
     }
  }

void OnTick()  { Process(); }
void OnTimer() { Process(); }

//--- bougie M15 close ; live = dernière bougie close (l'ordre réel part maintenant)
void OnM15(const MqlRates &r, const bool live)
  {
   DayUpdate(r);
   UpdateShadows(r);
   UpdateTrades();
   int d = g_h4.st.trend;
   int d1 = g_d1.st.trend;
   double atr4 = g_h4.Atr();
   double volr = atr4 > 0 ? atr4 / g_h4.AtrMean(100) : 0.0;
   double du = DayUsed();
   datetime p = ParisOf(r.time);
   MqlDateTime ps; TimeToStruct(p, ps);
   bool ctx = d != 0 && g_h4.st.has_prot && g_h4.st.has_leg && atr4 > 0 && d1 * d > 0 &&
              volr <= 0.95 && ps.hour >= 6 && ps.hour <= 14 && du >= 0 && du < 0.6;
   datetime day = p - (p % 86400);
   bool signal = ctx && day != g_signal_day && r.time >= InpTradeFrom;
   if(r.time >= InpTradeFrom)
      FileWriteString(g_fh_ctx, StringFormat("%s,%s,%d,%d,%d,%s,%s,%s,%d,%d\n", Ts(r.time), Ts(p), ps.hour, d, d1,
                      Fx(atr4, 3), Fx(volr, 3), Fx(du, 3), ctx ? 1 : 0, signal ? 1 : 0));
   if(!signal) return;
   g_signal_day = day;
   g_nsig++;
   string id = StringFormat("XAU_%s_%d", TimeToString(r.time, TIME_DATE | TIME_MINUTES), d);
   StringReplace(id, " ", "_"); StringReplace(id, ":", ""); StringReplace(id, ".", "");
   int n = ArraySize(g_sh);
   ArrayResize(g_sh, n + 1, 128);
   g_sh[n].id = id; g_sh[n].t_sig = r.time; g_sh[n].d = d; g_sh[n].atr = atr4; g_sh[n].E = 0; g_sh[n].rel = 0;
   g_sh[n].stopped = false; g_sh[n].mfe = 0; g_sh[n].mae = 0; g_sh[n].done = false;
   g_sh[n].volr = volr; g_sh[n].day_used = du; g_sh[n].hour = ps.hour;
   for(int k = 0; k < NTP; k++) { g_sh[n].hit[k] = false; g_sh[n].r[k] = 0; }
   if(InpTrade && live) OpenTrade(id, d, atr4, r.time);
   else if(InpTrade) XLog("skip;" + id + ";signal sur une bougie de rattrapage (pas d'ordre réel)");
  }

//--- shadow : règles exactes de ctx_trade.py (stop testé avant le TP dans la même bougie)
void UpdateShadows(const MqlRates &b)
  {
   for(int n = 0; n < ArraySize(g_sh); n++)
     {
      if(g_sh[n].done || b.time <= g_sh[n].t_sig) continue;
      g_sh[n].rel++;
      int d = g_sh[n].d;
      double a = g_sh[n].atr;
      if(g_sh[n].rel == 1) g_sh[n].E = b.open;
      double E = g_sh[n].E;
      double fav = (d == 1 ? b.high - E : E - b.low) / a;
      double adv = (d == 1 ? E - b.low : b.high - E) / a;
      if(!g_sh[n].stopped)
        {
         if(adv >= 1.0) g_sh[n].stopped = true;
         else
           {
            g_sh[n].mfe = MathMax(g_sh[n].mfe, fav);
            for(int k = 0; k < NTP; k++)
               if(!g_sh[n].hit[k] && fav >= g_tps[k]) { g_sh[n].hit[k] = true; g_sh[n].r[k] = g_tps[k]; }
           }
        }
      g_sh[n].mae = MathMax(g_sh[n].mae, adv);
      bool all = true;
      for(int k = 0; k < NTP; k++) if(!g_sh[n].hit[k]) all = false;
      if(g_sh[n].rel >= HZ || all || g_sh[n].stopped)
        {
         // TP non atteints : -1 si stoppé, sinon clôture de la 192e bougie (sortie à l'horizon)
         if(g_sh[n].stopped || g_sh[n].rel >= HZ)
           {
            for(int k = 0; k < NTP; k++)
               if(!g_sh[n].hit[k]) g_sh[n].r[k] = g_sh[n].stopped ? -1.0 : (b.close - E) * d / a;
            WriteShadow(n);
           }
         else if(all) WriteShadow(n);
        }
     }
  }

void WriteShadow(const int n)
  {
   g_sh[n].done = true;
   MqlDateTime dt; TimeToStruct(g_sh[n].t_sig, dt);
   double mainr = 0;
   for(int k = 0; k < NTP; k++) if(MathAbs(g_tps[k] - MAIN_TP) < 1e-9) mainr = g_sh[n].r[k];
   FileWriteString(g_fh_sh, StringFormat("%s,%s,%d,%d,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%d,%s\n",
                   g_sh[n].id, Ts(g_sh[n].t_sig), dt.year, g_sh[n].d, Fx(g_sh[n].atr, 3), Fx(g_sh[n].E, 3),
                   Fx(g_sh[n].r[0]), Fx(g_sh[n].r[1]), Fx(g_sh[n].r[2]), Fx(g_sh[n].r[3]), Fx(mainr),
                   Fx(g_sh[n].mfe, 3), Fx(g_sh[n].mae, 3), Fx(g_sh[n].volr, 3), Fx(g_sh[n].day_used, 3),
                   g_sh[n].hour, Fx(RESEARCH_COST / g_sh[n].atr)));
   FileFlush(g_fh_sh);
  }

//--- exécution réelle
void OpenTrade(const string id, const int d, const double atr, const datetime t_sig)
  {
   MqlTick tk;
   if(!SymbolInfoTick(g_sym, tk)) { XLog("error;" + id + ";pas de cotation"); return; }
   int digits = (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS);
   double px = d == 1 ? tk.ask : tk.bid;
   double sl = NormalizeDouble(px - d * atr, digits);
   double tp = NormalizeDouble(px + d * MAIN_TP * atr, digits);
   double tick_size = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tick_val <= 0.0) tick_val = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
   double vmin = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN), vmax = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   double per_lot = tick_size > 0 ? atr / tick_size * tick_val : 0.0;
   double vol = InpFixedLots;
   if(vol <= 0.0) vol = per_lot > 0 ? AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0 / per_lot : 0.0;
   vol = MathFloor(vol / vstep + 1e-9) * vstep;
   if(vol < vmin) { XLog(StringFormat("warning;%s;volume < minimum, %.2f lot (risque réel plus élevé)", id, vmin)); vol = vmin; }
   if(vol > vmax) vol = vmax;
   vol = NormalizeDouble(vol, 8);
   bool ok = d == 1 ? g_trade.Buy(vol, g_sym, 0.0, sl, tp, id) : g_trade.Sell(vol, g_sym, 0.0, sl, tp, id);
   uint rc = g_trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED && rc != TRADE_RETCODE_DONE_PARTIAL))
     { XLog(StringFormat("error;%s;ordre refusé retcode=%u %s", id, rc, g_trade.ResultRetcodeDescription())); return; }
   ulong deal = g_trade.ResultDeal();
   double fill = g_trade.ResultPrice();
   ulong pos_id = 0;
   if(deal > 0 && HistoryDealSelect(deal))
     { pos_id = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID); fill = HistoryDealGetDouble(deal, DEAL_PRICE); }
   if(pos_id == 0) pos_id = g_trade.ResultOrder();
   int n = ArraySize(g_tr);
   ArrayResize(g_tr, n + 1, 128);
   g_tr[n].id = id; g_tr[n].pos_id = pos_id; g_tr[n].d = d; g_tr[n].t_sig = t_sig; g_tr[n].t_open = TimeCurrent();
   g_tr[n].planned = iOpen(g_sym, PERIOD_M15, 0); g_tr[n].fill = fill; g_tr[n].sl = sl; g_tr[n].tp = tp;
   g_tr[n].atr = atr; g_tr[n].vol = vol; g_tr[n].bars = 0;
   g_tr[n].risk_money = tick_size > 0 ? MathAbs(fill - sl) / tick_size * tick_val * vol : 0.0;
   g_tr[n].spread_pts = (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
   g_tr[n].open = true; g_tr[n].timeout_sent = false;
  }

void UpdateTrades(void)
  {
   for(int n = 0; n < ArraySize(g_tr); n++)
     {
      if(!g_tr[n].open) continue;
      g_tr[n].bars++;
      if(g_tr[n].bars < HZ || g_tr[n].timeout_sent) continue;
      if(!PositionSelectByTicket(g_tr[n].pos_id)) { Finalize(n); continue; }
      g_tr[n].timeout_sent = true;
      if(!g_trade.PositionClose(g_tr[n].pos_id))
        { g_tr[n].timeout_sent = false; XLog(StringFormat("error;%s;clôture à l'horizon refusée %u", g_tr[n].id, g_trade.ResultRetcode())); }
     }
  }

void Finalize(const int n)
  {
   if(!HistorySelectByPosition(g_tr[n].pos_id)) return;
   double profit = 0, comm = 0, swap = 0, fee = 0, px = 0;
   datetime ct = 0;
   string reason = "other";
   for(int k = 0; k < HistoryDealsTotal(); k++)
     {
      ulong tk = HistoryDealGetTicket(k);
      if(tk == 0) continue;
      profit += HistoryDealGetDouble(tk, DEAL_PROFIT); comm += HistoryDealGetDouble(tk, DEAL_COMMISSION);
      swap += HistoryDealGetDouble(tk, DEAL_SWAP); fee += HistoryDealGetDouble(tk, DEAL_FEE);
      ENUM_DEAL_ENTRY en = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY);
      if(en == DEAL_ENTRY_OUT || en == DEAL_ENTRY_OUT_BY)
        {
         px = HistoryDealGetDouble(tk, DEAL_PRICE); ct = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
         ENUM_DEAL_REASON rs = (ENUM_DEAL_REASON)HistoryDealGetInteger(tk, DEAL_REASON);
         reason = rs == DEAL_REASON_SL ? "sl" : rs == DEAL_REASON_TP ? "tp" : rs == DEAL_REASON_SO ? "stop_out" :
                  rs == DEAL_REASON_EXPERT ? (g_tr[n].timeout_sent ? "timeout" : "expert") : "manual_or_other";
        }
     }
   int d = g_tr[n].d;
   double risk = MathAbs(g_tr[n].fill - g_tr[n].sl);
   double net = profit + comm + swap + fee;
   MqlDateTime dt; TimeToStruct(g_tr[n].t_sig, dt);
   FileWriteString(g_fh_tr, StringFormat("%s,%s,%s,%d,%d,%s,%s,%s,%s,%s,%s,%s,%.2f,%.2f,%d,%s,%s,%s,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%s\n",
                   g_tr[n].id, IntegerToString((long)g_tr[n].pos_id), Ts(g_tr[n].t_sig), dt.year, d, Ts(g_tr[n].t_open),
                   Fx(g_tr[n].planned, 3), Fx(g_tr[n].fill, 3),
                   Fx(g_tr[n].atr > 0 ? (g_tr[n].fill - g_tr[n].planned) * d / g_tr[n].atr : 0.0),
                   Fx(g_tr[n].sl, 3), Fx(g_tr[n].tp, 3), Fx(g_tr[n].atr, 3), g_tr[n].vol, g_tr[n].risk_money,
                   (int)g_tr[n].spread_pts, Ts(ct), Fx(px, 3), reason,
                   Fx(risk > 0 ? (px - g_tr[n].fill) * d / risk : 0.0), profit, comm, swap, fee, net,
                   Fx(g_tr[n].risk_money > 0 ? net / g_tr[n].risk_money : 0.0)));
   FileFlush(g_fh_tr);
   g_tr[n].open = false;
  }

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &req, const MqlTradeResult &res)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD || !HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   ENUM_DEAL_ENTRY en = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(en != DEAL_ENTRY_OUT && en != DEAL_ENTRY_OUT_BY) return;
   ulong pid = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   if(PositionSelectByTicket(pid)) return;
   for(int n = 0; n < ArraySize(g_tr); n++)
      if(g_tr[n].open && g_tr[n].pos_id == pid) { Finalize(n); break; }
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   int done = 0; double s = 0;
   for(int n = 0; n < ArraySize(g_sh); n++)
      if(g_sh[n].done) { done++; for(int k = 0; k < NTP; k++) if(MathAbs(g_tps[k] - MAIN_TP) < 1e-9) s += g_sh[n].r[k] - RESEARCH_COST / g_sh[n].atr; }
   XLog(StringFormat("summary;signals=%d;shadow_done=%d;mean_net_R_TP2=%.4f;final_balance=%.2f",
                    g_nsig, done, done > 0 ? s / done : 0.0, AccountInfoDouble(ACCOUNT_BALANCE)));
   if(g_fh_ctx != INVALID_HANDLE) FileClose(g_fh_ctx);
   if(g_fh_sh != INVALID_HANDLE) FileClose(g_fh_sh);
   if(g_fh_tr != INVALID_HANDLE) FileClose(g_fh_tr);
   if(g_fh_log != INVALID_HANDLE) FileClose(g_fh_log);
  }

double OnTester()
  {
   int done = 0; double s = 0;
   for(int n = 0; n < ArraySize(g_sh); n++)
      if(g_sh[n].done) { done++; s += g_sh[n].r[2] - RESEARCH_COST / g_sh[n].atr; }
   return done > 0 ? s / done : 0.0;
  }
//+------------------------------------------------------------------+
