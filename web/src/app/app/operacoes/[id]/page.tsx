import { notFound } from "next/navigation";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import TradeScoreCard from "@/components/app/trade-score-card";

// ── Helpers visuais ───────────────────────────────────────────────
function Badge({
  children,
  color = "slate",
}: {
  children: React.ReactNode;
  color?: "emerald" | "red" | "amber" | "sky" | "violet" | "slate";
}) {
  const cls = {
    emerald: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    red:     "border-red-500/30 bg-red-500/10 text-red-400",
    amber:   "border-amber-500/30 bg-amber-500/10 text-amber-400",
    sky:     "border-sky-500/30 bg-sky-500/10 text-sky-400",
    violet:  "border-violet-500/30 bg-violet-500/10 text-violet-400",
    slate:   "border-slate-700 bg-slate-800 text-slate-400",
  }[color];
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cls}`}>
      {children}
    </span>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2.5 border-b border-slate-800/60 last:border-0">
      <span className="text-sm text-slate-500 shrink-0">{label}</span>
      <span className="text-sm text-slate-200 text-right">{value ?? "—"}</span>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 overflow-hidden">
      <div className="border-b border-slate-800 px-5 py-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</h2>
      </div>
      <div className="px-5 py-1">{children}</div>
    </div>
  );
}

function Pnl({ value }: { value: number | null }) {
  if (value == null) return <span className="text-slate-500">—</span>;
  return (
    <span className={`font-bold tabular-nums ${value > 0 ? "text-emerald-400" : value < 0 ? "text-red-400" : "text-slate-400"}`}>
      {value > 0 ? "+" : ""}R$ {value.toFixed(2)}
    </span>
  );
}

function formatDt(dt: string | null) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

function confidence(c: number | null) {
  if (c == null) return "—";
  const pct = (c * 100).toFixed(1);
  if (c >= 0.75) return <Badge color="emerald">Alta · {pct}%</Badge>;
  if (c >= 0.55) return <Badge color="amber">Média · {pct}%</Badge>;
  return <Badge color="slate">Baixa · {pct}%</Badge>;
}

// ── Page ─────────────────────────────────────────────────────────
export default async function OperacaoDetalhePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();

  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return notFound();

  const { data: trade } = await supabase
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
        symbol,
        timeframe,
        side,
        confidence,
        risk_pct,
        rationale,
        mode,
        regime,
        user_id,
        created_at
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
    .single();

  if (!trade) return notFound();

  // Segurança: verifica que o trade pertence ao usuário autenticado
  const dec = Array.isArray(trade.trade_decisions)
    ? trade.trade_decisions[0] ?? null
    : trade.trade_decisions;
  const out = Array.isArray(trade.trade_outcomes)
    ? trade.trade_outcomes[0] ?? null
    : trade.trade_outcomes;

  if ((dec as { user_id?: string } | null)?.user_id !== user.id) return notFound();

  const sideColor  = dec?.side === "buy" ? "emerald" : dec?.side === "sell" ? "red" : "slate";
  const resultColor = out?.result === "win" ? "emerald" : out?.result === "loss" ? "red" : "slate";
  const sideLabel   = ({ buy: "COMPRA", sell: "VENDA", hold: "HOLD" } as Record<string, string>)[dec?.side ?? "hold"] ?? "—";
  const resultLabel = ({ win: "WIN", loss: "LOSS", breakeven: "EMPATE" } as Record<string, string>)[out?.result ?? ""] ?? "—";

  // Duração
  let duracao = "—";
  if (trade.opened_at && trade.closed_at) {
    const ms = new Date(trade.closed_at).getTime() - new Date(trade.opened_at).getTime();
    const minutes = Math.floor(ms / 60000);
    const hours = Math.floor(minutes / 60);
    duracao = hours > 0 ? `${hours}h ${minutes % 60}min` : `${minutes}min`;
  }

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-slate-500">
        <Link href="/app/operacoes" className="hover:text-slate-300 transition-colors">
          Operações
        </Link>
        <span>/</span>
        <span className="text-slate-400 font-mono">{id.slice(0, 8)}…</span>
      </div>

      {/* Cabeçalho */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {dec?.symbol ?? "—"}
            <span className="ml-2 text-slate-500 text-base font-normal">{dec?.timeframe ?? ""}</span>
          </h1>
          <p className="mt-1 font-mono text-xs text-slate-600">ID: {id}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {dec?.side && <Badge color={sideColor as "emerald" | "red" | "slate"}>{sideLabel}</Badge>}
          {out?.result && <Badge color={resultColor as "emerald" | "red" | "slate"}>{resultLabel}</Badge>}
          {dec?.mode === "real" ? (
            <Badge color="amber">Real</Badge>
          ) : (
            <Badge color="slate">Demo</Badge>
          )}
          {dec?.regime && <Badge color="sky">{dec.regime}</Badge>}
        </div>
      </div>

      {/* P&L destaque */}
      {out && (
        <div className={`rounded-xl border px-6 py-5 flex items-center justify-between ${
          out.result === "win"
            ? "border-emerald-500/20 bg-emerald-500/5"
            : out.result === "loss"
            ? "border-red-500/20 bg-red-500/5"
            : "border-slate-800 bg-slate-900"
        }`}>
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Resultado financeiro</p>
            <p className="text-3xl font-bold tabular-nums">
              <Pnl value={out.pnl_money} />
            </p>
            {out.pnl_points != null && (
              <p className="mt-1 text-xs text-slate-500">{out.pnl_points > 0 ? "+" : ""}{out.pnl_points} pontos</p>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Confiança da IA</p>
            <div>{confidence(dec?.confidence ?? null)}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* Execução */}
        <Section title="Execução">
          <InfoRow label="Ticket Broker" value={
            <span className="font-mono text-xs">{trade.broker_ticket ?? "—"}</span>
          } />
          <InfoRow label="Preço de entrada" value={trade.entry_price != null ? trade.entry_price.toFixed(2) : "—"} />
          <InfoRow label="Stop Loss" value={trade.stop_loss != null ? trade.stop_loss.toFixed(2) : "—"} />
          <InfoRow label="Take Profit" value={trade.take_profit != null ? trade.take_profit.toFixed(2) : "—"} />
          <InfoRow label="Lote" value={trade.lot ?? "—"} />
          <InfoRow label="Duração" value={duracao} />
          <InfoRow label="Abertura" value={formatDt(trade.opened_at)} />
          <InfoRow label="Fechamento" value={formatDt(trade.closed_at)} />
        </Section>

        {/* Decisão da IA */}
        <Section title="Decisão da IA">
          <InfoRow label="Símbolo" value={dec?.symbol ?? "—"} />
          <InfoRow label="Timeframe" value={dec?.timeframe ?? "—"} />
          <InfoRow label="Direção" value={
            dec?.side ? <Badge color={sideColor as "emerald" | "red" | "slate"}>{sideLabel}</Badge> : "—"
          } />
          <InfoRow label="Confiança" value={confidence(dec?.confidence ?? null)} />
          <InfoRow label="Risco sugerido" value={dec?.risk_pct != null ? `${dec.risk_pct}%` : "—"} />
          <InfoRow label="Regime" value={
            dec?.regime ? <Badge color="sky">{dec.regime}</Badge> : "—"
          } />
          <InfoRow label="Modo" value={
            dec?.mode === "real" ? <Badge color="amber">Real</Badge> : <Badge color="slate">Demo</Badge>
          } />
          <InfoRow label="Decisão registrada" value={formatDt(dec?.created_at ?? null)} />
        </Section>
      </div>

      {/* Rationale completo */}
      {(dec?.rationale || out?.win_loss_reason) && (
        <Section title="Análise do motor">
          <div className="py-3 space-y-3">
            {dec?.rationale && (
              <div>
                <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-2">Motivo da entrada</p>
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">{dec.rationale}</p>
              </div>
            )}
            {out?.win_loss_reason && (
              <div className="pt-2 border-t border-slate-800/60">
                <p className="text-[10px] uppercase tracking-wider text-slate-600 mb-2">Análise do resultado</p>
                <p className="text-sm text-slate-300 leading-relaxed">{out.win_loss_reason}</p>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* Score histórico da configuração */}
      <TradeScoreCard
        symbol={dec?.symbol ?? null}
        timeframe={dec?.timeframe ?? null}
        side={dec?.side ?? null}
        regime={dec?.regime ?? null}
        confidence={dec?.confidence ?? null}
      />

      {/* Rodapé de navegação */}
      <div className="pt-2 pb-8">
        <Link
          href="/app/operacoes"
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Voltar para operações
        </Link>
      </div>
    </div>
  );
}
