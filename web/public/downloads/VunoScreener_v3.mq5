//+------------------------------------------------------------------+
//| VunoScreener v3 — MT5 Multi-Asset Client (Conecta ao Cloud)      |
//| Rastreia uma lista de símbolos e envia dados iterativos.        |
//+------------------------------------------------------------------+

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

input group "=== CONEXÃO CLOUD ==="
input string   BackendURL       = "https://vunotrader-api.onrender.com";

input group "=== GESTÃO SCREENER ==="
input string   AssetList        = "EURUSD,GBPUSD,XAUUSD"; // Moedas
input int      DataBars         = 200;
input double   MaxDailyLoss     = 5.0;
input double   MaxDrawdown      = 15.0;
input int      MaxPositions     = 3; // Máximo global
input double   ATR_SL_Multi     = 2.0;
input string   TradingStart     = "08:00";
input string   TradingEnd       = "20:00";

input group "=== IDENTIFICAÇÃO VUNO ==="
input string   UserID           = "0e3d7cd9-7e39-4714-a52f-f7eb793a4640";
input string   OrganizationID   = "24affdc3-dc7b-4672-b20d-65033949bb76";
input string   RobotID          = "8e048faa-937c-4a3e-8760-9d59c3f64d77";
input string   RobotToken       = "dBiAqxGYo2S6nxFtdNH7oufKa_MYGms0";
input string   TradingMode      = "demo";

CTrade         Trade;
CPositionInfo  PositionInfo;

string         arrSymbols[];
int            arrATR[];
datetime       arrLastBar[];
double         g_dailyPnL      = 0;
double         g_initialBal    = 0;
double         g_peakBal       = 0;
datetime       g_lastReset     = 0;
bool           g_identityWarned= false;
datetime       g_lastHeartbeat = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(20260331);
   Trade.SetDeviationInPoints(10);
   
   // Prepara array de ativos
   ushort sep = StringGetCharacter(",",0);
   int count = StringSplit(AssetList, sep, arrSymbols);
   
   if(count == 0) {
      Print("ERRO: AssetList vazio.");
      return INIT_FAILED;
   }
   
   ArrayResize(arrATR, count);
   ArrayResize(arrLastBar, count);
   
   for(int i=0; i<count; i++) {
      string sym = arrSymbols[i];
      StringTrimLeft(sym);
      StringTrimRight(sym);
      arrSymbols[i] = sym; // salva sem espaço
      
      SymbolSelect(sym, true); // Garante que mercado observe ele
      
      arrATR[i] = iATR(sym, PERIOD_CURRENT, 14);
      if(arrATR[i] == INVALID_HANDLE) {
         Print("AVISO: Falha ao invocar iATR para ", sym);
      }
      arrLastBar[i] = 0; // zera controle de barra
   }

   g_initialBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_peakBal    = g_initialBal;
   
   // Screener de 5 segundos
   EventSetTimer(5);

   Print("VunoScreener v3 iniciado | ", count, " ativos.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnTimer()
{
   ResetDaily();
   if(!IdentityReady()) return;
   
   // Controlar envio de Heartbeat a cada 30 segundos
   datetime now = TimeCurrent();
   if(now - g_lastHeartbeat >= 30) {
      SendHeartbeat();
      g_lastHeartbeat = now;
   }
   
   // Verifica Nova Barra para cada símbolo e processa
   int count = ArraySize(arrSymbols);
   for(int i=0; i<count; i++) 
   {
      string sym = arrSymbols[i];
      datetime currentBar = iTime(sym, PERIOD_CURRENT, 0);
      
      if(currentBar != arrLastBar[i] && currentBar > 0) 
      {
         arrLastBar[i] = currentBar; // Marcou nova barra
         
         // Coleta dados
         string candles = CollectCandlesSymbol(sym, DataBars);
         if(candles == "") continue;
         
         // Determina modo efetivo
         // Se Fora do horário ou Safety der false, envia como Observer
         string effMode = TradingMode;
         bool safe = SafetyOK();
         bool inHr = TradingHour();
         
         if(!safe || !inHr) {
            effMode = "observer"; // Manda ao brain p/ aprendizado simulado // não opera
         }

         string request = StringFormat(
            "{\"type\":\"MARKET_DATA\","
            "\"symbol\":\"%s\","
            "\"timeframe\":\"%s\","
            "\"mode\":\"%s\","
            "\"user_id\":\"%s\","
            "\"organization_id\":\"%s\","
            "\"robot_id\":\"%s\","
            "\"robot_token\":\"%s\","
            "\"candles\":%s}",
            sym,
            TFToString(PERIOD_CURRENT),
            effMode,
            UserID, OrganizationID, RobotID, RobotToken,
            candles
         );
         
         string response = SendToCloud("/api/mt5/signal", request);
         if(response == "") continue;
         
         // Se modo efetivo era observer, descarta trade APÓS registrar na nuvem
         if(effMode == "observer") continue; 
         
         string signal     = ExtractString(response, "signal");
         double confidence = ExtractDouble(response, "confidence");
         double risk       = ExtractDouble(response, "risk");
         string decisionId = ExtractString(response, "decision_id");
         
         if(signal == "HOLD" || risk <= 0 || decisionId == "") continue;
         
         // Pode Exceder ordens globais?
         if(CountAllPositions() >= MaxPositions) continue;
         
         // Executar Trade
         ExecuteTrade(sym, arrATR[i], signal, confidence, risk, decisionId);
      }
   }
}

//+------------------------------------------------------------------+
void ExecuteTrade(string sym, int handleATR, string signal, double conf, double risk, string dId)
{
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(handleATR, 0, 0, 2, atr) < 2) return;
   
   double slDist = atr[1] * ATR_SL_Multi;
   double tpDist = slDist * 2.0;
   string cmt = StringFormat("VUNO|%s|%.0f%%", dId, conf * 100);
   
   if(signal == "BUY")
   {
      double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
      double sl  = ask - slDist;
      double tp  = ask + tpDist;
      double lot = CalcLotSymbol(sym, risk, slDist);
      if(lot>0) {
         if(Trade.Buy(lot, sym, 0, sl, tp, cmt)) {
             Print("BUY Executado [", sym, "] conf:", conf*100, "%");
         }
      }
   }
   else if(signal == "SELL")
   {
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      double sl  = bid + slDist;
      double tp  = bid - tpDist;
      double lot = CalcLotSymbol(sym, risk, slDist);
      if(lot>0) {
         if(Trade.Sell(lot, sym, 0, sl, tp, cmt)) {
            Print("SELL Executado [", sym, "] conf:", conf*100, "%");
         }
      }
   }
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& req, const MqlTradeResult& res)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   if(HistoryDealSelect(trans.deal))
   {
      double profit     = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
      if(profit == 0)   return;

      double entryPrice = HistoryDealGetDouble(trans.deal,  DEAL_PRICE);
      double lot        = HistoryDealGetDouble(trans.deal,  DEAL_VOLUME);
      long   dealTicket = HistoryDealGetInteger(trans.deal, DEAL_TICKET);
      long   orderTkt   = HistoryDealGetInteger(trans.deal, DEAL_ORDER);
      string sym        = HistoryDealGetString(trans.deal, DEAL_SYMBOL);
      
      double sl = 0, tp = 0;
      if(HistoryOrderSelect(orderTkt)) {
         sl = HistoryOrderGetDouble(orderTkt, ORDER_SL);
         tp = HistoryOrderGetDouble(orderTkt, ORDER_TP);
      }
      
      string dealMod = TradingMode;
      string dealCmt = HistoryDealGetString(trans.deal, DEAL_COMMENT);
      string decisionId = ExtractDecisionIdFromComment(dealCmt);
      if(decisionId == "" && HistoryOrderSelect(orderTkt)) {
          decisionId = ExtractDecisionIdFromComment(HistoryOrderGetString(orderTkt, ORDER_COMMENT));
      }
      
      g_dailyPnL += profit;
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal > g_peakBal) g_peakBal = bal;
      
      string msg = StringFormat(
         "{\"type\":\"TRADE_RESULT\",\"ticket\":\"%d\",\"decision_id\":\"%s\","
         "\"mode\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\","
         "\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"entry_price\":%.5f,"
         "\"stop_loss\":%.5f,\"take_profit\":%.5f,\"lot\":%.2f,\"profit\":%.2f,"
         "\"points\":0,\"symbol\":\"%s\"}",
         dealTicket, decisionId, dealMod, UserID, OrganizationID, RobotID, RobotToken,
         entryPrice, sl, tp, lot, profit, sym
      );
      SendToCloud("/api/mt5/signal", msg);
   }
}

//+------------------------------------------------------------------+
string CollectCandlesSymbol(string sym, int bars)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(sym, PERIOD_CURRENT, 0, bars, rates);
   if(copied < 50) return "";
   
   string json = "[";
   for(int i = copied - 1; i >= 0; i--) {
      json += StringFormat(
         "[%d,%.5f,%.5f,%.5f,%.5f,%.0f]%s",
         (int)rates[i].time, rates[i].open, rates[i].high, rates[i].low, rates[i].close,
         (double)rates[i].tick_volume, (i > 0 ? "," : "")
      );
   }
   json += "]";
   return json;
}

//+------------------------------------------------------------------+
int CountAllPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionInfo.SelectByIndex(i))
         if(PositionInfo.Magic() == 20260331) count++;
   return count;
}

//+------------------------------------------------------------------+
double CalcLotSymbol(string sym, double rPct, double slPts)
{
   if(slPts <= 0) return 0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double rAmt = bal * rPct / 100;
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double lmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double lmax = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double lstp = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(tv==0 || ts==0) return 0;
   double lots = rAmt / (slPts / ts * tv);
   lots = MathFloor(lots / lstp) * lstp;
   return MathMax(lmin, MathMin(lmax, lots));
}

//+------------------------------------------------------------------+
// Auxiliares originais adaptados...

bool SafetyOK()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peakBal > 0) {
      double dd = (g_peakBal - equity) / g_peakBal * 100;
      if(dd >= MaxDrawdown) return false;
   }
   double dLimit = g_initialBal * MaxDailyLoss / 100;
   if(g_dailyPnL < -dLimit) return false;
   return true;
}

bool TradingHour()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   string t = StringFormat("%02d:%02d", dt.hour, dt.min);
   return (t >= TradingStart && t <= TradingEnd);
}

void ResetDaily()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d 00:00", dt.year, dt.mon, dt.day));
   if(today > g_lastReset) { g_dailyPnL = 0; g_lastReset = today; }
}

bool IsUuidLike(string v)
{
   if(StringLen(v) != 36) return false;
   for(int i=0; i<36; i++) {
      ushort c = StringGetCharacter(v, i);
      if(i==8 || i==13 || i==18 || i==23) { if(c!='-') return false; continue; }
      if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')||(c>='A'&&c<='F'))) return false;
   }
   return true;
}

bool IdentityReady()
{
   if(IsUuidLike(UserID) && IsUuidLike(OrganizationID) && IsUuidLike(RobotID) && StringLen(RobotToken) >= 16) return true;
   if(!g_identityWarned) { Print("AVISO: Identidade Vuno incompleta."); g_identityWarned = true; }
   return false;
}

//+------------------------------------------------------------------+
// Comunicação HTTPS com Render (sem Python local)
//+------------------------------------------------------------------+
string SendToCloud(string path, string body)
{
   string url     = BackendURL + path;
   string headers = "Content-Type: application/json\r\n";
   uchar  bodyArr[], resArr[];
   string resHeaders;
   StringToCharArray(body, bodyArr, 0, StringLen(body));

   int code = WebRequest("POST", url, headers, 8000, bodyArr, resArr, resHeaders);
   if(code == 200)
      return CharArrayToString(resArr);

   if(code == -1)
      Print("[Cloud] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas");
   else
      Print("[Cloud] Erro HTTP ", code, " ao contactar Render");

   return "";
}

void SendHeartbeat()
{
   string url = BackendURL + "/api/mt5/heartbeat";
   string heads = "Content-Type: application/json\r\n";
   string body = StringFormat("{\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\",\"mode\":\"%s\"}", RobotID, RobotToken, UserID, OrganizationID, TradingMode);
   uchar ba[], ra[]; string rh;
   StringToCharArray(body, ba, 0, StringLen(body));
   WebRequest("POST", url, heads, 5000, ba, ra, rh);
}

string ExtractString(string json, string key) {
   string search = "\"" + key + "\":\"";
   int start = StringFind(json, search);
   if(start < 0) return "";
   start += StringLen(search);
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   return StringSubstr(json, start, end - start);
}
double ExtractDouble(string json, string key) {
   string search = "\"" + key + "\":";
   int start = StringFind(json, search);
   if(start < 0) return 0;
   start += StringLen(search);
   int end = start;
   while(end < StringLen(json)) {
      ushort c = StringGetCharacter(json, end);
      if(c == ',' || c == '}') break;
      end++;
   }
   return StringToDouble(StringSubstr(json, start, end - start));
}
string ExtractDecisionIdFromComment(string comment) {
   int p1 = StringFind(comment, "VUNO|");
   if(p1 < 0) return "";
   p1 += 5;
   int p2 = StringFind(comment, "|", p1);
   if(p2 <= p1) return "";
   return StringSubstr(comment, p1, p2 - p1);
}
string TFToString(ENUM_TIMEFRAMES tf) {
   return "M"+IntegerToString(PeriodSeconds(tf)/60);
}
void OnDeinit(const int reason) {
   EventKillTimer();
   for(int i=0; i<ArraySize(arrATR); i++) IndicatorRelease(arrATR[i]);
}
