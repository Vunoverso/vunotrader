//+------------------------------------------------------------------+
//| VunoTrader v2 — Cloud Enabled                                    |
//| Conecta diretamente ao Render via HTTPS (WebRequest)             |
//+------------------------------------------------------------------+

#include <Trade\Trade.mqh>

input group "=== CONEXÃO CLOUD ==="
input string   BackendURL       = "https://vunotrader-api.onrender.com";

input group "=== GESTÃO ==="
input double   MaxDailyLoss     = 5.0;    // Perda máxima diária (%)
input double   MaxDrawdown      = 15.0;   // Drawdown máximo (%)
input int      MaxPositions     = 3;      // Máximo posições simultâneas
input double   ATR_SL_Multi     = 2.0;   // Multiplicador ATR para SL
input string   TradingStart     = "08:00";
input string   TradingEnd       = "20:00";

input group "=== IDENTIFICAÇÃO VUNO (Supabase) ==="
input string   UserID           = "0e3d7cd9-7e39-4714-a52f-f7eb793a4640";        // UUID do usuário (copiar do painel)
input string   OrganizationID   = "24affdc3-dc7b-4672-b20d-65033949bb76";        // UUID da organização (copiar do painel)
input string   RobotID          = "8e048faa-937c-4a3e-8760-9d59c3f64d77";        // UUID da instância do robô
input string   RobotToken       = "dBiAqxGYo2S6nxFtdNH7oufKa_MYGms0";        // token da instância do robô
input string   TradingMode      = "demo";    // Modo: observer | demo | real

CTrade         Trade;

// Globais
int            hATR;
datetime       g_lastSignal    = 0;
int            g_signalDelay   = 60;     // 60s entre envios
int            DataBars        = 200;
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
   
   hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(hATR == INVALID_HANDLE) return INIT_FAILED;

   g_initialBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_peakBal    = g_initialBal;
   
   // Inicia timer para Heartbeat (30s)
   EventSetTimer(30);

   Print("VunoTrader v2 iniciado | Identidade Supabase configurada.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(hATR);
   EventKillTimer();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   if(!IdentityReady()) return;
   SendHeartbeat();
}

//+------------------------------------------------------------------+
void OnTick()
{
   ResetDaily();
   if(!IdentityReady()) return;
   if(TimeCurrent() - g_lastSignal < g_signalDelay) return;

   g_lastSignal = TimeCurrent();

   //--- Coletar dados de mercado
   string candles = CollectCandles(DataBars);
   if(candles == "") return;

   //--- Determinar Modo Efetivo (Opera ou apenas Observa?)
   string effMode = TradingMode;
   bool safe      = SafetyOK();
   bool inHr      = TradingHour();
   
   if(!safe) {
      effMode = "observer";
      static datetime lastErrLog = 0;
      if(TimeCurrent() - lastErrLog > 600) {
         Print("Vuno: Forçando modo OBSERVER por SEGURANÇA (Limite de perda/drawdown atingido).");
         lastErrLog = TimeCurrent();
      }
   } else if(!inHr) {
      effMode = "observer";
      static datetime lastHrLog = 0;
      if(TimeCurrent() - lastHrLog > 600) {
         Print("Vuno: Forçando modo OBSERVER por HORÁRIO (Fora da janela configurada: ", TradingStart, " - ", TradingEnd, ")");
         lastHrLog = TimeCurrent();
      }
   }

   //--- Montar payload com identificação Vuno
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
      _Symbol,
      TFToString(PERIOD_CURRENT),
      effMode,
      UserID,
      OrganizationID,
      RobotID,
      RobotToken,
      candles
   );

   string response = SendToCloud("/api/mt5/signal", request);
   if(response == "") return;

   // Se modo efetivo era observer, descarta trade APÓS registrar na nuvem
   if(effMode == "observer") return; 

   //--- Parsear resposta
   string signal     = ExtractString(response, "signal");
   double confidence = ExtractDouble(response, "confidence");
   double risk       = ExtractDouble(response, "risk");
   string decisionId = ExtractString(response, "decision_id"); // UUID do brain

   if(signal == "HOLD" || risk <= 0) return;
   if(decisionId == "")
   {
      Print("SINAL ignorado: decision_id ausente na resposta do brain");
      return;
   }

   int openPos = CountPositions();
   if(openPos >= MaxPositions) return;

   //--- Calcular SL/TP com ATR
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(hATR, 0, 0, 2, atr) < 2) return;

   double currentATR = atr[1];
   double slPoints   = currentATR * ATR_SL_Multi;
   double tpPoints   = slPoints * 2.0; // r:r 1:2

   // Ticket do Vuno: usado no comentário para rastreabilidade via auditoria
   string comment = StringFormat("VUNO|%s|%.0f%%", decisionId, confidence * 100);

   if(signal == "BUY")
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = ask - slPoints;
      double tp  = ask + tpPoints;
      double lots = CalcLot(risk, slPoints);
      if(lots > 0) {
         if(Trade.Buy(lots, _Symbol, 0, sl, tp, comment))
            Print("BUY executado: ", _Symbol, " conf:", confidence*100, "% id:", decisionId);
      }
   }
   else if(signal == "SELL")
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl  = bid + slPoints;
      double tp  = bid - tpPoints;
      double lots = CalcLot(risk, slPoints);
      if(lots > 0) {
         if(Trade.Sell(lots, _Symbol, 0, sl, tp, comment))
            Print("SELL executado: ", _Symbol, " conf:", confidence*100, "% id:", decisionId);
      }
   }
}

//+------------------------------------------------------------------+
// Envia o resultado do trade para o Cloud (DEAL_ADD)
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans, const MqlTradeRequest& req, const MqlTradeResult& res)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   if(HistoryDealSelect(trans.deal))
   {
      double profit     = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
      if(profit == 0)   return; // Ignora entrada ou taxas sem profit real p/ cálculo diário

      double entryPrice = HistoryDealGetDouble(trans.deal,  DEAL_PRICE);
      double lot        = HistoryDealGetDouble(trans.deal,  DEAL_VOLUME);
      long   dealTicket = HistoryDealGetInteger(trans.deal, DEAL_TICKET);
      long   orderTkt   = HistoryDealGetInteger(trans.deal, DEAL_ORDER);
      
      double sl = 0, tp = 0;
      if(HistoryOrderSelect(orderTkt)) {
         sl = HistoryOrderGetDouble(orderTkt, ORDER_SL);
         tp = HistoryOrderGetDouble(orderTkt, ORDER_TP);
      }
      
      string dealMod = TradingMode;
      string dealCmt = HistoryDealGetString(trans.deal, DEAL_COMMENT);
      string decisionId = ExtractDecisionIdFromComment(dealCmt);
      
      // Tenta buscar do comentário da ordem se o deal estiver vazio
      if(decisionId == "" && HistoryOrderSelect(orderTkt)) {
          decisionId = ExtractDecisionIdFromComment(HistoryOrderGetString(orderTkt, ORDER_COMMENT));
      }

      g_dailyPnL += profit;
      double bal = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal > g_peakBal) g_peakBal = bal;

      // Montar JSON de resultado (Trade Performance Tracker)
      string msg = StringFormat(
         "{\"type\":\"TRADE_RESULT\",\"ticket\":\"%d\",\"decision_id\":\"%s\","
         "\"mode\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\","
         "\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"entry_price\":%.5f,"
         "\"stop_loss\":%.5f,\"take_profit\":%.5f,\"lot\":%.2f,\"profit\":%.2f,"
         "\"points\":0,\"symbol\":\"%s\"}",
         dealTicket, decisionId, dealMod, UserID, OrganizationID, RobotID, RobotToken,
         entryPrice, sl, tp, lot, profit, _Symbol
      );

      SendToCloud("/api/mt5/signal", msg);
   }
}

//+------------------------------------------------------------------+
// Auxiliares
//+------------------------------------------------------------------+

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
   if(today > g_lastReset) {
      g_dailyPnL = 0;
      g_lastReset = today;
   }
}

string CollectCandles(int bars)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, bars, rates);
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

double CalcLot(double riskPct, double slPoints)
{
   if(slPoints <= 0) return 0;
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt = bal * riskPct / 100;
   double tickVal = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotMin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(tickVal == 0 || tickSize == 0) return 0;
   double lots = riskAmt / (slPoints / tickSize * tickVal);
   lots = MathFloor(lots / lotStep) * lotStep;
   return MathMax(lotMin, MathMin(lotMax, lots));
}

int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionSelectByTicket(PositionGetTicket(i)))
         if(PositionGetInteger(POSITION_MAGIC) == 20260331) count++;
   return count;
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
   datetime now = TimeCurrent();
   if(now - g_lastHeartbeat < 30) return;
   
   string path = "/api/mt5/heartbeat";
   string body = StringFormat(
      "{\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\",\"mode\":\"%s\"}",
      RobotID, RobotToken, UserID, OrganizationID, TradingMode
   );
   SendToCloud(path, body);
   g_lastHeartbeat = now;
}

bool IdentityReady()
{
   if(StringLen(UserID) == 36 && StringLen(RobotID) == 36 && StringLen(RobotToken) >= 16) return true;
   if(!g_identityWarned) {
      Print("Vuno: ID ou Token incompletos nas configurações do robô.");
      g_identityWarned = true;
   }
   return false;
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
