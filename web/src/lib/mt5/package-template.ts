import path from "path";

const DEFAULT_BACKEND_URL = "https://vunotrader-api.onrender.com";

export interface RobotPackageInput {
  robotId: string;
  robotToken: string;
  userId: string;
  organizationId: string;
  instanceName: string;
  mode: "demo" | "real";
  robotProductType: "robo_integrado" | "robo_hibrido_visual";
  visualShadowEnabled: boolean;
}

export function resolveRepoRoot(): string {
  return path.resolve(process.cwd(), "..");
}

export function resolvePackageTemplateRoot(): string {
  return path.join(resolveRepoRoot(), "vuno-robo");
}

export function resolveBackendUrl(): string {
  const candidate =
    process.env.VUNO_MT5_BACKEND_URL ||
    process.env.NEXT_PUBLIC_KEEP_ALIVE_URL ||
    DEFAULT_BACKEND_URL;

  return candidate.replace(/\/+$/, "");
}

export function buildBridgeName(robotId: string): string {
  const compactId = robotId.replace(/[^a-zA-Z0-9]/g, "").slice(0, 8);
  return `VunoBridge-${compactId || "main"}`;
}

export function buildPackageFileName(instanceName: string): string {
  const safeName = instanceName
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);

  return `${safeName || "vuno-robo"}.zip`;
}

export function buildRuntimeConfig(input: RobotPackageInput): string {
  const payload = {
    backend_url: resolveBackendUrl(),
    robot_id: input.robotId,
    robot_token: input.robotToken,
    user_id: input.userId,
    organization_id: input.organizationId,
    instance_name: input.instanceName,
    trading_mode: input.mode,
    robot_product_type: input.robotProductType,
    visual_shadow_enabled: input.visualShadowEnabled,
    bridge_name: buildBridgeName(input.robotId),
    poll_interval_seconds: 2,
    heartbeat_interval_seconds: 10,
    runtime_config_interval_seconds: 20,
    max_snapshot_age_seconds: 45,
    request_timeout_seconds: 12,
    max_spread_points: 30,
    default_lot: 0.01,
    stop_loss_points: 180,
    take_profit_points: 360,
    max_positions_per_symbol: 1,
    reentry_cooldown_seconds: 60,
    max_command_age_seconds: 45,
    deviation_points: 20,
    execution_retries: 3,
    use_local_fallback: true,
    pause_new_orders: false,
    snapshot_dir: "runtime/bridge/in",
    command_dir: "runtime/bridge/out",
    feedback_dir: "runtime/bridge/feedback",
    metadata_dir: "runtime/bridge/metadata",
    archive_dir: "runtime/archive",
  };

  return `${JSON.stringify(payload, null, 2)}\n`;
}

export function buildQuickStart(input: RobotPackageInput): string {
  const bridgeName = buildBridgeName(input.robotId);
  const tradingMode = input.mode === "real" ? "REAL" : "DEMO";
  const productLabel = input.robotProductType === "robo_hibrido_visual" ? "Robo Hibrido Visual" : "Robo Integrado";

  return [
    "Vuno Trader - pacote pronto da instancia",
    "",
    `Instancia: ${input.instanceName}`,
    `Linha do robo: ${productLabel}`,
    `Modo inicial: ${tradingMode}`,
    `Bridge MT5: ${bridgeName}`,
    `Shadow visual: ${input.visualShadowEnabled ? "habilitado" : "desligado"}`,
    "",
    "Passo a passo rapido:",
    "1. Extraia este zip em qualquer pasta sua.",
    "2. Abra agent-local/iniciar-vuno-robo.cmd com duplo clique.",
    "3. No MT5, copie mt5/VunoRemoteBridge.mq5 e a pasta mt5/vuno-bridge para MQL5/Experts.",
    "4. Compile o EA, anexe no grafico e use InpBridgeRoot igual ao valor acima.",
    "5. Nao configure URL permitida no MT5: a comunicacao vai pelo agente local.",
    "6. Durante homologacao, mantenha InpAllowRealTrading=false no EA.",
    "7. Volte ao painel e confirme heartbeat da instancia.",
    "",
    "Observacao: runtime/config.json ja sai preenchido com a chave desta instancia.",
    "Se gerar um novo pacote, a recomendacao e pausar a instancia antiga no painel.",
  ].join("\n");
}