//+------------------------------------------------------------------+
//| VunoScreener v3 — MT5 Multi-Asset Client (Conecta ao Python)     |
//| Rastreia uma lista de símbolos e envia dados iterativos.        |
//+------------------------------------------------------------------+

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

input group "=== CONEXÃO PYTHON ==="
input string   PythonHost       = "127.0.0.1";
input int      PythonPort       = 9999;
input int      DataBars         = 200;

input group "=== CONEXÃO CLOUD ==="
input string   BackendURL       = "https://vunotrader-api.onrender.com";

input group "=== GESTÃO SCREENER ==="
input string   AssetList        = "EURUSD,GBPUSD,XAUUSD"; // Moedas
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
string         g_lastSignal[];
double         g_lastConfidence[];
double         g_lastRisk[];
double         g_lastSpreadPoints[];
double         g_lastAtrPct[];
double         g_lastScore[];
string         g_lastRegime[];
string         g_lastReason[];
string         g_lastBlockReason[];
string         g_lastState[];
datetime       g_lastAnalyzedAt[];
double         g_dailyPnL      = 0;
double         g_initialBal    = 0;
double         g_peakBal       = 0;
datetime       g_lastReset     = 0;
bool           g_identityWarned= false;
datetime       g_lastHeartbeat = 0;
datetime       g_lastCycleAt   = 0;
int            g_cycleCounter  = 0;
string         g_panelStatus   = "INICIANDO";
string         g_panelMode     = "demo";
string         g_lastEvent     = "Aguardando primeiro ciclo";
double         g_runtimeMaxDrawdownPct = 0;
double         g_runtimeDailyLossMoney = -1;
string         g_runtimeTradingStart = "";
string         g_runtimeTradingEnd = "";
string         g_runtimeAllowedSymbols = "";

int    SymbolIndex(string sym);
void   InitPanelBuffers(int count);
void   UpdateSymbolPanel(int idx, string state, string signal, double confidence, double risk, double spreadPts, double atrPct, string regime, string reason, string blockReason);
double CalcSpreadPoints(string sym);
double CalcAtrPct(int handleATR, string sym);
int    CountPositionsBySymbol(string sym);
bool   ExecuteTrade(string sym, int handleATR, string signal, double conf, double risk, string dId);
bool   ExecuteOrder(string sym, string signal, double lot, double slDist, double tpDist, string comment, ulong &ticket, double &fillPrice, double &sl, double &tp);
bool   LoadMarketTick(string sym, MqlTick &tick);
bool   MarketOpen(string sym, string signal);
bool   SpreadOK(string sym, double &spreadPts, string &blockReason);
double SafeRisk(double risk);
double MaxSpreadPointsForSymbol(string sym);
string LocalFallbackSignal(string sym);
void   ApplyRuntimeConfig(string response);
bool   SymbolAllowedByRuntime(string sym);
string NormalizeTimeWindowValue(string value);
void   LogTradeFailure(string sym, string side, double lot, double price, double sl, double tp);
double CurrentDrawdownPct();
string BuildMood();
string Shorten(string value, int limit);
string FormatMoney(double value);
string FormatSignedMoney(double value);
void   NotifyTradeOpened(string decisionId, string sym, string side, ulong ticket, double price, double sl, double tp, double lot);
void   NotifyTradeOutcome(string decisionId, long ticket, string sym, string side, double profit, int points);
void   RenderPanel();

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
   InitPanelBuffers(count);
   
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
   g_runtimeMaxDrawdownPct = MaxDrawdown;
   g_runtimeTradingStart = TradingStart;
   g_runtimeTradingEnd = TradingEnd;
   
   // Screener de 5 segundos
   EventSetTimer(5);

   RenderPanel();

   Print("VunoScreener v3 iniciado | ", count, " ativos.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnTimer()
{
   ResetDaily();
   if(!IdentityReady()) {
      g_panelStatus = "IDENTIDADE";
      g_panelMode   = TradingMode;
      g_lastEvent   = "Preencha UserID, OrganizationID, RobotID e RobotToken validos.";
      RenderPanel();
      return;
   }
   
   // Controlar envio de Heartbeat a cada 30 segundos
   datetime now = TimeCurrent();
   if(now - g_lastHeartbeat >= 30) {
      SendHeartbeat();
      g_lastHeartbeat = now;
   }

   bool safe = SafetyOK();
   bool inHr = TradingHour();
   g_panelMode = TradingMode;
   if(!safe || !inHr)
      g_panelMode = "observer";
   g_panelStatus = (g_panelMode == "observer") ? "OBSERVANDO" : "RODANDO";
   
   // Verifica Nova Barra para cada símbolo e processa
   int count = ArraySize(arrSymbols);
   for(int i=0; i<count; i++) 
   {
      string sym = arrSymbols[i];
      datetime currentBar = iTime(sym, PERIOD_CURRENT, 0);
      double spreadPts = CalcSpreadPoints(sym);
      double atrPct    = CalcAtrPct(arrATR[i], sym);
      
      if(currentBar != arrLastBar[i] && currentBar > 0) 
      {
         g_cycleCounter++;
         g_lastCycleAt = now;
         arrLastBar[i] = currentBar; // Marcou nova barra
         
         // Coleta dados
         string candles = CollectCandlesSymbol(sym, DataBars);
         if(candles == "") {
            UpdateSymbolPanel(i, "ERRO", "HOLD", 0, 0, spreadPts, atrPct, "lateral", "candles_indisponiveis", "Sem candles suficientes");
            g_lastEvent = sym + ": coleta de candles indisponivel.";
            continue;
         }
         
         // Determina modo efetivo
         // Se Fora do horário ou Safety der false, envia como Observer
         string effMode = TradingMode;
         
         if(!safe) {
            effMode = "observer";
            static datetime lastLogSafe = 0;
            if(TimeCurrent() - lastLogSafe > 3600) {
                Print("Vuno: Modo Observador ATIVADO por Segurança (Limite de Perda/Drawdown)");
                lastLogSafe = TimeCurrent();
            }
         } else if(!inHr) {
            effMode = "observer";
            static datetime lastLogHr = 0;
            if(TimeCurrent() - lastLogHr > 3600) {
                Print("Vuno: Modo Observador ATIVADO por Horário (Fora da janela configurada)");
                lastLogHr = TimeCurrent();
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
            "\"candles\":%s,"
            "\"balance\":%.2f}",
            sym,
            TFToString(PERIOD_CURRENT),
            effMode,
            UserID,
            OrganizationID,
            RobotID,
            RobotToken,
            candles,
            AccountInfoDouble(ACCOUNT_BALANCE)
         );
         
         string response = SendToCloud("/api/mt5/signal", request);
         if(response == "") {
            string fallbackSignal = LocalFallbackSignal(sym);
            UpdateSymbolPanel(i, "LOCAL", fallbackSignal, 0.30, 0, spreadPts, atrPct, "fallback", "api_indisponivel", "Fallback local sem execucao");
            g_lastEvent = sym + ": API indisponivel, fallback local ativo sem execucao.";
            continue;
         }

         ApplyRuntimeConfig(response);

         string userMode = ExtractString(response, "user_mode");
         if(userMode != "") {
            effMode = userMode;
            g_panelMode = userMode;
         }

         if(!SafetyOK() || !TradingHour()) {
            effMode = "observer";
         }
         
         string signal     = ExtractString(response, "signal");
         double confidence = ExtractDouble(response, "confidence");
         double risk       = SafeRisk(ExtractDouble(response, "risk"));
         string decisionId = ExtractString(response, "decision_id");
         string regime     = ExtractString(response, "regime");
         string rationale  = ExtractString(response, "rationale");

         if(regime == "") regime = "lateral";
         if(signal == "") signal = "HOLD";

         if(effMode == "observer") {
            string observerReason = !safe ? "Observer por limite de risco" : (!inHr ? "Observer fora da janela" : "Observer definido no painel");
            UpdateSymbolPanel(i, "OBSERVANDO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, observerReason);
            g_lastEvent = sym + ": analise em observer.";
            continue;
         }
         
         if(signal == "HOLD") {
            UpdateSymbolPanel(i, "AGUARDAR", signal, confidence, risk, spreadPts, atrPct, regime, rationale, rationale);
            g_lastEvent = sym + ": sem gatilho para entrada.";
            continue;
         }

         if(risk <= 0 || decisionId == "") {
            string invalidReason = (risk <= 0) ? "Risco zerado" : "Decision ID ausente";
            UpdateSymbolPanel(i, "BLOQUEADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, invalidReason);
            g_lastEvent = sym + ": bloqueado por resposta invalida.";
            continue;
         }

         if(!SymbolAllowedByRuntime(sym)) {
            UpdateSymbolPanel(i, "BLOQUEADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "Ativo fora da lista permitida");
            g_lastEvent = sym + ": ativo fora da lista permitida.";
            continue;
         }

         string executionGuardReason = "";
         if(!MarketOpen(sym, signal)) {
            UpdateSymbolPanel(i, "BLOQUEADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "Mercado fechado ou lado bloqueado");
            g_lastEvent = sym + ": mercado fechado ou lado bloqueado.";
            continue;
         }

         if(!SpreadOK(sym, spreadPts, executionGuardReason)) {
            UpdateSymbolPanel(i, "BLOQUEADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, executionGuardReason);
            g_lastEvent = sym + ": " + executionGuardReason;
            continue;
         }

          // Evitar ordens duplicadas no mesmo par
          if(CountPositionsBySymbol(sym) > 0) {
             UpdateSymbolPanel(i, "OPERANDO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "Ja existe posicao aberta para " + sym);
             g_lastEvent = sym + ": sinal ignorado, ja operando.";
             continue;
          }
          
          // Pode Exceder ordens globais?
          if(CountAllPositions() >= MaxPositions) {
            UpdateSymbolPanel(i, "BLOQUEADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "Limite global de posicoes atingido");
            g_lastEvent = sym + ": limite global de posicoes atingido.";
            continue;
         }
         
         // Executar Trade
         if(ExecuteTrade(sym, arrATR[i], signal, confidence, risk, decisionId)) {
            UpdateSymbolPanel(i, "EXECUTADO", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "");
            g_lastEvent = sym + ": " + signal + " executado com " + DoubleToString(confidence * 100, 0) + "% de confianca.";
         }
         else {
            UpdateSymbolPanel(i, "FALHA", signal, confidence, risk, spreadPts, atrPct, regime, rationale, "Falha ao enviar ordem ao MT5");
            g_lastEvent = sym + ": falha ao enviar ordem.";
         }
      }
   }

   RenderPanel();
}

//+------------------------------------------------------------------+
bool ExecuteTrade(string sym, int handleATR, string signal, double conf, double risk, string dId)
{
   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(handleATR, 0, 0, 2, atr) < 2) {
      Print("[Trade] Falha ao copiar ATR para ", sym, ". Ordem abortada.");
      return false;
   }
   
   risk = SafeRisk(risk);
   if(risk <= 0) {
      Print("[Trade] Risco invalido apos clamp para ", sym, ". Ordem abortada.");
      return false;
   }

   double slDist = atr[1] * ATR_SL_Multi;
   double tpDist = slDist * 2.0;
   string cmt = StringFormat("VUNO|%s|%.0f%%", dId, conf * 100);
   double lot = CalcLotSymbol(sym, risk, slDist);
   if(lot <= 0) {
      Print("[Trade] ", signal, " bloqueado [", sym, "] lote calculado zero | risk=", DoubleToString(risk, 3), " | slDist=", DoubleToString(slDist, 5));
      return false;
   }

   ulong ticket = 0;
   double fillPrice = 0;
   double sl = 0;
   double tp = 0;
   if(!ExecuteOrder(sym, signal, lot, slDist, tpDist, cmt, ticket, fillPrice, sl, tp))
      return false;

   string side = signal == "BUY" ? "buy" : "sell";
   Print(signal, " Executado [", sym, "] conf:", conf * 100, "% | ticket=", IntegerToString((int)ticket));
   NotifyTradeOpened(dId, sym, side, ticket, fillPrice, sl, tp, lot);
   return true;
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

      LogTradeFailure(sym, signal, lot, fillPrice, sl, tp);
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
      NotifyTradeOutcome(decisionId, dealTicket, sym, "", profit, 0);

      int idx = SymbolIndex(sym);
      if(idx >= 0) {
         g_lastState[idx] = "FECHADO";
         g_lastBlockReason[idx] = "Resultado: " + ((profit > 0) ? "WIN " : (profit < 0 ? "LOSS " : "ZERO ")) + FormatSignedMoney(profit);
         g_lastAnalyzedAt[idx] = TimeCurrent();
      }
      g_lastEvent = sym + ": trade fechado em " + FormatSignedMoney(profit) + ".";
      RenderPanel();
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
   double maxDrawdownPct = g_runtimeMaxDrawdownPct > 0 ? g_runtimeMaxDrawdownPct : MaxDrawdown;
   if(g_peakBal > 0) {
      double dd = (g_peakBal - equity) / g_peakBal * 100;
      if(dd >= maxDrawdownPct) return false;
   }

   if(g_runtimeDailyLossMoney > 0) {
      if(g_dailyPnL < -g_runtimeDailyLossMoney) return false;
      return true;
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
   string start = NormalizeTimeWindowValue(g_runtimeTradingStart);
   string end = NormalizeTimeWindowValue(g_runtimeTradingEnd);
   if(start == "" || end == "") return true;
   return (t >= start && t <= end);
}

void ResetDaily()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   datetime today = StringToTime(StringFormat("%04d.%02d.%02d 00:00", dt.year, dt.mon, dt.day));
   if(today > g_lastReset) { g_dailyPnL = 0; g_lastReset = today; }
}

int SymbolIndex(string sym)
{
   for(int i=0; i<ArraySize(arrSymbols); i++)
      if(arrSymbols[i] == sym)
         return i;
   return -1;
}

void InitPanelBuffers(int count)
{
   ArrayResize(g_lastSignal, count);
   ArrayResize(g_lastConfidence, count);
   ArrayResize(g_lastRisk, count);
   ArrayResize(g_lastSpreadPoints, count);
   ArrayResize(g_lastAtrPct, count);
   ArrayResize(g_lastScore, count);
   ArrayResize(g_lastRegime, count);
   ArrayResize(g_lastReason, count);
   ArrayResize(g_lastBlockReason, count);
   ArrayResize(g_lastState, count);
   ArrayResize(g_lastAnalyzedAt, count);

   for(int i=0; i<count; i++) {
      g_lastSignal[i] = "HOLD";
      g_lastConfidence[i] = 0;
      g_lastRisk[i] = 0;
      g_lastSpreadPoints[i] = 0;
      g_lastAtrPct[i] = 0;
      g_lastScore[i] = 0;
      g_lastRegime[i] = "lateral";
      g_lastReason[i] = "Aguardando primeira leitura";
      g_lastBlockReason[i] = "";
      g_lastState[i] = "AGUARDANDO";
      g_lastAnalyzedAt[i] = 0;
   }
}

void UpdateSymbolPanel(int idx, string state, string signal, double confidence, double risk, double spreadPts, double atrPct, string regime, string reason, string blockReason)
{
   if(idx < 0 || idx >= ArraySize(arrSymbols)) return;

   g_lastState[idx] = state;
   g_lastSignal[idx] = signal;
   g_lastConfidence[idx] = confidence;
   g_lastRisk[idx] = risk;
   g_lastSpreadPoints[idx] = spreadPts;
   g_lastAtrPct[idx] = atrPct;
   g_lastScore[idx] = (confidence * 100.0) + (atrPct * 10000.0) - (spreadPts * 0.35);
   g_lastRegime[idx] = regime;
   g_lastReason[idx] = reason;
   g_lastBlockReason[idx] = blockReason;
   g_lastAnalyzedAt[idx] = TimeCurrent();
}

double CalcSpreadPoints(string sym)
{
   double ask = SymbolInfoDouble(sym, SYMBOL_ASK);
   double bid = SymbolInfoDouble(sym, SYMBOL_BID);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   if(point <= 0) return 0;
   return (ask - bid) / point;
}

double CalcAtrPct(int handleATR, string sym)
{
   if(handleATR == INVALID_HANDLE) return 0;

   double atr[];
   ArraySetAsSeries(atr, true);
   if(CopyBuffer(handleATR, 0, 0, 2, atr) < 2) return 0;

   double refPrice = SymbolInfoDouble(sym, SYMBOL_BID);
   if(refPrice <= 0) refPrice = SymbolInfoDouble(sym, SYMBOL_ASK);
   if(refPrice <= 0) return 0;
   return atr[1] / refPrice;
}

int CountPositionsBySymbol(string sym)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionInfo.SelectByIndex(i))
         if(PositionInfo.Magic() == 20260331 && PositionInfo.Symbol() == sym)
            count++;
   return count;
}

double CurrentDrawdownPct()
{
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(g_peakBal <= 0) return 0;
   double dd = (g_peakBal - equity) / g_peakBal * 100.0;
   return MathMax(0.0, dd);
}

string BuildMood()
{
   double avgConfidence = 0;
   int samples = 0;

   for(int i=0; i<ArraySize(arrSymbols); i++) {
      if(g_lastAnalyzedAt[i] <= 0) continue;
      avgConfidence += g_lastConfidence[i];
      samples++;
   }

   if(samples > 0)
      avgConfidence /= samples;

   if(!SafetyOK()) return "DEFENSIVA";
   if(g_dailyPnL < 0) return (avgConfidence >= 0.65 ? "CAUTELOSA" : "RETRAIDA");
   if(avgConfidence >= 0.75) return "CONFIANTE";
   if(avgConfidence >= 0.60) return "ATENTA";
   return "NEUTRA";
}

string Shorten(string value, int limit)
{
   if(limit <= 0) return "";
   if(StringLen(value) <= limit) return value;
   if(limit <= 3) return StringSubstr(value, 0, limit);
   return StringSubstr(value, 0, limit - 3) + "...";
}

string FormatMoney(double value)
{
   return "$" + DoubleToString(value, 2);
}

string FormatSignedMoney(double value)
{
   string prefix = value > 0 ? "+" : "";
   return prefix + "$" + DoubleToString(value, 2);
}

void RenderPanel()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   string hhmmss = StringFormat("%02d:%02d:%02d", dt.hour, dt.min, dt.sec);

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   int totalPos   = CountAllPositions();

   string panel = "";
   panel += "VUNO SCREENER v3\n";
   panel += "STATUS: " + g_panelStatus + " | MODO: " + g_panelMode + " | CICLO: #" + IntegerToString(g_cycleCounter) + " | HORA: " + hhmmss + "\n";
   panel += "HUMOR: " + BuildMood() + " | EVENTO: " + Shorten(g_lastEvent, 82) + "\n";
   panel += "---------------------------------------------\n";
   panel += "FINANCEIRO\n";
   panel += "Base: " + FormatMoney(g_initialBal) + " | Saldo: " + FormatMoney(balance) + " | Equity: " + FormatMoney(equity) + "\n";
   panel += "PnL dia: " + FormatSignedMoney(g_dailyPnL) + " | Pico: " + FormatMoney(g_peakBal) + " | DD: " + DoubleToString(CurrentDrawdownPct(), 2) + "%\n";
   panel += "RISCO\n";
   panel += "Seguranca: " + (SafetyOK() ? "ATIVA" : "PAUSADA") + " | Janela: " + (TradingHour() ? "ABERTA" : "FECHADA") + " | Posicoes: " + IntegerToString(totalPos) + "/" + IntegerToString(MaxPositions) + "\n";
   panel += "ANALISE POR ATIVO\n";

   int rows = MathMin(ArraySize(arrSymbols), 6);
   for(int i=0; i<rows; i++) {
      string line = arrSymbols[i] + " | " + g_lastSignal[i] + " | " + g_lastState[i] + " | conf " + DoubleToString(g_lastConfidence[i] * 100, 0) + "% | score " + DoubleToString(g_lastScore[i], 1) + " | pos " + IntegerToString(CountPositionsBySymbol(arrSymbols[i]));
      if(g_lastBlockReason[i] != "")
         line += " | " + Shorten(g_lastBlockReason[i], 34);
      else if(g_lastReason[i] != "")
         line += " | " + Shorten(g_lastReason[i], 34);
      panel += line + "\n";
   }

   int bestIdx = -1;
   double bestScore = -999999.0;
   for(int j=0; j<ArraySize(arrSymbols); j++) {
      if(g_lastScore[j] > bestScore) {
         bestScore = g_lastScore[j];
         bestIdx = j;
      }
   }

   panel += "CONTEXTO LIDER\n";
   if(bestIdx >= 0) {
      panel += arrSymbols[bestIdx] + " | regime " + g_lastRegime[bestIdx] + " | spread " + DoubleToString(g_lastSpreadPoints[bestIdx], 1) + " pts | atr " + DoubleToString(g_lastAtrPct[bestIdx] * 100, 3) + "%\n";
      panel += Shorten(g_lastReason[bestIdx], 100);
   } else {
      panel += "Sem contexto suficiente ainda.";
   }

   ChartComment(panel);
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
   string responseText = CharArrayToString(resArr);
   if(code == 200)
      return responseText;

   if(code == -1)
      Print("[Cloud] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas | rota=", path);
   else
      Print("[Cloud] Erro HTTP ", code, " ao contactar Render | rota=", path, " | resposta=", Shorten(responseText, 160));

   return "";
}

void NotifyTradeOpened(string decisionId, string sym, string side, ulong ticket, double price, double sl, double tp, double lot)
{
   if(decisionId == "") return;

   string body = StringFormat(
      "{\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\","
      "\"decision_id\":\"%s\",\"ticket\":\"%I64u\",\"symbol\":\"%s\",\"side\":\"%s\","
      "\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"lot\":%.2f,\"balance\":%.2f}",
      RobotID, RobotToken, UserID, OrganizationID,
      decisionId, ticket, sym, side,
      price, sl, tp, lot, AccountInfoDouble(ACCOUNT_BALANCE)
   );
   string response = SendToCloud("/api/mt5/trade-opened", body);
   if(response == "")
      Print("[Cloud] trade-opened sem confirmação | decision_id=", decisionId, " | ticket=", IntegerToString((int)ticket));
}

void NotifyTradeOutcome(string decisionId, long ticket, string sym, string side, double profit, int points)
{
   if(decisionId == "") return;

   string body = StringFormat(
      "{\"robot_id\":\"%s\",\"robot_token\":\"%s\",\"user_id\":\"%s\",\"organization_id\":\"%s\","
      "\"decision_id\":\"%s\",\"ticket\":\"%d\",\"symbol\":\"%s\",\"side\":\"%s\","
      "\"profit\":%.2f,\"points\":%d,\"mode\":\"%s\",\"balance\":%.2f}",
      RobotID, RobotToken, UserID, OrganizationID,
      decisionId, ticket, sym, side,
      profit, points, TradingMode, AccountInfoDouble(ACCOUNT_BALANCE)
   );
   string response = SendToCloud("/api/mt5/trade-outcome", body);
   if(response == "")
      Print("[Cloud] trade-outcome sem confirmação | decision_id=", decisionId, " | ticket=", IntegerToString((int)ticket));
}

string CollectPositionsJson()
{
   string json = "[";
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionSelectByTicket(PositionGetTicket(i)))
      {
         ulong  ticket = PositionGetInteger(POSITION_TICKET);
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

   int code = WebRequest("POST", url, headers, 3000, bodyArr, resArr, resHeaders);
   if(code == 200) {
      // heart beat ok
      g_lastHeartbeat = TimeCurrent();
   } else if(code == -1) {
      Print("[HB] ERRO: adicione '", url, "' em Ferramentas > Opções > Expert Advisors > URLs permitidas");
   } else {
      Print("[HB] HTTP ", code, " no heartbeat | resposta=", Shorten(CharArrayToString(resArr), 160));
   }
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

   if(remoteAllowed != "" && remoteAllowed != "null") {
      StringReplace(remoteAllowed, " ", "");
      g_runtimeAllowedSymbols = remoteAllowed;
   } else {
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

void LogTradeFailure(string sym, string side, double lot, double price, double sl, double tp)
{
   Print(
      "[Trade] ", side, " falhou [", sym, "] lot=", DoubleToString(lot, 2),
      " | price=", DoubleToString(price, 5),
      " | sl=", DoubleToString(sl, 5),
      " | tp=", DoubleToString(tp, 5),
      " | retcode=", IntegerToString((int)Trade.ResultRetcode()),
      " | desc=", Trade.ResultRetcodeDescription()
   );
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
   ChartComment("");
}
