import { NextResponse } from "next/server";

import { createClient } from "@/lib/supabase/server";
import { signVisualStoragePaths } from "@/lib/mt5/visual-shadow";

type LiveVisualRow = {
  cycle_id: string;
  chart_image_storage_path: string | null;
  visual_shadow_status: string;
  visual_alignment: string;
  visual_conflict_reason: string | null;
  visual_context: {
    summary?: string;
    signal_bias?: string;
  } | null;
  created_at: string;
};

type LiveTradeRow = {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  created_at: string;
  confidence: number;
  timeframe: string;
  robot_instance_id: string;
  robot_instances?: { name: string } | { name: string }[] | null;
  trade_visual_contexts?: LiveVisualRow[] | null;
};

function firstRelation<T>(value: T | T[] | null | undefined): T | null {
  if (Array.isArray(value)) {
    return value[0] ?? null;
  }
  return value ?? null;
}

export async function GET(): Promise<NextResponse> {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ ok: false, error: "Nao autenticado." }, { status: 401 });
  }

  const { data, error } = await supabase
    .from("trade_decisions")
    .select(`
      id,
      symbol,
      side,
      entry_price,
      stop_loss,
      take_profit,
      created_at,
      confidence,
      timeframe,
      robot_instance_id,
      robot_instances(name),
      trade_visual_contexts(
        cycle_id,
        chart_image_storage_path,
        visual_shadow_status,
        visual_alignment,
        visual_conflict_reason,
        visual_context,
        created_at
      )
    `)
    .eq("user_id", user.id)
    .eq("outcome_status", "executing")
    .order("created_at", { ascending: false });

  if (error) {
    return NextResponse.json({ ok: false, error: "Falha ao carregar operacoes ao vivo." }, { status: 500 });
  }

  const rows = (data ?? []) as LiveTradeRow[];
  const visualUrlMap = await signVisualStoragePaths(
    rows.map((row) => firstRelation(row.trade_visual_contexts)?.chart_image_storage_path ?? null)
  );

  const trades = rows.map((row) => {
    const visual = firstRelation(row.trade_visual_contexts);
    const robotInstance = firstRelation(row.robot_instances);

    return {
      id: row.id,
      symbol: row.symbol,
      side: row.side,
      entry_price: row.entry_price,
      stop_loss: row.stop_loss,
      take_profit: row.take_profit,
      created_at: row.created_at,
      confidence: row.confidence,
      timeframe: row.timeframe,
      robot_instance_id: row.robot_instance_id,
      robot_instances: robotInstance ? { name: robotInstance.name } : undefined,
      visual: visual
        ? {
            cycle_id: visual.cycle_id,
            visual_shadow_status: visual.visual_shadow_status,
            visual_alignment: visual.visual_alignment,
            visual_conflict_reason: visual.visual_conflict_reason,
            summary: visual.visual_context?.summary ?? null,
            signal_bias: visual.visual_context?.signal_bias ?? null,
            chart_image_url: visual.chart_image_storage_path
              ? visualUrlMap[visual.chart_image_storage_path] ?? null
              : null,
          }
        : null,
    };
  });

  return NextResponse.json({ ok: true, trades });
}