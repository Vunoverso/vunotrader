//+------------------------------------------------------------------+
//| VunoTrader v2 — MT5 Client (conecta ao Python Brain)            |
//| Versão: 2.1 | 30/03/2026                                        |
//| Recebe sinais do ML Python via socket TCP                        |
//| Envia user_id, org_id e repassa decision_id ao brain             |
//+------------------------------------------------------------------+

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

input group "=== CONEXÃO CLOUD ==="
input string   BackendURL       = "https://vunotrader-api.onrender.com"; // URL do backend Render
input int      DataBars         = 200;           // Candles enviados ao Render

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
CPositionInfo  PositionInfo;

int            hATR;
double         g_dailyPnL      = 0;
double         g_initialBal    = 0;
double         g_peakBal       = 0;
datetime       g_lastReset     = 0;
datetime       g_lastSignal    = 0;
int            g_signalDelay   = 30; // segundos entre sinais
bool           g_identityWarned = false;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(20260330);
   Trade.SetDeviationInPoints(10);

   hATR = iATR(_Symbol, PERIOD_CURRENT, 14);
   if(hATR == INVALID_HANDLE)
   {
      Print("ERRO: Falha ao criar ATR");
      return INIT_FAILED;
   }

   g_initialBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_peakBal    = g_initialBal;

   EventSetTimer(30); // Heartbeat a cada 30 segundos

   Print("VunoTrader v2 iniciado | Backend: ", BackendURL);
         
   // Envia primeiro heartbeat imediato ao iniciar
   if(IdentityReady()) {
      SendHeartbeat();
   }         
         
   return INIT_SUCCEEDED;
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

   double slDist = atr[1] * ATR_SL_Multi;
   double tpDist = slDist * 2.0; // RR 1:2

   // decision_id viaja no comment do trade para ser recuperado em OnTradeTransaction
   // Formato: "VUNO|<decision_id>|<confiança>"
   string tradeComment = StringFormat("VUNO|%s|%.0f%%", decisionId, confidence * 100);

   if(signal == "BUY")
   {
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl  = ask - slDist;
      double tp  = ask + tpDist;
      double lot = CalcLot(risk, slDist);

      if(lot > 0)
      {
         if(Trade.Buy(lot, _Symbol, 0, sl, tp, tradeComment))
         {
            Print("BUY executado | Conf: ", DoubleToString(confidence * 100, 1),
                  "% | Risk: ", risk, "% | Lot: ", lot,
                  " | DecisionID: ", decisionId);
         }
      }
   }
   else if(signal == "SELL")
   {
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl  = bid + slDist;
      double tp  = bid - tpDist;
      double lot = CalcLot(risk, slDist);

      if(lot > 0)
      {
         if(Trade.Sell(lot, _Symbol, 0, sl, tp, tradeComment))
         {
            Print("SELL executado | Conf: ", DoubleToString(confidence * 100, 1),
                  "% | Risk: ", risk, "% | Lot: ", lot,
                  " | DecisionID: ", decisionId);
         }
      }
   }
}

//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   if(HistoryDealSelect(trans.deal))
   {
      double profit     = HistoryDealGetDouble(trans.deal, DEAL_PROFIT);
      if(profit == 0)   return; // deals de abertura não têm lucro

      double entryPrice = HistoryDealGetDouble(trans.deal,  DEAL_PRICE);
      double lot        = HistoryDealGetDouble(trans.deal,  DEAL_VOLUME);
      long   dealTicket = HistoryDealGetInteger(trans.deal, DEAL_TICKET);
      long   orderTkt   = HistoryDealGetInteger(trans.deal, DEAL_ORDER);

      //--- Recuperar SL/TP da ordem original
      double sl = 0, tp = 0;
      if(HistoryOrderSelect(orderTkt))
      {
         sl = HistoryOrderGetDouble(orderTkt, ORDER_SL);
         tp = HistoryOrderGetDouble(orderTkt, ORDER_TP);
      }

      //--- Extrair decision_id do comment do deal ("VUNO|<uuid>|<conf>")
      string dealComment = HistoryDealGetString(trans.deal, DEAL_COMMENT);
      string decisionId  = ExtractDecisionIdFromComment(dealComment);

      // Fallback: alguns brokers mudam o comment do deal; tentar comment da order
      if(decisionId == "" && HistoryOrderSelect(orderTkt))
      {
         string orderComment = HistoryOrderGetString(orderTkt, ORDER_COMMENT);
         decisionId = ExtractDecisionIdFromComment(orderComment);
      }

      g_dailyPnL += profit;
      double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
      if(bal > g_peakBal) g_peakBal = bal;

      //--- Reportar resultado completo ao Python Brain
      string msg = StringFormat(
         "{\"type\":\"TRADE_RESULT\","
         "\"ticket\":\"%d\","
         "\"decision_id\":\"%s\","
         "\"mode\":\"%s\","
         "\"user_id\":\"%s\","
         "\"organization_id\":\"%s\","
         "\"robot_id\":\"%s\","
         "\"robot_token\":\"%s\","
         "\"entry_price\":%.5f,"
         "\"stop_loss\":%.5f,"
         "\"take_profit\":%.5f,"
         "\"lot\":%.2f,"
         "\"profit\":%.2f,"
         "\"points\":0,"
         "\"symbol\":\"%s\"}",
         dealTicket,
         decisionId,
         TradingMode,
         UserID,
         OrganizationID,
         RobotID,
         RobotToken,
         entryPrice,
         sl,
         tp,
         lot,
         profit,
         _Symbol
      );
      SendToCloud("/api/mt5/signal", msg);

      Print("Resultado: ", (profit > 0 ? "WIN" : "LOSS"),
            " | P&L: ",    DoubleToString(profit, 2),
            " | P&L Dia: ", DoubleToString(g_dailyPnL, 2),
            " | Ticket: ",  dealTicket,
            " | DecisionID: ", (StringLen(decisionId) > 0 ? decisionId : "n/a"));
   }
}

//+------------------------------------------------------------------+
// Converter timeframe em string legível (ex: PERIOD_M5 → "M5")
//+------------------------------------------------------------------+
string TFToString(ENUM_TIMEFRAMES tf)
{
   switch(tf)
   {
      case PERIOD_M1:  return "M1";
      case PERIOD_M2:  return "M2";
      case PERIOD_M3:  return "M3";
      case PERIOD_M4:  return "M4";
      case PERIOD_M5:  return "M5";
      case PERIOD_M6:  return "M6";
      case PERIOD_M10: return "M10";
      case PERIOD_M12: return "M12";
      case PERIOD_M15: return "M15";
      case PERIOD_M20: return "M20";
      case PERIOD_M30: return "M30";
      case PERIOD_H1:  return "H1";
      case PERIOD_H2:  return "H2";
      case PERIOD_H3:  return "H3";
      case PERIOD_H4:  return "H4";
      case PERIOD_H6:  return "H6";
      case PERIOD_H8:  return "H8";
      case PERIOD_H12: return "H12";
      case PERIOD_D1:  return "D1";
      case PERIOD_W1:  return "W1";
      case PERIOD_MN1: return "MN1";
      default:         return "M5";
   }
}

//+------------------------------------------------------------------+
// Coletar candles e formatar como JSON
//+------------------------------------------------------------------+
string CollectCandles(int bars)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);

   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, bars, rates);
   if(copied < 50) return "";

   string json = "[";
   for(int i = copied - 1; i >= 0; i--)
   {
      json += StringFormat(
         "[%d,%.5f,%.5f,%.5f,%.5f,%.0f]%s",
         (int)rates[i].time,
         rates[i].open,
         rates[i].high,
         rates[i].low,
         rates[i].close,
         (double)rates[i].tick_volume,
         (i > 0 ? "," : "")
      );
   }
   json += "]";
   return json;
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

//+------------------------------------------------------------------+
// Calcular lote baseado em risco %
//+------------------------------------------------------------------+
double CalcLot(double riskPct, double slPoints)
{
   if(slPoints <= 0) return 0;

   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmt   = balance * riskPct / 100;
   double tickVal   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotMin    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotMax    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(tickVal == 0 || tickSize == 0) return 0;

   double lots = riskAmt / (slPoints / tickSize * tickVal);
   lots = MathFloor(lots / lotStep) * lotStep;
   return MathMax(lotMin, MathMin(lotMax, lots));
}

//+------------------------------------------------------------------+
// Segurança
//+------------------------------------------------------------------+
bool SafetyOK()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(g_peakBal > 0)
   {
      double dd = (g_peakBal - equity) / g_peakBal * 100;
      if(dd >= MaxDrawdown)
      {
         Print("STOP: Drawdown ", DoubleToString(dd, 1), "%");
         return false;
      }
   }

   double dailyLimit = g_initialBal * MaxDailyLoss / 100;
   if(g_dailyPnL < -dailyLimit)
   {
      Print("STOP: Perda diária ", DoubleToString(g_dailyPnL, 2));
      return false;
   }

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
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d 00:00",
                                              dt.year, dt.mon, dt.day));
   if(today > g_lastReset)
   {
      g_dailyPnL  = 0;
      g_lastReset = today;
   }
}

int CountPositions()
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionInfo.SelectByIndex(i))
         if(PositionInfo.Magic() == 20260330 &&
            PositionInfo.Symbol() == _Symbol)
            count++;
   return count;
}

//+------------------------------------------------------------------+
// Parsear JSON simples
//+------------------------------------------------------------------+
string ExtractString(string json, string key)
{
   string search = "\"" + key + "\":\"";
   int start = StringFind(json, search);
   if(start < 0) return "";
   start += StringLen(search);
   int end = StringFind(json, "\"", start);
   if(end < 0) return "";
   return StringSubstr(json, start, end - start);
}

string ExtractDecisionIdFromComment(string comment)
{
   int p1 = StringFind(comment, "VUNO|");
   if(p1 < 0) return "";

   p1 += 5; // pular "VUNO|"
   int p2 = StringFind(comment, "|", p1);
   if(p2 <= p1) return "";

   return StringSubstr(comment, p1, p2 - p1);
}

bool IsUuidLike(string value)
{
   if(StringLen(value) != 36) return false;

   for(int i = 0; i < 36; i++)
   {
      ushort c = StringGetCharacter(value, i);
      if(i == 8 || i == 13 || i == 18 || i == 23)
      {
         if(c != '-') return false;
         continue;
      }

      bool isDigit = (c >= '0' && c <= '9');
      bool isHexLower = (c >= 'a' && c <= 'f');
      bool isHexUpper = (c >= 'A' && c <= 'F');
      if(!isDigit && !isHexLower && !isHexUpper) return false;
   }

   return true;
}

bool IdentityReady()
{
   bool ok = IsUuidLike(UserID) && IsUuidLike(OrganizationID) && IsUuidLike(RobotID) && StringLen(RobotToken) >= 16;
   if(ok) return true;

   if(!g_identityWarned)
   {
      Print("VUNO IDENTIDADE: configure UserID, OrganizationID, RobotID (UUID) e RobotToken valido para integrar MT5 -> brain -> Supabase.");
      g_identityWarned = true;
   }

   return false;
}

double ExtractDouble(string json, string key)
{
   string search = "\"" + key + "\":";
   int start = StringFind(json, search);
   if(start < 0) return 0;
   start += StringLen(search);
   int end = start;
   while(end < StringLen(json))
   {
      ushort c = StringGetCharacter(json, end);
      if(c == ',' || c == '}') break;
      end++;
   }
   return StringToDouble(StringSubstr(json, start, end - start));
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   IndicatorRelease(hATR);
   Print("VunoTrader v2 encerrado");
}

//+------------------------------------------------------------------+
// Envia heartbeat HTTPS direto ao backend Render (sem Python local)
//+------------------------------------------------------------------+
void SendHeartbeat()
{
   string url     = BackendURL + "/api/mt5/heartbeat";
   string headers = "Content-Type: application/json\r\n";
   string body    = StringFormat(
      "{\"robot_id\":\"%s\","
      "\"robot_token\":\"%s\","
      "\"user_id\":\"%s\","
      "\"organization_id\":\"%s\","
      "\"mode\":\"%s\"}",
      RobotID, RobotToken, UserID, OrganizationID, TradingMode
   );

   uchar  bodyArr[], resArr[];
   string resHeaders;
   StringToCharArray(body, bodyArr, 0, StringLen(body));

   int code = WebRequest("POST", url, headers, 5000, bodyArr, resArr, resHeaders);
   if(code == 200) {
      Print("[HB] Heartbeat enviado com sucesso → Render");
   } else if(code == -1) {
      // Fallback: tenta Python local se ainda estiver rodando
      string req = StringFormat(
         "{\"type\":\"HEARTBEAT\",\"user_id\":\"%s\","
         "\"organization_id\":\"%s\",\"robot_id\":\"%s\","
         "\"robot_token\":\"%s\"}",
         UserID, OrganizationID, RobotID, RobotToken
      );
      string r = SendToPython(req);
      if(r != "") Print("[HB] Fallback Python local OK");
      else Print("[HB] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas");
   } else {
      Print("[HB] Erro HTTP ", code, " ao contactar Render");
   }
}

//+------------------------------------------------------------------+
// Timer: dispara heartbeat a cada 30 segundos
//+------------------------------------------------------------------+
void OnTimer()
{
   if(!IdentityReady()) return;
   SendHeartbeat();
}
