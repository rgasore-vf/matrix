//+------------------------------------------------------------------+
//| SMV/Types.mqh                                                    |
//| Types de base du moteur SMV (portage de smv/types.py).           |
//|                                                                  |
//| Conventions (STRATEGY_SPEC §0.4, ARCHITECTURE §4) :              |
//| - indices CROISSANTS avec le temps (0 = plus ancienne bougie     |
//|   traitée) ; la série inversée de MQL5 n'est jamais utilisée     |
//|   dans la logique ;                                              |
//| - une bougie n'est transmise au moteur qu'une fois CLOSE ;       |
//| - chaque événement porte confirm (bougie close qui le rend vrai) |
//|   et anchor (bougie où il est dessiné), anchor <= confirm.       |
//+------------------------------------------------------------------+
#ifndef SMV_TYPES_MQH
#define SMV_TYPES_MQH

#define SMV_BULL  1
#define SMV_BEAR -1
#define SMV_NONE  0

//--- types d'événements (mêmes chaînes que smv.types.Kind)
#define K_PIVOT_HIGH       "PIVOT_HIGH"
#define K_PIVOT_LOW        "PIVOT_LOW"
#define K_TREND_INIT       "TREND_INIT"
#define K_BOS_CONTINUATION "BOS_CONTINUATION"
#define K_BOS_CHANGE       "BOS_CHANGE"
#define K_PROTECTED_SWEEP  "PROTECTED_SWEEP"
#define K_FAIL             "FAIL"
#define K_INDUCEMENT       "INDUCEMENT"
#define K_LIQ_LEVEL        "LIQ_LEVEL"
#define K_LIQ_CLEAN        "LIQ_CLEAN"
#define K_LIQ_BOS          "LIQ_BOS"
#define K_EQUAL_LEVELS     "EQUAL_LEVELS"
#define K_LIQ_SIGNATURE    "LIQ_SIGNATURE"
#define K_ZONE             "ZONE"
#define K_ZONE_TOUCH       "ZONE_TOUCH"
#define K_ZONE_BROKEN      "ZONE_BROKEN"
#define K_ODF_LINK         "ODF_LINK"
#define K_BREAKER          "BREAKER"
#define K_BREAKER_REACTION "BREAKER_REACTION"
#define K_RANGE_OPEN       "RANGE_OPEN"
#define K_RANGE_SWEEP      "RANGE_SWEEP"
#define K_RANGE_INTENTION  "RANGE_INTENTION"
#define K_CAUSE_COMPLETE   "CAUSE_COMPLETE"
#define K_RANGE_EXIT       "RANGE_EXIT"
#define K_IMBALANCE        "IMBALANCE"
#define K_SETUP            "SETUP"
#define K_SETUP_TRIGGERED  "SETUP_TRIGGERED"
#define K_SETUP_CLOSED     "SETUP_CLOSED"
#define K_SETUP_EXPIRED    "SETUP_EXPIRED"
#define K_SESSION          "SESSION"
#define K_MONTH_WINDOW     "MONTH_WINDOW"

//+------------------------------------------------------------------+
//| Bougie close.                                                    |
//| t_srv : heure serveur (affichage) ; t_open/t_close : UTC (calcul)|
//+------------------------------------------------------------------+
struct SmvBar
  {
   int      index;
   datetime t_srv;
   datetime t_open;
   datetime t_close;
   double   open;
   double   high;
   double   low;
   double   close;
  };

double BarBody(const SmvBar &b)  { return MathAbs(b.close - b.open); }
double BarRange(const SmvBar &b) { return b.high - b.low; }
double BarBodyRatio(const SmvBar &b)
  {
   double r = BarRange(b);
   return r > 0.0 ? BarBody(b) / r : 0.0;
  }
int BarColor(const SmvBar &b)
  {
   if(b.close > b.open) return SMV_BULL;
   if(b.close < b.open) return SMV_BEAR;
   return SMV_NONE;
  }

//+------------------------------------------------------------------+
//| Événement.                                                       |
//| `data` : charge utile sérialisée « clé=valeur;... » (export CSV, |
//| comparaison avec Python). Les champs typés i1..d2..s2 servent    |
//| aux modules consommateurs ; leur sens dépend du type :           |
//|   TREND_INIT, BOS_* : i1 = origin_index, d1 = origin_price       |
//|   INDUCEMENT        : s1 = level_ref, i1 = trend                 |
//|   FAIL              : i1 = prior_trend, i2 = climax_index,       |
//|                       i3 = ar_index, d1 = climax_price,          |
//|                       d2 = ar_price, s1 = st_ref                 |
//|   LIQ_CLEAN/LIQ_BOS : s1 = level                                 |
//|   LIQ_SIGNATURE     : s1 = side                                  |
//|   ZONE / BREAKER    : d1 = proximal, d2 = distal, s1 = source    |
//|   RANGE_SWEEP       : s1 = range, s2 = side                      |
//+------------------------------------------------------------------+
struct SmvEvent
  {
   string kind;
   int    confirm;
   int    anchor;
   int    dir;
   double price;
   string ref;
   string data;
   int    i1;
   int    i2;
   int    i3;
   double d1;
   double d2;
   string s1;
   string s2;
  };

//+------------------------------------------------------------------+
//| Sérialisation de la charge utile (format lu par                   |
//| tools/mt5_parity.py). Listes séparées par « | », None = vide.    |
//+------------------------------------------------------------------+
string FmtD(const double v) { return StringFormat("%.15g", v); }

void KvS(string &s, const string k, const string v)
  {
   if(StringLen(s) > 0) s += ";";
   s += k + "=" + v;
  }
void KvI(string &s, const string k, const int v)    { KvS(s, k, IntegerToString(v)); }
void KvD(string &s, const string k, const double v) { KvS(s, k, FmtD(v)); }
void KvB(string &s, const string k, const bool v)   { KvS(s, k, v ? "true" : "false"); }
void KvNone(string &s, const string k)              { KvS(s, k, ""); }

string SideStr(const int side) { return side > 0 ? "H" : "L"; }

//+------------------------------------------------------------------+
//| Journal d'événements en ajout seul.                              |
//+------------------------------------------------------------------+
class CSmvLog
  {
public:
   SmvEvent          ev[];
   int               count;

                     CSmvLog(void) { count = 0; ArrayResize(ev, 0, 4096); }
   void              Reset(void)   { count = 0; ArrayResize(ev, 0, 4096); }

   //--- ajoute et renvoie l'indice de l'événement (pour compléter les champs typés)
   int               Add(const string kind, const int confirm, const int anchor, const int dir,
                         const double price, const string ref, const string data)
     {
      if(anchor > confirm)
         Print("SMV: anchor > confirm pour ", kind, " ", ref);
      int n = count;
      if(ArraySize(ev) <= n)
         ArrayResize(ev, n + 1, 4096);
      ev[n].kind    = kind;
      ev[n].confirm = confirm;
      ev[n].anchor  = anchor;
      ev[n].dir     = dir;
      ev[n].price   = price;
      ev[n].ref     = ref;
      ev[n].data    = data;
      ev[n].i1 = 0; ev[n].i2 = 0; ev[n].i3 = 0;
      ev[n].d1 = 0.0; ev[n].d2 = 0.0;
      ev[n].s1 = ""; ev[n].s2 = "";
      count = n + 1;
      return n;
     }
  };

#endif
