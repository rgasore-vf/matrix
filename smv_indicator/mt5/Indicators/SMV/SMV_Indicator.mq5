//+------------------------------------------------------------------+
//| SMV_Indicator.mq5                                                |
//| Indicateur Smart Money Vision : portage MQL5 du moteur Python    |
//| smv_indicator (docs/STRATEGY_SPEC.md, docs/ARCHITECTURE.md).     |
//|                                                                  |
//| Contrat temporel :                                               |
//| - seules les bougies CLOSES sont transmises au moteur (la bougie |
//|   en formation, indice rates_total-1, n'est jamais lue) ;        |
//| - un événement n'est jamais modifié après sa confirmation ;      |
//| - l'UT supérieure n'est lue qu'à travers ses bougies closes      |
//|   (clôture nominale <= clôture de la bougie courante).           |
//|                                                                  |
//| Tampons (iCustom, fenêtre de données) : voir SMV_BUF_* plus bas. |
//| Validation : exporter le journal (InpExport) puis comparer avec  |
//| le moteur Python : python tools/mt5_parity.py <dossier>.         |
//+------------------------------------------------------------------+
#property copyright   "smv_indicator"
#property version     "0.20"
#property description "Structure, zones, liquidité, consolidations et setups SMV (bougies closes uniquement)."
#property indicator_chart_window
#property indicator_buffers 8
#property indicator_plots   8
#property indicator_type1 DRAW_NONE
#property indicator_label1 "SMV_Trend"
#property indicator_type2 DRAW_NONE
#property indicator_label2 "SMV_Protected"
#property indicator_type3 DRAW_NONE
#property indicator_label3 "SMV_SetupDir"
#property indicator_type4 DRAW_NONE
#property indicator_label4 "SMV_SetupEntry"
#property indicator_type5 DRAW_NONE
#property indicator_label5 "SMV_SetupStop"
#property indicator_type6 DRAW_NONE
#property indicator_label6 "SMV_SetupTarget"
#property indicator_type7 DRAW_NONE
#property indicator_label7 "SMV_HtfTrend"
#property indicator_type8 DRAW_NONE
#property indicator_label8 "SMV_BosTrap"

#include <SMV/Engine.mqh>
#include <SMV/Draw.mqh>

enum ENUM_SMV_MAJOR   { SMV_MAJOR_A = 0, SMV_MAJOR_B = 1 };
enum ENUM_SMV_PROX    { SMV_PROX_BODY = 0, SMV_PROX_WICK = 1 };
enum ENUM_SMV_ZONESON { SMV_ZONES_BOS = 0, SMV_ZONES_ALL = 1 };
enum ENUM_SMV_SESSION { SMV_SES_MEASURED = 0, SMV_SES_REPO = 1 };

input group "=== Moteur (valeurs par défaut : docs/CALIBRATION.md) ==="
input int              InpPivotLeft       = 2;                // Pivot : bougies à gauche (R-ST-02)
input int              InpPivotRight      = 2;                // Pivot : bougies à droite = retard de confirmation
input ENUM_SMV_MAJOR   InpMajorMode       = SMV_MAJOR_A;      // Niveau protégé : A = origine du dernier BOS (D-07)
input double           InpBosEps          = 0.0;              // Marge de cassure en prix (0 = clôture strictement au-delà)
input int              InpAtrLen          = 14;               // ATR de Wilder
input double           InpBmBodyMin       = 0.7;              // BM : corps / amplitude minimal (Q-02)
input double           InpBmRangeAtr      = 0.0;              // BM : amplitude minimale en ATR (0 = désactivé, Q-15)
input ENUM_SMV_PROX    InpZoneProximal    = SMV_PROX_BODY;    // Bord proximal : corps ou mèche de la BM (Q-03)
input ENUM_SMV_ZONESON InpZonesOn         = SMV_ZONES_BOS;    // Zones : origines des BOS ou tous les pivots (Q-04)
input double           InpEqTolAtr        = 0.1;              // EQH/EQL : tolérance en ATR (Q-07)
input int              InpEqMaxGap        = 500;              // EQH/EQL : écart maximal en bougies
input int              InpRangeAccept     = 3;                // Consolidation : clôtures hors bornes pour valider la sortie
input int              InpTestMaxBars     = 10;               // Golden entry : délai du test (Q-11)
input double           InpSlMaxAtr        = 2.5;              // Stop maximal en ATR (Q-12)
input int              InpSetupExpiry     = 100;              // Concept entry : durée de vie de l'ordre limite
input bool             InpEnableSetups    = true;             // Setups (repères, sans espérance démontrée)
input bool             InpEnableImbalance = false;            // FVG ICT (définition externe)
input bool             InpEnableSessions  = true;             // Heures de tir et fenêtre 26-9
input ENUM_SMV_SESSION InpSessionMode     = SMV_SES_MEASURED; // Heures : mesurées ou heures du dépôt (Q-10)

input group "=== Heure du serveur ==="
input ENUM_SMV_SERVER_TZ InpServerTz      = SMV_SRV_EET_EU;   // Fuseau du serveur (vérifier : script SMV_ServerTimeCheck)
input int              InpServerFixedHours = 2;               // Décalage fixe UTC+h (si mode fixe)

input group "=== Historique ==="
input int              InpMaxBars         = 20000;            // Bougies traitées au maximum
input ENUM_TIMEFRAMES  InpHtf             = PERIOD_CURRENT;   // UT supérieure (PERIOD_CURRENT = désactivée)
input int              InpHtfWarmup       = 300;              // Bougies d'UT supérieure avant la première bougie

input group "=== Affichage ==="
input int              InpDrawBars        = 3000;             // Dessiner les événements des N dernières bougies
input bool             InpShowStructure   = true;             // BOS, fail, IDM
input bool             InpShowPivots      = false;            // Étiquettes HH/HL/LH/LL
input bool             InpShowZones       = true;             // Zones d'offre et de demande
input bool             InpShowBreakers    = true;             // Breakers
input bool             InpShowLiquidity   = false;            // Tous les niveaux de liquidité intacts
input bool             InpShowEqual       = true;             // EQH / EQL
input bool             InpShowRanges      = true;             // Consolidations (expérimental)
input bool             InpShowSetups      = true;             // Setups
input bool             InpShowRejected    = false;            // Setups rejetés et motif
input bool             InpShowSessions    = true;             // Heures de tir
input bool             InpShowMonth       = true;             // Fenêtre du high/low du mois
input bool             InpShowImbalance   = false;            // FVG
input string           InpFont            = "Lora";           // Police (installée sous Windows, sinon substitution)
input int              InpFontSize        = 8;
input color            InpColBull         = C'120,140,93';    // Haussier
input color            InpColBear         = C'217,119,87';    // Baissier
input color            InpColDemand       = C'188,209,202';   // Zone de demande
input color            InpColSupply       = C'240,207,192';   // Zone d'offre
input color            InpColBreaker      = C'232,230,220';   // Breaker
input color            InpColRange        = C'240,238,230';   // Consolidation
input color            InpColNeutral      = C'176,174,165';   // Neutre
input color            InpColTarget       = C'106,155,204';   // Cibles, EQH/EQL

input group "=== Export (validation de parité) ==="
input bool             InpExport          = false;            // Écrire le journal et les bougies dans MQL5/Files/<dossier>
input string           InpExportFolder    = "SMV";

//--- index des tampons
#define SMV_BUF_TREND   0
#define SMV_BUF_PROT    1
#define SMV_BUF_SDIR    2
#define SMV_BUF_SENTRY  3
#define SMV_BUF_SSTOP   4
#define SMV_BUF_STARGET 5
#define SMV_BUF_HTF     6
#define SMV_BUF_TRAP    7

double     BufTrend[], BufProt[], BufSDir[], BufSEntry[], BufSStop[], BufSTarget[], BufHtf[], BufTrap[];

CSmvEngine g_eng;
CSmvEngine g_htf;
CSmvDraw   g_draw;
SmvConfig  g_cfg;
int        g_start = -1;          // indice graphique de la bougie moteur 0
datetime   g_start_time = 0;
bool       g_use_htf = false;
MqlRates   g_hr[];
int        g_hfed = 0;
string     g_prefix = "SMV_";

//+------------------------------------------------------------------+
int OnInit()
  {
   SmvConfigDefaults(g_cfg);
   g_cfg.pivot_left = InpPivotLeft;
   g_cfg.pivot_right = InpPivotRight;
   g_cfg.major_mode = InpMajorMode == SMV_MAJOR_A ? "A" : "B";
   g_cfg.bos_eps = InpBosEps;
   g_cfg.atr_len = InpAtrLen;
   g_cfg.bm_body_min = InpBmBodyMin;
   g_cfg.bm_range_atr = InpBmRangeAtr;
   g_cfg.zone_proximal = InpZoneProximal == SMV_PROX_BODY ? "body" : "wick";
   g_cfg.zones_on = InpZonesOn == SMV_ZONES_BOS ? "bos_origin" : "all_pivots";
   g_cfg.eq_tol_atr = InpEqTolAtr;
   g_cfg.eq_max_gap = InpEqMaxGap;
   g_cfg.range_accept_bars = InpRangeAccept;
   g_cfg.test_max_bars = InpTestMaxBars;
   g_cfg.sl_max_atr = InpSlMaxAtr;
   g_cfg.setup_expiry_bars = InpSetupExpiry;
   g_cfg.enable_setups = InpEnableSetups;
   g_cfg.enable_imbalance = InpEnableImbalance;
   g_cfg.enable_sessions = InpEnableSessions;
   g_cfg.session_mode = InpSessionMode == SMV_SES_MEASURED ? "measured" : "repo";
   string err;
   if(!SmvConfigValid(g_cfg, err))
     {
      Print("SMV: paramètre invalide : ", err);
      return INIT_PARAMETERS_INCORRECT;
     }
   g_use_htf = InpHtf != PERIOD_CURRENT && PeriodSeconds(InpHtf) > PeriodSeconds(_Period) && InpHtf != PERIOD_MN1;
   if(InpHtf != PERIOD_CURRENT && !g_use_htf)
      Print("SMV: UT supérieure ignorée (doit être supérieure à l'UT du graphique, hors MN1)");

   SetIndexBuffer(SMV_BUF_TREND, BufTrend, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_PROT, BufProt, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_SDIR, BufSDir, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_SENTRY, BufSEntry, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_SSTOP, BufSStop, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_STARGET, BufSTarget, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_HTF, BufHtf, INDICATOR_DATA);
   SetIndexBuffer(SMV_BUF_TRAP, BufTrap, INDICATOR_DATA);
   for(int b = 0; b < 8; b++)
      PlotIndexSetDouble(b, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   ArraySetAsSeries(BufTrend, false);  ArraySetAsSeries(BufProt, false);
   ArraySetAsSeries(BufSDir, false);   ArraySetAsSeries(BufSEntry, false);
   ArraySetAsSeries(BufSStop, false);  ArraySetAsSeries(BufSTarget, false);
   ArraySetAsSeries(BufHtf, false);    ArraySetAsSeries(BufTrap, false);

   SmvLayers L;
   L.structure = InpShowStructure; L.pivots = InpShowPivots; L.zones = InpShowZones;
   L.breakers = InpShowBreakers; L.liquidity = InpShowLiquidity; L.equal_levels = InpShowEqual;
   L.ranges = InpShowRanges; L.setups = InpShowSetups; L.rejected = InpShowRejected;
   L.sessions = InpShowSessions; L.month = InpShowMonth; L.imbalance = InpShowImbalance;
   SmvColors C;
   C.bull = InpColBull; C.bear = InpColBear; C.demand = InpColDemand; C.supply = InpColSupply;
   C.breaker = InpColBreaker; C.range = InpColRange; C.neutral = InpColNeutral; C.text = InpColNeutral;
   C.target = InpColTarget;
   g_prefix = "SMV_" + IntegerToString(ChartID() % 100000) + "_";
   g_draw.Init(g_prefix, L, C, InpFont, InpFontSize);
   IndicatorSetString(INDICATOR_SHORTNAME, "SMV");
   g_start = -1;
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(InpExport && g_start >= 0) Export();
   ObjectsDeleteAll(0, g_prefix);
   Comment("");
  }

//+------------------------------------------------------------------+
//| Remise à zéro complète : historique modifié, premier appel, etc. |
//+------------------------------------------------------------------+
void FullReset(const int rates_total, const datetime &time[])
  {
   g_eng.Init(g_cfg);
   g_draw.Reset();
   g_start = rates_total - 1 - InpMaxBars > 0 ? rates_total - 1 - InpMaxBars : 0;
   g_start_time = time[g_start];
   ArrayInitialize(BufTrend, EMPTY_VALUE);  ArrayInitialize(BufProt, EMPTY_VALUE);
   ArrayInitialize(BufSDir, EMPTY_VALUE);   ArrayInitialize(BufSEntry, EMPTY_VALUE);
   ArrayInitialize(BufSStop, EMPTY_VALUE);  ArrayInitialize(BufSTarget, EMPTY_VALUE);
   ArrayInitialize(BufHtf, EMPTY_VALUE);    ArrayInitialize(BufTrap, EMPTY_VALUE);
   if(g_use_htf)
     {
      SmvConfig hc = g_cfg;
      hc.enable_setups = false;
      hc.enable_sessions = false;
      hc.enable_imbalance = false;
      g_htf.Init(hc);
      g_hfed = 0;
      ArrayResize(g_hr, 0);
     }
  }

//+------------------------------------------------------------------+
//| UT supérieure : charge les bougies et alimente le moteur avec    |
//| celles dont la clôture nominale est <= t (heure serveur).        |
//+------------------------------------------------------------------+
bool HtfLoad(const datetime from_srv)
  {
   MqlRates more[];
   datetime start = ArraySize(g_hr) > 0 ? g_hr[ArraySize(g_hr) - 1].time + 1
                                         : from_srv - (datetime)(PeriodSeconds(InpHtf) * (long)InpHtfWarmup);
   int n = CopyRates(_Symbol, InpHtf, start, TimeCurrent(), more);
   if(n < 0) return false;    // historique pas encore disponible : nouvel essai au prochain appel
   // seules les bougies terminées sont conservées : la bougie en formation serait figée
   // avec des valeurs provisoires (elle sera relue une fois close)
   int ph = PeriodSeconds(InpHtf);
   int base = ArraySize(g_hr);
   for(int k = 0; k < n; k++)
     {
      if(more[k].time + ph > TimeCurrent()) break;
      ArrayResize(g_hr, base + 1, 1024);
      g_hr[base++] = more[k];
     }
   return true;
  }

void HtfFeedUntil(const datetime t_srv_close)
  {
   int ph = PeriodSeconds(InpHtf);
   while(g_hfed < ArraySize(g_hr) && g_hr[g_hfed].time + ph <= t_srv_close)
     {
      SmvBar b;
      b.index = g_htf.Count();
      b.t_srv = g_hr[g_hfed].time;
      b.t_open = ServerToUtc(b.t_srv, InpServerTz, InpServerFixedHours);
      b.t_close = b.t_open + ph;
      b.open = g_hr[g_hfed].open; b.high = g_hr[g_hfed].high;
      b.low = g_hr[g_hfed].low;   b.close = g_hr[g_hfed].close;
      g_htf.OnBar(b);
      g_hfed++;
     }
  }

//--- R-MTF-03 (PROPOSITION) : BOS de continuation contraire à l'UT haute, sous son niveau protégé
bool BosTrapRisk(const SmvEvent &e)
  {
   if(!g_use_htf || e.kind != K_BOS_CONTINUATION) return false;
   int ht = g_htf.structure.trend;
   if(ht == SMV_NONE || !g_htf.structure.has_prot || e.dir == ht) return false;
   double prot = g_htf.structure.prot_p;
   if(e.dir == SMV_BULL && ht == SMV_BEAR) return e.price < prot;
   if(e.dir == SMV_BEAR && ht == SMV_BULL) return e.price > prot;
   return false;
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[], const double &close[],
                const long &tick_volume[], const long &volume[], const int &spread[])
  {
   ArraySetAsSeries(time, false);
   ArraySetAsSeries(open, false);
   ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);
   ArraySetAsSeries(close, false);
   if(rates_total < InpPivotLeft + InpPivotRight + 3) return 0;
   const int last_closed = rates_total - 2;

   //--- remise à zéro si l'historique a changé (chargement, trou comblé, décalage à gauche)
   bool reset = prev_calculated == 0 || g_start < 0 || g_start >= rates_total || time[g_start] != g_start_time;
   if(!reset && g_eng.Count() > 0)
     {
      int lastIdx = g_start + g_eng.Count() - 1;
      if(lastIdx > last_closed || time[lastIdx] != g_eng.ctx.bars[g_eng.Count() - 1].t_srv) reset = true;
     }
   bool full = reset;
   if(reset) FullReset(rates_total, time);
   if(g_use_htf && !HtfLoad(time[g_start])) { g_start = -1; return 0; }

   const int ps = PeriodSeconds(_Period);
   const int before = g_eng.Count();
   for(int idx = g_start + g_eng.Count(); idx <= last_closed; idx++)
     {
      SmvBar b;
      b.index = idx - g_start;
      b.t_srv = time[idx];
      b.t_open = ServerToUtc(time[idx], InpServerTz, InpServerFixedHours);
      b.t_close = b.t_open + ps;
      b.open = open[idx]; b.high = high[idx]; b.low = low[idx]; b.close = close[idx];
      if(g_use_htf) HtfFeedUntil(time[idx] + ps);
      if(!g_eng.OnBar(b)) { g_start = -1; return 0; }
      //--- tampons de la bougie close idx
      BufTrend[idx] = g_eng.structure.trend;
      BufProt[idx] = g_eng.structure.has_prot ? g_eng.structure.prot_p : EMPTY_VALUE;
      BufHtf[idx] = g_use_htf ? g_htf.structure.trend : EMPTY_VALUE;
      BufSDir[idx] = 0; BufSEntry[idx] = EMPTY_VALUE; BufSStop[idx] = EMPTY_VALUE; BufSTarget[idx] = EMPTY_VALUE;
      BufTrap[idx] = 0;
      for(int k = g_eng.bar_from; k < g_eng.log.count; k++)
        {
         if(g_eng.log.ev[k].kind == K_SETUP && g_eng.log.ev[k].s2 == "")
           {
            BufSDir[idx] = g_eng.log.ev[k].dir;
            BufSEntry[idx] = g_eng.log.ev[k].price;
            BufSStop[idx] = g_eng.log.ev[k].d1;
            BufSTarget[idx] = g_eng.log.ev[k].d2;
           }
         if(BosTrapRisk(g_eng.log.ev[k])) BufTrap[idx] = g_eng.log.ev[k].dir;
        }
     }
   //--- la bougie en formation ne porte aucune valeur
   BufTrend[rates_total - 1] = EMPTY_VALUE; BufProt[rates_total - 1] = EMPTY_VALUE;
   BufSDir[rates_total - 1] = EMPTY_VALUE;  BufSEntry[rates_total - 1] = EMPTY_VALUE;
   BufSStop[rates_total - 1] = EMPTY_VALUE; BufSTarget[rates_total - 1] = EMPTY_VALUE;
   BufHtf[rates_total - 1] = EMPTY_VALUE;   BufTrap[rates_total - 1] = EMPTY_VALUE;

   //--- affichage (seulement si de nouvelles bougies closes ont été traitées)
   if(!full && g_eng.Count() == before) return rates_total;
   int draw_from = g_eng.Count() - InpDrawBars;
   g_draw.DrawNew(g_eng, draw_from > 0 ? draw_from : 0);
   g_draw.Extend(time[rates_total - 1]);
   Status();
   ChartRedraw();
   if(full && InpExport) Export();
   return rates_total;
  }

//+------------------------------------------------------------------+
void Status()
  {
   string tr = g_eng.structure.trend > 0 ? "haussière" : (g_eng.structure.trend < 0 ? "baissière" : "indéfinie");
   string s = "SMV  tendance " + tr;
   if(g_eng.structure.has_prot) s += "  |  protégé " + DoubleToString(g_eng.structure.prot_p, _Digits);
   if(g_use_htf)
     {
      int ht = g_htf.structure.trend;
      s += "  |  " + EnumToString(InpHtf) + " " + (ht > 0 ? "haussière" : (ht < 0 ? "baissière" : "indéfinie"));
     }
   s += "  |  " + IntegerToString(g_eng.Count()) + " bougies closes, " + IntegerToString(g_eng.log.count) + " événements";
   Comment(s);
  }

//+------------------------------------------------------------------+
//| Export : journal et bougies, relus par tools/mt5_parity.py       |
//+------------------------------------------------------------------+
void Export()
  {
   FolderCreate(InpExportFolder);
   string base = InpExportFolder + "\\" + _Symbol + "_" + StringSubstr(EnumToString(_Period), 7);
   int h = FileOpen(base + "_events.tsv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) { Print("SMV: export impossible, erreur ", GetLastError()); return; }
   FileWriteString(h, "#smv_mt5 0.20\n");
   FileWriteString(h, "#symbol=" + _Symbol + "\n");
   FileWriteString(h, "#server_tz=" + EnumToString(InpServerTz) + "\n");
   FileWriteString(h, "#config " + SmvConfigHeader(g_cfg) + "\n");
   FileWriteString(h, "kind\tconfirm\tanchor\tdir\tprice\tref\tdata\n");
   for(int k = 0; k < g_eng.log.count; k++)
     {
      SmvEvent e = g_eng.log.ev[k];
      FileWriteString(h, e.kind + "\t" + IntegerToString(e.confirm) + "\t" + IntegerToString(e.anchor) + "\t" +
                      IntegerToString(e.dir) + "\t" + FmtD(e.price) + "\t" + e.ref + "\t" + e.data + "\n");
     }
   FileClose(h);
   h = FileOpen(base + "_bars.tsv", FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) { Print("SMV: export impossible, erreur ", GetLastError()); return; }
   FileWriteString(h, "index\tt_open_utc\tt_close_utc\tt_srv\topen\thigh\tlow\tclose\n");
   for(int k = 0; k < g_eng.Count(); k++)
     {
      SmvBar b = g_eng.ctx.bars[k];
      FileWriteString(h, IntegerToString(k) + "\t" + IntegerToString((long)b.t_open) + "\t" +
                      IntegerToString((long)b.t_close) + "\t" + TimeToString(b.t_srv, TIME_DATE | TIME_SECONDS) + "\t" +
                      StringFormat("%.17g\t%.17g\t%.17g\t%.17g", b.open, b.high, b.low, b.close) + "\n");
     }
   FileClose(h);
   PrintFormat("SMV: export de %d événements et %d bougies dans MQL5\\Files\\%s_*.tsv",
               g_eng.log.count, g_eng.Count(), base);
  }
//+------------------------------------------------------------------+
