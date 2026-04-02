"use client";

import { useState } from "react";
import { createClient } from "@/lib/supabase/client";
import RecommendationAdvisor from "@/components/app/recommendation-advisor";

type RobotMode = "observer" | "demo" | "real";
type StopLossMode = "atr" | "fixed_points";

export interface ParametrosData {
  id?: string;
  organization_id?: string;
  mode: RobotMode;
  capital_usd: string;
  daily_profit_target: string;
  weekly_profit_target: string;
  monthly_profit_target: string;
  daily_loss_limit: string;
  max_drawdown_pct: string;
  risk_per_trade_pct: string;
  per_trade_stop_loss_mode: StopLossMode;
  per_trade_stop_loss_value: string;
  per_trade_take_profit_rr: string;
  max_trades_per_day: string;
  trading_start_time: string;
  trading_end_time: string;
  allowed_symbols: string;
  max_consecutive_losses: string;
  drawdown_pause_pct: string;
  auto_reduce_risk: boolean;
}

const DEFAULT: ParametrosData = {
  mode: "demo",
  capital_usd: "10000",
  daily_profit_target: "",
  weekly_profit_target: "",
  monthly_profit_target: "",
  daily_loss_limit: "",
  max_drawdown_pct: "",
  risk_per_trade_pct: "",
  per_trade_stop_loss_mode: "atr",
  per_trade_stop_loss_value: "2",
  per_trade_take_profit_rr: "2",
  max_trades_per_day: "",
  trading_start_time: "09:00",
  trading_end_time: "17:30",
  allowed_symbols: "",
  max_consecutive_losses: "3",
  drawdown_pause_pct: "5",
  auto_reduce_risk: true,
};

// ── Helpers de UI ────────────────────────────────────────────
function FieldGroup({ label, tooltip, hint, children }: { label: string; tooltip?: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 mb-1">
        <label className="block text-sm font-medium text-slate-300">{label}</label>
        {tooltip && (
          <div className="group relative inline-block">
            <div className="cursor-help rounded-full bg-slate-800 p-0.5 text-slate-500 hover:bg-slate-700 hover:text-sky-400 transition-colors">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="h-3 w-3">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 16v-4m0-4h.01" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            {/* Balloon / Tooltip */}
            <div className="invisible group-hover:visible absolute left-1/2 bottom-full mb-2 -translate-x-1/2 w-48 rounded-lg bg-slate-950 border border-slate-700 p-2.5 text-[11px] leading-relaxed text-slate-300 shadow-xl z-50 animate-in fade-in slide-in-from-bottom-1">
              {tooltip}
              <div className="absolute top-full left-1/2 -ml-1 border-4 border-transparent border-t-slate-700" />
            </div>
          </div>
        )}
      </div>
      {hint && <p className="text-xs text-slate-600 mb-1.5">{hint}</p>}
      {children}
    </div>
  );
}

function Input({
  value, onChange, type = "text", placeholder, prefix, suffix, min, step,
}: {
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  prefix?: string;
  suffix?: string;
  min?: string;
  step?: string;
}) {
  return (
    <div className="flex items-center rounded-lg border border-slate-700 bg-slate-800 overflow-hidden focus-within:border-sky-500 focus-within:ring-1 focus-within:ring-sky-500/30 transition">
      {prefix && (
        <span className="px-3 py-2.5 text-xs text-slate-500 border-r border-slate-700 bg-slate-900 select-none">
          {prefix}
        </span>
      )}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        min={min}
        step={step}
        className="flex-1 bg-transparent px-3 py-2.5 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none"
      />
      {suffix && (
        <span className="px-3 py-2.5 text-xs text-slate-500 border-l border-slate-700 bg-slate-900 select-none">
          {suffix}
        </span>
      )}
    </div>
  );
}

const MODE_OPTIONS: { value: RobotMode; label: string; desc: string; color: string }[] = [
  {
    value: "observer",
    label: "Observer",
    desc: "Analisa o mercado e gera sinais sem executar ordens",
    color: "border-yellow-500/50 bg-yellow-500/10 text-yellow-400",
  },
  {
    value: "demo",
    label: "Demo",
    desc: "Opera em conta demo, aprende com os resultados",
    color: "border-sky-500/50 bg-sky-500/10 text-sky-400",
  },
  {
    value: "real",
    label: "Real",
    desc: "Opera na conta real com modelo aprovado e validado",
    color: "border-emerald-500/50 bg-emerald-500/10 text-emerald-400",
  },
];

const STOP_LOSS_OPTIONS: { value: StopLossMode; label: string; desc: string }[] = [
  {
    value: "atr",
    label: "ATR",
    desc: "Usa volatilidade do ativo para definir a distancia do stop.",
  },
  {
    value: "fixed_points",
    label: "Pontos fixos",
    desc: "Mantem uma distancia fixa por operacao.",
  },
];

// ── Componente principal ─────────────────────────────────────
export default function ParametrosForm({
  initial,
  userId,
  organizationId,
}: {
  initial: ParametrosData | null;
  userId: string;
  organizationId: string | null;
}) {
  const [form, setForm] = useState<ParametrosData>(initial ?? DEFAULT);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");

  function set<K extends keyof ParametrosData>(key: K, value: ParametrosData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setStatus("idle");
  }

  function applyRecommendationPatch(patch: Record<string, string | boolean>) {
    setForm((prev) => ({
      ...prev,
      risk_per_trade_pct: typeof patch.risk_per_trade_pct === "string" ? patch.risk_per_trade_pct : prev.risk_per_trade_pct,
      max_drawdown_pct: typeof patch.max_drawdown_pct === "string" ? patch.max_drawdown_pct : prev.max_drawdown_pct,
      drawdown_pause_pct: typeof patch.drawdown_pause_pct === "string" ? patch.drawdown_pause_pct : prev.drawdown_pause_pct,
      max_consecutive_losses: typeof patch.max_consecutive_losses === "string" ? patch.max_consecutive_losses : prev.max_consecutive_losses,
      max_trades_per_day: typeof patch.max_trades_per_day === "string" ? patch.max_trades_per_day : prev.max_trades_per_day,
      auto_reduce_risk: typeof patch.auto_reduce_risk === "boolean" ? patch.auto_reduce_risk : prev.auto_reduce_risk,
      per_trade_stop_loss_mode:
        patch.per_trade_stop_loss_mode === "atr" || patch.per_trade_stop_loss_mode === "fixed_points"
          ? patch.per_trade_stop_loss_mode
          : prev.per_trade_stop_loss_mode,
      per_trade_stop_loss_value:
        typeof patch.per_trade_stop_loss_value === "string"
          ? patch.per_trade_stop_loss_value
          : prev.per_trade_stop_loss_value,
      per_trade_take_profit_rr:
        typeof patch.per_trade_take_profit_rr === "string"
          ? patch.per_trade_take_profit_rr
          : prev.per_trade_take_profit_rr,
    }));
    setStatus("idle");
  }

  async function handleSave() {
    setSaving(true);
    setStatus("idle");

    const supabase = createClient();

    const payload = {
      user_id: userId,
      organization_id: organizationId,
      mode: form.mode,
      capital_usd: form.capital_usd ? parseFloat(form.capital_usd) : 10000,
      daily_profit_target: form.daily_profit_target ? parseFloat(form.daily_profit_target) : null,
      weekly_profit_target: form.weekly_profit_target ? parseFloat(form.weekly_profit_target) : null,
      monthly_profit_target: form.monthly_profit_target ? parseFloat(form.monthly_profit_target) : null,
      daily_loss_limit: form.daily_loss_limit ? parseFloat(form.daily_loss_limit) : null,
      max_drawdown_pct: form.max_drawdown_pct ? parseFloat(form.max_drawdown_pct) : null,
      risk_per_trade_pct: form.risk_per_trade_pct ? parseFloat(form.risk_per_trade_pct) : null,
      per_trade_stop_loss_mode: form.per_trade_stop_loss_mode,
      per_trade_stop_loss_value: form.per_trade_stop_loss_value ? parseFloat(form.per_trade_stop_loss_value) : null,
      per_trade_take_profit_rr: form.per_trade_take_profit_rr ? parseFloat(form.per_trade_take_profit_rr) : null,
      max_trades_per_day: form.max_trades_per_day ? parseInt(form.max_trades_per_day) : null,
      trading_start_time: form.trading_start_time || null,
      trading_end_time: form.trading_end_time || null,
      allowed_symbols: form.allowed_symbols
        ? form.allowed_symbols.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
        : null,
      max_consecutive_losses: form.max_consecutive_losses ? parseInt(form.max_consecutive_losses) : 3,
      drawdown_pause_pct: form.drawdown_pause_pct ? parseFloat(form.drawdown_pause_pct) : 5.0,
      auto_reduce_risk: form.auto_reduce_risk,
      updated_at: new Date().toISOString(),
    };

    let error;

    if (form.id) {
      ({ error } = await supabase
        .from("user_parameters")
        .update(payload)
        .eq("id", form.id));
    } else {
      const { data, error: insertError } = await supabase
        .from("user_parameters")
        .insert(payload)
        .select("id")
        .single();
      error = insertError;
      if (data) setForm((prev) => ({ ...prev, id: data.id }));
    }

    setSaving(false);
    setStatus(error ? "error" : "saved");
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <RecommendationAdvisor form={form} onApply={applyRecommendationPatch} />

      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Parâmetros do Robô</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Configurações que controlam o comportamento do brain Python e do EA no MT5
          </p>
        </div>
        <div className="flex items-center gap-3">
          {status === "saved" && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M20 6 9 17l-5-5" />
              </svg>
              Salvo
            </span>
          )}
          {status === "error" && (
            <span className="text-xs text-red-400">Erro ao salvar. Tente novamente.</span>
          )}
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-lg bg-sky-600 px-5 py-2 text-sm font-semibold text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {saving ? "Salvando…" : "Salvar alterações"}
          </button>
        </div>
      </div>

      {/* ── Bloco 1: Modo de operação ── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          Modo de operação
        </h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => set("mode", opt.value)}
              className={`rounded-lg border-2 px-4 py-3 text-left transition ${
                form.mode === opt.value
                  ? opt.color + " border-opacity-100"
                  : "border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
              }`}
            >
              <p className="text-sm font-semibold mb-0.5">{opt.label}</p>
              <p className="text-xs opacity-70 leading-snug">{opt.desc}</p>
            </button>
          ))}
        </div>
        {form.mode === "real" && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-400">
            ⚠️ Modo real opera com dinheiro real. Certifique-se de que o modelo foi validado em demo antes de ativar.
          </div>
        )}
      </section>

      {/* ── Bloco 2: Metas de profit ── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          Metas de resultado
        </h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
          <FieldGroup label="Meta diária" hint="Alvo de lucro por dia">
            <Input
              value={form.daily_profit_target}
              onChange={(v) => set("daily_profit_target", v)}
              type="number"
              placeholder="Ex: 500"
              prefix="R$"
              min="0"
              step="0.01"
            />
          </FieldGroup>
          <FieldGroup label="Meta semanal" hint="Alvo de lucro por semana">
            <Input
              value={form.weekly_profit_target}
              onChange={(v) => set("weekly_profit_target", v)}
              type="number"
              placeholder="Ex: 2000"
              prefix="R$"
              min="0"
              step="0.01"
            />
          </FieldGroup>
          <FieldGroup label="Meta mensal" hint="Alvo de lucro por mês">
            <Input
              value={form.monthly_profit_target}
              onChange={(v) => set("monthly_profit_target", v)}
              type="number"
              placeholder="Ex: 8000"
              prefix="R$"
              min="0"
              step="0.01"
            />
          </FieldGroup>
        </div>
      </section>

      {/* ── Bloco 3: Limites de risco ── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          Limites de risco
        </h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <FieldGroup 
            label="Capital de referência" 
            hint="Base usada para calcular risco e drawdown"
            tooltip="Base usada para calcular o risco em dinheiro e lotes. O robô usará este valor para definir o tamanho das ordens."
          >
            <Input
              value={form.capital_usd}
              onChange={(v) => set("capital_usd", v)}
              type="number"
              placeholder="Ex: 10000"
              prefix="R$"
              min="0"
              step="0.01"
            />
          </FieldGroup>
          <FieldGroup 
            label="Limite de perda diária" 
            hint="Robô para ao atingir este valor"
            tooltip="Trava de segurança: se o robô perder este valor líquido em um único dia (PnL Realizado), ele pausa até o dia seguinte."
          >
            <Input
              value={form.daily_loss_limit}
              onChange={(v) => set("daily_loss_limit", v)}
              type="number"
              placeholder="Ex: 300"
              prefix="R$"
              min="0"
              step="0.01"
            />
          </FieldGroup>
          <FieldGroup 
            label="Drawdown máximo" 
            hint="Percentual máximo de queda permitido"
            tooltip="A queda máxima total permitida a partir do seu topo de capital. Serve para proteger sua conta de grandes sequências de perdas."
          >
            <Input
              value={form.max_drawdown_pct}
              onChange={(v) => set("max_drawdown_pct", v)}
              type="number"
              placeholder="Ex: 5"
              suffix="%"
              min="0"
              step="0.1"
            />
          </FieldGroup>
          <FieldGroup 
            label="Risco por trade" 
            hint="Percentual do capital por operação"
            tooltip="Quanto você aceita perder em uma única operação (em % do capital). Lotes maiores = maior risco."
          >
            <Input
              value={form.risk_per_trade_pct}
              onChange={(v) => set("risk_per_trade_pct", v)}
              type="number"
              placeholder="Ex: 1"
              suffix="%"
              min="0"
              step="0.1"
            />
          </FieldGroup>
          <FieldGroup 
            label="Máx. trades por dia" 
            hint="Quantidade máxima de operações"
            tooltip="Trava para evitar o excesso de operações (overtrading) e reduzir custos de corretagem e exposição desnecessária."
          >
            <Input
              value={form.max_trades_per_day}
              onChange={(v) => set("max_trades_per_day", v)}
              type="number"
              placeholder="Ex: 5"
              min="1"
              step="1"
            />
          </FieldGroup>
        </div>
      </section>

      {/* ── Bloco 4: Saida por operacao ── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Saida por operacao
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            O MetaTrader continua enviando ao Vuno os valores executados de entrada, stop e take profit.
            Aqui voce define a politica operacional que orienta esses niveis.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {STOP_LOSS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => set("per_trade_stop_loss_mode", opt.value)}
              className={`rounded-lg border px-4 py-3 text-left transition ${
                form.per_trade_stop_loss_mode === opt.value
                  ? "border-sky-500 bg-sky-500/10 text-sky-300"
                  : "border-slate-700 bg-slate-800 text-slate-400 hover:border-slate-600"
              }`}
            >
              <p className="text-sm font-semibold">{opt.label}</p>
              <p className="text-xs opacity-75 mt-1 leading-snug">{opt.desc}</p>
            </button>
          ))}
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <FieldGroup
            label={form.per_trade_stop_loss_mode === "atr" ? "Multiplicador de stop" : "Stop loss em pontos"}
            hint={form.per_trade_stop_loss_mode === "atr" ? "Ex.: 2 significa stop a 2x o ATR atual." : "Distancia fixa de perda por operacao."}
          >
            <Input
              value={form.per_trade_stop_loss_value}
              onChange={(v) => set("per_trade_stop_loss_value", v)}
              type="number"
              placeholder={form.per_trade_stop_loss_mode === "atr" ? "Ex: 2" : "Ex: 250"}
              suffix={form.per_trade_stop_loss_mode === "atr" ? "x ATR" : "pts"}
              min="0"
              step="0.1"
            />
          </FieldGroup>
          <FieldGroup label="Take profit por risco" hint="Relacao alvo de ganho sobre o risco. Ex.: 2 = alvo de 2R.">
            <Input
              value={form.per_trade_take_profit_rr}
              onChange={(v) => set("per_trade_take_profit_rr", v)}
              type="number"
              placeholder="Ex: 2"
              suffix="R"
              min="0.5"
              step="0.1"
            />
          </FieldGroup>
        </div>
      </section>

      {/* ── Bloco 4B: Proteção automática ── */}
      <section className="rounded-xl border border-orange-500/20 bg-slate-900 p-6 space-y-5">
        <div>
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
            Proteção automática
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            O motor bloqueia novos sinais automaticamente quando os limites abaixo são atingidos.
            Funciona no servidor — independente do EA ou do MT5.
          </p>
        </div>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <FieldGroup label="Máx. perdas consecutivas" hint="Motor pausa ao atingir N perdas seguidas (padrão: 3)">
            <Input
              value={form.max_consecutive_losses}
              onChange={(v) => set("max_consecutive_losses", v)}
              type="number"
              placeholder="3"
              suffix="perdas"
              min="1"
              step="1"
            />
          </FieldGroup>
          <FieldGroup label="Pause por drawdown" hint="Pausa automática se o drawdown diário ultrapassar este percentual">
            <Input
              value={form.drawdown_pause_pct}
              onChange={(v) => set("drawdown_pause_pct", v)}
              type="number"
              placeholder="5"
              suffix="%"
              min="0.5"
              step="0.5"
            />
          </FieldGroup>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            role="switch"
            aria-checked={form.auto_reduce_risk}
            onClick={() => set("auto_reduce_risk", !form.auto_reduce_risk)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              form.auto_reduce_risk ? "bg-sky-600" : "bg-slate-700"
            }`}
          >
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
              form.auto_reduce_risk ? "translate-x-6" : "translate-x-1"
            }`} />
          </button>
          <div>
            <p className="text-sm text-slate-300 font-medium">Reduzir risco automaticamente</p>
            <p className="text-xs text-slate-500">Ao perder consistência, o motor usa risco menor até recuperar o padrão.</p>
          </div>
        </div>
      </section>

      {/* ── Bloco 5: Horários e ativos ── */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 space-y-5">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
          Horários e ativos
        </h2>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <FieldGroup label="Início das operações">
            <Input
              value={form.trading_start_time}
              onChange={(v) => set("trading_start_time", v)}
              type="time"
            />
          </FieldGroup>
          <FieldGroup label="Encerramento das operações">
            <Input
              value={form.trading_end_time}
              onChange={(v) => set("trading_end_time", v)}
              type="time"
            />
          </FieldGroup>
        </div>
        <FieldGroup
          label="Ativos permitidos"
          hint='Símbolos separados por vírgula. Deixe vazio para qualquer ativo. Ex: WIN$N, WDO$N, PETR4'
        >
          <Input
            value={form.allowed_symbols}
            onChange={(v) => set("allowed_symbols", v)}
            placeholder="WIN$N, WDO$N"
          />
        </FieldGroup>
      </section>
    </div>
  );
}
