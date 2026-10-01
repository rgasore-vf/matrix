//+------------------------------------------------------------------+
//| SMV/Engine.mqh                                                   |
//| Orchestrateur (portage de smv/engine.py) : consomme des bougies  |
//| CLOSES une par une et produit un journal en ajout seul.          |
//|                                                                  |
//| Ordre pour la bougie i (identique au moteur Python) :            |
//|  1. contexte (ATR) ;                                             |
//|  2. objets créés AVANT i : liquidités, zones, consolidation,     |
//|     setups ;                                                     |
//|  3. nouveautés de i : pivots, structure, zones des BOS, zones    |
//|     des pivots, niveaux, signatures, consolidation, setups ;     |
//|  4. marqueurs : imbalance, sessions, fenêtre mensuelle.          |
//| Aucune règle de stratégie n'est écrite dans l'affichage.         |
//+------------------------------------------------------------------+
#ifndef SMV_ENGINE_MQH
#define SMV_ENGINE_MQH

#include "Structure.mqh"
#include "Zones.mqh"
#include "Liquidity.mqh"
#include "Ranges.mqh"
#include "Setups.mqh"
#include "Timing.mqh"

class CSmvEngine
  {
public:
   SmvConfig         cfg;
   CSmvContext       ctx;
   CSmvLog           log;
   CSmvPivots        pivots;
   CSmvStructure     structure;
   CSmvZones         zones;
   CSmvLiquidity     liquidity;
   CSmvRanges        ranges;
   CSmvSetups        setups;
   CSmvSessions      sessions;
   CSmvMonthWindow   month;
   int               bar_from;     // premier événement de la dernière bougie traitée

   void              Init(const SmvConfig &c)
     {
      cfg = c;
      ctx.Init(cfg.atr_len);
      log.Reset();
      pivots.Reset();
      structure.Reset();
      zones.Reset();
      liquidity.Reset();
      ranges.Reset();
      setups.Reset();
      setups.be_at_r = cfg.be_at_r;
      month.Reset();
      bar_from = 0;
     }

   int               Count(void) const { return ctx.n; }

   //--- traite une bougie CLOSE ; renvoie false si la bougie est refusée
   bool              OnBar(const SmvBar &bar)
     {
      if(!ctx.Append(bar)) return false;
      const int i = bar.index;
      const int start = log.count;
      bar_from = start;
      //--- 2. objets antérieurs
      liquidity.Update(i, ctx, log);
      zones.Update(i, cfg, ctx, log);
      ranges.Update(i, cfg, ctx, log);
      if(cfg.enable_setups) setups.Update(i, ctx, log);
      //--- 3. nouveautés de la bougie i
      SmvPivot newp[];
      int nnew = pivots.Update(i, cfg, ctx, log, newp);
      int s0 = log.count;
      structure.Update(i, newp, nnew, cfg, ctx, pivots, log);
      int s1 = log.count;
      zones.OnStructure(i, s0, s1, cfg, ctx, log);
      zones.OnPivots(i, newp, nnew, cfg, ctx, log);
      liquidity.OnPivots(i, newp, nnew, cfg, ctx, log);
      int c0 = log.count;
      CandleScan(i, cfg, ctx, log);
      int c1 = log.count;
      liquidity.OnSignatures(i, c0, c1, log);
      ranges.OnEvents(i, start, log.count, log);
      if(cfg.enable_setups)
         setups.OnEvents(i, start, log.count, cfg, ctx, structure.trend, liquidity, ranges, log);
      //--- 4. marqueurs
      if(cfg.enable_imbalance) ImbalanceScan(i, ctx, log);
      if(cfg.enable_sessions)
        {
         sessions.Update(i, cfg, ctx, log);
         month.Update(i, ctx, log);
        }
      //--- contrat temporel : tout événement émis à i est confirmé à i
      for(int k = start; k < log.count; k++)
         if(log.ev[k].confirm != i)
            PrintFormat("SMV: contrat violé, %s confirmé à %d émis à %d", log.ev[k].kind, log.ev[k].confirm, i);
      return true;
     }
  };

#endif
