import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const userId = searchParams.get("userId");
  const robotId = searchParams.get("robotId");

  if (!userId) {
    return NextResponse.json([], { status: 400 });
  }

  const supabase = await createClient();

  // Verifica autenticação
  const { data: { user } } = await supabase.auth.getUser();
  if (!user || user.id !== userId) {
    return NextResponse.json([], { status: 401 });
  }

  let query = supabase
    .from("trade_decisions")
    .select("id, symbol, timeframe, side, confidence, risk_pct, mode, rationale, created_at")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(25);

  if (robotId) {
    query = query.eq("robot_instance_id", robotId);
  }

  const { data, error } = await query;

  if (error) {
    return NextResponse.json([], { status: 500 });
  }

  return NextResponse.json(data ?? []);
}
