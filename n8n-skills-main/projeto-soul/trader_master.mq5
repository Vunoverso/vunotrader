//+------------------------------------------------------------------+
//|                                              TraderMasterBot.mq5 |
//|                                  Copyright 2026, Antigravity AI  |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Antigravity AI"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

//--- Input Parameters
input int      InpEMA_Fast = 9;      // EMA Rápida
input int      InpEMA_Slow = 21;     // EMA Lenta
input int      InpRSI_Period = 14;   // Período do RSI
input double   InpMinScore = 6.0;    // Score mínimo para entrada (0-10)
input string   InpWebhookURL = "";   // URL do n8n para alertas (Telegram)

//--- Global Variables
int      handle_ema_fast;
int      handle_ema_slow;
int      handle_rsi;
int      handle_macd;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   //--- Indicadores
   handle_ema_fast = iMA(_Symbol, _Period, InpEMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   handle_ema_slow = iMA(_Symbol, _Period, InpEMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   handle_rsi = iRSI(_Symbol, _Period, InpRSI_Period, PRICE_CLOSE);
   handle_macd = iMACD(_Symbol, _Period, 12, 26, 9, PRICE_CLOSE);
   
   if(handle_ema_fast == INVALID_HANDLE || handle_ema_slow == INVALID_HANDLE || handle_rsi == INVALID_HANDLE)
   {
      Print("Erro ao criar handles dos indicadores");
      return(INIT_FAILED);
   }

   Print("Trader Master Inicializado! Aguardando confluências...");
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handle_ema_fast);
   IndicatorRelease(handle_ema_slow);
   IndicatorRelease(handle_rsi);
   IndicatorRelease(handle_macd);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   double ema_f[1], ema_s[1], rsi[1], macd_main[1], macd_sig[1];
   
   if(CopyBuffer(handle_ema_fast, 0, 0, 1, ema_f) <= 0) return;
   if(CopyBuffer(handle_ema_slow, 0, 0, 1, ema_s) <= 0) return;
   if(CopyBuffer(handle_rsi, 0, 0, 1, rsi) <= 0) return;
   if(CopyBuffer(handle_macd, 0, 0, 1, macd_main) <= 0) return;
   if(CopyBuffer(handle_macd, 1, 0, 1, macd_sig) <= 0) return;
   
   double score = CalculateScore(ema_f[0], ema_s[0], rsi[0], macd_main[0], macd_sig[0]);
   
   if(score >= InpMinScore)
   {
      string signal_type = (ema_f[0] > ema_s[0]) ? "COMPRA" : "VENDA";
      Print("SINAL DETECTADO: ", signal_type, " | Score: ", DoubleToString(score, 1));
      
      // Aqui entraria a lógica de abertura de ordem: OrderSend(...)
      
      // Enviar para n8n se a URL estiver configurada
      if(InpWebhookURL != "")
         SendSignalToN8N(signal_type, score);
   }
}

//+------------------------------------------------------------------+
//| Calculate strategy score (0-10)                                  |
//+------------------------------------------------------------------+
double CalculateScore(double ef, double es, double r, double mm, double ms)
{
   double s = 0;
   
   // 1. Tendência EMA (4 pts)
   if(ef > es) s += 4; // Tendência de Alta
   else if(ef < es) s += 4; // Tendência de Baixa (para simplificar, somamos pontos pela definição clara)
   
   // 2. RSI (3 pts)
   if(ef > es && r < 70) s += 3; // Não sobrecomprado em alta
   if(ef < es && r > 30) s += 3; // Não sobrevendido em baixa
   
   // 3. MACD (3 pts)
   if(ef > es && mm > ms) s += 3; // Momentum positivo
   if(ef < es && mm < ms) s += 3; // Momentum negativo
   
   return s;
}

//+------------------------------------------------------------------+
//| Send signal to n8n Webhook                                       |
//+------------------------------------------------------------------+
void SendSignalToN8N(string type, double score)
{
   string cookie=NULL,headers;
   char post[],result[];
   int res;
   
   string body = "{\"symbol\":\"" + _Symbol + "\", \"type\":\"" + type + "\", \"score\":" + DoubleToString(score, 1) + "}";
   StringToCharArray(body, post);
   
   res = WebRequest("POST", InpWebhookURL, cookie, NULL, 50, post, 0, result, headers);
   
   if(res == -1)
      Print("Erro no WebRequest: ", GetLastError());
   else
      Print("Sinal enviado com sucesso para o n8n!");
}
//+------------------------------------------------------------------+
