#ifndef VUNO_BRIDGE_SYMBOLS_MQH
#define VUNO_BRIDGE_SYMBOLS_MQH

string g_tracked_symbols[];
string g_command_state_symbols[];
long g_command_state_timestamps[];

string TrimSymbolValue(string value)
{
   string result = value;

   while(StringLen(result) > 0 && StringGetCharacter(result, 0) <= 32)
      result = StringSubstr(result, 1);

   while(StringLen(result) > 0 && StringGetCharacter(result, StringLen(result) - 1) <= 32)
      result = StringSubstr(result, 0, StringLen(result) - 1);

   return result;
}


int FindStringValue(const string &values[], string target)
{
   for(int i = 0; i < ArraySize(values); i++)
   {
      if(values[i] == target)
         return i;
   }

   return -1;
}


void AddTrackedSymbol(string &symbols[], string rawSymbol)
{
   string symbol = TrimSymbolValue(rawSymbol);
   if(symbol == "" || FindStringValue(symbols, symbol) >= 0)
      return;

   int next = ArraySize(symbols);
   ArrayResize(symbols, next + 1);
   symbols[next] = symbol;
}


void BuildTrackedSymbols()
{
   ArrayResize(g_tracked_symbols, 0);
   AddTrackedSymbol(g_tracked_symbols, _Symbol);

   string raw = InpAdditionalSymbols;
   StringReplace(raw, ";", ",");
   StringReplace(raw, "\r", ",");
   StringReplace(raw, "\n", ",");
   if(raw == "")
      return;

   string parts[];
   ushort comma = (ushort)StringGetCharacter(",", 0);
   int total = StringSplit(raw, comma, parts);

   for(int i = 0; i < total; i++)
      AddTrackedSymbol(g_tracked_symbols, parts[i]);
}


void PrepareTrackedSymbols()
{
   BuildTrackedSymbols();
   ArrayResize(g_command_state_symbols, ArraySize(g_tracked_symbols));
   ArrayResize(g_command_state_timestamps, ArraySize(g_tracked_symbols));

   string monitored = "";

   for(int i = 0; i < ArraySize(g_tracked_symbols); i++)
   {
      g_command_state_symbols[i] = g_tracked_symbols[i];
      g_command_state_timestamps[i] = 0;

      if(monitored != "")
         monitored += ", ";
      monitored += g_tracked_symbols[i];

      if(!SymbolSelect(g_tracked_symbols[i], true))
         Print("Falha ao habilitar simbolo: ", g_tracked_symbols[i]);
   }

   Print("Ativos monitorados pelo Vuno: ", monitored);
}


bool IsTrackedSymbol(string symbol)
{
   return FindStringValue(g_tracked_symbols, symbol) >= 0;
}


long LastCommandTimestamp(string symbol)
{
   int index = FindStringValue(g_command_state_symbols, symbol);
   if(index < 0)
      return 0;

   return g_command_state_timestamps[index];
}


void RememberCommandTimestamp(string symbol, long generatedAt)
{
   int index = FindStringValue(g_command_state_symbols, symbol);
   if(index < 0)
   {
      int next = ArraySize(g_command_state_symbols);
      ArrayResize(g_command_state_symbols, next + 1);
      ArrayResize(g_command_state_timestamps, next + 1);
      g_command_state_symbols[next] = symbol;
      g_command_state_timestamps[next] = generatedAt;
      return;
   }

   g_command_state_timestamps[index] = generatedAt;
}


bool EnsureTrackedSymbolReady(string symbol)
{
   if(!IsTrackedSymbol(symbol))
      return false;

   if(!SymbolSelect(symbol, true))
   {
      Print("Simbolo indisponivel no Market Watch: ", symbol);
      return false;
   }

   MqlTick tick;
   if(!SymbolInfoTick(symbol, tick))
   {
      Print("Sem tick disponivel para: ", symbol);
      return false;
   }

   return true;
}

#endif