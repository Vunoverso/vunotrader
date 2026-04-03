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
double         g_runtimeMaxDrawdownPct = 0;
double         g_runtimeDailyLossMoney = -1;
string         g_runtimeTradingStart = "";
string         g_runtimeTradingEnd = "";
string         g_runtimeAllowedSymbols = "";

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
   g_runtimeMaxDrawdownPct = MaxDrawdown;
   g_runtimeTradingStart = TradingStart;
   g_runtimeTradingEnd = TradingEnd;

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

   //--- Montar payload com identificação Vuno e INFO de posição atual
   string openPosInfo = ",\"open_side\":null,\"open_entry\":null,\"open_sl\":null,\"open_tp\":null";
   
   // Verifica se já temos posição aberta para este símbolo (VUNO)
   if(PositionSelect(_Symbol))
   {
      if(PositionGetInteger(POSITION_MAGIC) == 20260330)
      {
         string side = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY ? "buy" : "sell");
         openPosInfo = StringFormat(
            ",\"open_side\":\"%s\",\"open_entry\":%.5f,\"open_sl\":%.5f,\"open_tp\":%.5f",
            side, PositionGetDouble(POSITION_PRICE_OPEN), PositionGetDouble(POSITION_SL), PositionGetDouble(POSITION_TP)
         );
      }
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
      "\"candles\":%s%s,"
      "\"balance\":%.2f}",
      _Symbol,
      TFToString(PERIOD_CURRENT),
      effMode,
      UserID,
      OrganizationID,
      RobotID,
      RobotToken,
      candles,
      openPosInfo,
      AccountInfoDouble(ACCOUNT_BALANCE)
   );

   string response = SendToCloud("/api/mt5/signal", request);
   if(response == "")
   {
      string fallbackSignal = LocalFallbackSignal(_Symbol);
      Print("[Fallback] API indisponivel | sinal local=", fallbackSignal, " | execucao bloqueada sem decision_id");
      return;
   }

   ApplyRuntimeConfig(response);

   // ── Sincronizar modo com o painel Vuno (user_mode retornado pelo backend) ──
   string cloudMode = ExtractString(response, "user_mode");
   if(cloudMode != "" && cloudMode != "null")
   {
      effMode = cloudMode;
      static datetime lastModeLog = 0;
      if(TimeCurrent() - lastModeLog > 300) {
         Print("[Vuno] Modo sincronizado com painel: ", cloudMode);
         lastModeLog = TimeCurrent();
      }
   }

   if(!SafetyOK() || !TradingHour())
      effMode = "observer";

   // Se o brain enviou um comando de FECHAMENTO (Smart Exit)
   string signal = ExtractString(response, "signal");
   if(signal == "CLOSE_BUY" || signal == "CLOSE_SELL")
   {
      if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC) == 20260330)
      {
         if(Trade.PositionClose(_Symbol))
            Print("SMART EXIT: Posição encerrada antecipadamente por confirmação Price Action.");
      }
      return;
   }

   // ── GESTÃO ADICIONAL: Trailing Stop Automático ──
   if(PositionSelect(_Symbol) && PositionGetInteger(POSITION_MAGIC) == 20260330)
   {
      ApplyTrailingStop();
   }

   // Se modo efetivo era observer, descarta trade APÓS registrar na nuvem
   if(effMode == "observer") return; 

   //--- Parsear resposta do sinal
   double confidence = ExtractDouble(response, "confidence");
   double risk       = SafeRisk(ExtractDouble(response, "risk"));
   string decisionId = ExtractString(response, "decision_id"); // UUID do brain

   if(signal == "HOLD" || risk <= 0) return;

   if(!SymbolAllowedByRuntime(_Symbol))
   {
      Print("[Vuno] Ativo fora da lista permitida no painel: ", _Symbol);
      return;
   }

   if(!MarketOpen(_Symbol, signal))
   {
      Print("[Vuno] Mercado fechado ou lado bloqueado para ", _Symbol, " | sinal=", signal);
      return;
   }

   double spreadPts = 0;
   string spreadReason = "";
   if(!SpreadOK(_Symbol, spreadPts, spreadReason))
   {
      Print("[Vuno] Execucao bloqueada em ", _Symbol, " | ", spreadReason);
      return;
   }

   // ── TRAVA DIRECIONAL (Anti-Hedge) ──
   // Se já houver posição, não abre outra (mesmo que seja na mesma direção, para evitar overtrading)
   if(CountPositions() > 0)
   {
      static datetime lastLog = 0;
      if(TimeCurrent() - lastLog > 300) 
      {
         Print("[Vuno] TRAVA Anti-Hedge: Ja existe posicao aberta para ", _Symbol, ". Ignorando novas entradas.");
         lastLog = TimeCurrent();
      }
      return;
   }

   if(decisionId == "")
   {
      Print("SINAL ignorado: decision_id ausente na resposta do brain");
      return;
   }

   int openTotal = CountPositions(); // redundante pelo check anterior mas mantido por segurança
   if(openTotal >= MaxPositions) return;

   //--- Calcular SL/TP com ATR
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(hATR, 0, 0, 2, atr) < 2)
   {
      Print("[Trade] Falha ao copiar ATR para ", _Symbol, ". Ordem abortada.");
      return;
   }

   double slDist = atr[1] * ATR_SL_Multi;
   double tpDist = slDist * 2.0; // RR 1:2 default (agora customizável via Cloud)

   // decision_id viaja no comment do trade para ser recuperado em OnTradeTransaction
   // Formato: "VUNO|<decision_id>|<confiança>"
   string tradeComment = StringFormat("VUNO|%s|%.0f%%", decisionId, confidence * 100);

   double lot = CalcLot(risk, slDist);
   if(lot <= 0)
   {
      Print("[Trade] ", signal, " bloqueado [", _Symbol, "] lote calculado zero | risk=", DoubleToString(risk, 3), " | slDist=", DoubleToString(slDist, 5));
      return;
   }

   ulong ticket = 0;
   double fillPrice = 0;
   double sl = 0;
   double tp = 0;
   if(!ExecuteOrder(_Symbol, signal, lot, slDist, tpDist, tradeComment, ticket, fillPrice, sl, tp))
      return;

   string side = signal == "BUY" ? "buy" : "sell";
   string openMsg = StringFormat(
      "{\"decision_id\":\"%s\",\"ticket\":\"%I64u\",\"symbol\":\"%s\",\"side\":\"%s\","
      "\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"lot\":%.2f,"
      "\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\","
      "\"balance\":%.2f}",
      decisionId, ticket, _Symbol, side, fillPrice, sl, tp, lot,
      RobotID, RobotToken, UserID, OrganizationID,
      AccountInfoDouble(ACCOUNT_BALANCE)
   );
   SendToCloud("/api/mt5/trade-opened", openMsg);

   Print(signal, " executado | Conf: ", DoubleToString(confidence * 100, 1),
         "% | Ticket: ", IntegerToString((int)ticket));
}

//+------------------------------------------------------------------+
// Gerencia Trailing Stop / Break Even
//+------------------------------------------------------------------+
void ApplyTrailingStop()
{
   double priceOpen = PositionGetDouble(POSITION_PRICE_OPEN);
   double currentPrice = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double currentSL = PositionGetDouble(POSITION_SL);
   
   // Break Even: Se atingir 1:1 do risco (lucro >= distância inicial do stop), move SL para o preço de entrada
   if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
   {
      double slDist = priceOpen - currentSL;
      if(slDist > 0 && currentPrice >= (priceOpen + slDist))
      {
         if(currentSL < priceOpen) // Move para BE apenas se ainda não estiver no lucro
         {
            if(Trade.PositionModify(_Symbol, priceOpen, PositionGetDouble(POSITION_TP)))
               Print("TRAILING: SL movido para Break Even (COMPRA)");
         }
      }
   }
   else if(PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_SELL)
   {
      double slDist = currentSL - priceOpen;
      if(slDist > 0 && currentPrice <= (priceOpen - slDist))
      {
         if(currentSL > priceOpen) // Move para BE apenas se ainda não estiver no lucro
         {
            if(Trade.PositionModify(_Symbol, priceOpen, PositionGetDouble(POSITION_TP)))
               Print("TRAILING: SL movido para Break Even (VENDA)");
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
         "\"symbol\":\"%s\","
         "\"balance\":%.2f}",
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
         _Symbol,
         AccountInfoDouble(ACCOUNT_BALANCE)
      );
      SendToCloud("/api/mt5/trade-outcome", msg);

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
   string responseText = CharArrayToString(resArr);
   if(code == 200)
      return responseText;

   if(code == -1)
      Print("[Cloud] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas | rota=", path);
   else
      Print("[Cloud] Erro HTTP ", code, " ao contactar Render | rota=", path, " | resposta=", responseText);

   return "";
}

bool ExecuteOrder(string sym, string signal, double lot, double slDist, double tpDist, string comment, ulong &ticket, double &fillPrice, double &sl, double &tp)
{
   int maxRetries = 3;
   ticket = 0;
   fillPrice = 0;
   sl = 0;
   tp = 0;

   for(int i = 0; i < maxRetries; i++)
   {
      MqlTick tick;
      if(!LoadMarketTick(sym, tick))
      {
         Sleep(300);
         continue;
      }

      Trade.SetDeviationInPoints(20);
      Trade.SetTypeFillingBySymbol(sym);
      ResetLastError();

      bool result = false;
      if(signal == "BUY")
      {
         fillPrice = tick.ask;
         sl = fillPrice - slDist;
         tp = fillPrice + tpDist;
         result = Trade.Buy(lot, sym, fillPrice, sl, tp, comment);
      }
      else if(signal == "SELL")
      {
         fillPrice = tick.bid;
         sl = fillPrice + slDist;
         tp = fillPrice - tpDist;
         result = Trade.Sell(lot, sym, fillPrice, sl, tp, comment);
      }

      if(result)
      {
         ticket = Trade.ResultOrder();
         double executedPrice = Trade.ResultPrice();
         if(executedPrice > 0)
            fillPrice = executedPrice;
         return true;
      }

      LogTradeFailure(signal, lot, fillPrice, sl, tp);
      Sleep(300);
   }

   Print("[Trade] FALHA AO EXECUTAR ORDEM: ", sym, " | sinal=", signal);
   return false;
}

bool LoadMarketTick(string sym, MqlTick &tick)
{
   ZeroMemory(tick);
   if(!SymbolSelect(sym, true))
   {
      Print("[Market] SymbolSelect falhou para ", sym);
      return false;
   }

   for(int i = 0; i < 3; i++)
   {
      if(SymbolInfoTick(sym, tick) && tick.ask > 0 && tick.bid > 0)
         return true;
      Sleep(300);
   }

   Print("[Market] Sem preco valido para ", sym, " | ask=", DoubleToString(tick.ask, 5), " | bid=", DoubleToString(tick.bid, 5));
   return false;
}

bool MarketOpen(string sym, string signal)
{
   long mode = SymbolInfoInteger(sym, SYMBOL_TRADE_MODE);
   if(mode == SYMBOL_TRADE_MODE_FULL)
      return true;
   if(signal == "BUY" && mode == SYMBOL_TRADE_MODE_LONGONLY)
      return true;
   if(signal == "SELL" && mode == SYMBOL_TRADE_MODE_SHORTONLY)
      return true;
   return false;
}

bool SpreadOK(string sym, double &spreadPts, string &blockReason)
{
   MqlTick tick;
   if(!LoadMarketTick(sym, tick))
   {
      spreadPts = 0;
      blockReason = "Sem preco/tick para " + sym;
      return false;
   }

   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(point <= 0)
   {
      spreadPts = 0;
      blockReason = "Point invalido para " + sym;
      return false;
   }

   spreadPts = (tick.ask - tick.bid) / point;
   double maxSpread = MaxSpreadPointsForSymbol(sym);
   if(spreadPts > maxSpread)
   {
      blockReason = "Spread alto: " + DoubleToString(spreadPts, 1) + " pts";
      return false;
   }

   return true;
}

double SafeRisk(double risk)
{
   if(risk <= 0)
      return 0;
   if(risk > 1.0)
      return 1.0;
   return risk;
}

double MaxSpreadPointsForSymbol(string sym)
{
   if(StringFind(sym, "XAU") >= 0)
      return 80.0;
   if(StringFind(sym, "BTC") >= 0 || StringFind(sym, "ETH") >= 0)
      return 3000.0;
   return 30.0;
}

string LocalFallbackSignal(string sym)
{
   int fastHandle = iMA(sym, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE);
   int slowHandle = iMA(sym, PERIOD_CURRENT, 21, 0, MODE_EMA, PRICE_CLOSE);
   if(fastHandle == INVALID_HANDLE || slowHandle == INVALID_HANDLE)
   {
      if(fastHandle != INVALID_HANDLE) IndicatorRelease(fastHandle);
      if(slowHandle != INVALID_HANDLE) IndicatorRelease(slowHandle);
      return "HOLD";
   }

   double fast[];
   double slow[];
   ArraySetAsSeries(fast, true);
   ArraySetAsSeries(slow, true);
   bool ok = CopyBuffer(fastHandle, 0, 0, 1, fast) >= 1 && CopyBuffer(slowHandle, 0, 0, 1, slow) >= 1;
   IndicatorRelease(fastHandle);
   IndicatorRelease(slowHandle);

   if(!ok)
      return "HOLD";
   if(fast[0] > slow[0])
      return "BUY";
   if(fast[0] < slow[0])
      return "SELL";
   return "HOLD";
}

void ApplyRuntimeConfig(string response)
{
   double remoteMaxDrawdown = ExtractDouble(response, "max_drawdown_pct");
   double remoteDailyLoss = ExtractDouble(response, "daily_loss_limit");
   string remoteStart = NormalizeTimeWindowValue(ExtractString(response, "trading_start"));
   string remoteEnd = NormalizeTimeWindowValue(ExtractString(response, "trading_end"));
   string remoteAllowed = ExtractString(response, "allowed_symbols");

   g_runtimeMaxDrawdownPct = remoteMaxDrawdown > 0 ? remoteMaxDrawdown : MaxDrawdown;
   g_runtimeDailyLossMoney = remoteDailyLoss > 0 ? remoteDailyLoss : -1;
   g_runtimeTradingStart = remoteStart != "" ? remoteStart : TradingStart;
   g_runtimeTradingEnd = remoteEnd != "" ? remoteEnd : TradingEnd;

   if(remoteAllowed != "" && remoteAllowed != "null")
   {
      StringReplace(remoteAllowed, " ", "");
      g_runtimeAllowedSymbols = remoteAllowed;
   }
   else
   {
      g_runtimeAllowedSymbols = "";
   }
}

bool SymbolAllowedByRuntime(string sym)
{
   if(g_runtimeAllowedSymbols == "") return true;
   string haystack = "," + g_runtimeAllowedSymbols + ",";
   string needle = "," + sym + ",";
   return StringFind(haystack, needle) >= 0;
}

string NormalizeTimeWindowValue(string value)
{
   if(value == "" || value == "null") return "";
   if(StringLen(value) >= 5) return StringSubstr(value, 0, 5);
   return value;
}

void LogTradeFailure(string side, double lot, double price, double sl, double tp)
{
   Print(
      "[Trade] ", side, " falhou [", _Symbol, "] lot=", DoubleToString(lot, 2),
      " | price=", DoubleToString(price, 5),
      " | sl=", DoubleToString(sl, 5),
      " | tp=", DoubleToString(tp, 5),
      " | retcode=", IntegerToString((int)Trade.ResultRetcode()),
      " | desc=", Trade.ResultRetcodeDescription()
   );
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
   double maxDrawdownPct = g_runtimeMaxDrawdownPct > 0 ? g_runtimeMaxDrawdownPct : MaxDrawdown;

   if(g_peakBal > 0)
   {
      double dd = (g_peakBal - equity) / g_peakBal * 100;
      if(dd >= maxDrawdownPct)
      {
         Print("STOP: Drawdown ", DoubleToString(dd, 1), "%");
         return false;
      }
   }

   if(g_runtimeDailyLossMoney > 0)
   {
      if(g_dailyPnL < -g_runtimeDailyLossMoney)
      {
         Print("STOP: Perda diária ", DoubleToString(g_dailyPnL, 2), " | limite remoto: ", DoubleToString(g_runtimeDailyLossMoney, 2));
         return false;
      }
      return true;
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
   string start = NormalizeTimeWindowValue(g_runtimeTradingStart);
   string end = NormalizeTimeWindowValue(g_runtimeTradingEnd);
   if(start == "" || end == "") return true;
   return (t >= start && t <= end);
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
   int total = PositionsTotal();
   
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         if(PositionGetInteger(POSITION_MAGIC) == 20260330 &&
            PositionGetString(POSITION_SYMBOL) == _Symbol)
         {
            count++;
         }
      }
   }
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
      "\"mode\":\"%s\","
      "\"balance\":%.2f,"
      "\"positions\":%s}",
      RobotID, RobotToken, UserID, OrganizationID, TradingMode,
      AccountInfoDouble(ACCOUNT_BALANCE),
      CollectPositionsJson()
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
         "\"robot_token\":\"%s\","
         "\"balance\":%.2f}",
         UserID, OrganizationID, RobotID, RobotToken,
         AccountInfoDouble(ACCOUNT_BALANCE)
      );
      string r = SendToPython(req);
      if(r != "") Print("[HB] Fallback Python local OK");
      else Print("[HB] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas");
   } else {
      Print("[HB] Erro HTTP ", code, " ao contactar Render | resposta=", CharArrayToString(resArr));
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

//+------------------------------------------------------------------+
// Coleta todas as posicoes abertas em formato JSON para sincronizar com o painel
//+------------------------------------------------------------------+
string CollectPositionsJson()
{
   string json = "[";
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket))
      {
         string sym    = PositionGetString(POSITION_SYMBOL);
         long   type   = PositionGetInteger(POSITION_TYPE);
         double vol    = PositionGetDouble(POSITION_VOLUME);
         double prc    = PositionGetDouble(POSITION_PRICE_OPEN);
         double prof   = PositionGetDouble(POSITION_PROFIT);
         double sl     = PositionGetDouble(POSITION_SL);
         double tp     = PositionGetDouble(POSITION_TP);
         string cmt    = PositionGetString(POSITION_COMMENT);
         string dId    = ExtractDecisionIdFromComment(cmt);

         if(count > 0) json += ",";
         json += StringFormat("{\"ticket\":%I64u,\"symbol\":\"%s\",\"side\":\"%s\",\"volume\":%.2f,\"price\":%.5f,\"profit\":%.2f,\"sl\":%.5f,\"tp\":%.5f,\"decision_id\":\"%s\"}",
            ticket, sym, (type == POSITION_TYPE_BUY ? "buy" : "sell"), vol, prc, prof, sl, tp, dId);
         count++;
      }
   }
   json += "]";
   return json;
}

