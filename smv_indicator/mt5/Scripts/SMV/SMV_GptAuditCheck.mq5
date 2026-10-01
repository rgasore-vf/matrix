// Independent, hand-calculated regression vectors for the native engine.
// Compile/run in MetaEditor/MT5. NOT executed or compiled in the GPT workspace.
// Uses synthetic closed UTC bars; no broker data, drawing or trading orders.
#property script_show_inputs
#include <SMV/Engine.mqh>

int passed = 0, failed = 0;

void Check(const bool ok, const string label)
  {
   if(ok) { passed++; Print("PASS ", label); }
   else   { failed++; Print("FAIL ", label); }
  }

string Field(const string data, const string key)
  {
   string parts[];
   int n = StringSplit(data, ';', parts);
   for(int k = 0; k < n; k++)
     {
      int p = StringFind(parts[k], "=");
      if(p >= 0 && StringSubstr(parts[k], 0, p) == key) return StringSubstr(parts[k], p + 1);
     }
   return "";
  }

bool Has(const CSmvLog &log, const string kind, const int confirm, const int anchor,
         const int dir, const double price)
  {
   for(int k = 0; k < log.count; k++)
      if(log.ev[k].kind == kind && log.ev[k].confirm == confirm && log.ev[k].anchor == anchor &&
         log.ev[k].dir == dir && MathAbs(log.ev[k].price - price) < 1e-9) return true;
   return false;
  }

bool Sweep(const CSmvLog &log, const int confirm, const string side)
  {
   for(int k = 0; k < log.count; k++)
      if(log.ev[k].kind == K_RANGE_SWEEP && log.ev[k].confirm == confirm &&
         Field(log.ev[k].data, "side") == side) return true;
   return false;
  }

SmvBar Make(const int i, const double o, const double h, const double l, const double c,
            const int direction = SMV_BULL, const datetime start = D'2025.01.06 00:00', const int step = 900)
  {
   SmvBar b;
   b.index = i; b.t_open = start + i * step; b.t_close = b.t_open + step; b.t_srv = b.t_open;
   if(direction == SMV_BULL) { b.open=o; b.high=h; b.low=l; b.close=c; }
   else { b.open=40-o; b.high=40-l; b.low=40-h; b.close=40-c; }
   return b;
  }

void Feed(CSmvEngine &eng, const double &closes[], const int direction)
  {
   double prev = closes[0];
   for(int i = 0; i < ArraySize(closes); i++)
     {
      SmvBar b = Make(i, prev, MathMax(prev, closes[i]), MathMin(prev, closes[i]), closes[i], direction);
      Check(eng.OnBar(b), "input bar " + IntegerToString(i));
      prev = closes[i];
     }
  }

void StructureCases(const int direction)
  {
   SmvConfig cfg; SmvConfigDefaults(cfg); cfg.pivot_left=1; cfg.pivot_right=1;
   CSmvEngine eng; eng.Init(cfg);
   double base[] = {10,11,12,11,10,11,12.5,13,12,11.5,12};
   Feed(eng, base, direction);
   SmvBar b = Make(11,12,14,9,14,direction);
   Check(eng.OnBar(b), "outside input");
   Check(Has(eng.log,K_BOS_CONTINUATION,11,7,direction,direction>0?13:27), "simultaneous BOS");
   Check(Has(eng.log,K_PROTECTED_SWEEP,11,4,-direction,direction>0?10:30), "simultaneous protected sweep");

   eng.Init(cfg); Feed(eng,base,direction);
   double extra[][4] = {{12,20,11.8,12.5},{12.5,14,11,14},{14,18,12,17},{17,17.5,12,16}};
   for(int k=0;k<4;k++)
     {
      b=Make(11+k,extra[k][0],extra[k][1],extra[k][2],extra[k][3],direction);
      Check(eng.OnBar(b),"fail input");
     }
   Check(Has(eng.log,K_FAIL,14,13,-direction,direction>0?18:22), "first post-BOS fail");

   eng.Init(cfg);
   double range_base[] = {10,11,12,11,10,11,12.5,13,12,11.5,12.6,12.2,12.4};
   Feed(eng,range_base,direction);
   b=Make(13,12.4,13.4,11.3,13.2,direction); Check(eng.OnBar(b),"range outside input");
   b=Make(14,13.2,13.3,11.6,12.6,direction); Check(eng.OnBar(b),"range recovery input");
   Check(Sweep(eng.log,13,direction>0?"L":"H"),"range opposite sweep during pending exit");
   Check(Sweep(eng.log,14,direction>0?"H":"L"),"range recovered sweep");
  }

void StopGapCase()
  {
   CSmvContext ctx; ctx.Init(14);
   SmvBar b=Make(0,10,11,9.5,10); Check(ctx.Append(b),"gap input 0");
   b=Make(1,10,11,9.5,10); Check(ctx.Append(b),"gap input 1");
   b=Make(2,7,8,6,7); Check(ctx.Append(b),"gap input 2");
   CSmvSetups tracker;
   ArrayResize(tracker.act,1); tracker.nact=1;
   tracker.act[0].sid="S"; tracker.act[0].kind="CONCEPT"; tracker.act[0].dir=SMV_BULL;
   tracker.act[0].entry=10; tracker.act[0].stop=9; tracker.act[0].t1=12;
   tracker.act[0].created=0; tracker.act[0].deadline=100; tracker.act[0].zone="Z";
   tracker.act[0].label="IDM"; tracker.act[0].triggered=1; tracker.act[0].mfe_r=0;
   CSmvLog log; tracker.Update(2,ctx,log);
   bool found=false;
   for(int k=0;k<log.count;k++)
      if(log.ev[k].kind==K_SETUP_CLOSED && Field(log.ev[k].data,"reason")=="stop_gap" &&
         StringToDouble(Field(log.ev[k].data,"r"))==-3 &&
         StringToDouble(Field(log.ev[k].data,"execution_price"))==7) found=true;
   Check(found,"open position stop gap = -3 R at 7");
  }

void MonthBoundaryCase()
  {
   SmvConfig cfg; SmvConfigDefaults(cfg); cfg.enable_sessions=true;
   CSmvEngine eng; eng.Init(cfg);
   SmvBar b=Make(0,1,2,0.5,1,SMV_BULL,D'2026.01.08 00:00',86400);
   Check(eng.OnBar(b),"month input 0");
   b=Make(1,1,99,0.1,1,SMV_BULL,D'2026.01.08 00:00',86400);
   Check(eng.OnBar(b),"month input 1");
   bool found=false;
   for(int k=0;k<eng.log.count;k++)
      if(eng.log.ev[k].kind==K_MONTH_WINDOW && Field(eng.log.ev[k].data,"coverage")=="partial" &&
         StringToDouble(Field(eng.log.ev[k].data,"high"))==2 &&
         Field(eng.log.ev[k].data,"excluded_boundary_bars")=="1") found=true;
   Check(found,"month boundary excludes high 99");
  }

void OnStart()
  {
   StructureCases(SMV_BULL); StructureCases(SMV_BEAR);
   StopGapCase(); MonthBoundaryCase();
   PrintFormat("SMV GPT native checks: %d passed, %d failed. HTF/drawing/broker parity require separate checks.",passed,failed);
  }
