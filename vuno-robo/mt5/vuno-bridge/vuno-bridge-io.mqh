#ifndef VUNO_BRIDGE_IO_MQH
#define VUNO_BRIDGE_IO_MQH

datetime g_last_symbol_catalog_export_at = 0;
string g_last_symbol_catalog_signature = "";


string SanitizeCycleToken(string value)
{
   string result = "";
   int len = StringLen(value);
   for(int i = 0; i < len; i++)
   {
      ushort c = StringGetCharacter(value, i);
      bool isAlphaNum = (c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
      if(isAlphaNum)
         result += StringSubstr(value, i, 1);
      else if(StringLen(result) == 0 || StringGetCharacter(result, StringLen(result) - 1) != '_')
         result += "_";
   }

   while(StringLen(result) > 0 && StringGetCharacter(result, StringLen(result) - 1) == '_')
      result = StringSubstr(result, 0, StringLen(result) - 1);

   return result == "" ? "bridge" : result;
}


string BuildCycleId(string sym, string timeframeLabel)
{
   return SanitizeCycleToken(InpBridgeRoot) + "_" + SanitizeCycleToken(sym) + "_" + timeframeLabel + "_" + IntegerToString((int)TimeCurrent()) + "_" + IntegerToString((int)GetTickCount());
}


bool CaptureChartImage(string sym, ENUM_TIMEFRAMES timeframe, string imageFileName, string &status)
{
   status = "capturing";
   if(sym != _Symbol || timeframe != (ENUM_TIMEFRAMES)_Period)
   {
      status = "skipped_non_chart_symbol";
      return false;
   }

   string imagePath = SnapshotDirectory() + "\\" + imageFileName;
   if(ChartScreenShot(0, imagePath, 1600, 900, ALIGN_RIGHT))
   {
      status = "captured";
      return true;
   }

   status = "error";
   return false;
}


bool ShouldExportSymbolCatalog(string signature)
{
   if(signature == "")
      return false;

   if(g_last_symbol_catalog_signature != signature)
      return true;

   return ((long)TimeCurrent() - (long)g_last_symbol_catalog_export_at) >= 60;
}


void ExportSymbolCatalog()
{
   string availableSymbols[];
   string marketWatchSymbols[];
   string trackedSymbols[];
   CollectTerminalSymbols(false, availableSymbols);
   CollectTerminalSymbols(true, marketWatchSymbols);
   CopyStringArray(g_tracked_symbols, trackedSymbols);

   string availableJson = BuildJsonArrayFromSymbols(availableSymbols);
   string marketWatchJson = BuildJsonArrayFromSymbols(marketWatchSymbols);
   string trackedJson = BuildJsonArrayFromSymbols(trackedSymbols);
   string chartSymbol = _Symbol;
   string chartTimeframe = TimeframeLabel((ENUM_TIMEFRAMES)_Period);
   string signature = InpBridgeRoot + "|" + chartSymbol + "|" + chartTimeframe + "|" + availableJson + "|" + marketWatchJson + "|" + trackedJson;

   if(!ShouldExportSymbolCatalog(signature))
      return;

   string exportedAt = TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
   string loginValue = StringFormat("%I64d", (long)AccountInfoInteger(ACCOUNT_LOGIN));
   string json = "{\n";
   json += "  \"bridge_name\": \"" + JsonEscape(InpBridgeRoot) + "\",\n";
   json += "  \"chart_symbol\": \"" + JsonEscape(chartSymbol) + "\",\n";
   json += "  \"chart_timeframe\": \"" + JsonEscape(chartTimeframe) + "\",\n";
   json += "  \"exported_at\": \"" + JsonEscape(exportedAt) + "\",\n";
   json += "  \"account_login\": " + loginValue + ",\n";
   json += "  \"server\": \"" + JsonEscape(AccountInfoString(ACCOUNT_SERVER)) + "\",\n";
   json += "  \"company\": \"" + JsonEscape(AccountInfoString(ACCOUNT_COMPANY)) + "\",\n";
   json += "  \"terminal_name\": \"" + JsonEscape(TerminalInfoString(TERMINAL_NAME)) + "\",\n";
   json += "  \"available_symbols\": " + availableJson + ",\n";
   json += "  \"market_watch_symbols\": " + marketWatchJson + ",\n";
   json += "  \"tracked_symbols\": " + trackedJson + "\n";
   json += "}";

   string fileName = MetadataDirectory() + "\\symbols_" + IntegerToString((int)TimeCurrent()) + "_" + IntegerToString((int)GetTickCount()) + ".catalog.json";
   int handle = FileOpen(fileName, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);

   if(handle == INVALID_HANDLE)
   {
      Print("Falha ao abrir arquivo de metadata: ", fileName);
      return;
   }

   FileWriteString(handle, json);
   FileClose(handle);
   g_last_symbol_catalog_signature = signature;
   g_last_symbol_catalog_export_at = TimeCurrent();
}

void ExportSnapshotForSymbol(string sym, ENUM_TIMEFRAMES timeframe)
{
   if(!EnsureTrackedSymbolReady(sym))
      return;

   string timeframeLabel = TimeframeLabel(timeframe);
   string higherTimeframeLabel = TimeframeLabel(InpHigherTimeframe);
   string cycleId = BuildCycleId(sym, timeframeLabel);
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   if(digits <= 0)
      digits = _Digits;
   string candlesJson = BuildCandlesJson(sym, timeframe, InpSnapshotCandles);
   string higherTimeframeCandlesJson = BuildCandlesJson(sym, InpHigherTimeframe, InpHigherTimeframeCandles);
   ulong openPositionTicket = 0;
   string openPositionDirection = "";
   double openPositionVolume = 0;
   double openPositionEntryPrice = 0;
   double openPositionCurrentPrice = 0;
   double openPositionStopLoss = 0;
   double openPositionTakeProfit = 0;
   double openPositionProfit = 0;
   double openPositionProfitPoints = 0;
   GetManagedPositionSnapshot(
      sym,
      openPositionTicket,
      openPositionDirection,
      openPositionVolume,
      openPositionEntryPrice,
      openPositionCurrentPrice,
      openPositionStopLoss,
      openPositionTakeProfit,
      openPositionProfit,
      openPositionProfitPoints
   );

   string chartImageFile = cycleId + ".chart.png";
   string chartImageRelativePath = SnapshotDirectory() + "\\" + chartImageFile;
   string chartImageStatus = "";
   if(!CaptureChartImage(sym, timeframe, chartImageFile, chartImageStatus))
      chartImageFile = "";
   else
      chartImageFile = chartImageRelativePath;

   string fileName = SnapshotDirectory() + "\\" + cycleId + ".snapshot.json";
   int handle = FileOpen(fileName, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);

   if(handle == INVALID_HANDLE)
   {
      Print("Falha ao abrir arquivo de snapshot: ", fileName);
      return;
   }

   string capturedAt = TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
   string json = "{\n";
   json += "  \"cycle_id\": \"" + JsonEscape(cycleId) + "\",\n";
   json += "  \"bridge_name\": \"" + JsonEscape(InpBridgeRoot) + "\",\n";
   json += "  \"symbol\": \"" + JsonEscape(sym) + "\",\n";
   json += "  \"timeframe\": \"" + JsonEscape(timeframeLabel) + "\",\n";
   json += "  \"chart_symbol\": \"" + JsonEscape(_Symbol) + "\",\n";
   json += "  \"chart_timeframe\": \"" + JsonEscape(TimeframeLabel((ENUM_TIMEFRAMES)_Period)) + "\",\n";
   json += "  \"bid\": " + DoubleToString(SymbolInfoDouble(sym, SYMBOL_BID), digits) + ",\n";
   json += "  \"ask\": " + DoubleToString(SymbolInfoDouble(sym, SYMBOL_ASK), digits) + ",\n";
   json += "  \"spread_points\": " + DoubleToString(CurrentSpreadPoints(sym), 2) + ",\n";
   json += "  \"close\": " + DoubleToString(iClose(sym, timeframe, 1), digits) + ",\n";
   json += "  \"ema_fast\": " + DoubleToString(GetEMA(sym, timeframe, 9, 1), digits) + ",\n";
   json += "  \"ema_slow\": " + DoubleToString(GetEMA(sym, timeframe, 21, 1), digits) + ",\n";
   json += "  \"rsi\": " + DoubleToString(GetRSI(sym, timeframe, 14, 1), 2) + ",\n";
   json += "  \"balance\": " + DoubleToString(AccountInfoDouble(ACCOUNT_BALANCE), 2) + ",\n";
   json += "  \"equity\": " + DoubleToString(AccountInfoDouble(ACCOUNT_EQUITY), 2) + ",\n";
   json += "  \"open_positions\": " + IntegerToString(CountSymbolPositions(sym)) + ",\n";
   json += "  \"open_position_ticket\": " + IntegerToString((int)openPositionTicket) + ",\n";
   json += "  \"open_position_direction\": \"" + JsonEscape(openPositionDirection) + "\",\n";
   json += "  \"open_position_volume\": " + DoubleToString(openPositionVolume, 2) + ",\n";
   json += "  \"open_position_entry_price\": " + DoubleToString(openPositionEntryPrice, digits) + ",\n";
   json += "  \"open_position_current_price\": " + DoubleToString(openPositionCurrentPrice, digits) + ",\n";
   json += "  \"open_position_stop_loss\": " + DoubleToString(openPositionStopLoss, digits) + ",\n";
   json += "  \"open_position_take_profit\": " + DoubleToString(openPositionTakeProfit, digits) + ",\n";
   json += "  \"open_position_profit\": " + DoubleToString(openPositionProfit, 2) + ",\n";
   json += "  \"open_position_profit_points\": " + DoubleToString(openPositionProfitPoints, 2) + ",\n";
   json += "  \"captured_at\": \"" + JsonEscape(capturedAt) + "\",\n";
   json += "  \"chart_image_file\": \"" + JsonEscape(chartImageFile) + "\",\n";
   json += "  \"chart_image_captured_at\": \"" + JsonEscape(capturedAt) + "\",\n";
   json += "  \"chart_image_status\": \"" + JsonEscape(chartImageStatus) + "\",\n";
   json += "  \"candles\": " + candlesJson + ",\n";
   json += "  \"htf_timeframe\": \"" + JsonEscape(higherTimeframeLabel) + "\",\n";
   json += "  \"htf_candles\": " + higherTimeframeCandlesJson + "\n";
   json += "}";

   FileWriteString(handle, json);
   FileClose(handle);
}


void ProcessCommandForSymbol(string sym, ENUM_TIMEFRAMES timeframe)
{
   if(!IsTrackedSymbol(sym))
      return;

   string commandPath = CommandDirectory() + "\\" + sym + ".command.json";
   if(!FileIsExist(commandPath, FILE_COMMON))
      return;

   int handle = FileOpen(commandPath, FILE_READ | FILE_TXT | FILE_COMMON | FILE_ANSI);
   if(handle == INVALID_HANDLE)
      return;

   string payload = FileReadString(handle, (int)FileSize(handle));
   FileClose(handle);

   string signal = JsonGetString(payload, "signal");
   string positionAction = JsonGetString(payload, "position_action");
   string commandComment = JsonGetString(payload, "comment");
   ulong requestedTicket = (ulong)JsonGetLong(payload, "position_ticket", 0);
   double requestedStopLoss = JsonGetDouble(payload, "position_stop_loss", 0);
   double requestedTakeProfit = JsonGetDouble(payload, "position_take_profit", 0);
   double requestedEntryStopLoss = JsonGetDouble(payload, "stop_loss_price", 0);
   double requestedEntryTakeProfit = JsonGetDouble(payload, "take_profit_price", 0);
   long generatedAt = JsonGetLong(payload, "generated_at_unix", 0);
   long lastGeneratedAt = LastCommandTimestamp(sym);

   if(generatedAt <= 0 || generatedAt == lastGeneratedAt)
      return;

   if((long)TimeCurrent() - generatedAt > g_runtime_max_command_age_seconds)
      return;

   if(signal == "" && g_runtime_use_local_fallback)
      signal = LocalFallbackSignal(sym, timeframe);

   if(positionAction == "CLOSE" || positionAction == "PROTECT")
   {
      ulong liveTicket = 0;
      string liveDirection = "";
      double liveVolume = 0;
      double liveEntryPrice = 0;
      double liveCurrentPrice = 0;
      double liveStopLoss = 0;
      double liveTakeProfit = 0;
      double liveProfit = 0;
      double liveProfitPoints = 0;
      bool hasPosition = GetManagedPositionSnapshot(
         sym,
         liveTicket,
         liveDirection,
         liveVolume,
         liveEntryPrice,
         liveCurrentPrice,
         liveStopLoss,
         liveTakeProfit,
         liveProfit,
         liveProfitPoints
      );

      if(!hasPosition)
      {
         RememberCommandTimestamp(sym, generatedAt);
         return;
      }

      if(requestedTicket == 0)
         requestedTicket = liveTicket;

      if(positionAction == "CLOSE")
      {
         if(CloseManagedPosition(sym, requestedTicket))
            RememberCommandTimestamp(sym, generatedAt);
         return;
      }

      if(positionAction == "PROTECT")
      {
         if(requestedStopLoss <= 0)
            requestedStopLoss = liveStopLoss;
         if(requestedTakeProfit <= 0)
            requestedTakeProfit = liveTakeProfit;

         requestedStopLoss = NormalizePriceForSymbol(sym, requestedStopLoss);
         requestedTakeProfit = NormalizePriceForSymbol(sym, requestedTakeProfit);
         if(ModifyManagedPosition(sym, requestedTicket, requestedStopLoss, requestedTakeProfit))
            RememberCommandTimestamp(sym, generatedAt);
         return;
      }
   }

   if(signal == "HOLD" || signal == "")
   {
      RememberCommandTimestamp(sym, generatedAt);
      return;
   }

   if(NewOrdersBlocked())
      return;

   if(!MarketOpen(sym))
      return;

   if(!SpreadOK(sym))
      return;

   if(CountSymbolPositions(sym) >= g_runtime_max_positions_per_symbol)
      return;

   if(!ReentryCooldownPassed(sym))
      return;

   double risk = SafeRisk(JsonGetDouble(payload, "risk", g_runtime_risk_per_trade));
   int slPoints = (int)JsonGetDouble(payload, "stop_loss_points", g_runtime_stop_loss_points);
   int tpPoints = (int)JsonGetDouble(payload, "take_profit_points", g_runtime_take_profit_points);
   double lot = CalculateLot(sym, risk);
   double sl = 0;
   double tp = 0;
   if(requestedEntryStopLoss > 0 && requestedEntryTakeProfit > 0)
   {
      sl = NormalizePriceForSymbol(sym, requestedEntryStopLoss);
      tp = NormalizePriceForSymbol(sym, requestedEntryTakeProfit);
   }
   else
   {
      BuildStops(sym, signal, slPoints, tpPoints, sl, tp);
   }

   if(commandComment == "")
      commandComment = "VUNO/REMOTE";

   if(ExecuteOrder(sym, signal, lot, sl, tp, commandComment))
      RememberCommandTimestamp(sym, generatedAt);
}


void ExportFeedback(ulong dealTicket)
{
   if(dealTicket == 0)
      return;

   if(!HistorySelect(0, TimeCurrent()))
      return;

   string symbol = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
   long magic = HistoryDealGetInteger(dealTicket, DEAL_MAGIC);
   long entry = HistoryDealGetInteger(dealTicket, DEAL_ENTRY);

   if(!IsTrackedSymbol(symbol) || magic != InpMagic || entry != DEAL_ENTRY_OUT)
      return;

   double profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
   double volume = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
   string outcome = profit >= 0 ? "WIN" : "LOSS";
   string fileName = FeedbackDirectory() + "\\" + symbol + "_" + IntegerToString((int)dealTicket) + ".feedback.json";
   int handle = FileOpen(fileName, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);

   if(handle == INVALID_HANDLE)
      return;

   string closedAt = TimeToString((datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME), TIME_DATE | TIME_SECONDS);
   string json = "{\n";
   json += "  \"symbol\": \"" + JsonEscape(symbol) + "\",\n";
   json += "  \"outcome\": \"" + outcome + "\",\n";
   json += "  \"pnl\": " + DoubleToString(profit, 2) + ",\n";
   json += "  \"closed_at\": \"" + JsonEscape(closedAt) + "\",\n";
   json += "  \"ticket\": " + IntegerToString((int)dealTicket) + ",\n";
   json += "  \"volume\": " + DoubleToString(volume, 2) + "\n";
   json += "}";

   FileWriteString(handle, json);
   FileClose(handle);
}

#endif