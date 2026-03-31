/**
 * lib/sql-guard.ts
 *
 * Cliente do Skill Engine — valida queries SQL antes de executar.
 * Copie este arquivo para qualquer projeto Node.js / Next.js.
 *
 * Uso:
 *   import { validateQuery, blockIfUnsafe } from "@/lib/sql-guard";
 */

const SKILL_ENGINE_URL =
  process.env.SKILL_ENGINE_URL || "https://ia-enginer.onrender.com";

export interface ValidateQueryOptions {
  offline?: boolean;
}

export interface ValidateQueryResponse {
  success: boolean;
  decision: { action: "ignore" | "warn" | "review" | "block"; reason: string };
  issues: Array<{
    id: string;
    severity: string;
    message: string;
    fix: string;
    observationId?: number;
  }>;
  summary: { total: number; critical: number; high: number };
}

/**
 * Valida uma query SQL contra o Skill Engine.
 *
 * @param query - SQL a ser analisado
 * @param options - Opções extras
 */
export async function validateQuery(
  query: string,
  options: ValidateQueryOptions = {}
): Promise<ValidateQueryResponse> {
  const res = await fetch(`${SKILL_ENGINE_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, options }),
  });

  return res.json();
}

/**
 * Lança erro se a query for considerada insegura (decision = "block").
 * Use antes de qualquer query crítica em produção.
 *
 * @param query - SQL a analisar
 * @throws {Error} se a query for bloqueada
 *
 * @example
 * await blockIfUnsafe("SELECT * FROM users");
 * // lança: "Query bloqueada [select-star]: SELECT * carrega colunas..."
 */
export async function blockIfUnsafe(
  query: string
): Promise<ValidateQueryResponse> {
  const result = await validateQuery(query);

  if (result.decision?.action === "block") {
    const first = result.issues?.[0];
    throw new Error(
      `Query bloqueada [${first?.id ?? "unknown"}]: ${
        first?.message ?? result.decision.reason
      }`
    );
  }

  return result;
}

/**
 * Envia feedback sobre uma observação gerada pelo /analyze.
 * Alimenta o sistema de aprendizado adaptativo.
 *
 * @param observationId - retornado em issues[n].observationId
 * @param outcome - Resultado do feedback
 * @param actualImprovement - Melhorias reais de latência
 */
export async function sendFeedback(
  observationId: number,
  outcome: "confirmed" | "ignored" | "false_positive" | "fixed_differently",
  actualImprovement?: { latency_before_ms?: number; latency_after_ms?: number }
) {
  await fetch(`${SKILL_ENGINE_URL}/learning/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      observation_id: observationId,
      outcome,
      actual_improvement: actualImprovement,
    }),
  });
}
