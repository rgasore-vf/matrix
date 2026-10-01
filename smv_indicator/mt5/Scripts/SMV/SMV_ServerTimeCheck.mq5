//+------------------------------------------------------------------+
//| SMV_ServerTimeCheck.mq5                                          |
//| Détermine la convention horaire du serveur du courtier, pour     |
//| régler InpServerTz de SMV_Indicator.                             |
//|                                                                  |
//| Méthode (celle utilisée pour les données de calibrage, voir      |
//| research/marketdata.py) : le marché des changes ferme le vendredi|
//| à 17:00 New York. Pendant les semaines où l'heure d'été est      |
//| active aux États-Unis mais pas en Europe (mars) ou l'inverse     |
//| (fin octobre), l'heure serveur de la dernière bougie H1 du       |
//| vendredi diffère selon la convention :                           |
//|  - New York + 7 : dernière bougie 23:00 toute l'année ;          |
//|  - Europe/Athènes (UTC+2/+3, règles UE) : 22:00 pendant ces      |
//|    semaines désynchronisées, 23:00 le reste de l'année.          |
//| Le script affiche aussi le décalage courant serveur - GMT.       |
//+------------------------------------------------------------------+
#property script_show_inputs
#property version "0.20"

#include <SMV/Timing.mqh>

input int InpYears = 4;   // Nombre d'années examinées

//--- heure serveur de la dernière bougie H1 du vendredi dont la date est `friday`
int LastFridayHour(const datetime friday)
  {
   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_H1, friday, friday + 86400 - 1, r);
   if(n <= 0) return -1;
   MqlDateTime s;
   TimeToStruct(r[n - 1].time, s);
   return s.hour;
  }

void OnStart()
  {
   long off = (long)(TimeTradeServer() - TimeGMT());
   PrintFormat("SMV: décalage courant serveur - GMT = %+.1f h", off / 3600.0);
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);
   int votes_ny = 0, votes_eu = 0;
   for(int y = now.year - InpYears; y <= now.year; y++)
     {
      // semaine désynchronisée de mars : vendredi qui suit le 2e dimanche de mars
      datetime f_mar = SundayOf(y, 3, 2) + 5 * 86400;
      // semaine désynchronisée d'automne : vendredi qui suit le dernier dimanche d'octobre
      datetime f_oct = SundayOf(y, 10, -1) + 5 * 86400;
      datetime ref = SundayOf(y, 6, 2) + 5 * 86400;   // semaine normale de juin (référence)
      int hm = LastFridayHour(f_mar), ho = LastFridayHour(f_oct), hr = LastFridayHour(ref);
      PrintFormat("SMV: %d  vendredi de mars désynchronisé : %d h ; fin octobre : %d h ; juin : %d h", y, hm, ho, hr);
      if(hm < 0 || hr < 0) continue;
      if(hm == hr) votes_ny++;
      else if(hm == hr - 1) votes_eu++;
     }
   if(votes_ny > votes_eu)
      Print("SMV: convention probable NEW YORK + 7 -> InpServerTz = SMV_SRV_NY7");
   else if(votes_eu > votes_ny)
      Print("SMV: convention probable EUROPE (Athènes) -> InpServerTz = SMV_SRV_EET_EU");
   else
      Print("SMV: indéterminé (historique H1 insuffisant ?) ; vérifier à la main ou utiliser un décalage fixe");
  }
