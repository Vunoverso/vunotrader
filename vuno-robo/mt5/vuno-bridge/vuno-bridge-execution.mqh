#ifndef VUNO_BRIDGE_EXECUTION_MQH
#define VUNO_BRIDGE_EXECUTION_MQH

double NormalizeLotValue(string sym, double rawLot)
{
   double minLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);

   if(step <= 0)
      step = 0.01;

   double bounded = MathMax(minLot, MathMin(maxLot, rawLot));
   double normalized = MathFloor(bounded / step) * step;
   int digits = 2;

   if(step == 1.0)
      digits = 0;
   else if(step == 0.1)
      digits = 1;

   return NormalizeDouble(normalized, digits);
}


double CalculateLot(string sym, double risk)
{
   risk = SafeRisk(risk);
   double multiplier = MathMax(0.5, risk / 0.5);
   return NormalizeLotValue(sym, g_runtime_default_lot * multiplier);
}


void BuildStops(string sym, string signal, int slPoints, int tpPoints, double &sl, double &tp)
{
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);

   sl = 0;
   tp = 0;

   if(signal == "BUY")
   {
      sl = NormalizeDouble(ask - (slPoints * point), digits);
      tp = NormalizeDouble(ask + (tpPoints * point), digits);
   }

   if(signal == "SELL")
   {
      sl = NormalizeDouble(bid + (slPoints * point), digits);
      tp = NormalizeDouble(bid - (tpPoints * point), digits);
   }
}


bool ExecuteOrder(string sym, string signal, double lot, double sl, double tp, string comment)
{
   int maxRetries = g_runtime_execution_retries;

   for(int i = 0; i < maxRetries; i++)
   {
      MqlTick tick;
      if(!SymbolInfoTick(sym, tick))
      {
         Sleep(300);
         continue;
      }

      Trade.SetDeviationInPoints(g_runtime_deviation_points);
      Trade.SetTypeFilling(ORDER_FILLING_IOC);

      bool result = false;

      if(signal == "BUY")
         result = Trade.Buy(lot, sym, tick.ask, sl, tp, comment);

      if(signal == "SELL")
         result = Trade.Sell(lot, sym, tick.bid, sl, tp, comment);

      if(result)
         return true;

      Sleep(300);
   }

   Print("FALHA AO EXECUTAR ORDEM: ", sym);
   return false;
}


bool ModifyManagedPosition(string sym, ulong ticket, double stopLoss, double takeProfit)
{
   if(ticket == 0)
      return false;

   int maxRetries = g_runtime_execution_retries;
   for(int i = 0; i < maxRetries; i++)
   {
      Trade.SetDeviationInPoints(g_runtime_deviation_points);
      if(Trade.PositionModify(ticket, stopLoss, takeProfit))
         return true;
      Sleep(300);
   }

   Print("FALHA AO MODIFICAR POSICAO: ", sym, " ticket=", (long)ticket);
   return false;
}


bool CloseManagedPosition(string sym, ulong ticket)
{
   if(ticket == 0)
      return false;

   int maxRetries = g_runtime_execution_retries;
   for(int i = 0; i < maxRetries; i++)
   {
      Trade.SetDeviationInPoints(g_runtime_deviation_points);
      if(Trade.PositionClose(ticket))
         return true;
      Sleep(300);
   }

   Print("FALHA AO FECHAR POSICAO: ", sym, " ticket=", (long)ticket);
   return false;
}


bool ReentryCooldownPassed(string sym)
{
   if(g_runtime_reentry_cooldown_seconds <= 0)
      return true;

   if(!HistorySelect(0, TimeCurrent()))
      return true;

   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = HistoryDealGetTicket(i);
      if(ticket == 0)
         continue;

      string symbol = HistoryDealGetString(ticket, DEAL_SYMBOL);
      long magic = HistoryDealGetInteger(ticket, DEAL_MAGIC);
      long entry = HistoryDealGetInteger(ticket, DEAL_ENTRY);

      if(symbol != sym || magic != InpMagic || entry != DEAL_ENTRY_OUT)
         continue;

      datetime closedAt = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);
      long elapsed = (long)TimeCurrent() - (long)closedAt;
      return elapsed >= g_runtime_reentry_cooldown_seconds;
   }

   return true;
}

#endif