//+------------------------------------------------------------------+
//| SMV_ExportBars.mq5                                               |
//| Exporte les bougies (M5 par défaut) d'une liste de symboles en   |
//| CSV, avec l'écart du courtier, pour la recherche Python          |
//| (research/topdown). Fichiers : MQL5/Files commun /EXPORT/        |
//+------------------------------------------------------------------+
#property copyright "smv_indicator"
#property version   "1.00"
#property script_show_inputs

input string          InpSymbols = "EURUSD,GBPUSD,AUDUSD,USDCAD,USDCHF,EURGBP,EURCHF,USDJPY,EURJPY,GBPJPY,AUDJPY,XAUUSD"; // Symboles
input string          InpSuffix  = "";                 // Suffixe du courtier
input ENUM_TIMEFRAMES InpTf      = PERIOD_M5;          // Unité de temps
input datetime        InpFrom    = D'2018.01.01 00:00'; // Début

void OnStart()
  {
   string parts[];
   int n = StringSplit(InpSymbols, ',', parts);
   FolderCreate("EXPORT", FILE_COMMON);
   for(int k = 0; k < n; k++)
     {
      string sym = parts[k];
      StringTrimLeft(sym);
      StringTrimRight(sym);
      sym += InpSuffix;
      if(!SymbolSelect(sym, true)) { Print("EXPORT: symbole introuvable ", sym); continue; }
      MqlRates r[];
      ArraySetAsSeries(r, false);
      int got = -1;
      for(int attempt = 0; attempt < 20 && got <= 0; attempt++)
        {
         got = CopyRates(sym, InpTf, InpFrom, TimeCurrent(), r);
         if(got <= 0) Sleep(500);                     // historique en cours de chargement
        }
      if(got <= 0) { PrintFormat("EXPORT: aucune bougie pour %s (erreur %d)", sym, GetLastError()); continue; }
      string tf = StringSubstr(EnumToString(InpTf), 7);
      string f = "EXPORT\\" + sym + "_" + tf + ".csv";
      int h = FileOpen(f, FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
      if(h == INVALID_HANDLE) { PrintFormat("EXPORT: impossible d'écrire %s", f); continue; }
      int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
      double point = SymbolInfoDouble(sym, SYMBOL_POINT);
      FileWriteString(h, StringFormat("#symbol=%s;tf=%s;digits=%d;point=%g;server=%s\n", sym, tf, digits, point,
                                      AccountInfoString(ACCOUNT_SERVER)));
      FileWriteString(h, "time_srv,open,high,low,close,tick_volume,spread_points\n");
      for(int i = 0; i < got; i++)
         FileWriteString(h, StringFormat("%s,%s,%s,%s,%s,%s,%d\n", TimeToString(r[i].time, TIME_DATE | TIME_MINUTES),
                         DoubleToString(r[i].open, digits), DoubleToString(r[i].high, digits),
                         DoubleToString(r[i].low, digits), DoubleToString(r[i].close, digits),
                         IntegerToString(r[i].tick_volume), r[i].spread));
      FileClose(h);
      PrintFormat("EXPORT: %s %d bougies (%s -> %s)", sym, got, TimeToString(r[0].time), TimeToString(r[got - 1].time));
     }
   Print("EXPORT: terminé. Dossier : Terminal/Common/Files/EXPORT");
  }
