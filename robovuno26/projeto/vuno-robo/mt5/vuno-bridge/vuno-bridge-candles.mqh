#ifndef VUNO_BRIDGE_CANDLES_MQH
#define VUNO_BRIDGE_CANDLES_MQH

string TimeframeLabel(ENUM_TIMEFRAMES timeframe)
{
   string label = EnumToString(timeframe);
   StringReplace(label, "PERIOD_", "");
   return label;
}


string CandleTimeLabel(datetime value)
{
   return TimeToString(value, TIME_DATE | TIME_SECONDS);
}


string BuildCandlesJson(string sym, ENUM_TIMEFRAMES timeframe, int requestedCount)
{
   if(requestedCount <= 0)
      return "[]";

   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(sym, timeframe, 1, requestedCount, rates);
   if(copied <= 0)
      return "[]";

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   if(digits <= 0)
      digits = _Digits;

   string json = "[";

   for(int i = copied - 1; i >= 0; i--)
   {
         string tickVolume = StringFormat("%I64d", (long)rates[i].tick_volume);

      if(i != copied - 1)
         json += ",";

      json += "\n    {";
      json += "\"time\": \"" + JsonEscape(CandleTimeLabel((datetime)rates[i].time)) + "\", ";
      json += "\"open\": " + DoubleToString(rates[i].open, digits) + ", ";
      json += "\"high\": " + DoubleToString(rates[i].high, digits) + ", ";
      json += "\"low\": " + DoubleToString(rates[i].low, digits) + ", ";
      json += "\"close\": " + DoubleToString(rates[i].close, digits) + ", ";
         json += "\"tick_volume\": " + tickVolume;
      json += "}";
   }

   if(copied > 0)
      json += "\n  ";

   json += "]";
   return json;
}

#endif