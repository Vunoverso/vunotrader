"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";

type Status = "waiting" | "connected" | "timeout";

const POLL_MS = 5000;     // verifica a cada 5 s
const TIMEOUT_MS = 120000; // desiste após 2 min sem conexão

export default function Mt5ConnectionChecker({ userId }: { userId: string }) {
  const [status, setStatus] = useState<Status>("waiting");
  const [instanceName, setInstanceName] = useState<string | null>(null);
  const [lastSeen, setLastSeen] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [active, setActive] = useState(false);

  const check = useCallback(async () => {
    const supabase = createClient();
    // Precisa ir via profile_id
    const { data: profile } = await supabase
      .from("user_profiles")
      .select("id")
      .eq("auth_user_id", userId)
      .limit(1)
      .maybeSingle();
    if (!profile) return;

    const { data: robot } = await supabase
      .from("robot_instances")
      .select("name, last_seen_at")
      .eq("profile_id", profile.id)
      .eq("status", "active")
      .order("last_seen_at", { ascending: false, nullsFirst: false })
      .limit(1)
      .maybeSingle();

    if (robot?.last_seen_at) {
      const diffMs = Date.now() - new Date(robot.last_seen_at).getTime();
      if (diffMs < 5 * 60 * 1000) {
        setStatus("connected");
        setInstanceName(robot.name ?? "Instância");
        setLastSeen(robot.last_seen_at);
        return;
      }
    }
    // Não conectado ainda
  }, [userId]);

  useEffect(() => {
    if (!active) return;
    // não chamar setState síncrono — inicializar com startMs via ref
    const startMs = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startMs;
      setElapsedMs(elapsed);
      if (elapsed >= TIMEOUT_MS) {
        clearInterval(interval);
        setStatus("timeout");
        return;
      }
      check();
    }, POLL_MS);

    // Adiar a chamada inicial para fora do corpo do efeito,
    // evitando setState síncrono dentro do useEffect.
    const initialTimer = setTimeout(() => check(), 0);

    return () => {
      clearInterval(interval);
      clearTimeout(initialTimer);
    };
  }, [active, check]);

  if (!active) {
    return (
      <div className="rounded-xl border border-sky-500/20 bg-sky-500/5 p-5">
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-sky-500/20 bg-sky-500/10 text-sky-400 text-lg">
            📡
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-slate-200">Validar conexão com o MT5</h3>
            <p className="mt-1 text-xs text-slate-400">
              Clique em &quot;Iniciar verificação&quot; após configurar o EA no MT5.
              O painel detectará automaticamente quando o robô conectar.
            </p>
            <button
              type="button"
              onClick={() => setActive(true)}
              className="mt-3 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700 transition"
            >
              Iniciar verificação
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (status === "connected") {
    return (
      <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-5">
        <div className="flex items-start gap-4">
          <span className="text-2xl">✅</span>
          <div>
            <h3 className="text-sm font-semibold text-emerald-300">MT5 conectado com sucesso!</h3>
            <p className="mt-1 text-xs text-slate-400">
              Instância: <span className="font-semibold text-slate-200">{instanceName}</span>
              {lastSeen && (
                <> · último heartbeat {new Date(lastSeen).toLocaleTimeString("pt-BR")}</>
              )}
            </p>
            <p className="mt-2 text-xs text-emerald-300">
              Seu robô está ativo e enviando dados ao motor de decisão. Confira o dashboard para acompanhar os sinais.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (status === "timeout") {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5 space-y-3">
        <div className="flex items-start gap-4">
          <span className="text-2xl">⚠️</span>
          <div>
            <h3 className="text-sm font-semibold text-red-300">Conexão não detectada em 2 minutos</h3>
            <p className="mt-1 text-xs text-slate-400">Verifique os itens abaixo e tente novamente.</p>
          </div>
        </div>
        <ul className="space-y-1.5 text-xs text-slate-300 pl-2">
          <li className="flex items-start gap-2"><span className="text-red-400 mt-0.5">·</span> O campo <strong>RobotToken</strong> no EA está preenchido com seu token do painel?</li>
          <li className="flex items-start gap-2"><span className="text-red-400 mt-0.5">·</span> O AutoTrading está habilitado no MT5?</li>
          <li className="flex items-start gap-2"><span className="text-red-400 mt-0.5">·</span> O EA aparece no gráfico (não foi removido)?</li>
          <li className="flex items-start gap-2"><span className="text-red-400 mt-0.5">·</span> O brain Python está rodando na sua máquina ou servidor?</li>
        </ul>
        <button
          type="button"
          onClick={() => { setStatus("waiting"); setElapsedMs(0); setActive(false); setTimeout(() => setActive(true), 50); }}
          className="rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10 transition"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  // waiting
  const progressPct = Math.min(100, (elapsedMs / TIMEOUT_MS) * 100);
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 p-5">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-sky-500/20 bg-sky-500/10">
          <span className="h-3 w-3 rounded-full bg-sky-400 animate-pulse" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-slate-200">Aguardando conexão do MT5…</h3>
          <p className="mt-1 text-xs text-slate-500">
            Verificando a cada 5 segundos. Certifique-se de que o EA está configurado no gráfico com AutoTrading ativo.
          </p>
          <div className="mt-3 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
            <div
              className="h-full rounded-full bg-sky-500 transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <p className="mt-1 text-[10px] text-slate-600">
            {Math.round(elapsedMs / 1000)}s · {Math.round((TIMEOUT_MS - elapsedMs) / 1000)}s restantes
          </p>
        </div>
      </div>
    </div>
  );
}
