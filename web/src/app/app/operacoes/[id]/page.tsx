import { notFound } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import TradeScoreCard from "@/components/app/trade-score-card";

type OutcomeResult = "win" | "loss" | "breakeven";
type DecisionOutcomeStatus = "pending" | "executing" | OutcomeResult | "neutral" | null;

type DecisionRow = {
  id: string;
  user_id: string;
  symbol: string;
  timeframe: string;
  side: "buy" | "sell" | "hold";
  confidence: number | null;
  risk_pct: number | null;
  rationale: string | null;
  mode: string;
  regime: string | null;
  created_at: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  outcome_status: DecisionOutcomeStatus;
  outcome_profit: number | null;
  outcome_pips: number | null;
  post_analysis: string | null;
  closed_at: string | null;
};

type OutcomeRow = {
  id?: string;
  result: OutcomeResult;
  pnl_money: number | null;
  pnl_points: number | null;
  win_loss_reason: string | null;
  created_at?: string | null;
};

type ExecutedTradeRow = {
  id: string;
  broker_ticket: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lot: number | null;
  status: "open" | "closed" | "canceled";
  opened_at: string | null;
  closed_at: string | null;
  trade_decisions?: DecisionRow[] | DecisionRow | null;
  trade_outcomes?: OutcomeRow[] | OutcomeRow | null;
};

type ExecutionView = {
  id: string;
  broker_ticket: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  lot: number | null;
  status: "open" | "closed" | "canceled";
  opened_at: string | null;
  closed_at: string | null;
};

function pickFirst<T>(value: T[] | T | null | undefined): T | null {
  if (!value) return null;
  if (Array.isArray(value)) return value[0] ?? null;
  return value;
}

function mapDecisionResult(status: DecisionOutcomeStatus): OutcomeResult | null {
  if (status === "win" || status === "loss" || status === "breakeven") return status;
  if (status === "neutral") return "breakeven";
  return null;
}

function mapDecisionStatus(status: DecisionOutcomeStatus): ExecutionView["status"] {
  if (status === "win" || status === "loss" || status === "breakeven" || status === "neutral") return "closed";
  return "open";
}

function deriveOutcomeFromDecision(decision: DecisionRow): OutcomeRow | null {
  const result = mapDecisionResult(decision.outcome_status);
  if (!result) return null;
  return {
    result,
    pnl_money: decision.outcome_profit ?? null,
    pnl_points: decision.outcome_pips ?? null,
    win_loss_reason: decision.post_analysis ?? null,
  };
}

function Badge({
  children,
  color = "slate",
}: {
  children: React.ReactNode;
  color?: "emerald" | "red" | "amber" | "sky" | "violet" | "slate";
}) {
  const cls = {
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    red: "border-red-500/30 bg-red-500/10 text-red-400",
    amber: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    sky: "border-sky-500/30 bg-sky-500/10 text-sky-400",
    violet: "border-violet-500/30 bg-violet-500/10 text-violet-400",
    slate: "border-slate-700 bg-slate-800 text-slate-400",
  }[color];
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </span>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-800/60 py-2.5 last:border-0">
      <span className="shrink-0 text-sm text-slate-500">{label}</span>
      <span className="text-right text-sm text-slate-200">{value ?? "-"}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900">
      <div className="border-b border-slate-800 px-5 py-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</h2>
      </div>
      <div className="px-5 py-1">{children}</div>
    </div>
  );
}

function Pnl({ value }: { value: number | null }) {
  if (value == null) return <span className="text-slate-500">-</span>;
  return (
    <span className={`font-bold tabular-nums ${value > 0 ? "text-emerald-400" : value < 0 ? "text-red-400" : "text-slate-400"}`}>
      {value > 0 ? "+" : ""}R$ {value.toFixed(2)}
    </span>
  );
}

function formatDt(dt: string | null) {
  if (!dt) return "-";
  return new Date(dt).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function confidence(c: number | null) {
  if (c == null) return "-";
  const pct = (c * 100).toFixed(1);
  if (c >= 0.75) return <Badge color="emerald">Alta · {pct}%</Badge>;
  if (c >= 0.55) return <Badge color="amber">Media · {pct}%</Badge>;
  return <Badge color="slate">Baixa · {pct}%</Badge>;
}

export default async function OperacaoDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return notFound();

  const { data: executedTrade } = await supabase
    .from("executed_trades")
    .select(`
      id,
      broker_ticket,
      entry_price,
      stop_loss,
      take_profit,
      lot,
      status,
      opened_at,
      closed_at,
      trade_decisions (
        id,
        user_id,
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        rationale,
        mode,
        regime,
        created_at,
        entry_price,
        stop_loss,
        take_profit,
        outcome_status,
        outcome_profit,
        outcome_pips,
        post_analysis,
        closed_at
      ),
      trade_outcomes (
        id,
        result,
        pnl_money,
        pnl_points,
        win_loss_reason,
        created_at
      )
    `)
    .eq("id", id)
    .maybeSingle();

  let decision: DecisionRow | null = null;
  let outcome: OutcomeRow | null = null;
  let execution: ExecutionView | null = null;

  if (executedTrade) {
    const dec = pickFirst(executedTrade.trade_decisions as DecisionRow[] | DecisionRow | null);
    if (!dec || dec.user_id !== user.id) return notFound();

    const out = pickFirst(executedTrade.trade_outcomes as OutcomeRow[] | OutcomeRow | null);
    decision = dec;
    outcome = out ?? deriveOutcomeFromDecision(dec);
    execution = {
      id: executedTrade.id,
      broker_ticket: executedTrade.broker_ticket,
      entry_price: executedTrade.entry_price ?? dec.entry_price,
      stop_loss: executedTrade.stop_loss ?? dec.stop_loss,
      take_profit: executedTrade.take_profit ?? dec.take_profit,
      lot: executedTrade.lot,
      status: executedTrade.status,
      opened_at: executedTrade.opened_at ?? dec.created_at,
      closed_at: executedTrade.closed_at ?? dec.closed_at,
    };
  } else {
    const { data: decisionFallback } = await supabase
      .from("trade_decisions")
      .select(`
        id,
        user_id,
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        rationale,
        mode,
        regime,
        created_at,
        entry_price,
        stop_loss,
        take_profit,
        outcome_status,
        outcome_profit,
        outcome_pips,
        post_analysis,
        closed_at,
        executed_trades (
          id,
          broker_ticket,
          entry_price,
          stop_loss,
          take_profit,
          lot,
          status,
          opened_at,
          closed_at,
          trade_outcomes (
            id,
            result,
            pnl_money,
            pnl_points,
            win_loss_reason,
            created_at
          )
        )
      `)
      .eq("id", id)
      .eq("user_id", user.id)
      .maybeSingle();

    if (!decisionFallback) return notFound();

    const dec = decisionFallback as unknown as DecisionRow & { executed_trades?: ExecutedTradeRow[] | null };
    const executed = pickFirst(dec.executed_trades as ExecutedTradeRow[] | null);
    const out = executed ? pickFirst(executed.trade_outcomes as OutcomeRow[] | OutcomeRow | null) : null;

    decision = dec;
    outcome = out ?? deriveOutcomeFromDecision(dec);
    execution = {
      id: executed?.id ?? dec.id,
      broker_ticket: executed?.broker_ticket ?? null,
      entry_price: executed?.entry_price ?? dec.entry_price,
      stop_loss: executed?.stop_loss ?? dec.stop_loss,
      take_profit: executed?.take_profit ?? dec.take_profit,
      lot: executed?.lot ?? null,
      status: executed?.status ?? mapDecisionStatus(dec.outcome_status),
      opened_at: executed?.opened_at ?? dec.created_at,
      closed_at: executed?.closed_at ?? dec.closed_at,
    };
  }

  if (!decision || !execution) return notFound();

  const sideColor = decision.side === "buy" ? "emerald" : decision.side === "sell" ? "red" : "slate";
  const resultColor = outcome?.result === "win" ? "emerald" : outcome?.result === "loss" ? "red" : "slate";
  const sideLabel = ({ buy: "COMPRA", sell: "VENDA", hold: "HOLD" } as Record<string, string>)[decision.side ?? "hold"] ?? "-";
  const resultLabel = ({ win: "WIN", loss: "LOSS", breakeven: "EMPATE" } as Record<string, string>)[outcome?.result ?? ""] ?? "-";

  let duracao = "-";
  if (execution.opened_at && execution.closed_at) {
    const ms = new Date(execution.closed_at).getTime() - new Date(execution.opened_at).getTime();
    const minutes = Math.floor(ms / 60000);
    const hours = Math.floor(minutes / 60);
    duracao = hours > 0 ? `${hours}h ${minutes % 60}min` : `${minutes}min`;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link href="/app/operacoes" className="transition-colors hover:text-slate-300">
          Operacoes
        </Link>
        <span>/</span>
        <span className="font-mono text-slate-400">{id.slice(0, 8)}...</span>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {decision.symbol ?? "-"}
            <span className="ml-2 text-base font-normal text-slate-500">{decision.timeframe ?? ""}</span>
          </h1>
          <p className="mt-1 font-mono text-xs text-slate-600">ID: {execution.id}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {decision.side && <Badge color={sideColor as "emerald" | "red" | "slate"}>{sideLabel}</Badge>}
          {outcome?.result && <Badge color={resultColor as "emerald" | "red" | "slate"}>{resultLabel}</Badge>}
          {decision.mode === "real" ? <Badge color="amber">Real</Badge> : <Badge color="slate">Demo</Badge>}
          {decision.regime && <Badge color="sky">{decision.regime}</Badge>}
        </div>
      </div>

      {outcome && (
        <div
          className={`flex items-center justify-between rounded-xl border px-6 py-5 ${
            outcome.result === "win"
              ? "border-emerald-500/20 bg-emerald-500/5"
              : outcome.result === "loss"
              ? "border-red-500/20 bg-red-500/5"
              : "border-slate-800 bg-slate-900"
          }`}
        >
          <div>
            <p className="mb-1 text-xs uppercase tracking-wider text-slate-500">Resultado financeiro</p>
            <p className="text-3xl font-bold tabular-nums">
              <Pnl value={outcome.pnl_money} />
            </p>
            {outcome.pnl_points != null && (
              <p className="mt-1 text-xs text-slate-500">
                {outcome.pnl_points > 0 ? "+" : ""}
                {outcome.pnl_points} pontos
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="mb-1 text-xs uppercase tracking-wider text-slate-500">Confianca da IA</p>
            <div>{confidence(decision.confidence ?? null)}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Section title="Execucao">
          <InfoRow
            label="Ticket Broker"
            value={<span className="font-mono text-xs">{execution.broker_ticket ?? "-"}</span>}
          />
          <InfoRow label="Preco de entrada" value={execution.entry_price != null ? execution.entry_price.toFixed(2) : "-"} />
          <InfoRow label="Stop Loss" value={execution.stop_loss != null ? execution.stop_loss.toFixed(2) : "-"} />
          <InfoRow label="Take Profit" value={execution.take_profit != null ? execution.take_profit.toFixed(2) : "-"} />
          <InfoRow label="Lote" value={execution.lot ?? "-"} />
          <InfoRow label="Duracao" value={duracao} />
          <InfoRow label="Abertura" value={formatDt(execution.opened_at)} />
          <InfoRow label="Fechamento" value={formatDt(execution.closed_at)} />
        </Section>

        <Section title="Decisao da IA">
          <InfoRow label="Simbolo" value={decision.symbol ?? "-"} />
          <InfoRow label="Timeframe" value={decision.timeframe ?? "-"} />
          <InfoRow
            label="Direcao"
            value={decision.side ? <Badge color={sideColor as "emerald" | "red" | "slate"}>{sideLabel}</Badge> : "-"}
          />
          <InfoRow label="Confianca" value={confidence(decision.confidence ?? null)} />
          <InfoRow label="Risco sugerido" value={decision.risk_pct != null ? `${decision.risk_pct}%` : "-"} />
          <InfoRow label="Regime" value={decision.regime ? <Badge color="sky">{decision.regime}</Badge> : "-"} />
          <InfoRow label="Modo" value={decision.mode === "real" ? <Badge color="amber">Real</Badge> : <Badge color="slate">Demo</Badge>} />
          <InfoRow label="Decisao registrada" value={formatDt(decision.created_at ?? null)} />
        </Section>
      </div>

      {(decision.rationale || outcome?.win_loss_reason) && (
        <Section title="Analise do motor">
          <div className="space-y-3 py-3">
            {decision.rationale && (
              <div>
                <p className="mb-2 text-[10px] uppercase tracking-wider text-slate-600">Motivo da entrada</p>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{decision.rationale}</p>
              </div>
            )}
            {outcome?.win_loss_reason && (
              <div className="border-t border-slate-800/60 pt-2">
                <p className="mb-2 text-[10px] uppercase tracking-wider text-slate-600">Analise do resultado</p>
                <p className="text-sm leading-relaxed text-slate-300">{outcome.win_loss_reason}</p>
              </div>
            )}
          </div>
        </Section>
      )}

      <TradeScoreCard
        symbol={decision.symbol ?? null}
        timeframe={decision.timeframe ?? null}
        side={decision.side ?? null}
        regime={decision.regime ?? null}
        confidence={decision.confidence ?? null}
      />

      <div className="pb-8 pt-2">
        <Link
          href="/app/operacoes"
          className="inline-flex items-center gap-2 text-sm text-slate-500 transition-colors hover:text-slate-300"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Voltar para operacoes
        </Link>
      </div>
    </div>
  );
}
