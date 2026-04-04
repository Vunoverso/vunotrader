#ifndef VUNO_BRIDGE_MARKET_MQH
#define VUNO_BRIDGE_MARKET_MQH

double CurrentSpreadPoints(string sym)
{
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);

   if(point <= 0)
      return 0;

   return (ask - bid) / point;
}


double IndicatorValue(int handle, int shift = 1)
{
   if(handle == INVALID_HANDLE)
      return 0.0;

   double buffer[];
   ArraySetAsSeries(buffer, true);
   if(CopyBuffer(handle, 0, shift, 1, buffer) <= 0)
   {
      IndicatorRelease(handle);
      return 0.0;
   }

   double value = buffer[0];
   IndicatorRelease(handle);
   return value;
}


double GetEMA(string sym, ENUM_TIMEFRAMES timeframe, int period, int shift = 1)
{
   int handle = iMA(sym, timeframe, period, 0, MODE_EMA, PRICE_CLOSE);
   return IndicatorValue(handle, shift);
}


double GetRSI(string sym, ENUM_TIMEFRAMES timeframe, int period, int shift = 1)
{
   int handle = iRSI(sym, timeframe, period, PRICE_CLOSE);
   return IndicatorValue(handle, shift);
}


double SafeRisk(double risk)
{
   if(risk <= 0)
      return 0;

   if(risk > 1.0)
      risk = 1.0;

   return risk;
}


bool SpreadOK(string sym)
{
   double spread = CurrentSpreadPoints(sym);

   if(spread > g_runtime_max_spread_points)
   {
      Print("Spread alto: ", sym, " = ", spread);
      return false;
   }

   return true;
}


bool MarketOpen(string sym)
{
   long mode = SymbolInfoInteger(sym, SYMBOL_TRADE_MODE);
   return (mode == SYMBOL_TRADE_MODE_FULL);
}


double NormalizePriceForSymbol(string sym, double value)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   if(digits < 0)
      digits = _Digits;
   return NormalizeDouble(value, digits);
}


int CountSymbolPositions(string sym)
{
   int count = 0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionInfo.SelectByIndex(i))
      {
         if(PositionInfo.Symbol() == sym && PositionInfo.Magic() == InpMagic)
            count++;
      }
   }

   return count;
}


bool GetManagedPositionSnapshot(
   string sym,
   ulong &ticket,
   string &direction,
   double &volume,
   double &entryPrice,
   double &currentPrice,
   double &stopLoss,
   double &takeProfit,
   double &profit,
   double &profitPoints
)
{
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(point <= 0)
      point = _Point;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i))
         continue;

      if(PositionInfo.Symbol() != sym || PositionInfo.Magic() != InpMagic)
         continue;

      ticket = (ulong)PositionInfo.Ticket();
      long positionType = PositionInfo.PositionType();
      direction = (positionType == POSITION_TYPE_SELL) ? "SELL" : "BUY";
      volume = PositionInfo.Volume();
      entryPrice = NormalizePriceForSymbol(sym, PositionInfo.PriceOpen());
      currentPrice = NormalizePriceForSymbol(sym, PositionInfo.PriceCurrent());
      stopLoss = NormalizePriceForSymbol(sym, PositionInfo.StopLoss());
      takeProfit = NormalizePriceForSymbol(sym, PositionInfo.TakeProfit());
      profit = PositionInfo.Profit();
      if(direction == "BUY")
         profitPoints = (currentPrice - entryPrice) / point;
      else
         profitPoints = (entryPrice - currentPrice) / point;
      return true;
   }

   ticket = 0;
   direction = "";
   volume = 0;
   entryPrice = 0;
   currentPrice = 0;
   stopLoss = 0;
   takeProfit = 0;
   profit = 0;
   profitPoints = 0;
   return false;
}


string LocalFallbackSignal(string sym, ENUM_TIMEFRAMES timeframe)
{
   double maFast = GetEMA(sym, timeframe, 9);
   double maSlow = GetEMA(sym, timeframe, 21);

   if(maFast > maSlow)
      return "BUY";

   if(maFast < maSlow)
      return "SELL";

   return "HOLD";
}

#endif