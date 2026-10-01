//+------------------------------------------------------------------+
//| SMV/Draw.mqh                                                     |
//| Couche d'affichage : lit le journal du moteur et dessine des     |
//| objets graphiques. AUCUNE règle de stratégie ici : on ne fait    |
//| que représenter des événements déjà confirmés.                   |
//|                                                                  |
//| Objets « ouverts » (zone active, consolidation, setup en cours,  |
//| niveau intact) : prolongés jusqu'à la bougie courante, puis      |
//| fermés à la bougie de l'événement qui les termine.               |
//+------------------------------------------------------------------+
#ifndef SMV_DRAW_MQH
#define SMV_DRAW_MQH

#include "Engine.mqh"

struct SmvLayers
  {
   bool structure;
   bool pivots;
   bool zones;
   bool breakers;
   bool liquidity;
   bool equal_levels;
   bool ranges;
   bool setups;
   bool rejected;
   bool sessions;
   bool month;
   bool imbalance;
  };

struct SmvColors
  {
   color bull;
   color bear;
   color demand;
   color supply;
   color breaker;
   color range;
   color neutral;
   color text;
   color target;
  };

struct SmvOpenObj
  {
   string key;     // identifiant de l'objet métier (zone, niveau, consolidation, setup)
   string name;    // nom de l'objet graphique
  };

//--- lit « clé=valeur » dans la charge utile d'un événement
string DataGet(const string data, const string key)
  {
   string parts[];
   int n = StringSplit(data, ';', parts);
   for(int k = 0; k < n; k++)
     {
      int p = StringFind(parts[k], "=");
      if(p > 0 && StringSubstr(parts[k], 0, p) == key) return StringSubstr(parts[k], p + 1);
     }
   return "";
  }

class CSmvDraw
  {
public:
   string            prefix;
   SmvLayers         L;
   SmvColors         C;
   string            font;
   int               font_size;
   SmvOpenObj        open[];
   int               nopen;
   int               drawn;      // événements du journal déjà examinés

   void              Init(const string pfx, const SmvLayers &layers, const SmvColors &colors, const string f,
                          const int fs)
     {
      prefix = pfx; L = layers; C = colors; font = f; font_size = fs;
      Reset();
     }

   void              Reset(void)
     {
      ObjectsDeleteAll(0, prefix);
      nopen = 0;
      ArrayResize(open, 0, 512);
      drawn = 0;
     }

   //--- dessine les événements [drawn, log.count) dont la confirmation est >= min_confirm
   void              DrawNew(CSmvEngine &eng, const int min_confirm)
     {
      for(int k = drawn; k < eng.log.count; k++)
        {
         SmvEvent e = eng.log.ev[k];
         // les fermetures s'appliquent toujours (l'objet a pu être dessiné plus tôt)
         CloseFor(e, eng);
         if(e.confirm >= min_confirm) DrawOne(e, eng);
        }
      drawn = eng.log.count;
     }

   //--- prolonge les objets ouverts jusqu'au temps t
   void              Extend(const datetime t)
     {
      for(int k = 0; k < nopen; k++)
         ObjectSetInteger(0, open[k].name, OBJPROP_TIME, 1, t);
     }

private:
   datetime          T(CSmvEngine &eng, const int idx) const { return eng.ctx.bars[idx].t_srv; }

   void              Register(const string key, const string name)
     {
      ArrayResize(open, nopen + 1, 512);
      open[nopen].key = key; open[nopen].name = name; nopen++;
     }

   void              Close(const string key, const datetime t)
     {
      int m = 0;
      for(int k = 0; k < nopen; k++)
        {
         if(open[k].key == key) { ObjectSetInteger(0, open[k].name, OBJPROP_TIME, 1, t); continue; }
         if(m != k) open[m] = open[k];
         m++;
        }
      nopen = m;
      ArrayResize(open, nopen, 512);
     }

   void              Line(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
                          const color c, const int style, const int width, const string tip)
     {
      if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_COLOR, c);
      ObjectSetInteger(0, name, OBJPROP_STYLE, style);
      ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
     }

   void              Rect(const string name, const datetime t1, const double p1, const datetime t2, const double p2,
                          const color c, const string tip)
     {
      if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_COLOR, c);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
     }

   void              Text(const string name, const datetime t, const double p, const string txt, const color c,
                          const ENUM_ANCHOR_POINT anchor, const string tip)
     {
      if(ObjectFind(0, name) >= 0) ObjectDelete(0, name);
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
      ObjectSetString(0, name, OBJPROP_TEXT, txt);
      ObjectSetString(0, name, OBJPROP_FONT, font);
      ObjectSetInteger(0, name, OBJPROP_FONTSIZE, font_size);
      ObjectSetInteger(0, name, OBJPROP_COLOR, c);
      ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
     }

   color             Dir(const int d) const { return d > 0 ? C.bull : (d < 0 ? C.bear : C.neutral); }
   ENUM_ANCHOR_POINT Above(const int d) const { return d >= 0 ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER; }

   //--- fermeture des objets ouverts par l'événement e
   void              CloseFor(const SmvEvent &e, CSmvEngine &eng)
     {
      datetime t = T(eng, e.confirm);
      if(e.kind == K_ZONE_BROKEN)          Close("Z:" + StringSubstr(e.ref, 3), t);
      else if(e.kind == K_LIQ_CLEAN || e.kind == K_LIQ_BOS) Close("L:" + e.s1, t);
      else if(e.kind == K_RANGE_EXIT)      Close("R:" + StringSubstr(e.ref, 3), t);
      else if(e.kind == K_RANGE_OPEN)
        {
         // une nouvelle consolidation remplace la précédente
         for(int k = nopen - 1; k >= 0; k--)
            if(StringSubstr(open[k].key, 0, 2) == "R:") { Close(open[k].key, t); break; }
        }
      else if(e.kind == K_SETUP_CLOSED || e.kind == K_SETUP_EXPIRED)
         Close("S:" + DataGet(e.data, "setup"), t);
     }

   void              DrawOne(const SmvEvent &e, CSmvEngine &eng)
     {
      string nm = prefix + e.kind + ":" + e.ref;
      datetime ta = T(eng, e.anchor), tc = T(eng, e.confirm);
      string tip = e.kind + " " + e.ref;
      //--- structure
      if(L.structure && (e.kind == K_BOS_CHANGE || e.kind == K_BOS_CONTINUATION || e.kind == K_TREND_INIT))
        {
         bool chg = e.kind == K_BOS_CHANGE;
         Line(nm, ta, e.price, tc, e.price, Dir(e.dir), chg ? STYLE_SOLID : STYLE_DOT, chg ? 2 : 1, tip);
         string txt = chg ? "BOS (changement)" : (e.kind == K_TREND_INIT ? "INIT" : "BOS");
         Text(nm + ":t", ta, e.price, txt, Dir(e.dir), Above(e.dir), tip);
         return;
        }
      if(L.structure && e.kind == K_FAIL)
        { Text(nm, ta, e.price, "fail", C.neutral, Above(-e.dir), tip + " (changement de caractère)"); return; }
      if(L.structure && e.kind == K_INDUCEMENT)
        { Text(nm, ta, e.price, "IDM", C.neutral, ANCHOR_LEFT, tip); return; }
      if(L.structure && e.kind == K_PROTECTED_SWEEP)
        { Text(nm, tc, e.price, "$ protégé", C.neutral, ANCHOR_LEFT, tip); return; }
      if(L.pivots && (e.kind == K_PIVOT_HIGH || e.kind == K_PIVOT_LOW))
        {
         string lab = DataGet(e.data, "label");
         if(lab != "")
            Text(nm, ta, e.price, lab, C.neutral, e.kind == K_PIVOT_HIGH ? ANCHOR_LOWER : ANCHOR_UPPER, tip);
         return;
        }
      //--- zones
      if((e.kind == K_ZONE && L.zones) || (e.kind == K_BREAKER && L.breakers))
        {
         color c = e.kind == K_BREAKER ? C.breaker : (e.dir > 0 ? C.demand : C.supply);
         string t2 = tip + " source=" + DataGet(e.data, "source") + " BM=" + DataGet(e.data, "bm_index");
         Rect(nm, ta, e.d1, tc, e.d2, c, t2);
         Register("Z:" + e.ref, nm);
         return;
        }
      //--- liquidité
      if(L.liquidity && e.kind == K_LIQ_LEVEL)
        {
         Line(nm, ta, e.price, tc, e.price, C.neutral, STYLE_DOT, 1, tip);
         Register("L:" + e.ref, nm);
         return;
        }
      if(L.equal_levels && e.kind == K_EQUAL_LEVELS)
        {
         string sd = DataGet(e.data, "side");
         Line(nm, ta, e.price, tc, e.price, C.target, STYLE_DASH, 1, tip);
         Text(nm + ":t", ta, e.price, sd == "H" ? "EQH" : "EQL", C.target, sd == "H" ? ANCHOR_LEFT_LOWER : ANCHOR_LEFT_UPPER, tip);
         return;
        }
      //--- consolidation (expérimental)
      if(L.ranges && e.kind == K_RANGE_OPEN)
        {
         double lo = StringToDouble(DataGet(e.data, "low")), hi = StringToDouble(DataGet(e.data, "high"));
         Rect(nm, ta, lo, tc, hi, C.range, tip + " " + DataGet(e.data, "context"));
         Register("R:" + e.ref, nm);
         Text(nm + ":t", ta, hi, "range " + DataGet(e.data, "context"), C.neutral, ANCHOR_LEFT_LOWER, tip);
         return;
        }
      if(L.ranges && e.kind == K_RANGE_SWEEP)
        {
         Text(nm, ta, e.price, DataGet(e.data, "label_candidate") + "?", Dir(-e.dir),
              e.dir > 0 ? ANCHOR_LOWER : ANCHOR_UPPER, tip + " (candidat, confirmé à la sortie)");
         return;
        }
      if(L.ranges && e.kind == K_RANGE_EXIT)
        {
         Text(nm, tc, e.price, "sortie " + DataGet(e.data, "outcome") + " " + DataGet(e.data, "wyckoff_type"),
              Dir(e.dir), Above(e.dir), tip);
         return;
        }
      //--- setups
      if(L.setups && e.kind == K_SETUP)
        {
         if(e.s2 != "")
           {
            if(L.rejected) Text(nm, tc, e.price, "rejeté : " + e.s2, C.neutral, ANCHOR_LEFT, tip);
            return;
           }
         string sid = e.ref;
         string rr = DataGet(e.data, "rr");
         int bar = StringFind(rr, "|");
         if(bar > 0) rr = StringSubstr(rr, 0, bar);
         string t2 = tip + " entrée=" + FmtD(e.price) + " stop=" + FmtD(e.d1) + " cible=" + FmtD(e.d2);
         Line(nm + ":e", tc, e.price, tc, e.price, Dir(e.dir), STYLE_SOLID, 2, t2);
         Line(nm + ":s", tc, e.d1, tc, e.d1, C.bear, STYLE_SOLID, 1, t2);
         Line(nm + ":t", tc, e.d2, tc, e.d2, C.target, STYLE_SOLID, 1, t2);
         Register("S:" + sid, nm + ":e");
         Register("S:" + sid, nm + ":s");
         Register("S:" + sid, nm + ":t");
         Text(nm + ":l", tc, e.price, e.s1 + " " + DataGet(e.data, "label") + "  RR " + rr, Dir(e.dir),
              Above(-e.dir), t2);
         return;
        }
      if(L.setups && e.kind == K_SETUP_CLOSED)
        {
         string r = DataGet(e.data, "r");
         double rv = StringToDouble(r);
         Text(nm, tc, e.price, (rv > 0 ? "+" : "") + DoubleToString(rv, 2) + " R", rv > 0 ? C.bull : C.bear,
              ANCHOR_LEFT, tip + " " + DataGet(e.data, "reason"));
         return;
        }
      if(L.setups && e.kind == K_SETUP_EXPIRED)
        { Text(nm, tc, e.price, "expiré", C.neutral, ANCHOR_LEFT, tip + " " + DataGet(e.data, "reason")); return; }
      //--- marqueurs
      if(L.sessions && e.kind == K_SESSION)
        {
         if(ObjectFind(0, nm) >= 0) ObjectDelete(0, nm);
         ObjectCreate(0, nm, OBJ_VLINE, 0, tc, 0);
         ObjectSetInteger(0, nm, OBJPROP_COLOR, C.neutral);
         ObjectSetInteger(0, nm, OBJPROP_STYLE, STYLE_DOT);
         ObjectSetInteger(0, nm, OBJPROP_BACK, true);
         ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
         ObjectSetString(0, nm, OBJPROP_TEXT, DataGet(e.data, "name"));
         ObjectSetString(0, nm, OBJPROP_TOOLTIP, DataGet(e.data, "name") + " " + DataGet(e.data, "start"));
         return;
        }
      if(L.month && e.kind == K_MONTH_WINDOW)
        {
         double hi = StringToDouble(DataGet(e.data, "high")), lo = StringToDouble(DataGet(e.data, "low"));
         datetime th = T(eng, (int)StringToInteger(DataGet(e.data, "high_index")));
         datetime tl = T(eng, (int)StringToInteger(DataGet(e.data, "low_index")));
         Line(nm + ":h", th, hi, tc, hi, C.neutral, STYLE_DASHDOT, 1, tip + " haut 26-9");
         Line(nm + ":l", tl, lo, tc, lo, C.neutral, STYLE_DASHDOT, 1, tip + " bas 26-9");
         return;
        }
      if(L.imbalance && e.kind == K_IMBALANCE)
        {
         double top = StringToDouble(DataGet(e.data, "top")), bot = StringToDouble(DataGet(e.data, "bottom"));
         Rect(nm, ta, top, tc, bot, C.neutral, tip + " (définition ICT externe)");
         return;
        }
     }
  };

#endif
