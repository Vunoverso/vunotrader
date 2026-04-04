#ifndef VUNO_BRIDGE_IO_MQH
#define VUNO_BRIDGE_IO_MQH

void ExportSnapshotForSymbol(string sym, ENUM_TIMEFRAMES timeframe)
{
   if(!EnsureTrackedSymbolReady(sym))
      return;

   string timeframeLabel = TimeframeLabel(timeframe);
   string higherTimeframeLabel = TimeframeLabel(InpHigherTimeframe);
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
   string openPositionOpenedAt = "";
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
      openPositionProfitPoints,
      openPositionOpenedAt
   );

   string fileName = SnapshotDirectory() + "\\" + sym + "_" + timeframeLabel + "_" + IntegerToString((int)TimeCurrent()) + ".snapshot.json";
   int handle = FileOpen(fileName, FILE_WRITE | FILE_TXT | FILE_COMMON | FILE_ANSI);

   if(handle == INVALID_HANDLE)
   {
      Print("Falha ao abrir arquivo de snapshot: ", fileName);
      return;
   }

   string capturedAt = TimeToString(TimeCurrent(), TIME_DATE | TIME_SECONDS);
   string json = "{\n";
   json += "  \"symbol\": \"" + JsonEscape(sym) + "\",\n";
   json += "  \"timeframe\": \"" + JsonEscape(timeframeLabel) + "\",\n";
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
   json += "  \"open_position_opened_at\": \"" + JsonEscape(openPositionOpenedAt) + "\",\n";
   json += "  \"captured_at\": \"" + JsonEscape(capturedAt) + "\",\n";
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
   ulong requestedTicket = (ulong)JsonGetLong(payload, "position_ticket", 0);
   double requestedStopLoss = JsonGetDouble(payload, "position_stop_loss", 0);
   double requestedTakeProfit = JsonGetDouble(payload, "position_take_profit", 0);
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
      string liveOpenedAt = "";
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
         liveProfitPoints,
         liveOpenedAt
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
   BuildStops(sym, signal, slPoints, tpPoints, sl, tp);

   if(ExecuteOrder(sym, signal, lot, sl, tp, "VUNO/REMOTE"))
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