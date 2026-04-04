#ifndef VUNO_BRIDGE_RUNTIME_MQH
#define VUNO_BRIDGE_RUNTIME_MQH

void ResetRuntimeSettings()
{
   g_runtime_risk_per_trade = 0.5;
   g_runtime_max_spread_points = InpMaxSpreadPoints;
   g_runtime_default_lot = InpDefaultLot;
   g_runtime_stop_loss_points = 180;
   g_runtime_take_profit_points = 360;
   g_runtime_max_positions_per_symbol = 1;
   g_runtime_reentry_cooldown_seconds = 60;
   g_runtime_max_command_age_seconds = 45;
   g_runtime_deviation_points = 20;
   g_runtime_execution_retries = 3;
   g_runtime_pause_new_orders = false;
   g_runtime_use_local_fallback = InpUseLocalFallback;
   g_runtime_trading_mode = "DEMO";
}


void RefreshRuntimeSettings()
{
   ResetRuntimeSettings();

   string settingsPath = CommandDirectory() + "\\runtime.settings.json";
   if(!FileIsExist(settingsPath, FILE_COMMON))
      return;

   int handle = FileOpen(settingsPath, FILE_READ | FILE_TXT | FILE_COMMON | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;

   string payload = FileReadString(handle, (int)FileSize(handle));
   FileClose(handle);

   string tradingMode = JsonGetString(payload, "trading_mode");
   if(tradingMode != "")
   {
      StringToUpper(tradingMode);
      if(tradingMode == "DEMO" || tradingMode == "REAL")
         g_runtime_trading_mode = tradingMode;
      else
         g_runtime_trading_mode = "DEMO";
   }

   g_runtime_risk_per_trade = SafeRisk(JsonGetDouble(payload, "risk_per_trade", g_runtime_risk_per_trade));
   g_runtime_max_spread_points = JsonGetDouble(payload, "max_spread_points", g_runtime_max_spread_points);
   g_runtime_default_lot = JsonGetDouble(payload, "default_lot", g_runtime_default_lot);
   g_runtime_stop_loss_points = (int)JsonGetDouble(payload, "stop_loss_points", g_runtime_stop_loss_points);
   g_runtime_take_profit_points = (int)JsonGetDouble(payload, "take_profit_points", g_runtime_take_profit_points);
   g_runtime_max_positions_per_symbol = (int)JsonGetDouble(payload, "max_positions_per_symbol", g_runtime_max_positions_per_symbol);
   g_runtime_reentry_cooldown_seconds = (int)JsonGetDouble(payload, "reentry_cooldown_seconds", g_runtime_reentry_cooldown_seconds);
   g_runtime_max_command_age_seconds = (int)JsonGetDouble(payload, "max_command_age_seconds", g_runtime_max_command_age_seconds);
   g_runtime_deviation_points = (int)JsonGetDouble(payload, "deviation_points", g_runtime_deviation_points);
   g_runtime_execution_retries = (int)JsonGetDouble(payload, "execution_retries", g_runtime_execution_retries);
   g_runtime_pause_new_orders = (JsonGetLong(payload, "pause_new_orders", g_runtime_pause_new_orders ? 1 : 0) == 1);
   g_runtime_use_local_fallback = (JsonGetLong(payload, "use_local_fallback", g_runtime_use_local_fallback ? 1 : 0) == 1);
}


bool NewOrdersBlocked()
{
   if(g_runtime_trading_mode != "DEMO" && g_runtime_trading_mode != "REAL")
   {
      Print("Modo operacional invalido. Apenas DEMO ou REAL sao aceitos.");
      return true;
   }

   if(g_runtime_pause_new_orders)
   {
      Print("Novas ordens bloqueadas pelo contrato operacional.");
      return true;
   }

   if(g_runtime_trading_mode == "REAL" && !InpAllowRealTrading)
   {
      Print("Modo REAL bloqueado. Ative InpAllowRealTrading para liberar execucao real.");
      return true;
   }

   return false;
}

#endif
