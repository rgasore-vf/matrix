//+------------------------------------------------------------------+
//| ASYM_Vault.mq5                                                   |
//| Test du coffre-fort (mars 2022 -> aujourd'hui) des candidats     |
//| FIGÉS de docs/ASYM_RESEARCH.md §5. Aucun paramètre de stratégie  |
//| n'est réglable : seules l'exécution et la journalisation le sont.|
//|                                                                  |
//|  A : H4, amplitude des 20 bougies précédentes <= 4 ATR, bougie   |
//|      de signal >= 2 ATR, suivre son sens ; SL 1 ATR ; TP 2 R.    |
//|  B : même règle, TP 3 R.                                         |
//|  C : D1, BOS (continuation ou changement) lu à l'envers ;        |
//|      SL 1 ATR ; TP 3 R.                                          |
//|  Entrée à l'ouverture de la bougie suivante ; sortie à l'horizon |
//|  (96 bougies H4, 20 bougies D1) si ni SL ni TP.                  |
//|  ATR : Wilder 14 du moteur SMV (identique au moteur Python).     |
//|                                                                  |
//| Deux mesures, journalisées séparément :                          |
//|  - « shadow » : simulation bougie par bougie avec EXACTEMENT les  |
//|    règles de la recherche (stop prioritaire dans la même bougie, |
//|    gap au-delà du stop compté à l'ouverture, R pour TP 1 à 4) ;  |
//|    comparable directement aux chiffres de développement ;        |
//|  - « trades » : exécution réelle du testeur (écart, glissement,  |
//|    commission, swap), en R prix et en R monétaire.               |
//| Fichiers : MQL5/Files (dossier commun) /ASYM/*.csv               |
//+------------------------------------------------------------------+
#property copyright   "smv_indicator"
#property version     "1.10"
#property description "Coffre-fort ASYM : candidats figés A, B, C avec journal CSV (shadow + exécution réelle)."

#include <Trade/Trade.mqh>
#include <SMV/Structure.mqh>

//+------------------------------------------------------------------+
//| Noyau minimal : ATR de Wilder, pivots et structure seulement.    |
//| La structure SMV ne dépend que du contexte et des pivots (même   |
//| chose dans smv/structure.py) : les BOS sont identiques à ceux du |
//| moteur complet. v1.10 : le moteur complet (zones, liquidités,    |
//| consolidations, signatures) provoquait une violation d'accès en  |
//| testeur et n'est d'aucune utilité pour A, B et C.                |
//+------------------------------------------------------------------+
class CAsymCore
  {
public:
   SmvConfig         cfg;
   CSmvContext       ctx;
   CSmvPivots        pivots;
   CSmvStructure     structure;
   CSmvLog           log;            // événements de la DERNIÈRE bougie seulement
   bool              with_structure;

   void              Init(const SmvConfig &c, const bool ws)
     {
      cfg = c;
      ctx.Init(cfg.atr_len);
      pivots.Reset();
      structure.Reset();
      log.Reset();
      with_structure = ws;
     }

   int               Count(void) const { return ctx.n; }

   bool              OnBar(const SmvBar &bar)
     {
      if(!ctx.Append(bar)) return false;
      log.Reset();
      if(!with_structure) return true;
      SmvPivot newp[];
      int nnew = pivots.Update(bar.index, cfg, ctx, log, newp);
      structure.Update(bar.index, newp, nnew, cfg, ctx, pivots, log);
      return true;
     }
  };

enum ENUM_ASYM_STRAT
  {
   ASYM_B_H4_EXPANSION_3R = 0,   // B : expansion H4, TP 3R
   ASYM_C_D1_BOSFADE_3R   = 1,   // C : BOS D1 lu à l'envers, TP 3R
   ASYM_A_H4_EXPANSION_2R = 2    // A : expansion H4, TP 2R
  };

input group "=== Stratégie (règles figées, non réglables) ==="
input ENUM_ASYM_STRAT InpStrategy     = ASYM_B_H4_EXPANSION_3R; // Candidat

input group "=== Instrument ==="
input string   InpSymbol       = "";       // Symbole (vide = symbole du graphique)
input string   InpSymbolList   = "EURUSD,GBPUSD,AUDUSD,USDCAD,USDCHF,EURGBP,EURCHF,USDJPY,EURJPY,GBPJPY,AUDJPY,XAUUSD"; // Liste pour l'optimisation
input int      InpSymbolIdx    = -1;       // Indice dans la liste (-1 = ignorer ; 0..11 pour optimiser)
input string   InpSymbolSuffix = "";       // Suffixe du courtier (ex. ".m", "pro")

input group "=== Exécution ==="
input bool     InpTrade        = true;     // Exécuter réellement (sinon shadow seulement)
input datetime InpTradeFrom    = D'2022.03.01 00:00'; // Signaux pris à partir de (avant : chauffe)
input double   InpRiskPct      = 1.0;      // Risque par trade en % du solde (si lots fixes = 0)
input double   InpFixedLots    = 0.0;      // Lots fixes (0 = risque en %)
input bool     InpAllowOverlap = true;     // Plusieurs positions simultanées (comme la recherche ; compte hedging)
input int      InpDeviationPts = 30;       // Glissement maximal accepté (points)
input long     InpMagic        = 2610022;  // Numéro magique

input group "=== Historique et journal ==="
input int      InpHistoryBars  = 3000;     // Bougies d'historique chargées au départ (chauffe ATR/structure)
input string   InpLogTag       = "";       // Étiquette ajoutée aux noms de fichiers

//--- géométrie figée
#define ASYM_NTP 6
double         g_tps[ASYM_NTP] = {1.0, 1.5, 2.0, 2.5, 3.0, 4.0};

//--- trade simulé selon les règles de la recherche
struct AsymShadow
  {
   string   id;
   int      sig;          // indice de la bougie de signal
   int      dir;
   double   atr;
   double   E;            // ouverture de sig+1
   bool     stopped;
   int      t_sl;         // bougie relative du stop (H+1 si aucun)
   double   sl_r;
   bool     hit[ASYM_NTP];
   double   r[ASYM_NTP];
   double   mfe;
   int      t_mfe;
   double   mae;
   double   comp_prev;
   double   range_atr;
   double   spread_r;
   datetime t_sig;
   bool     done;
  };

//--- trade réel
struct AsymTrade
  {
   string   id;
   ulong    pos_id;
   int      sig;
   int      dir;
   datetime t_sig;
   datetime t_open;
   double   planned;      // ouverture de la bougie d'entrée (bid)
   double   fill;
   double   sl;
   double   tp;
   double   atr;
   double   vol;
   double   risk_money;
   double   spread_pts;
   double   mfe;          // en R, bougies closes pendant la vie du trade
   double   mae;
   bool     open;
   bool     timeout_sent;
  };

CAsymCore      g_eng;
SmvConfig      g_cfg;
CTrade         g_trade;
AsymShadow     g_sh[];
AsymTrade      g_tr[];
string         g_sym;
string         g_name;
ENUM_TIMEFRAMES g_tf;
int            g_H;
int            g_warm;
double         g_tp;
datetime       g_last_fed = 0;     // ouverture de la dernière bougie close transmise
bool           g_ready = false;
bool           g_hedging = false;
int            g_fh_bar = INVALID_HANDLE, g_fh_sh = INVALID_HANDLE, g_fh_tr = INVALID_HANDLE, g_fh_sig = INVALID_HANDLE, g_fh_log = INVALID_HANDLE;
string         g_prefix;
int            g_nsig = 0;
double         g_research_cost = 0.0;

//+------------------------------------------------------------------+
//| Utilitaires                                                      |
//+------------------------------------------------------------------+
string Fx(const double v, const int dg = 5) { return DoubleToString(v, dg); }
string Ts(const datetime t) { return TimeToString(t, TIME_DATE | TIME_MINUTES); }

void AsymLog(const string what)
  {
   if(g_fh_log != INVALID_HANDLE)
     {
      FileWriteString(g_fh_log, Ts(TimeCurrent()) + "," + what + "\n");
      FileFlush(g_fh_log);
     }
   Print("ASYM: ", what);
  }

int OpenCsv(const string kind, const string header)
  {
   string f = g_prefix + "_" + kind + ".csv";
   int h = FileOpen(f, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("ASYM: impossible d'ouvrir %s (erreur %d)", f, GetLastError());
      return h;
     }
   FileWriteString(h, header + "\n");
   FileFlush(h);
   return h;
  }

//--- coût nominal de la recherche (research/setup_dataset.py COST), en prix
double ResearchCost(const string sym)
  {
   string s = sym;
   StringToUpper(s);
   string base = StringSubstr(s, 0, 6);
   if(base == "EURUSD") return 0.00010;
   if(base == "GBPUSD") return 0.00012;
   if(base == "AUDUSD") return 0.00012;
   if(base == "USDCAD") return 0.00015;
   if(base == "USDCHF") return 0.00015;
   if(base == "EURGBP") return 0.00015;
   if(base == "EURCHF") return 0.00020;
   if(base == "USDJPY") return 0.012;
   if(base == "EURJPY") return 0.015;
   if(base == "GBPJPY") return 0.025;
   if(base == "AUDJPY") return 0.020;
   if(base == "XAUUSD") return 0.35;
   return 0.0;
  }

string PickSymbol(void)
  {
   if(InpSymbolIdx >= 0)
     {
      string parts[];
      int n = StringSplit(InpSymbolList, ',', parts);
      if(InpSymbolIdx < n)
        {
         string s = parts[InpSymbolIdx];
         StringTrimLeft(s);
         StringTrimRight(s);
         return s + InpSymbolSuffix;
        }
      return "";
     }
   if(StringLen(InpSymbol) > 0) return InpSymbol + InpSymbolSuffix;
   return _Symbol;
  }

//+------------------------------------------------------------------+
//| Initialisation                                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   g_sym = PickSymbol();
   if(g_sym == "" || !SymbolSelect(g_sym, true))
     {
      Print("ASYM: symbole introuvable : ", g_sym);
      return INIT_PARAMETERS_INCORRECT;
     }
   switch(InpStrategy)
     {
      case ASYM_C_D1_BOSFADE_3R:   g_name = "C_D1_BOSFADE_3R";   g_tf = PERIOD_D1; g_H = 20; g_warm = 120; g_tp = 3.0; break;
      case ASYM_A_H4_EXPANSION_2R: g_name = "A_H4_EXPANSION_2R"; g_tf = PERIOD_H4; g_H = 96; g_warm = 600; g_tp = 2.0; break;
      default:                     g_name = "B_H4_EXPANSION_3R"; g_tf = PERIOD_H4; g_H = 96; g_warm = 600; g_tp = 3.0; break;
     }
   if(PeriodSeconds(_Period) > PeriodSeconds(g_tf))
     {
      // en mode « prix d'ouverture », le testeur refuse les UT inférieures à celle du graphique
      PrintFormat("ASYM: lancer %s sur un graphique %s ou inférieur (graphique actuel : %s)",
                  g_name, EnumToString(g_tf), EnumToString(_Period));
      return INIT_PARAMETERS_INCORRECT;
     }
   if(InpHistoryBars < g_warm + 1)
     {
      PrintFormat("ASYM: InpHistoryBars doit dépasser %d", g_warm);
      return INIT_PARAMETERS_INCORRECT;
     }
   SmvConfigDefaults(g_cfg);
   g_cfg.zones_on = "bos_origin";      // comme build_matrix2.py
   g_cfg.enable_setups = false;        // sans effet sur la structure ; inutile ici
   string err;
   if(!SmvConfigValid(g_cfg, err))
     {
      Print("ASYM: configuration SMV invalide : ", err);
      return INIT_PARAMETERS_INCORRECT;
     }
   g_eng.Init(g_cfg, g_tf == PERIOD_D1);   // structure seulement pour C
   g_hedging = (ENUM_ACCOUNT_MARGIN_MODE)AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING;
   g_research_cost = ResearchCost(g_sym);

   MqlDateTime now;
   TimeToStruct(TimeLocal(), now);
   string stamp = StringFormat("%04d%02d%02d_%02d%02d%02d", now.year, now.mon, now.day, now.hour, now.min, now.sec);
   string tag = StringLen(InpLogTag) > 0 ? "_" + InpLogTag : "";
   FolderCreate("ASYM", FILE_COMMON);
   g_prefix = "ASYM\\" + g_name + "_" + g_sym + tag + "_" + stamp;

   g_fh_log = OpenCsv("log", "time_srv,message");
   g_fh_sig = OpenCsv("signals",
                      "id,strategy,symbol,tf,sig_time_srv,sig_index,year,dir,atr,open,high,low,close,comp20_prev_atr,range_atr,body_atr,"
                      "spread_pts,spread_R,research_cost_R,action");
   g_fh_sh = OpenCsv("shadow",
                     "id,strategy,symbol,tf,sig_time_srv,year,dir,atr,entry_E,r_1,r_1.5,r_2,r_2.5,r_3,r_4,"
                     "r_main,mfe_R,t_mfe,mae_R,t_sl,comp20_prev_atr,range_atr,spread_R_at_signal,research_cost_R");
   g_fh_tr = OpenCsv("trades",
                     "id,strategy,symbol,pos_id,sig_time_srv,year,dir,open_time,planned_E,fill,slip_R,sl,tp,atr,volume,"
                     "risk_money,risk_pct_balance,spread_pts_entry,close_time,close_price,exit_reason,bars_held,"
                     "R_price,profit,commission,swap,fee,net_money,R_money,mfe_R,mae_R");
   g_fh_bar = OpenCsv("bars", "index,time_srv,open,high,low,close,atr,live");
   if(g_fh_bar == INVALID_HANDLE || g_fh_log == INVALID_HANDLE || g_fh_sig == INVALID_HANDLE || g_fh_sh == INVALID_HANDLE || g_fh_tr == INVALID_HANDLE)
      return INIT_FAILED;

   AsymLog(StringFormat("start;strategy=%s;symbol=%s;tf=%s;H=%d;tp=%.1f;warm=%d;trade=%s;risk_pct=%.2f;fixed_lots=%.2f;overlap=%s;hedging=%s",
                    g_name, g_sym, EnumToString(g_tf), g_H, g_tp, g_warm, InpTrade ? "yes" : "no", InpRiskPct, InpFixedLots,
                    InpAllowOverlap ? "yes" : "no", g_hedging ? "yes" : "no"));
   AsymLog(StringFormat("account;server=%s;company=%s;currency=%s;balance=%.2f;leverage=%d",
                    AccountInfoString(ACCOUNT_SERVER), AccountInfoString(ACCOUNT_COMPANY),
                    AccountInfoString(ACCOUNT_CURRENCY), AccountInfoDouble(ACCOUNT_BALANCE),
                    (int)AccountInfoInteger(ACCOUNT_LEVERAGE)));
   AsymLog(StringFormat("symbol;digits=%d;point=%g;contract=%g;tick_size=%g;tick_value=%g;vol_min=%g;vol_step=%g;stops_level=%d;spread_float=%s;research_cost=%g",
                    (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS), SymbolInfoDouble(g_sym, SYMBOL_POINT),
                    SymbolInfoDouble(g_sym, SYMBOL_TRADE_CONTRACT_SIZE), SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE),
                    SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE), SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN),
                    SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP), (int)SymbolInfoInteger(g_sym, SYMBOL_TRADE_STOPS_LEVEL),
                    SymbolInfoInteger(g_sym, SYMBOL_SPREAD_FLOAT) != 0 ? "yes" : "no", g_research_cost));
   if(g_research_cost == 0.0)
      AsymLog("warning;symbole hors de l'univers de recherche : research_cost_R = 0");
   if(InpTrade && InpAllowOverlap && !g_hedging)
      AsymLog("warning;compte en netting : les positions simultanées sont impossibles, les signaux qui se chevauchent seront ignorés en réel (le shadow les garde)");

   g_trade.SetExpertMagicNumber((ulong)InpMagic);
   g_trade.SetDeviationInPoints((ulong)InpDeviationPts);
   g_trade.SetTypeFillingBySymbol(g_sym);
   EventSetTimer(60);
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
//| Chargement des bougies closes                                    |
//+------------------------------------------------------------------+
bool FeedBar(const MqlRates &r, const bool live)
  {
   SmvBar b;
   b.index = g_eng.Count();
   b.t_srv = r.time;
   b.t_open = r.time;                                  // heure serveur : sans effet sur A, B, C
   b.t_close = r.time + PeriodSeconds(g_tf);
   b.open = r.open; b.high = r.high; b.low = r.low; b.close = r.close;
   if(g_eng.Count() > 0)
     {
      MqlDateTime dt;
      TimeToStruct(r.time, dt);
      static bool sunday_warned = false;
      if(g_tf == PERIOD_D1 && dt.day_of_week == 0 && !sunday_warned)
        {
         sunday_warned = true;
         AsymLog("warning;bougie D1 du dimanche " + Ts(r.time) + " : les données de recherche n'en avaient pas (ATR et structure différents)");
        }
     }
   if(!g_eng.OnBar(b))
     {
      AsymLog("error;bougie refusée par le moteur " + Ts(r.time));
      return false;
     }
   g_last_fed = r.time;
   // bougies transmises au moteur, pour la vérification de parité avec Python
   FileWriteString(g_fh_bar, StringFormat("%d,%s,%s,%s,%s,%s,%s,%d\n", b.index, TimeToString(r.time, TIME_DATE | TIME_MINUTES),
                   Fx(r.open, 6), Fx(r.high, 6), Fx(r.low, 6), Fx(r.close, 6), Fx(g_eng.ctx.atr[b.index], 7), live ? 1 : 0));
   if(live) OnClosedBar(b.index);
   return true;
  }

void Process(void)
  {
   datetime cur = iTime(g_sym, g_tf, 0);
   if(cur <= 0) return;
   if(!g_ready)
     {
      MqlRates rr[];
      ArraySetAsSeries(rr, false);
      int got = CopyRates(g_sym, g_tf, 1, InpHistoryBars, rr);
      if(got <= 0) return;                             // historique pas encore prêt
      if(got < g_warm + 1)
        {
         static datetime warned = 0;
         if(warned != cur) { AsymLog(StringFormat("warning;historique insuffisant (%d bougies, %d requises) : avancer la date de départ du testeur", got, g_warm + 1)); warned = cur; }
         return;
        }
      for(int k = 0; k < got; k++)
         if(!FeedBar(rr[k], false)) { ExpertRemove(); return; }
      g_ready = true;
      AsymLog(StringFormat("ready;bougies=%d;premiere=%s;derniere=%s", got, Ts(rr[0].time), Ts(rr[got - 1].time)));
      return;
     }
   if(cur <= g_last_fed) return;
   MqlRates nr[];
   ArraySetAsSeries(nr, false);
   int got = CopyRates(g_sym, g_tf, g_last_fed + 1, cur - 1, nr);
   if(got < 0) return;
   for(int k = 0; k < got; k++)
     {
      if(nr[k].time <= g_last_fed || nr[k].time >= cur) continue;
      if(!FeedBar(nr[k], true)) { ExpertRemove(); return; }
     }
  }

void OnTick()  { Process(); }
void OnTimer() { Process(); }

//+------------------------------------------------------------------+
//| Bougie i close (temps réel ou testeur)                           |
//+------------------------------------------------------------------+
void OnClosedBar(const int i)
  {
   UpdateShadows(i);
   UpdateTrades(i);
   if(i < g_warm) return;
   SmvBar b = g_eng.ctx.bars[i];
   if(b.t_srv < InpTradeFrom) return;
   const double atr = g_eng.ctx.atr[i];
   if(atr <= 0.0) return;
   bool want[2] = {false, false};                     // [0] = achat, [1] = vente
   double comp_prev = EMPTY_VALUE;
   if(g_tf == PERIOD_H4)
     {
      double hi, lo; int ih, il;
      g_eng.ctx.Highest(i - 20, i - 1, hi, ih);
      g_eng.ctx.Lowest(i - 20, i - 1, lo, il);
      comp_prev = (hi - lo) / atr;
      double rng = (b.high - b.low) / atr;
      // volx : comp <= 4 ATR, bougie >= 1,5 ATR, C != O ; candidat : bougie >= 2 ATR
      if(comp_prev <= 4.0 && (b.high - b.low) >= 1.5 * atr && b.close != b.open && rng >= 2.0)
         want[b.close > b.open ? 0 : 1] = true;
     }
   else
     {
      for(int k = 0; k < g_eng.log.count; k++)
        {
         string kind = g_eng.log.ev[k].kind;
         int d = g_eng.log.ev[k].dir;
         if((kind == K_BOS_CONTINUATION || kind == K_BOS_CHANGE) && (d == 1 || d == -1))
            want[d == 1 ? 1 : 0] = true;               // lu à l'envers
        }
     }
   for(int s = 0; s < 2; s++)
      if(want[s]) NewSignal(i, s == 0 ? 1 : -1, atr, comp_prev);
  }

//+------------------------------------------------------------------+
//| Signal : journal, shadow, ordre                                  |
//+------------------------------------------------------------------+
void NewSignal(const int i, const int d, const double atr, const double comp_prev)
  {
   SmvBar b = g_eng.ctx.bars[i];
   g_nsig++;
   string id = StringFormat("%s_%s_%d", g_sym, TimeToString(b.t_srv, TIME_DATE | TIME_MINUTES), d);
   StringReplace(id, " ", "_");
   StringReplace(id, ":", "");
   StringReplace(id, ".", "");
   double point = SymbolInfoDouble(g_sym, SYMBOL_POINT);
   long spread_pts = SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
   double spread_r = spread_pts * point / atr;
   double rng = (b.high - b.low) / atr;
   MqlDateTime dt;
   TimeToStruct(b.t_srv, dt);

   int n = ArraySize(g_sh);
   ArrayResize(g_sh, n + 1, 256);
   g_sh[n].id = id; g_sh[n].sig = i; g_sh[n].dir = d; g_sh[n].atr = atr; g_sh[n].E = 0.0;
   g_sh[n].stopped = false; g_sh[n].t_sl = g_H + 1; g_sh[n].sl_r = -1.0;
   for(int k = 0; k < ASYM_NTP; k++) { g_sh[n].hit[k] = false; g_sh[n].r[k] = 0.0; }
   g_sh[n].mfe = -DBL_MAX; g_sh[n].t_mfe = 0; g_sh[n].mae = -DBL_MAX;
   g_sh[n].comp_prev = comp_prev; g_sh[n].range_atr = rng; g_sh[n].spread_r = spread_r;
   g_sh[n].t_sig = b.t_srv; g_sh[n].done = false;

   string action = InpTrade ? OpenTrade(id, i, d, atr, b.t_srv) : "shadow_only";
   string cp = comp_prev == EMPTY_VALUE ? "" : Fx(comp_prev, 3);
   FileWriteString(g_fh_sig, StringFormat("%s,%s,%s,%s,%s,%d,%d,%d,%s,%s,%s,%s,%s,%s,%s,%s,%d,%s,%s,%s\n",
                   id, g_name, g_sym, EnumToString(g_tf), Ts(b.t_srv), i, dt.year, d, Fx(atr, 6),
                   Fx(b.open, 6), Fx(b.high, 6), Fx(b.low, 6), Fx(b.close, 6), cp, Fx(rng, 3),
                   Fx((b.close - b.open) * d / atr, 3), (int)spread_pts, Fx(spread_r, 4),
                   Fx(g_research_cost / atr, 4), action));
   FileFlush(g_fh_sig);
  }

int OpenCount(void)
  {
   int c = 0;
   for(int k = 0; k < ArraySize(g_tr); k++) if(g_tr[k].open) c++;
   return c;
  }

string OpenTrade(const string id, const int i, const int d, const double atr, const datetime t_sig)
  {
   if(OpenCount() > 0 && (!InpAllowOverlap || !g_hedging))
     {
      AsymLog("skip;" + id + ";position déjà ouverte (chevauchement interdit ou compte netting)");
      return "skipped_overlap";
     }
   MqlTick tk;
   if(!SymbolInfoTick(g_sym, tk)) { AsymLog("error;" + id + ";pas de cotation"); return "error_tick"; }
   int digits = (int)SymbolInfoInteger(g_sym, SYMBOL_DIGITS);
   double px = d == 1 ? tk.ask : tk.bid;
   double sl = NormalizeDouble(px - d * atr, digits);
   double tp = NormalizeDouble(px + d * g_tp * atr, digits);
   //--- taille
   double tick_size = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_SIZE);
   double tick_val = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tick_val <= 0.0) tick_val = SymbolInfoDouble(g_sym, SYMBOL_TRADE_TICK_VALUE);
   double vmin = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(g_sym, SYMBOL_VOLUME_STEP);
   double money_per_lot = tick_size > 0.0 ? atr / tick_size * tick_val : 0.0;
   double vol = InpFixedLots;
   if(vol <= 0.0)
     {
      double risk = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0;
      vol = money_per_lot > 0.0 ? risk / money_per_lot : 0.0;
     }
   vol = MathFloor(vol / vstep + 1e-9) * vstep;
   if(vol < vmin)
     {
      AsymLog(StringFormat("warning;%s;volume calculé < minimum, %.2f lot utilisé (risque réel plus élevé que prévu)", id, vmin));
      vol = vmin;
     }
   if(vol > vmax) vol = vmax;
   vol = NormalizeDouble(vol, 8);
   bool ok = d == 1 ? g_trade.Buy(vol, g_sym, 0.0, sl, tp, id) : g_trade.Sell(vol, g_sym, 0.0, sl, tp, id);
   uint rc = g_trade.ResultRetcode();
   if(!ok || (rc != TRADE_RETCODE_DONE && rc != TRADE_RETCODE_PLACED && rc != TRADE_RETCODE_DONE_PARTIAL))
     {
      AsymLog(StringFormat("error;%s;ordre refusé retcode=%u %s", id, rc, g_trade.ResultRetcodeDescription()));
      return "error_order_" + IntegerToString((int)rc);
     }
   ulong deal = g_trade.ResultDeal();
   double fill = g_trade.ResultPrice();
   ulong pos_id = 0;
   if(deal > 0 && HistoryDealSelect(deal))
     {
      pos_id = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
      fill = HistoryDealGetDouble(deal, DEAL_PRICE);
     }
   if(pos_id == 0) pos_id = g_trade.ResultOrder();
   int n = ArraySize(g_tr);
   ArrayResize(g_tr, n + 1, 256);
   g_tr[n].id = id; g_tr[n].pos_id = pos_id; g_tr[n].sig = i; g_tr[n].dir = d; g_tr[n].t_sig = t_sig;
   g_tr[n].t_open = TimeCurrent(); g_tr[n].planned = iOpen(g_sym, g_tf, 0); g_tr[n].fill = fill;
   g_tr[n].sl = sl; g_tr[n].tp = tp; g_tr[n].atr = atr; g_tr[n].vol = vol;
   g_tr[n].risk_money = tick_size > 0.0 ? MathAbs(fill - sl) / tick_size * tick_val * vol : 0.0;
   g_tr[n].spread_pts = (double)SymbolInfoInteger(g_sym, SYMBOL_SPREAD);
   g_tr[n].mfe = 0.0; g_tr[n].mae = 0.0; g_tr[n].open = true; g_tr[n].timeout_sent = false;
   return StringFormat("opened_%.2f", vol);
  }

//+------------------------------------------------------------------+
//| Shadow : règles exactes de build_matrix2.outcomes()              |
//+------------------------------------------------------------------+
void UpdateShadows(const int j)
  {
   SmvBar b = g_eng.ctx.bars[j];
   for(int n = 0; n < ArraySize(g_sh); n++)
     {
      if(g_sh[n].done) continue;
      int rel = j - (g_sh[n].sig + 1);
      if(rel < 0) continue;
      int d = g_sh[n].dir;
      double risk = g_sh[n].atr;
      if(rel == 0) g_sh[n].E = b.open;
      double E = g_sh[n].E;
      double fav = (d == 1 ? b.high - E : E - b.low) / risk;
      double adv = (d == 1 ? E - b.low : b.high - E) / risk;
      bool was_stopped = g_sh[n].stopped;
      if(!was_stopped)
        {
         if(fav > g_sh[n].mfe) { g_sh[n].mfe = fav; g_sh[n].t_mfe = rel; }   // MFE jusqu'à la bougie du stop incluse
         if(adv >= 1.0)
           {
            g_sh[n].stopped = true;
            g_sh[n].t_sl = rel;
            double gap = rel > 0 ? (d == 1 ? E - b.open : b.open - E) / risk : 0.0;
            g_sh[n].sl_r = -MathMax(1.0, gap);
           }
         else
            for(int k = 0; k < ASYM_NTP; k++)
               if(!g_sh[n].hit[k] && fav >= g_tps[k]) { g_sh[n].hit[k] = true; g_sh[n].r[k] = g_tps[k]; }
        }
      if(adv > g_sh[n].mae) g_sh[n].mae = adv;                                // MAE sur tout l'horizon
      if(rel == g_H - 1)
        {
         for(int k = 0; k < ASYM_NTP; k++)
            if(!g_sh[n].hit[k])
               g_sh[n].r[k] = g_sh[n].stopped ? g_sh[n].sl_r : (b.close - E) * d / risk;
         g_sh[n].done = true;
         WriteShadow(n);
        }
     }
  }

double MainR(const int n)
  {
   for(int k = 0; k < ASYM_NTP; k++) if(MathAbs(g_tps[k] - g_tp) < 1e-9) return g_sh[n].r[k];
   return 0.0;
  }

void WriteShadow(const int n)
  {
   MqlDateTime dt;
   TimeToStruct(g_sh[n].t_sig, dt);
   string cp = g_sh[n].comp_prev == EMPTY_VALUE ? "" : Fx(g_sh[n].comp_prev, 3);
   string rs = "";
   for(int k = 0; k < ASYM_NTP; k++) rs += Fx(g_sh[n].r[k], 4) + ",";
   FileWriteString(g_fh_sh, StringFormat("%s,%s,%s,%s,%s,%d,%d,%s,%s,%s%s,%s,%d,%s,%d,%s,%s,%s,%s\n",
                   g_sh[n].id, g_name, g_sym, EnumToString(g_tf), Ts(g_sh[n].t_sig), dt.year, g_sh[n].dir,
                   Fx(g_sh[n].atr, 6), Fx(g_sh[n].E, 6), rs, Fx(MainR(n), 4), Fx(g_sh[n].mfe, 3), g_sh[n].t_mfe,
                   Fx(g_sh[n].mae, 3), g_sh[n].t_sl, cp, Fx(g_sh[n].range_atr, 3), Fx(g_sh[n].spread_r, 4),
                   Fx(g_research_cost / g_sh[n].atr, 4)));
   FileFlush(g_fh_sh);
  }

//+------------------------------------------------------------------+
//| Trades réels : MFE/MAE, sortie à l'horizon                       |
//+------------------------------------------------------------------+
void UpdateTrades(const int j)
  {
   SmvBar b = g_eng.ctx.bars[j];
   for(int n = 0; n < ArraySize(g_tr); n++)
     {
      if(!g_tr[n].open) continue;
      if(j <= g_tr[n].sig) continue;
      int d = g_tr[n].dir;
      double risk = MathAbs(g_tr[n].fill - g_tr[n].sl);
      if(risk <= 0.0) risk = g_tr[n].atr;
      double fav = (d == 1 ? b.high - g_tr[n].fill : g_tr[n].fill - b.low) / risk;
      double adv = (d == 1 ? g_tr[n].fill - b.low : b.high - g_tr[n].fill) / risk;
      if(fav > g_tr[n].mfe) g_tr[n].mfe = fav;
      if(adv > g_tr[n].mae) g_tr[n].mae = adv;
      // la recherche sort à la clôture de la bougie sig+H, donc à l'ouverture de sig+H+1
      if(j >= g_tr[n].sig + g_H && !g_tr[n].timeout_sent)
        {
         if(!PositionSelectByTicket(g_tr[n].pos_id))
           {
            FinalizeTrade(n);                          // clôture non notifiée (SL/TP manqué par la transaction)
            continue;
           }
           {
            g_tr[n].timeout_sent = true;
            if(!g_trade.PositionClose(g_tr[n].pos_id))
              {
               g_tr[n].timeout_sent = false;
               AsymLog(StringFormat("error;%s;clôture à l'horizon refusée retcode=%u", g_tr[n].id, g_trade.ResultRetcode()));
              }
           }
        }
     }
  }

void FinalizeTrade(const int n)
  {
   if(!HistorySelectByPosition(g_tr[n].pos_id)) return;
   double profit = 0, comm = 0, swap = 0, fee = 0, close_px = 0;
   datetime close_t = 0;
   string reason = "other";
   int deals = HistoryDealsTotal();
   for(int k = 0; k < deals; k++)
     {
      ulong tk = HistoryDealGetTicket(k);
      if(tk == 0) continue;
      profit += HistoryDealGetDouble(tk, DEAL_PROFIT);
      comm   += HistoryDealGetDouble(tk, DEAL_COMMISSION);
      swap   += HistoryDealGetDouble(tk, DEAL_SWAP);
      fee    += HistoryDealGetDouble(tk, DEAL_FEE);
      ENUM_DEAL_ENTRY en = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY);
      if(en == DEAL_ENTRY_OUT || en == DEAL_ENTRY_OUT_BY)
        {
         close_px = HistoryDealGetDouble(tk, DEAL_PRICE);
         close_t = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
         ENUM_DEAL_REASON rs = (ENUM_DEAL_REASON)HistoryDealGetInteger(tk, DEAL_REASON);
         if(rs == DEAL_REASON_SL) reason = "sl";
         else if(rs == DEAL_REASON_TP) reason = "tp";
         else if(rs == DEAL_REASON_SO) reason = "stop_out";
         else if(rs == DEAL_REASON_EXPERT) reason = g_tr[n].timeout_sent ? "timeout" : "expert";
         else reason = "manual_or_other";
        }
     }
   int d = g_tr[n].dir;
   double risk = MathAbs(g_tr[n].fill - g_tr[n].sl);
   double r_price = risk > 0.0 ? (close_px - g_tr[n].fill) * d / risk : 0.0;
   double net = profit + comm + swap + fee;
   double r_money = g_tr[n].risk_money > 0.0 ? net / g_tr[n].risk_money : 0.0;
   double slip_r = g_tr[n].atr > 0.0 ? (g_tr[n].fill - g_tr[n].planned) * d / g_tr[n].atr : 0.0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE) - net;
   int held = close_t > 0 ? Bars(g_sym, g_tf, g_tr[n].t_open, close_t) : 0;
   MqlDateTime dt;
   TimeToStruct(g_tr[n].t_sig, dt);
   FileWriteString(g_fh_tr, StringFormat("%s,%s,%s,%s,%s,%d,%d,%s,%s,%s,%s,%s,%s,%s,%.2f,%.2f,%.3f,%d,%s,%s,%s,%d,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%s,%s,%s\n",
                   g_tr[n].id, g_name, g_sym, IntegerToString((long)g_tr[n].pos_id), Ts(g_tr[n].t_sig), dt.year, d, Ts(g_tr[n].t_open),
                   Fx(g_tr[n].planned, 6), Fx(g_tr[n].fill, 6), Fx(slip_r, 4), Fx(g_tr[n].sl, 6), Fx(g_tr[n].tp, 6),
                   Fx(g_tr[n].atr, 6), g_tr[n].vol, g_tr[n].risk_money,
                   bal > 0 ? 100.0 * g_tr[n].risk_money / bal : 0.0, (int)g_tr[n].spread_pts,
                   Ts(close_t), Fx(close_px, 6), reason, held, Fx(r_price, 4), profit, comm, swap, fee, net,
                   Fx(r_money, 4), Fx(g_tr[n].mfe, 3), Fx(g_tr[n].mae, 3)));
   FileFlush(g_fh_tr);
   g_tr[n].open = false;
  }

void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &req, const MqlTradeResult &res)
  {
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetInteger(trans.deal, DEAL_MAGIC) != InpMagic) return;
   ENUM_DEAL_ENTRY en = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
   if(en != DEAL_ENTRY_OUT && en != DEAL_ENTRY_OUT_BY) return;
   ulong pid = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
   if(PositionSelectByTicket(pid)) return;            // clôture partielle : attendre la fin
   for(int n = 0; n < ArraySize(g_tr); n++)
      if(g_tr[n].open && g_tr[n].pos_id == pid) { FinalizeTrade(n); break; }
  }

//+------------------------------------------------------------------+
//| Fin : résumé                                                     |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   int ns = 0, pending = 0;
   double sum[ASYM_NTP];
   ArrayInitialize(sum, 0.0);
   double sum_cost = 0.0, sum_spread = 0.0;
   for(int n = 0; n < ArraySize(g_sh); n++)
     {
      if(!g_sh[n].done) { pending++; continue; }
      ns++;
      for(int k = 0; k < ASYM_NTP; k++) sum[k] += g_sh[n].r[k];
      sum_cost += g_research_cost / g_sh[n].atr;
      sum_spread += g_sh[n].spread_r;
     }
   string s = StringFormat("summary;signals=%d;shadow_done=%d;shadow_pending=%d", g_nsig, ns, pending);
   if(ns > 0)
     {
      for(int k = 0; k < ASYM_NTP; k++) s += StringFormat(";mean_r_%g=%.4f", g_tps[k], sum[k] / ns);
      s += StringFormat(";mean_research_cost_R=%.4f;mean_spread_R_signal=%.4f", sum_cost / ns, sum_spread / ns);
     }
   int open_left = OpenCount();
   s += StringFormat(";real_trades_open_at_end=%d;final_balance=%.2f", open_left, AccountInfoDouble(ACCOUNT_BALANCE));
   AsymLog(s);
   if(g_fh_bar != INVALID_HANDLE) FileClose(g_fh_bar);
   if(g_fh_log != INVALID_HANDLE) FileClose(g_fh_log);
   if(g_fh_sig != INVALID_HANDLE) FileClose(g_fh_sig);
   if(g_fh_sh != INVALID_HANDLE) FileClose(g_fh_sh);
   if(g_fh_tr != INVALID_HANDLE) FileClose(g_fh_tr);
  }

double OnTester()
  {
   int ns = 0;
   double sum = 0.0;
   for(int n = 0; n < ArraySize(g_sh); n++)
      if(g_sh[n].done) { ns++; sum += MainR(n) - g_research_cost / g_sh[n].atr; }
   return ns > 0 ? sum / ns : 0.0;                    // espérance nette shadow (coût de recherche) par trade
  }
//+------------------------------------------------------------------+
