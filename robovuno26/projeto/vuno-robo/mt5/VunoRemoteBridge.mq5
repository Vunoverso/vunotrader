#property strict

#include <Trade/Trade.mqh>
#include <Trade/PositionInfo.mqh>

input string InpBridgeRoot = "VunoBridge";
input string InpAdditionalSymbols = "";
input int InpSnapshotCandles = 80;
input ENUM_TIMEFRAMES InpHigherTimeframe = PERIOD_H1;
input int InpHigherTimeframeCandles = 30;
input int InpTimerSeconds = 5;
input double InpMaxSpreadPoints = 30;
input double InpDefaultLot = 0.01;
input long InpMagic = 20260402;
input bool InpUseLocalFallback = true;
input bool InpAllowRealTrading = false;

CTrade Trade;
CPositionInfo PositionInfo;
double g_runtime_risk_per_trade = 0.5;
double g_runtime_max_spread_points = 30.0;
double g_runtime_default_lot = 0.01;
int g_runtime_stop_loss_points = 180;
int g_runtime_take_profit_points = 360;
int g_runtime_max_positions_per_symbol = 1;
int g_runtime_reentry_cooldown_seconds = 60;
int g_runtime_max_command_age_seconds = 45;
int g_runtime_deviation_points = 20;
int g_runtime_execution_retries = 3;
bool g_runtime_pause_new_orders = false;
bool g_runtime_use_local_fallback = true;
string g_runtime_trading_mode = "DEMO";

#include "vuno-bridge/vuno-bridge-json.mqh"
#include "vuno-bridge/vuno-bridge-paths.mqh"
#include "vuno-bridge/vuno-bridge-runtime.mqh"
#include "vuno-bridge/vuno-bridge-market.mqh"
#include "vuno-bridge/vuno-bridge-symbols.mqh"
#include "vuno-bridge/vuno-bridge-candles.mqh"
#include "vuno-bridge/vuno-bridge-execution.mqh"
#include "vuno-bridge/vuno-bridge-io.mqh"


int OnInit()
{
   EnsureBridgeFolders();
   PrepareTrackedSymbols();
   ResetRuntimeSettings();
   RefreshRuntimeSettings();
   Trade.SetExpertMagicNumber(InpMagic);
   EventSetTimer(MathMax(InpTimerSeconds, 1));
   return INIT_SUCCEEDED;
}


void OnDeinit(const int reason)
{
   EventKillTimer();
}


void OnTimer()
{
   RefreshRuntimeSettings();
   for(int i = 0; i < ArraySize(g_tracked_symbols); i++)
   {
      string symbol = g_tracked_symbols[i];
      ExportSnapshotForSymbol(symbol, (ENUM_TIMEFRAMES)_Period);
      ProcessCommandForSymbol(symbol, (ENUM_TIMEFRAMES)_Period);
   }
}


void OnTradeTransaction(const MqlTradeTransaction &trans, const MqlTradeRequest &request, const MqlTradeResult &result)
{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
      ExportFeedback(trans.deal);
}