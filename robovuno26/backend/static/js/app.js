const SESSION_KEY = "vuno_session";
const AUTO_REFRESH_MS = 15000;

const state = {
  session: null,
  me: null,
  authenticated: false,
  instrumentProfiles: [],
  summary: null,
  instances: [],
  auditEvents: [],
  parameters: null,
  lastCreatedInstance: null,
  editingRobotInstanceId: null,
};

let autoRefreshTimerId = 0;
let autoRefreshTickerId = 0;
let nextAutoRefreshAt = 0;
let lastAutoRefreshAt = 0;
let refreshInFlight = false;
let autoRefreshMode = "off";
let autoRefreshMessage = "";

const dom = {
  appShell: document.getElementById("appShell"),
  sidebarNav: document.getElementById("sidebarNav"),
  sidebarOverlay: document.getElementById("sidebarOverlay"),
  sidebarToggleBtn: document.getElementById("sidebarToggleBtn"),
  sidebarCloseBtn: document.getElementById("sidebarCloseBtn"),

  email: document.getElementById("email"),
  password: document.getElementById("password"),
  tenantName: document.getElementById("tenantName"),
  registerBtn: document.getElementById("registerBtn"),
  loginBtn: document.getElementById("loginBtn"),
  logoutBtn: document.getElementById("logoutBtn"),
  refreshAllBtn: document.getElementById("refreshAllBtn"),
  status: document.getElementById("status"),
  autoRefreshBadge: document.getElementById("autoRefreshBadge"),
  autoRefreshLabel: document.getElementById("autoRefreshLabel"),
  autoRefreshMeta: document.getElementById("autoRefreshMeta"),

  sessionUser: document.getElementById("sessionUser"),
  sessionTenant: document.getElementById("sessionTenant"),
  sessionExpiry: document.getElementById("sessionExpiry"),

  navButtons: [...document.querySelectorAll("[data-view-target]")],
  views: [...document.querySelectorAll(".view")],

  metricDecisions: document.getElementById("metricDecisions"),
  metricResults: document.getElementById("metricResults"),
  metricWinRate: document.getElementById("metricWinRate"),
  metricPnlTotal: document.getElementById("metricPnlTotal"),
  metricProfitFactor: document.getElementById("metricProfitFactor"),
  metricInstancesOnline: document.getElementById("metricInstancesOnline"),
  dashboardSummary: document.getElementById("dashboardSummary"),
  dashboardEvents: document.getElementById("dashboardEvents"),

  instanceName: document.getElementById("instanceName"),
  instanceMode: document.getElementById("instanceMode"),
  instanceFormTitle: document.getElementById("instanceFormTitle"),
  instanceBrokerProfile: document.getElementById("instanceBrokerProfile"),
  instancePrimarySymbol: document.getElementById("instancePrimarySymbol"),
  instanceChartTimeframe: document.getElementById("instanceChartTimeframe"),
  instanceSymbols: document.getElementById("instanceSymbols"),
  instanceSymbolOptions: document.getElementById("instanceSymbolOptions"),
  instanceProfileHint: document.getElementById("instanceProfileHint"),
  instanceDetectedSymbols: document.getElementById("instanceDetectedSymbols"),
  createInstanceBtn: document.getElementById("createInstanceBtn"),
  cancelInstanceEditBtn: document.getElementById("cancelInstanceEditBtn"),
  refreshInstancesBtn: document.getElementById("refreshInstancesBtn"),
  newTokenBox: document.getElementById("newTokenBox"),
  instancesTableBody: document.getElementById("instancesTableBody"),
  instancesEmpty: document.getElementById("instancesEmpty"),
  instancesTableWrap: document.getElementById("instancesTableWrap"),
  instanceSearch: document.getElementById("instanceSearch"),
  instanceFilterMode: document.getElementById("instanceFilterMode"),
  instanceFilterStatus: document.getElementById("instanceFilterStatus"),
  applyInstanceFiltersBtn: document.getElementById("applyInstanceFiltersBtn"),

  riskPerTrade: document.getElementById("riskPerTrade"),
  maxSpread: document.getElementById("maxSpread"),
  defaultLot: document.getElementById("defaultLot"),
  stopLoss: document.getElementById("stopLoss"),
  takeProfit: document.getElementById("takeProfit"),
  maxPositions: document.getElementById("maxPositions"),
  reentryCooldown: document.getElementById("reentryCooldown"),
  maxCommandAge: document.getElementById("maxCommandAge"),
  deviation: document.getElementById("deviation"),
  retries: document.getElementById("retries"),
  pauseNewOrders: document.getElementById("pauseNewOrders"),
  localFallback: document.getElementById("localFallback"),
  decisionEngineMode: document.getElementById("decisionEngineMode"),
  operationalTimeframe: document.getElementById("operationalTimeframe"),
  confirmationTimeframe: document.getElementById("confirmationTimeframe"),
  marketSessionGuardEnabled: document.getElementById("marketSessionGuardEnabled"),
  newsPauseEnabled: document.getElementById("newsPauseEnabled"),
  newsPauseSymbols: document.getElementById("newsPauseSymbols"),
  newsPauseCountries: document.getElementById("newsPauseCountries"),
  newsPauseBefore: document.getElementById("newsPauseBefore"),
  newsPauseAfter: document.getElementById("newsPauseAfter"),
  newsPauseImpact: document.getElementById("newsPauseImpact"),
  performanceGateEnabled: document.getElementById("performanceGateEnabled"),
  performanceGateMinPf: document.getElementById("performanceGateMinPf"),
  performanceGateMinTrades: document.getElementById("performanceGateMinTrades"),
  validatedBacktestPf: document.getElementById("validatedBacktestPf"),
  validatedBacktestTrades: document.getElementById("validatedBacktestTrades"),
  dailyLossLimit: document.getElementById("dailyLossLimit"),
  maxEquityDrawdownPct: document.getElementById("maxEquityDrawdownPct"),
  breakEvenTriggerPoints: document.getElementById("breakEvenTriggerPoints"),
  trailingTriggerPoints: document.getElementById("trailingTriggerPoints"),
  positionTimeStopMinutes: document.getElementById("positionTimeStopMinutes"),
  positionStagnationWindowCandles: document.getElementById("positionStagnationWindowCandles"),
  loadParametersBtn: document.getElementById("loadParametersBtn"),
  saveParametersBtn: document.getElementById("saveParametersBtn"),
  parametersMeta: document.getElementById("parametersMeta"),
  parametersStory: document.getElementById("parametersStory"),
  parametersView: document.getElementById("view-parameters"),

  auditLimit: document.getElementById("auditLimit"),
  auditEventType: document.getElementById("auditEventType"),
  auditRobotId: document.getElementById("auditRobotId"),
  auditPositionAction: document.getElementById("auditPositionAction"),
  auditDateFrom: document.getElementById("auditDateFrom"),
  auditDateTo: document.getElementById("auditDateTo"),
  refreshAuditBtn: document.getElementById("refreshAuditBtn"),
  auditTableBody: document.getElementById("auditTableBody"),
  auditEmpty: document.getElementById("auditEmpty"),
  auditTableWrap: document.getElementById("auditTableWrap"),

  tutorialOpenBtn: document.getElementById("tutorialOpenBtn"),
  tutorialCloseBtn: document.getElementById("tutorialCloseBtn"),
  tutorialOverlay: document.getElementById("tutorialOverlay"),
  downloadAgentPackageBtn: document.getElementById("downloadAgentPackageBtn"),
  tutorialDownloadPackageBtn: document.getElementById("tutorialDownloadPackageBtn"),
  tutorialActionStatus: document.getElementById("tutorialActionStatus"),
};

function isCompactNavigation() {
  return window.matchMedia("(max-width: 1120px)").matches;
}

function syncSidebarState() {
  if (!dom.appShell) return;

  const isOpen = dom.appShell.classList.contains("sidebar-open");
  const canCollapse = isCompactNavigation();

  if (!canCollapse) {
    dom.appShell.classList.remove("sidebar-open");
  }

  const nextOpen = canCollapse && isOpen;
  if (dom.sidebarNav) {
    dom.sidebarNav.setAttribute("aria-hidden", nextOpen ? "false" : String(canCollapse));
  }
  if (dom.sidebarOverlay) {
    dom.sidebarOverlay.setAttribute("aria-hidden", nextOpen ? "false" : "true");
  }
  if (dom.sidebarToggleBtn) {
    dom.sidebarToggleBtn.setAttribute("aria-expanded", String(nextOpen));
  }
}

function setSidebarOpen(open) {
  if (!dom.appShell || !isCompactNavigation()) {
    syncSidebarState();
    return;
  }

  dom.appShell.classList.toggle("sidebar-open", Boolean(open));
  syncSidebarState();
}

function closeSidebar() {
  setSidebarOpen(false);
}

function toggleSidebar() {
  if (!dom.appShell) return;
  setSidebarOpen(!dom.appShell.classList.contains("sidebar-open"));
}

function setStatus(message, level = "info") {
  dom.status.textContent = message;
  dom.status.classList.remove("ok", "warn", "error");
  if (level === "ok") dom.status.classList.add("ok");
  if (level === "warn") dom.status.classList.add("warn");
  if (level === "error") dom.status.classList.add("error");
}

function safeJsonString(payload) {
  try {
    return JSON.stringify(payload, null, 2);
  } catch (_err) {
    return String(payload);
  }
}

function extractLastCreatedInstanceFromTokenBox() {
  const robotInstanceId = Number(dom.newTokenBox?.dataset.robotInstanceId);
  if (!Number.isInteger(robotInstanceId) || robotInstanceId <= 0) return null;
  return { robot_instance_id: robotInstanceId };
}

function getInstanceById(robotInstanceId) {
  const targetId = Number(robotInstanceId);
  if (!Number.isInteger(targetId) || targetId <= 0) return null;
  return state.instances.find((item) => Number(item.robot_instance_id) === targetId) || null;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatNumber(value, minimumFractionDigits = 0, maximumFractionDigits = minimumFractionDigits) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(number);
}

function formatSignedNumber(value) {
  const number = Number(value || 0);
  const signal = number > 0 ? "+" : number < 0 ? "-" : "";
  return `${signal}${formatNumber(Math.abs(number), 2, 2)}`;
}

function formatModeLabel(mode) {
  if (mode === "DEMO") return "Teste";
  if (mode === "REAL") return "Real";
  return mode || "-";
}

function getInstrumentProfileById(profileId) {
  return state.instrumentProfiles.find((item) => item.profile_id === profileId) || null;
}

function formatBrokerProfileLabel(profileId) {
  const profile = getInstrumentProfileById(profileId);
  return profile?.label || profileId || "Personalizado";
}

function collectUniqueSymbols(...groups) {
  const unique = [];
  const seen = new Set();

  for (const group of groups) {
    const items = Array.isArray(group) ? group : [];
    for (const rawItem of items) {
      const symbol = String(rawItem || "").trim();
      if (!symbol) continue;

      const dedupeKey = symbol.toUpperCase();
      if (seen.has(dedupeKey)) continue;

      seen.add(dedupeKey);
      unique.push(symbol);
    }
  }

  return unique;
}

function parseSymbolList(value) {
  const chunks = String(value || "")
    .split(/[\n,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);

  return collectUniqueSymbols(chunks).slice(0, 12);
}

function formatSymbolsSummary(symbols, primarySymbol = "") {
  const normalized = collectUniqueSymbols(primarySymbol ? [primarySymbol] : [], symbols);
  if (!normalized.length) {
    return "Aguardando setup do gráfico no MT5.";
  }
  if (normalized.length <= 4) {
    return normalized.join(", ");
  }
  return `${normalized.slice(0, 4).join(", ")} +${normalized.length - 4} mais`;
}

function formatDetectedSymbolsSummary(symbols) {
  const normalized = collectUniqueSymbols(symbols);
  if (!normalized.length) {
    return "Nenhum catálogo do MT5 recebido ainda.";
  }
  if (normalized.length <= 10) {
    return normalized.join(", ");
  }
  return `${normalized.slice(0, 10).join(", ")} +${normalized.length - 10} mais`;
}

function renderInstrumentProfiles() {
  if (!dom.instanceBrokerProfile) return;

  const profiles = state.instrumentProfiles.length
    ? state.instrumentProfiles
    : [
      {
        profile_id: "CUSTOM",
        label: "Personalizado",
        description: "Use os símbolos exatos do seu MT5.",
        suggested_symbols: [],
        note: "",
      },
    ];

  const currentValue = dom.instanceBrokerProfile.value || profiles[0].profile_id;
  dom.instanceBrokerProfile.innerHTML = profiles.map((profile) => `
    <option value="${escapeHtml(profile.profile_id)}">${escapeHtml(profile.label)}</option>
  `).join("");

  const nextValue = profiles.some((profile) => profile.profile_id === currentValue)
    ? currentValue
    : profiles[0].profile_id;
  dom.instanceBrokerProfile.value = nextValue;
  updateInstrumentProfileHint();
  renderInstanceSymbolOptions();
}

function updateInstrumentProfileHint(prefillIfEmpty = false) {
  if (!dom.instanceProfileHint || !dom.instanceBrokerProfile) return;

  const profile = getInstrumentProfileById(dom.instanceBrokerProfile.value);
  if (!profile) {
    dom.instanceProfileHint.textContent = "Use os nomes exatos exibidos pelo MT5 da sua corretora.";
    return;
  }

  const suggested = Array.isArray(profile.suggested_symbols) ? profile.suggested_symbols : [];
  if (prefillIfEmpty && dom.instancePrimarySymbol && !dom.instancePrimarySymbol.value.trim() && suggested.length) {
    dom.instancePrimarySymbol.value = suggested[0];
  }
  if (prefillIfEmpty && dom.instanceSymbols && !dom.instanceSymbols.value.trim() && suggested.length) {
    dom.instanceSymbols.value = suggested.join(", ");
  }

  const parts = [profile.description, profile.note];
  if (suggested.length) {
    parts.push(`Sugestão inicial: ${suggested.join(", ")}.`);
  }
  dom.instanceProfileHint.textContent = parts.filter(Boolean).join(" ");
  renderInstanceSymbolOptions();
}

function renderInstanceSymbolOptions(instance = null) {
  if (!dom.instanceSymbolOptions) return;

  const currentInstance = instance || getInstanceById(state.editingRobotInstanceId);
  const profile = getInstrumentProfileById(dom.instanceBrokerProfile?.value || "CUSTOM");
  const symbols = collectUniqueSymbols(
    profile?.suggested_symbols || [],
    currentInstance?.discovered_symbols || [],
    currentInstance?.selected_symbols || [],
    currentInstance?.primary_symbol ? [currentInstance.primary_symbol] : []
  );

  dom.instanceSymbolOptions.innerHTML = symbols
    .map((symbol) => `<option value="${escapeHtml(symbol)}"></option>`)
    .join("");
}

function renderDetectedSymbolsBox(instance = null) {
  if (!dom.instanceDetectedSymbols) return;

  const currentInstance = instance || getInstanceById(state.editingRobotInstanceId);
  if (!currentInstance) {
    dom.instanceDetectedSymbols.innerHTML = "Quando o MT5 ligar e mandar o catálogo, os símbolos detectados aparecem aqui.";
    return;
  }

  const detectedSymbols = Array.isArray(currentInstance.discovered_symbols) ? currentInstance.discovered_symbols : [];
  const detectedAt = currentInstance.symbols_detected_at
    ? formatDate(currentInstance.symbols_detected_at)
    : "aguardando o primeiro envio";

  if (!detectedSymbols.length) {
    dom.instanceDetectedSymbols.innerHTML = `
      <div class="stack">
        <strong>${escapeHtml(currentInstance.name || "Instância selecionada")}</strong>
        <div class="muted">Ainda não recebi o catálogo do MT5 desta instância.</div>
        <div class="muted">Assim que o EA ligar, o painel mostra aqui o ativo principal, o timeframe e os símbolos disponíveis.</div>
      </div>
    `;
    return;
  }

  dom.instanceDetectedSymbols.innerHTML = `
    <div class="stack">
      <strong>${escapeHtml(currentInstance.name || "Instância selecionada")}</strong>
      <div class="muted">Catálogo recebido ${escapeHtml(detectedAt)} • gráfico ${escapeHtml(currentInstance.primary_symbol || "-")} em ${escapeHtml(currentInstance.chart_timeframe || "-")}.</div>
      <div>${escapeHtml(formatDetectedSymbolsSummary(detectedSymbols))}</div>
    </div>
  `;
}

function renderInstanceFormMode() {
  const isEditing = Number.isInteger(Number(state.editingRobotInstanceId)) && Number(state.editingRobotInstanceId) > 0;

  if (dom.instanceFormTitle) {
    dom.instanceFormTitle.textContent = isEditing ? "Editar setup do robô" : "Criar novo robô";
  }
  if (dom.createInstanceBtn) {
    dom.createInstanceBtn.textContent = isEditing ? "Salvar setup" : "Criar robô";
  }
  if (dom.cancelInstanceEditBtn) {
    dom.cancelInstanceEditBtn.hidden = !isEditing;
  }
}

function resetInstanceForm() {
  state.editingRobotInstanceId = null;
  if (dom.instanceName) dom.instanceName.value = "";
  if (dom.instanceMode) dom.instanceMode.value = "DEMO";
  if (dom.instanceBrokerProfile) dom.instanceBrokerProfile.value = "CUSTOM";
  if (dom.instancePrimarySymbol) dom.instancePrimarySymbol.value = "";
  if (dom.instanceChartTimeframe) {
    dom.instanceChartTimeframe.value = state.parameters?.operational_timeframe || "M5";
  }
  if (dom.instanceSymbols) dom.instanceSymbols.value = "";

  renderInstanceFormMode();
  updateInstrumentProfileHint(false);
  renderDetectedSymbolsBox(null);
}

function fillInstanceForm(instance) {
  if (!instance) return;

  state.editingRobotInstanceId = Number(instance.robot_instance_id);
  if (dom.instanceName) dom.instanceName.value = instance.name || "";
  if (dom.instanceMode) dom.instanceMode.value = instance.mode || "DEMO";
  if (dom.instanceBrokerProfile) dom.instanceBrokerProfile.value = instance.broker_profile || "CUSTOM";
  if (dom.instancePrimarySymbol) dom.instancePrimarySymbol.value = instance.primary_symbol || "";
  if (dom.instanceChartTimeframe) dom.instanceChartTimeframe.value = instance.chart_timeframe || "M5";
  if (dom.instanceSymbols) dom.instanceSymbols.value = Array.isArray(instance.selected_symbols)
    ? instance.selected_symbols.join(", ")
    : "";

  renderInstanceFormMode();
  updateInstrumentProfileHint(false);
  renderInstanceSymbolOptions(instance);
  renderDetectedSymbolsBox(instance);
}

function formatRuntimeLabel(runtime) {
  if (runtime === "exe") return "aplicativo";
  if (runtime === "python") return "assistido";
  return runtime || "-";
}

function formatRobotStatus(status) {
  const normalized = String(status || "").toUpperCase();
  if (normalized === "ACTIVE") return "Ativo";
  if (normalized === "INACTIVE") return "Parado";
  if (normalized === "OFFLINE") return "Sem sinal";
  if (!normalized) return "Aguardando";
  return `${normalized.charAt(0)}${normalized.slice(1).toLowerCase()}`;
}

function formatSignalLabel(signal) {
  const normalized = String(signal || "").toUpperCase();
  if (normalized === "BUY") return "Compra";
  if (normalized === "SELL") return "Venda";
  if (normalized === "HOLD") return "Aguardar";
  return signal || "Sem decisão";
}

function toneFromSignal(signal) {
  const normalized = String(signal || "").toUpperCase();
  if (normalized === "BUY") return "buy";
  if (normalized === "SELL") return "sell";
  if (normalized === "HOLD") return "hold";
  return "info";
}

function humanizeToken(value) {
  const normalized = String(value || "").trim();
  if (!normalized || normalized === "none") return "-";
  return normalized.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatSetupLabel(setup) {
  const normalized = String(setup || "").toLowerCase();
  if (!normalized || normalized === "none") return "-";
  const map = {
    pin_bar: "Pin bar",
    bullish_pin_bar: "Pin bar de alta",
    bearish_pin_bar: "Pin bar de baixa",
    engulfing: "Engolfo",
    bullish_engulfing: "Engolfo de alta",
    bearish_engulfing: "Engolfo de baixa",
    inside_bar: "Inside bar",
    bullish_inside_bar: "Inside bar comprador",
    bearish_inside_bar: "Inside bar vendedor",
  };
  return map[normalized] || humanizeToken(normalized);
}

function formatZoneLabel(zone) {
  const normalized = String(zone || "").toLowerCase();
  const map = {
    support: "suporte",
    resistance: "resistência",
    range_low: "base do range",
    range_high: "topo do range",
    mid_range: "meio do range",
    neutral: "zona neutra",
  };
  return map[normalized] || humanizeToken(normalized).toLowerCase();
}

function formatStructureLabel(state) {
  const normalized = String(state || "").toLowerCase();
  const map = {
    bullish: "estrutura compradora",
    bearish: "estrutura vendedora",
    range: "mercado lateral",
    neutral: "estrutura neutra",
  };
  return map[normalized] || humanizeToken(normalized).toLowerCase();
}

function formatPauseReasonLabel(reason) {
  const normalized = String(reason || "").toLowerCase();
  const map = {
    manual_pause: "pausa manual",
    performance_gate: "edge mínimo não validado",
    news_pause: "janela de notícia",
    news_feed_unavailable: "calendário econômico indisponível",
    market_session_closed: "mercado fechado para este ativo",
    daily_loss_limit: "corte diário por perda fechada",
    equity_drawdown_limit: "corte por drawdown da equity",
  };
  return map[normalized] || humanizeToken(normalized).toLowerCase();
}

function formatDataQualityReasonLabel(reason) {
  const normalized = String(reason || "").toLowerCase();
  const map = {
    dados_repetidos: "dados repetidos no feed",
    feed_congelado: "feed congelado",
    ativo_parado: "ativo sem movimento",
  };
  return map[normalized] || humanizeToken(normalized).toLowerCase();
}

function formatPositionActionLabel(action) {
  const normalized = String(action || "").toUpperCase();
  const map = {
    NONE: "Gestão ativa",
    PROTECT: "Proteger lucro",
    CLOSE: "Fechar posição",
  };
  return map[normalized] || humanizeToken(normalized);
}

function toneFromPositionAction(action) {
  const normalized = String(action || "").toUpperCase();
  if (normalized === "PROTECT") return "buy";
  if (normalized === "CLOSE") return "sell";
  return "hold";
}

function formatManagementReasonLabel(reason) {
  const normalized = String(reason || "").toLowerCase();
  const map = {
    lucro_protegido: "lucro protegido",
    monitorando_sem_nova_entrada: "monitorando sem nova entrada",
    breakeven_ativo: "breakeven ativado",
    trailing_estrutural: "trailing estrutural",
    time_stop: "time stop atingido",
    estagnacao: "posição estagnada",
    dados_repetidos: "dados repetidos no feed",
    feed_congelado: "feed congelado",
    ativo_parado: "ativo sem movimento",
    rejeicao_em_resistencia: "rejeição em resistência",
    rejeicao_em_suporte: "rejeição em suporte",
    choch_bullish: "CHOCH comprador",
    choch_bearish: "CHOCH vendedor",
    false_breakout_bullish: "falso rompimento comprador",
    false_breakout_bearish: "falso rompimento vendedor",
    zone_false_breakout_bullish: "falso rompimento comprador na zona",
    zone_false_breakout_bearish: "falso rompimento vendedor na zona",
    fibonacci_bullish: "fibonacci comprador",
    fibonacci_bearish: "fibonacci vendedor",
  };
  return map[normalized] || humanizeToken(normalized).toLowerCase();
}

function formatTimeframePair(operational, confirmation) {
  if (!operational && !confirmation) return "-";
  if (!confirmation) return String(operational || "-");
  return `${operational || "-"} -> ${confirmation}`;
}

function formatRobotReference(source) {
  const robotId = Number(source?.scope_robot_instance_id ?? source?.robot_instance_id);
  const robotName = String(source?.scope_robot_name ?? source?.robot_name ?? source?.name ?? "").trim();

  if (Number.isInteger(robotId) && robotId > 0 && robotName) {
    return `#${robotId} ${robotName}`;
  }
  if (Number.isInteger(robotId) && robotId > 0) {
    return `#${robotId}`;
  }
  return robotName || "";
}

function prependRobotTag(tags, source) {
  const robotLabel = formatRobotReference(source);
  if (!robotLabel) return tags;
  return [{ label: robotLabel, tone: "info" }, ...tags];
}

function decorateEventTitle(title, source) {
  const robotLabel = formatRobotReference(source);
  return robotLabel ? `${robotLabel} • ${title}` : title;
}

function buildDecisionNarrative(signal, analysis, fallbackText) {
  if (!analysis || typeof analysis !== "object") return fallbackText;

  if (analysis.engine === "runtime_guard") {
    const reasons = Array.isArray(analysis.pause_reasons)
      ? analysis.pause_reasons.map(formatPauseReasonLabel).join(", ")
      : "travamento operacional";
    const firstNews = Array.isArray(analysis.news_pause_events) ? analysis.news_pause_events[0] : null;
    if (firstNews?.title) {
      return `Entrada pausada por ${reasons}. Evento ativo: ${firstNews.title} (${firstNews.country || "-"}).`;
    }
    return `Entrada pausada por ${reasons}.`;
  }

  if (analysis.engine === "market_data_guard") {
    const reasons = Array.isArray(analysis.data_quality_reasons) && analysis.data_quality_reasons.length
      ? analysis.data_quality_reasons.map(formatDataQualityReasonLabel).join(", ")
      : "qualidade insuficiente do mercado";
    return `Entrada pausada por ${reasons}. O feed recente não mostrou movimento confiável para nova entrada.`;
  }

  if (analysis.engine === "position_manager_v1") {
    const actionLabel = formatPositionActionLabel(analysis.management_action || "NONE");
    const parts = [`${actionLabel}.`];
    if (analysis.open_position_profit_points != null) {
      parts.push(`Lucro aberto de ${formatNumber(analysis.open_position_profit_points, 1, 1)} ponto(s).`);
    }
    if (analysis.open_position_elapsed_minutes != null) {
      parts.push(`Posição acompanhada há ${formatNumber(analysis.open_position_elapsed_minutes)} min.`);
    }
    if (Array.isArray(analysis.management_reasons) && analysis.management_reasons.length) {
      parts.push(`Motivo: ${analysis.management_reasons.map(formatManagementReasonLabel).join(", ")}.`);
    }
    if (analysis.stagnation_detected) {
      parts.push(`Leitura lateral na última janela de ${formatNumber(analysis.stagnation_window_size || 0)} candle(s).`);
    }
    if (analysis.fib_in_retracement_zone) {
      parts.push(`Fibonacci em zona de retração ${analysis.fib_entry_zone_label || "38.2%-61.8%"}${analysis.fib_anchor_source === "confirmed_pivot" ? " por pivô confirmado" : ""}.`);
    } else if (analysis.fib_near_retracement_zone) {
      parts.push("Fibonacci alinhado com a leitura atual.");
    }
    return parts.join(" ");
  }

  const parts = [];
  const setup = formatSetupLabel(analysis.setup_label || analysis.setup);
  const zone = formatZoneLabel(analysis.zone_type);
  const structure = formatStructureLabel(analysis.structure_state || analysis.state);
  const higherState = formatStructureLabel(analysis.higher_state);
  const extras = [];

  if (setup !== "-") {
    parts.push(`${setup} em ${zone}`);
  } else if (zone !== "-") {
    parts.push(`Leitura em ${zone}`);
  }

  if (structure !== "-") {
    extras.push(structure);
  }
  if (higherState !== "-" && higherState !== structure) {
    extras.push(`confirmação ${higherState}`);
  }
  if (analysis.bos_signal && analysis.bos_signal !== "none") {
    extras.push(`BOS ${analysis.bos_signal === "bullish" ? "comprador" : "vendedor"}`);
  }
  if (analysis.choch_signal && analysis.choch_signal !== "none") {
    extras.push(`CHOCH ${analysis.choch_signal === "bullish" ? "comprador" : "vendedor"}`);
  }
  if (analysis.structure_false_breakout_signal && analysis.structure_false_breakout_signal !== "none") {
    extras.push(`falso rompimento ${analysis.structure_false_breakout_signal === "bullish" ? "de alta" : "de baixa"}`);
  }
  if (analysis.fib_in_retracement_zone) {
    extras.push(`fibonacci ${analysis.fib_entry_zone_label || "38.2%-61.8%"}`);
  } else if (analysis.fib_near_retracement_zone) {
    extras.push("fibonacci alinhado");
  }

  if (extras.length) {
    parts.push(extras.join(" • "));
  }
  if (analysis.score != null) {
    parts.push(`score ${formatNumber(analysis.score, 2, 2)}`);
  }
  if (!parts.length && analysis.engine === "legacy_v1") {
    parts.push(`Fallback legado por tendência simples em ${analysis.observed_timeframe || "-"}`);
  }

  return parts.join(". ") || `${formatSignalLabel(signal)}: ${fallbackText}`;
}

function buildParametersStoryMarkup(parameters) {
  const timeframes = formatTimeframePair(parameters.operational_timeframe, parameters.confirmation_timeframe);
  const newsSymbols = parameters.news_pause_symbols === "*" ? "todos os ativos monitorados" : parameters.news_pause_symbols || "nenhum ativo";
  const newsCountries = parameters.news_pause_countries || "auto";
  const engineLabel = {
    HYBRID: "Híbrido",
    PRICE_ACTION_ONLY: "Só Price Action",
    LEGACY_ONLY: "Só legado",
  }[parameters.decision_engine_mode] || parameters.decision_engine_mode || "Híbrido";
  const robotLabel = formatRobotReference(parameters);
  const scopeStatus = parameters.parameter_scope === "robot"
    ? parameters.scope_inherited
      ? `Este robô ainda segue o padrão da conta: ${robotLabel}.`
      : `Proteções exclusivas ativas para ${robotLabel}.`
    : "Estas proteções valem como padrão da conta para novos robôs e fallback geral.";
  const newsStatus = parameters.news_pause_enabled
    ? parameters.news_pause_active
      ? `Pausa de notícias ativa agora para ${newsSymbols}.`
      : `Pausa de notícias ligada para ${newsSymbols} com foco em ${newsCountries}.`
    : "Pausa de notícias desligada.";
  const gateStatus = parameters.performance_gate_enabled
    ? parameters.performance_gate_passed
      ? `Edge aprovado: PF ${formatNumber(parameters.validated_backtest_profit_factor, 2, 2)} em ${formatNumber(parameters.validated_backtest_trades)} trade(s).`
      : `Edge ainda insuficiente: PF ${formatNumber(parameters.validated_backtest_profit_factor, 2, 2)} de ${formatNumber(parameters.performance_gate_min_profit_factor, 2, 2)} e ${formatNumber(parameters.validated_backtest_trades)} de ${formatNumber(parameters.performance_gate_min_trades)} trade(s).`
    : "Gate de edge desligado.";
  const sessionStatus = parameters.market_session_guard_enabled
    ? "Sessão por ativo ligada: o robô evita entrada fora do horário operacional do mercado monitorado."
    : "Sessão por ativo desligada.";
  const drawdownStatus = Number(parameters.daily_loss_limit || 0) > 0 || Number(parameters.max_equity_drawdown_pct || 0) > 0
    ? `Hard stop ativo em ${formatNumber(parameters.daily_loss_limit || 0, 2, 2)} de perda diária fechada e ${formatNumber(parameters.max_equity_drawdown_pct || 0, 1, 1)}% de drawdown da equity.`
    : "Hard stop diário/equity desligado.";
  const managementStatus = `Gestão de posição com breakeven em ${formatNumber(parameters.break_even_trigger_points || 0)} pts, trailing em ${formatNumber(parameters.trailing_trigger_points || 0)} pts, time stop de ${formatNumber(parameters.position_time_stop_minutes || 0)} min e leitura de estagnação em ${formatNumber(parameters.position_stagnation_window_candles || 0)} candle(s).`;
  const pauseStatus = parameters.runtime_pause_new_orders
    ? `Novas entradas pausadas por ${parameters.runtime_pause_reasons.map(formatPauseReasonLabel).join(", ")}.`
    : "Novas entradas liberadas neste momento.";

  return `
    <div class="stack">
      <div><strong>Escopo:</strong> ${escapeHtml(scopeStatus)}</div>
      <div><strong>Motor:</strong> ${escapeHtml(engineLabel)}</div>
      <div><strong>Leitura ativa:</strong> ${escapeHtml(timeframes)}</div>
      <div>${escapeHtml(newsStatus)}</div>
      <div>${escapeHtml(gateStatus)}</div>
      <div>${escapeHtml(sessionStatus)}</div>
      <div>${escapeHtml(drawdownStatus)}</div>
      <div>${escapeHtml(managementStatus)}</div>
      <div>${escapeHtml(pauseStatus)}</div>
    </div>
  `;
}

function formatOutcomeLabel(outcome) {
  const normalized = String(outcome || "").toUpperCase();
  if (normalized === "WIN") return "ganho";
  if (normalized === "LOSS") return "perda";
  if (normalized === "BREAKEVEN") return "zero a zero";
  if (!normalized) return "resultado recebido";
  return normalized.replaceAll("_", " ").toLowerCase();
}

function ageToLabel(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return "-";
  const age = Number(seconds);
  if (age < 60) return "agora";
  if (age < 3600) return `${Math.floor(age / 60)} min`;
  if (age < 86400) return `${Math.floor(age / 3600)} h`;
  return `${Math.floor(age / 86400)} d`;
}

function buildParametersQuery() {
  const editingId = Number(state.editingRobotInstanceId);
  if (Number.isInteger(editingId) && editingId > 0) {
    return `?robot_instance_id=${editingId}`;
  }
  return "";
}

function toIsoFromLocalDateTime(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

function isSessionExpired(session) {
  if (!session?.expires_at) return false;
  const expiry = new Date(session.expires_at).getTime();
  if (Number.isNaN(expiry)) return false;
  return Date.now() >= expiry;
}

function isLoggedIn() {
  return Boolean(state.authenticated);
}

function persistSession(session) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function readSession() {
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw);
    return isSessionExpired(parsed) ? null : parsed;
  } catch (_err) {
    return null;
  }
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
  stopAutoRefresh();
  state.session = null;
  state.me = null;
  state.authenticated = false;
  state.summary = null;
  state.instances = [];
  state.auditEvents = [];
  state.parameters = null;
  state.lastCreatedInstance = null;
  state.editingRobotInstanceId = null;
  renderSession();
  renderDashboard();
  renderInstances();
  renderAudit();
  renderParameters();
  renderLastCreatedInstanceBox();
  resetInstanceForm();
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(path, {
    method: options.method || "GET",
    headers,
    credentials: "include",
    body: options.body,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && options.auth !== false) {
      clearSession();
    }
    const detail = data?.detail || `Erro HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

function setView(viewName) {
  dom.navButtons.forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.viewTarget === viewName);
  });
  dom.views.forEach((view) => {
    view.classList.toggle("active", view.dataset.view === viewName);
  });
  closeSidebar();
}

function setAutoRefreshMode(mode, message = "") {
  autoRefreshMode = mode;
  autoRefreshMessage = message;
  renderAutoRefreshStatus();
}

function getAutoRefreshMetaText() {
  if (!isLoggedIn()) {
    return "Entre na sua conta e a tela passa a acompanhar tudo sozinha.";
  }

  if (document.hidden) {
    return "A aba está em segundo plano. Quando você voltar, eu sincronizo de novo.";
  }

  if (!lastAutoRefreshAt) {
    return "A primeira leitura automática aparece logo que a conta estiver conectada.";
  }

  const secondsLeft = Math.max(Math.ceil((nextAutoRefreshAt - Date.now()) / 1000), 0);
  const lastRefreshLabel = new Date(lastAutoRefreshAt).toLocaleTimeString("pt-BR");
  return `Última atualização às ${lastRefreshLabel}. Nova checagem em ${secondsLeft}s.`;
}

function renderAutoRefreshStatus() {
  if (!dom.autoRefreshBadge || !dom.autoRefreshLabel || !dom.autoRefreshMeta) return;

  dom.autoRefreshBadge.classList.remove("live", "syncing", "warn", "off");

  if (!isLoggedIn()) {
    dom.autoRefreshBadge.classList.add("off");
    dom.autoRefreshLabel.textContent = "Atualização automática em espera";
    dom.autoRefreshMeta.textContent = "Entre na sua conta e a tela começa a se atualizar sozinha.";
    return;
  }

  if (autoRefreshMode === "syncing") {
    dom.autoRefreshBadge.classList.add("syncing");
    dom.autoRefreshLabel.textContent = "Atualizando sem travar a tela";
    dom.autoRefreshMeta.textContent = autoRefreshMessage || "Buscando novidades agora.";
    return;
  }

  if (autoRefreshMode === "warn") {
    dom.autoRefreshBadge.classList.add("warn");
    dom.autoRefreshLabel.textContent = "Tentando reconectar";
    dom.autoRefreshMeta.textContent = autoRefreshMessage || "Falhou agora, mas vou tentar de novo sozinha.";
    return;
  }

  dom.autoRefreshBadge.classList.add("live");
  dom.autoRefreshLabel.textContent = "Atualização automática ligada";
  dom.autoRefreshMeta.textContent = autoRefreshMessage || getAutoRefreshMetaText();
}

function scheduleNextAutoRefresh() {
  nextAutoRefreshAt = Date.now() + AUTO_REFRESH_MS;
  if (autoRefreshMode === "live") {
    renderAutoRefreshStatus();
  }
}

function stopAutoRefresh() {
  if (autoRefreshTimerId) {
    window.clearInterval(autoRefreshTimerId);
    autoRefreshTimerId = 0;
  }
  if (autoRefreshTickerId) {
    window.clearInterval(autoRefreshTickerId);
    autoRefreshTickerId = 0;
  }
  nextAutoRefreshAt = 0;
  lastAutoRefreshAt = 0;
  autoRefreshMode = "off";
  autoRefreshMessage = "";
  renderAutoRefreshStatus();
}

function startAutoRefresh() {
  if (!isLoggedIn()) {
    stopAutoRefresh();
    return;
  }

  if (!autoRefreshTickerId) {
    autoRefreshTickerId = window.setInterval(() => {
      if (autoRefreshMode === "live") {
        renderAutoRefreshStatus();
      }
    }, 1000);
  }

  if (!autoRefreshTimerId) {
    scheduleNextAutoRefresh();
    autoRefreshTimerId = window.setInterval(() => {
      if (!isLoggedIn()) {
        stopAutoRefresh();
        return;
      }
      if (document.hidden) return;
      void runRefreshCycle({ silent: true, source: "auto" });
    }, AUTO_REFRESH_MS);
  }

  setAutoRefreshMode("live");
}

function isEditingParameters() {
  const active = document.activeElement;
  return Boolean(
    active
      && dom.parametersView
      && dom.parametersView.contains(active)
      && ["INPUT", "SELECT", "TEXTAREA"].includes(active.tagName)
  );
}

function openTutorial() {
  if (!dom.tutorialOverlay) return;
  dom.tutorialOverlay.classList.add("open");
  dom.tutorialOverlay.setAttribute("aria-hidden", "false");
}

function closeTutorial() {
  if (!dom.tutorialOverlay) return;
  dom.tutorialOverlay.classList.remove("open");
  dom.tutorialOverlay.setAttribute("aria-hidden", "true");
}

function renderLastCreatedInstanceBox(instance = null) {
  if (!dom.newTokenBox) return;

  const lastInstance = instance || state.lastCreatedInstance;
  if (!lastInstance) {
    dom.newTokenBox.dataset.robotInstanceId = "";
    dom.newTokenBox.innerHTML = "Quando você criar um robô, o resumo dele aparece aqui.";
    return;
  }

  const technicalToken = lastInstance.token || "-";
  const bridgeName = lastInstance.bridge_name || "VunoBridge";
  const brokerLabel = formatBrokerProfileLabel(lastInstance.broker_profile);
  const symbolsLabel = formatSymbolsSummary(lastInstance.selected_symbols, lastInstance.primary_symbol);
  const setupLabel = lastInstance.primary_symbol
    ? `${lastInstance.primary_symbol} • ${lastInstance.chart_timeframe || "M5"}`
    : `Timeframe ${lastInstance.chart_timeframe || "M5"}`;
  const detectedCount = Array.isArray(lastInstance.discovered_symbols) ? lastInstance.discovered_symbols.length : 0;
  dom.newTokenBox.dataset.robotInstanceId = String(lastInstance.robot_instance_id || "");
  dom.newTokenBox.innerHTML = `
    <div class="stack">
      <strong>${escapeHtml(lastInstance.name || "Novo robô")}</strong>
      <div class="muted">Conta ${escapeHtml(formatModeLabel(lastInstance.mode))} pronta para baixar.</div>
      <div class="muted">Perfil ${escapeHtml(brokerLabel)} • bridge ${escapeHtml(bridgeName)}</div>
      <div class="muted">Setup: ${escapeHtml(setupLabel)}</div>
      <div class="muted">Ativos: ${escapeHtml(symbolsLabel)}</div>
      <div class="muted">MT5 detectado: ${escapeHtml(detectedCount ? `${detectedCount} símbolo(s)` : "aguardando catálogo")}</div>
      <div>O pacote já vai com tudo ligado. Você só precisa baixar, extrair e abrir.</div>
      <div class="muted">Se o suporte pedir, este é o código técnico do robô:</div>
      <div class="token-inline">${escapeHtml(technicalToken)}</div>
    </div>
  `;
}

function setTutorialActionStatus(message, level = "muted") {
  if (!dom.tutorialActionStatus) return;
  dom.tutorialActionStatus.textContent = message;
  dom.tutorialActionStatus.classList.remove("ok", "warn");
  if (level === "ok") dom.tutorialActionStatus.classList.add("ok");
  if (level === "warn") dom.tutorialActionStatus.classList.add("warn");
}

function pulseButtonLabel(button, successLabel, defaultLabel, ms = 1800) {
  if (!button) return;
  button.textContent = successLabel;
  button.disabled = true;
  window.setTimeout(() => {
    button.textContent = defaultLabel;
    button.disabled = false;
  }, ms);
}

function getLatestRobotInstanceId() {
  const directId = Number(state.lastCreatedInstance?.robot_instance_id);
  if (Number.isInteger(directId) && directId > 0) {
    return directId;
  }

  const parsed = extractLastCreatedInstanceFromTokenBox();
  const parsedId = Number(parsed?.robot_instance_id);
  if (Number.isInteger(parsedId) && parsedId > 0) {
    return parsedId;
  }

  if (state.instances.length === 1) {
    const singleId = Number(state.instances[0]?.robot_instance_id);
    if (Number.isInteger(singleId) && singleId > 0) {
      return singleId;
    }
  }

  return null;
}

function describeAuditEvent(event) {
  const payload = event?.payload || {};

  if (event?.event_type === "trade_decision_recorded") {
    const symbol = payload.symbol || payload.snapshot?.symbol || "Mercado";
    const signal = payload.signal || payload.decision?.signal || "HOLD";
    const rationale = payload.rationale || payload.decision?.rationale || "Analise concluida.";
    const analysis = payload.analysis || payload.decision?.analysis || {};
    const positionAction = payload.position_action || payload.decision?.position_action || analysis.management_action || "NONE";
    const timeframe = payload.timeframe || analysis.observed_timeframe || "";
    const tags = [
      { label: symbol, tone: "info" },
      analysis.engine === "position_manager_v1"
        ? { label: formatPositionActionLabel(positionAction), tone: toneFromPositionAction(positionAction) }
        : { label: formatSignalLabel(signal), tone: toneFromSignal(signal) },
    ];
    if (analysis.setup_label || analysis.setup) {
      tags.push({ label: formatSetupLabel(analysis.setup_label || analysis.setup), tone: "info" });
    }
    if (analysis.zone_type) {
      tags.push({ label: formatZoneLabel(analysis.zone_type), tone: "hold" });
    }
    if (analysis.fib_in_retracement_zone) {
      tags.push({ label: `Fib ${analysis.fib_entry_zone_label || "38.2%-61.8%"}`, tone: "info" });
    } else if (analysis.fib_near_retracement_zone) {
      tags.push({ label: "Fib alinhado", tone: "info" });
    }
    if (analysis.score != null) {
      tags.push({ label: `score ${formatNumber(analysis.score, 2, 2)}`, tone: "hold" });
    }
    if (Array.isArray(analysis.management_reasons) && analysis.management_reasons.length) {
      tags.push({ label: formatManagementReasonLabel(analysis.management_reasons[0]), tone: "hold" });
    }
    return {
      title: decorateEventTitle(
        timeframe
          ? `${symbol} (${timeframe}): ${analysis.engine === "position_manager_v1" ? formatPositionActionLabel(positionAction) : formatSignalLabel(signal)}`
          : `${symbol}: ${analysis.engine === "position_manager_v1" ? formatPositionActionLabel(positionAction) : formatSignalLabel(signal)}`,
        event,
      ),
      text: buildDecisionNarrative(signal, analysis, rationale),
      tags: prependRobotTag(tags, event),
    };
  }

  if (event?.event_type === "position_management_recorded") {
    const symbol = payload.symbol || payload.snapshot?.symbol || "Mercado";
    const analysis = payload.analysis || payload.decision?.analysis || {};
    const timeframe = payload.timeframe || analysis.observed_timeframe || "";
    const positionAction = payload.position_action || payload.decision?.position_action || analysis.management_action || "NONE";
    const tags = [
      { label: symbol, tone: "info" },
      { label: formatPositionActionLabel(positionAction), tone: toneFromPositionAction(positionAction) },
    ];
    if (analysis.open_position_profit_points != null) {
      tags.push({ label: `${formatNumber(analysis.open_position_profit_points, 1, 1)} pts`, tone: "hold" });
    }
    if (analysis.fib_in_retracement_zone) {
      tags.push({ label: `Fib ${analysis.fib_entry_zone_label || "38.2%-61.8%"}`, tone: "info" });
    }
    if (Array.isArray(analysis.management_reasons) && analysis.management_reasons.length) {
      tags.push({ label: formatManagementReasonLabel(analysis.management_reasons[0]), tone: "hold" });
    }
    return {
      title: decorateEventTitle(
        timeframe ? `${symbol} (${timeframe}): ${formatPositionActionLabel(positionAction)}` : `${symbol}: ${formatPositionActionLabel(positionAction)}`,
        event,
      ),
      text: buildDecisionNarrative(payload.signal || "HOLD", analysis, payload.rationale || "Gestao de posicao."),
      tags: prependRobotTag(tags, event),
    };
  }

  if (event?.event_type === "trade_result_recorded") {
    const symbol = payload.symbol || payload.feedback?.symbol || "Operação";
    const outcome = payload.outcome || payload.feedback?.outcome || "";
    const pnl = payload.pnl ?? payload.feedback?.pnl;
    const pnlTone = Number(pnl) > 0 ? "buy" : Number(pnl) < 0 ? "sell" : "hold";
    return {
      title: decorateEventTitle(`${symbol}: ${formatOutcomeLabel(outcome)}`, event),
      text: pnl == null
        ? "O sistema recebeu o retorno de uma operação executada."
        : `O retorno desta operação foi ${formatSignedNumber(pnl)}.`,
      tags: prependRobotTag([
        { label: symbol, tone: "info" },
        { label: formatOutcomeLabel(outcome), tone: pnlTone },
      ], event),
    };
  }

  if (event?.event_type === "robot_instance_created") {
    return {
      title: decorateEventTitle("Novo robô criado", event),
      text: `${payload.name || "Seu robô"} foi criado no modo ${formatModeLabel(payload.mode)}.`,
      tags: prependRobotTag([{ label: formatModeLabel(payload.mode), tone: "info" }], event),
    };
  }

  if (event?.event_type === "robot_instance_updated") {
    return {
      title: decorateEventTitle("Setup atualizado", event),
      text: `${payload.name || "O robô"} agora usa ${payload.primary_symbol || "o ativo do gráfico"} em ${payload.chart_timeframe || "M5"}.`,
      tags: prependRobotTag([{ label: payload.chart_timeframe || "M5", tone: "info" }], event),
    };
  }

  if (event?.event_type === "robot_symbols_detected") {
    const count = Number(payload.available_symbols_count || 0);
    const chartSymbol = payload.chart_symbol || "gráfico atual";
    return {
      title: decorateEventTitle("Catálogo recebido do MT5", event),
      text: count
        ? `${count} símbolo(s) foram detectados. O gráfico atual está em ${chartSymbol} ${payload.chart_timeframe ? `(${payload.chart_timeframe})` : ""}.`
        : "O MT5 respondeu, mas ainda não enviou símbolos disponíveis.",
      tags: prependRobotTag([
        { label: chartSymbol, tone: "info" },
        { label: payload.chart_timeframe || "M5", tone: "hold" },
      ], event),
    };
  }

  if (event?.event_type === "agent_package_downloaded") {
    return {
      title: decorateEventTitle("Pacote baixado", event),
      text: `O pacote pronto do robô ${payload.name || "selecionado"} foi baixado pelo painel.`,
      tags: prependRobotTag([{ label: formatModeLabel(payload.mode), tone: "info" }], event),
    };
  }

  if (event?.event_type === "robot_instance_creation_blocked") {
    return {
      title: decorateEventTitle("Criação bloqueada pelo gate", event),
      text: `O sistema segurou ${payload.name || "o robô"} porque o edge validado ainda não bate o mínimo exigido.`,
      tags: prependRobotTag([{ label: formatModeLabel(payload.mode), tone: "hold" }], event),
    };
  }

  if (event?.event_type === "user_parameters_updated") {
    const isRobotScope = payload.parameter_scope === "robot";
    return {
      title: isRobotScope
        ? decorateEventTitle("Proteções do robô atualizadas", event)
        : "Proteções da conta atualizadas",
      text: isRobotScope
        ? `${payload.scope_robot_name || "Este robô"} recebeu uma configuração própria de risco, leitura e filtros.`
        : "O padrão da conta foi atualizado para novos robôs e para quem ainda não tiver override próprio.",
      tags: prependRobotTag([
        { label: isRobotScope ? "Escopo do robô" : "Padrão da conta", tone: "info" },
      ], event),
    };
  }

  if (event?.event_type === "robot_instance_deleted") {
    return {
      title: decorateEventTitle("Robô excluído", event),
      text: `${payload.name || "O robô"} saiu da lista ativa do painel.`,
      tags: prependRobotTag([{ label: formatModeLabel(payload.mode), tone: "hold" }], event),
    };
  }

  if (event?.event_type === "user_logged_in") {
    return {
      title: "Conta conectada",
      text: "O acesso ao painel foi confirmado com sucesso.",
      tags: [{ label: "Acesso", tone: "buy" }],
    };
  }

  if (event?.event_type === "user_logged_out") {
    return {
      title: "Conta desconectada",
      text: "A sessão foi encerrada pelo usuário.",
      tags: [{ label: "Saída", tone: "hold" }],
    };
  }

  if (event?.event_type === "user_registered") {
    return {
      title: "Conta criada",
      text: "Uma nova conta foi aberta neste painel.",
      tags: [{ label: "Cadastro", tone: "buy" }],
    };
  }

  const fallbackTitle = String(event?.event_type || "Atualização")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
  return {
    title: fallbackTitle,
    text: "Uma atualização foi registrada pelo sistema.",
    tags: [],
  };
}

function buildEventTagsMarkup(tags = []) {
  if (!tags.length) return "";
  return `
    <div class="event-tags">
      ${tags.map((tag) => `<span class="tag ${tag.tone || "info"}">${escapeHtml(tag.label)}</span>`).join("")}
    </div>
  `;
}

function buildDashboardSummaryMarkup(summary) {
  const latestDecisionEvent = state.auditEvents.find((event) => ["trade_decision_recorded", "position_management_recorded"].includes(event.event_type));
  const latestDecision = latestDecisionEvent ? describeAuditEvent(latestDecisionEvent) : null;
  const decisions = Number(summary?.decisions_total || 0);
  const results = Number(summary?.results_total || 0);
  const online = Number(summary?.instances_online || 0);
  const totalInstances = Number(summary?.instances_total || 0);
  const winRate = Number(summary?.win_rate_pct || 0);
  const pnlTotal = Number(summary?.pnl_total || 0);
  const parameterState = state.parameters;
  const tenantName = state.session?.user?.tenant_name || "Sua conta";
  const userEmail = state.me?.email || "Entre para começar";
  const onlineHeadline = totalInstances
    ? `${online} de ${totalInstances} robô(s) ligados agora`
    : "Ainda não há robôs cadastrados";
  const onlineText = totalInstances
    ? `Último sinal do painel em ${summary?.last_decision_at ? formatDate(summary.last_decision_at) : "ainda sem análise registrada"}.`
    : "Crie o primeiro robô e o painel passa a acompanhar tudo daqui.";
  const resultHeadline = results
    ? `${formatNumber(summary?.wins || 0)} ganho(s) e ${formatNumber(summary?.losses || 0)} perda(s)`
    : "Ainda sem operação encerrada";
  const resultText = results
    ? `Acerto de ${formatNumber(winRate, 1, 1)}% e saldo acumulado de ${formatSignedNumber(pnlTotal)}.`
    : "Quando a primeira operação fechar, o desempenho aparece aqui automaticamente.";
  const signalsText = decisions
    ? `Sinais gerados até agora: ${formatNumber(summary?.buy_signals || 0)} de compra, ${formatNumber(summary?.sell_signals || 0)} de venda e ${formatNumber(summary?.hold_signals || 0)} de espera.`
    : "Ainda não há sinais registrados. Assim que surgir algo novo, esta área se atualiza sozinha.";
  const strategyText = parameterState
    ? `Leitura principal em ${formatTimeframePair(parameterState.operational_timeframe, parameterState.confirmation_timeframe)}.${parameterState.runtime_pause_new_orders ? ` Entradas pausadas por ${parameterState.runtime_pause_reasons.map(formatPauseReasonLabel).join(", ")}.` : " Entradas liberadas agora."}`
    : "";

  return `
    <div class="summary-grid">
      <article class="summary-card">
        <span class="eyebrow">Conta</span>
        <strong>${escapeHtml(tenantName)}</strong>
        <p>${escapeHtml(userEmail)}</p>
      </article>
      <article class="summary-card">
        <span class="eyebrow">Robôs ligados</span>
        <strong>${escapeHtml(onlineHeadline)}</strong>
        <p>${escapeHtml(onlineText)}</p>
      </article>
      <article class="summary-card">
        <span class="eyebrow">Última análise</span>
        <strong>${escapeHtml(latestDecision ? latestDecision.title : "Ainda sem leitura do mercado")}</strong>
        <p>${escapeHtml(latestDecision ? latestDecision.text : "Quando o robô ler o gráfico, você verá aqui o ativo, a direção e o motivo.")}</p>
      </article>
      <article class="summary-card">
        <span class="eyebrow">Resultado</span>
        <strong>${escapeHtml(resultHeadline)}</strong>
        <p>${escapeHtml(resultText)}</p>
      </article>
    </div>
    <div class="summary-note">${escapeHtml(`${signalsText} ${strategyText}`.trim())}</div>
  `;
}

function buildDashboardEventsMarkup(events) {
  if (!events.length) {
    return '<div class="empty">Ainda não houve movimentações por aqui. Assim que algo acontecer, você vê nesta lista sem apertar F5.</div>';
  }

  return `
    <div class="events-feed">
      ${events.map((event) => {
        const item = describeAuditEvent(event);
        return `
          <article class="event-card">
            <div class="event-top">
              <strong class="event-title">${escapeHtml(item.title)}</strong>
              <span class="event-time">${escapeHtml(formatDate(event.created_at || event.at))}</span>
            </div>
            <p class="event-text">${escapeHtml(item.text)}</p>
            ${buildEventTagsMarkup(item.tags)}
          </article>
        `;
      }).join("")}
    </div>
  `;
}

function extractFilenameFromDisposition(contentDisposition, fallbackFilename) {
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch (_err) {
      return utf8Match[1];
    }
  }

  const match = contentDisposition.match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallbackFilename;
}

async function downloadBinaryFile(url, fallbackFilename) {
  const response = await fetch(url, {
    method: "GET",
    credentials: "include",
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      clearSession();
    }
    throw new Error(data?.detail || `Erro HTTP ${response.status}`);
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("content-disposition") || "";
  const filename = extractFilenameFromDisposition(contentDisposition, fallbackFilename);
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}

async function handleAgentPackageDownload(button = null, explicitRobotInstanceId = null) {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta antes de baixar o robô.", "warn");
    setTutorialActionStatus("Entre na sua conta antes de baixar o robô.", "warn");
    return;
  }

  const robotInstanceId = explicitRobotInstanceId || getLatestRobotInstanceId();
  if (!robotInstanceId) {
    setStatus("Crie um robô primeiro para liberar o pacote pronto.", "warn");
    setTutorialActionStatus("Crie um robô antes de baixar o pacote pronto.", "warn");
    return;
  }

  await downloadBinaryFile(
    `/api/robot-instances/${robotInstanceId}/agent-package`,
    `vuno-robo-${robotInstanceId}.zip`
  );
  setStatus("Download concluído. Extraia o arquivo e abra iniciar-vuno-robo.cmd.", "ok");
  setTutorialActionStatus("Pacote baixado. Agora extraia o arquivo e abra iniciar-vuno-robo.cmd.", "ok");

  if (button) {
    const defaultLabel = button.dataset.defaultLabel || button.textContent;
    pulseButtonLabel(button, "Baixado!", defaultLabel);
  }
}

async function handleDeleteInstance(robotInstanceId) {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta antes de excluir um robô.", "warn");
    return;
  }

  const instance = getInstanceById(robotInstanceId);
  if (!instance) {
    setStatus("Não consegui identificar esse robô para excluir.", "warn");
    return;
  }

  const confirmed = window.confirm(`Excluir ${instance.name}? O robô sai da lista ativa e o token deixa de funcionar.`);
  if (!confirmed) return;

  await api(`/api/robot-instances/${robotInstanceId}`, { method: "DELETE" });

  if (Number(state.editingRobotInstanceId) === robotInstanceId) {
    resetInstanceForm();
    await loadParameters();
  }
  if (Number(state.lastCreatedInstance?.robot_instance_id) === robotInstanceId) {
    state.lastCreatedInstance = null;
  }

  await Promise.all([loadInstances(), loadSummary(), loadAudit(Number(dom.auditLimit.value) || 50)]);
  renderDashboard();
  renderLastCreatedInstanceBox();
  setTutorialActionStatus("Robô excluído da lista ativa.", "ok");
  setStatus(`Robô ${instance.name} excluído com sucesso.`, "ok");
}

async function handleInstancesTableClick(event) {
  const actionButton = event.target.closest("[data-instance-action]");
  if (!actionButton) return;

  const action = actionButton.dataset.instanceAction;
  const robotInstanceId = Number(actionButton.dataset.robotInstanceId);
  if (!Number.isInteger(robotInstanceId) || robotInstanceId <= 0) {
    setStatus("Não consegui identificar essa instância.", "warn");
    return;
  }

  if (action === "edit-instance") {
    const instance = getInstanceById(robotInstanceId);
    if (!instance) {
      setStatus("Não consegui carregar esse setup agora. Atualize a lista e tente de novo.", "warn");
      return;
    }

    fillInstanceForm(instance);
    await loadParameters();
    setStatus(`Setup de ${instance.name} carregado. A aba Proteções agora edita este robô.`, "ok");
    return;
  }

  if (action === "delete-instance") {
    await handleDeleteInstance(robotInstanceId);
    return;
  }

  if (action !== "download-agent-package") return;

  actionButton.dataset.defaultLabel = actionButton.dataset.defaultLabel || actionButton.textContent;
  await handleAgentPackageDownload(actionButton, robotInstanceId);
}

function renderSession() {
  if (!isLoggedIn()) {
    dom.sessionUser.textContent = "Conta desconectada";
    dom.sessionTenant.textContent = "-";
    dom.sessionExpiry.textContent = "-";
    renderAutoRefreshStatus();
    return;
  }

  const userLabel = state.session?.user?.email || "usuário";
  const tenantLabel = state.session?.user?.tenant_name || "-";
  dom.sessionUser.textContent = `Conectado como ${userLabel}`;
  dom.sessionTenant.textContent = tenantLabel;
  dom.sessionExpiry.textContent = formatDate(state.session?.expires_at);
  renderAutoRefreshStatus();
}

function renderDashboard() {
  const summary = state.summary;
  const decisions = Number(summary?.decisions_total || 0);
  const results = Number(summary?.results_total || 0);
  const winRate = Number(summary?.win_rate_pct || 0);
  const pnlTotal = Number(summary?.pnl_total || 0);
  const pf = Number(summary?.profit_factor || 0);
  const online = Number(summary?.instances_online || 0);
  const totalInstances = Number(summary?.instances_total || 0);

  dom.metricDecisions.textContent = formatNumber(decisions);
  dom.metricResults.textContent = formatNumber(results);
  dom.metricWinRate.textContent = `${formatNumber(winRate, 1, 1)}%`;
  dom.metricPnlTotal.textContent = formatSignedNumber(pnlTotal);
  dom.metricProfitFactor.textContent = formatNumber(pf, 2, 2);
  dom.metricInstancesOnline.textContent = `${online}/${totalInstances}`;

  dom.dashboardSummary.innerHTML = buildDashboardSummaryMarkup(summary);
  dom.dashboardEvents.innerHTML = buildDashboardEventsMarkup(state.auditEvents.slice(0, 6));
}

function renderInstances() {
  const rows = state.instances || [];
  dom.instancesTableBody.innerHTML = "";

  if (!rows.length) {
    dom.instancesEmpty.hidden = false;
    dom.instancesTableWrap.hidden = true;
    return;
  }

  dom.instancesEmpty.hidden = true;
  dom.instancesTableWrap.hidden = false;

  for (const row of rows) {
    const tr = document.createElement("tr");
    const status = row.last_status || "-";
    const brokerLabel = formatBrokerProfileLabel(row.broker_profile);
    const symbolsLabel = formatSymbolsSummary(row.selected_symbols, row.primary_symbol);
    const detectedCount = Array.isArray(row.discovered_symbols) ? row.discovered_symbols.length : 0;
    const setupFlow = row.primary_symbol
      ? `${row.primary_symbol} • gráfico ${row.chart_timeframe || "M5"}`
      : `gráfico ${row.chart_timeframe || "M5"}`;
    const connectivity = row.is_online
      ? '<span class="tag buy" title="Ligado agora">On</span>'
      : '<span class="tag hold" title="Sem sinal">Off</span>';
    const packageDelivery = row.package_delivery_mode === "exe"
      ? { title: "Abre direto", hint: "Sem depender do Python" }
      : { title: "Assistido", hint: "Instala e abre sozinho" };
    const heartbeatDetails = row.last_heartbeat_details || {};

    const heartbeatAgeLabel = ageToLabel(row.heartbeat_age_seconds);
    const heartbeatLabel = row.last_heartbeat_at
      ? `${formatDate(row.last_heartbeat_at)} • ${heartbeatAgeLabel === "agora" ? "agora" : `há ${heartbeatAgeLabel}`}`
      : "Ainda sem contato";
    const heartbeatSummaryParts = [];
    if (typeof heartbeatDetails.agent_runtime === "string" && heartbeatDetails.agent_runtime) {
      heartbeatSummaryParts.push(`rodando em ${formatRuntimeLabel(heartbeatDetails.agent_runtime)}`);
    }
    const pendingSnapshots = Number(heartbeatDetails.pending_snapshots);
    const pendingFeedback = Number(heartbeatDetails.pending_feedback);
    if (Number.isInteger(pendingSnapshots) && pendingSnapshots > 0) {
      heartbeatSummaryParts.push(`${pendingSnapshots} leitura(s) na fila`);
    }
    if (Number.isInteger(pendingFeedback) && pendingFeedback > 0) {
      heartbeatSummaryParts.push(`${pendingFeedback} retorno(s) pendente(s)`);
    }
    const heartbeatSummary = heartbeatSummaryParts.join(" • ") || (row.is_online
      ? "Tudo em dia por agora."
      : "Esperando o primeiro sinal deste robô.");
    const runtimeFlow = formatTimeframePair(row.operational_timeframe, row.confirmation_timeframe);
    const runtimeState = row.runtime_pause_new_orders
      ? `Entradas pausadas: ${row.runtime_pause_reasons.map(formatPauseReasonLabel).join(", ")}`
      : row.news_pause_active
        ? "Janela de notícia ativa agora."
        : row.performance_gate_passed
          ? "Leitura liberada para operar."
          : "Aguardando edge mínimo.";

    tr.innerHTML = `
      <td data-label="ID">${row.robot_instance_id}</td>
      <td data-label="Robô">
        <strong>${escapeHtml(row.name)}</strong>
        <div class="muted">${escapeHtml(brokerLabel)} • bridge ${escapeHtml(row.bridge_name || "VunoBridge")}</div>
        <div class="muted">${escapeHtml(symbolsLabel)}</div>
        <div class="muted">${escapeHtml(detectedCount ? `${detectedCount} símbolo(s) detectado(s) no MT5` : "Catálogo do MT5 ainda não recebido")}</div>
      </td>
      <td data-label="Conta">${escapeHtml(formatModeLabel(row.mode))}</td>
      <td data-label="Situação">${escapeHtml(formatRobotStatus(status))}</td>
      <td data-label="Ao vivo">${connectivity}</td>
      <td data-label="Último contato">
        <div>${escapeHtml(heartbeatLabel)}</div>
        <div class="muted">${escapeHtml(heartbeatSummary)}</div>
      </td>
      <td data-label="Setup / leitura">
        <div>${escapeHtml(setupFlow)}</div>
        <div class="muted">Leitura ${escapeHtml(runtimeFlow)}</div>
        <div class="muted">${escapeHtml(runtimeState)}</div>
      </td>
      <td data-label="Pacote">
        <div>${escapeHtml(packageDelivery.title)}</div>
        <div class="muted">${escapeHtml(packageDelivery.hint)}</div>
      </td>
      <td data-label="Ações">
        <div class="button-row">
          <button
            type="button"
            class="ghost"
            data-instance-action="edit-instance"
            data-robot-instance-id="${row.robot_instance_id}"
          >Editar setup</button>
          <button
            type="button"
            class="ghost"
            data-instance-action="download-agent-package"
            data-robot-instance-id="${row.robot_instance_id}"
          >Baixar robô pronto</button>
          <button
            type="button"
            class="warn"
            data-instance-action="delete-instance"
            data-robot-instance-id="${row.robot_instance_id}"
          >Excluir</button>
        </div>
      </td>
    `;
    dom.instancesTableBody.appendChild(tr);
  }
}

function renderParameters() {
  const p = state.parameters;
  if (!p) {
    dom.parametersMeta.textContent = "Última atualização: nada carregado ainda.";
    return;
  }

  dom.riskPerTrade.value = p.risk_per_trade;
  dom.maxSpread.value = p.max_spread_points;
  dom.defaultLot.value = p.default_lot;
  dom.stopLoss.value = p.stop_loss_points;
  dom.takeProfit.value = p.take_profit_points;
  dom.maxPositions.value = p.max_positions_per_symbol;
  dom.reentryCooldown.value = p.reentry_cooldown_seconds;
  dom.maxCommandAge.value = p.max_command_age_seconds;
  dom.deviation.value = p.deviation_points;
  dom.retries.value = p.execution_retries;
  dom.pauseNewOrders.value = String(Boolean(p.pause_new_orders));
  dom.localFallback.value = String(Boolean(p.use_local_fallback));
  dom.decisionEngineMode.value = p.decision_engine_mode || "HYBRID";
  dom.operationalTimeframe.value = p.operational_timeframe;
  dom.confirmationTimeframe.value = p.confirmation_timeframe;
  dom.marketSessionGuardEnabled.value = String(Boolean(p.market_session_guard_enabled));
  dom.newsPauseEnabled.value = String(Boolean(p.news_pause_enabled));
  dom.newsPauseSymbols.value = p.news_pause_symbols;
  dom.newsPauseCountries.value = p.news_pause_countries;
  dom.newsPauseBefore.value = p.news_pause_before_minutes;
  dom.newsPauseAfter.value = p.news_pause_after_minutes;
  dom.newsPauseImpact.value = p.news_pause_impact;
  dom.performanceGateEnabled.value = String(Boolean(p.performance_gate_enabled));
  dom.performanceGateMinPf.value = p.performance_gate_min_profit_factor;
  dom.performanceGateMinTrades.value = p.performance_gate_min_trades;
  dom.validatedBacktestPf.value = p.validated_backtest_profit_factor;
  dom.validatedBacktestTrades.value = p.validated_backtest_trades;
  dom.dailyLossLimit.value = p.daily_loss_limit;
  dom.maxEquityDrawdownPct.value = p.max_equity_drawdown_pct;
  dom.breakEvenTriggerPoints.value = p.break_even_trigger_points;
  dom.trailingTriggerPoints.value = p.trailing_trigger_points;
  dom.positionTimeStopMinutes.value = p.position_time_stop_minutes;
  dom.positionStagnationWindowCandles.value = p.position_stagnation_window_candles;
  const robotLabel = formatRobotReference(p);
  const scopeText = p.parameter_scope === "robot"
    ? p.scope_inherited
      ? `Robô selecionado: ${robotLabel}. Ainda usando o padrão da conta.`
      : `Robô selecionado: ${robotLabel}. Proteções exclusivas ativas.`
    : "Padrão da conta para novos robôs e fallback geral.";
  dom.parametersMeta.textContent = `${scopeText} Última atualização: ${formatDate(p.updated_at)}`;
  if (dom.loadParametersBtn) {
    dom.loadParametersBtn.textContent = p.parameter_scope === "robot"
      ? "Atualizar proteções deste robô"
      : "Atualizar proteções";
  }
  if (dom.saveParametersBtn) {
    dom.saveParametersBtn.textContent = p.parameter_scope === "robot"
      ? "Salvar proteções deste robô"
      : "Salvar proteções";
  }
  if (dom.parametersStory) {
    dom.parametersStory.innerHTML = buildParametersStoryMarkup(p);
  }
}

function renderAudit() {
  dom.auditTableBody.innerHTML = "";
  const rows = state.auditEvents || [];

  if (!rows.length) {
    dom.auditEmpty.hidden = false;
    dom.auditTableWrap.hidden = true;
    return;
  }

  dom.auditEmpty.hidden = true;
  dom.auditTableWrap.hidden = false;

  for (const event of rows) {
    const description = describeAuditEvent(event);
    const robotLabel = formatRobotReference(event) || "-";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td data-label="ID">${event.event_id}</td>
      <td data-label="Data">${escapeHtml(formatDate(event.created_at))}</td>
      <td data-label="Evento">${escapeHtml(description.title)}</td>
      <td data-label="Usuário">${event.user_id ?? "-"}</td>
      <td data-label="Robô">${escapeHtml(robotLabel)}</td>
      <td data-label="Detalhe">
        <div>${escapeHtml(description.text)}</div>
        ${buildEventTagsMarkup(description.tags)}
      </td>
    `;
    dom.auditTableBody.appendChild(tr);
  }
}

function buildInstancesQuery() {
  const params = new URLSearchParams();
  params.set("online_window_seconds", "120");

  const search = dom.instanceSearch.value.trim();
  const mode = dom.instanceFilterMode.value;
  const status = dom.instanceFilterStatus.value;

  if (search) params.set("search", search);
  if (mode) params.set("mode", mode);
  if (status) params.set("status", status);

  return params.toString();
}

function buildAuditQuery(limit) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));

  const eventType = dom.auditEventType.value.trim();
  const robotId = dom.auditRobotId.value.trim();
  const positionAction = dom.auditPositionAction.value.trim();
  const dateFromIso = toIsoFromLocalDateTime(dom.auditDateFrom.value);
  const dateToIso = toIsoFromLocalDateTime(dom.auditDateTo.value);

  if (eventType) params.set("event_type", eventType);
  if (robotId) params.set("robot_instance_id", robotId);
  if (positionAction) params.set("position_action", positionAction);
  if (dateFromIso) params.set("date_from", dateFromIso);
  if (dateToIso) params.set("date_to", dateToIso);

  return params.toString();
}

async function loadMe() {
  state.me = await api("/api/auth/me");
  state.authenticated = true;
}

async function loadInstrumentProfiles() {
  state.instrumentProfiles = await api("/api/instrument-profiles", { auth: false });
  renderInstrumentProfiles();
}

async function loadSummary() {
  state.summary = await api("/api/summary");
}

async function loadInstances() {
  const query = buildInstancesQuery();
  state.instances = await api(`/api/robot-instances?${query}`);
  renderInstances();

  const lastCreatedId = Number(state.lastCreatedInstance?.robot_instance_id);
  if (Number.isInteger(lastCreatedId) && lastCreatedId > 0) {
    const refreshed = getInstanceById(lastCreatedId);
    if (refreshed) {
      state.lastCreatedInstance = { ...state.lastCreatedInstance, ...refreshed };
    }
  }

  renderLastCreatedInstanceBox();
  const editingInstance = getInstanceById(state.editingRobotInstanceId);
  renderInstanceSymbolOptions(editingInstance || null);
  renderDetectedSymbolsBox(editingInstance || null);
}

async function loadParameters() {
  state.parameters = await api(`/api/parameters${buildParametersQuery()}`);
  renderParameters();
}

async function loadAudit(limit) {
  const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 200);
  const query = buildAuditQuery(safeLimit);
  state.auditEvents = await api(`/api/audit-events?${query}`);
  renderAudit();
}

async function refreshDashboardBundle(options = {}) {
  const limit = Number(dom.auditLimit.value) || 50;
  const tasks = [loadMe(), loadSummary(), loadInstances(), loadAudit(limit)];
  if (!options.skipParameters) {
    tasks.push(loadParameters());
  }
  await Promise.all(tasks);

  renderSession();
  renderDashboard();
}

async function runRefreshCycle({ silent = false, source = "manual", successMessage = "Painel sincronizado agora." } = {}) {
  if (!isLoggedIn()) {
    renderAutoRefreshStatus();
    if (!silent) {
      setStatus("Entre na sua conta e a tela passa a acompanhar tudo sozinha.", "warn");
    }
    return;
  }

  if (refreshInFlight) return;

  refreshInFlight = true;
  setAutoRefreshMode(
    "syncing",
    source === "auto"
      ? "Buscando novidades sem recarregar a página."
      : "Sincronizando tudo agora."
  );

  try {
    await refreshDashboardBundle({
      skipParameters: source === "auto" && isEditingParameters(),
    });
    lastAutoRefreshAt = Date.now();
    if (isLoggedIn()) {
      scheduleNextAutoRefresh();
      setAutoRefreshMode("live");
    }
    if (!silent && successMessage) {
      setStatus(successMessage, "ok");
    }
  } catch (err) {
    if (isLoggedIn()) {
      scheduleNextAutoRefresh();
      setAutoRefreshMode("warn", "Não consegui atualizar agora. Vou tentar de novo sozinha.");
    } else {
      renderAutoRefreshStatus();
    }
    if (!silent) {
      throw err;
    }
  } finally {
    refreshInFlight = false;
  }
}

function readParametersForm() {
  return {
    risk_per_trade: Number(dom.riskPerTrade.value),
    max_spread_points: Number(dom.maxSpread.value),
    default_lot: Number(dom.defaultLot.value),
    stop_loss_points: Number(dom.stopLoss.value),
    take_profit_points: Number(dom.takeProfit.value),
    max_positions_per_symbol: Number(dom.maxPositions.value),
    reentry_cooldown_seconds: Number(dom.reentryCooldown.value),
    max_command_age_seconds: Number(dom.maxCommandAge.value),
    deviation_points: Number(dom.deviation.value),
    execution_retries: Number(dom.retries.value),
    pause_new_orders: dom.pauseNewOrders.value === "true",
    use_local_fallback: dom.localFallback.value === "true",
    decision_engine_mode: dom.decisionEngineMode.value,
    operational_timeframe: dom.operationalTimeframe.value,
    confirmation_timeframe: dom.confirmationTimeframe.value,
    market_session_guard_enabled: dom.marketSessionGuardEnabled.value === "true",
    news_pause_enabled: dom.newsPauseEnabled.value === "true",
    news_pause_symbols: dom.newsPauseSymbols.value.trim().toUpperCase(),
    news_pause_countries: dom.newsPauseCountries.value.trim().toUpperCase(),
    news_pause_before_minutes: Number(dom.newsPauseBefore.value),
    news_pause_after_minutes: Number(dom.newsPauseAfter.value),
    news_pause_impact: dom.newsPauseImpact.value,
    performance_gate_enabled: dom.performanceGateEnabled.value === "true",
    performance_gate_min_profit_factor: Number(dom.performanceGateMinPf.value),
    performance_gate_min_trades: Number(dom.performanceGateMinTrades.value),
    validated_backtest_profit_factor: Number(dom.validatedBacktestPf.value),
    validated_backtest_trades: Number(dom.validatedBacktestTrades.value),
    daily_loss_limit: Number(dom.dailyLossLimit.value),
    max_equity_drawdown_pct: Number(dom.maxEquityDrawdownPct.value),
    break_even_trigger_points: Number(dom.breakEvenTriggerPoints.value),
    trailing_trigger_points: Number(dom.trailingTriggerPoints.value),
    position_time_stop_minutes: Number(dom.positionTimeStopMinutes.value),
    position_stagnation_window_candles: Number(dom.positionStagnationWindowCandles.value),
  };
}

async function handleRegister() {
  const email = dom.email.value.trim();
  const password = dom.password.value;
  const tenantName = dom.tenantName.value.trim();

  if (!email || !password) {
    setStatus("Preencha email e senha para criar sua conta.", "warn");
    return;
  }

  const payload = { email, password };
  if (tenantName) payload.tenant_name = tenantName;

  const data = await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    auth: false,
  });

  setStatus(`Conta criada para ${data.email}. Agora é só entrar.`, "ok");
}

async function handleLogin() {
  const email = dom.email.value.trim();
  const password = dom.password.value;

  if (!email || !password) {
    setStatus("Digite email e senha para entrar.", "warn");
    return;
  }

  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    auth: false,
  });

  state.session = {
    expires_at: data.expires_at,
    user: data.user,
  };
  state.me = data.user;
  state.authenticated = true;
  persistSession(state.session);
  renderSession();
  await runRefreshCycle({ silent: true, source: "login" });
  startAutoRefresh();
  setStatus("Você entrou. A tela já começou a se atualizar sozinha.", "ok");
}

async function handleLogout() {
  if (isLoggedIn()) {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch (_err) {
      // ignora falha de logout remoto e limpa sessão local
    }
  }

  clearSession();
  setStatus("Você saiu da conta.", "ok");
}

async function handleCreateInstance() {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta antes de criar um robô.", "warn");
    return;
  }

  const name = dom.instanceName.value.trim() || "Robô local";
  const mode = dom.instanceMode.value;
  const brokerProfile = dom.instanceBrokerProfile?.value || "CUSTOM";
  const primarySymbol = dom.instancePrimarySymbol?.value.trim() || "";
  const chartTimeframe = dom.instanceChartTimeframe?.value || "M5";
  const selectedSymbols = parseSymbolList(dom.instanceSymbols?.value || "");
  const editingId = Number(state.editingRobotInstanceId);
  const isEditing = Number.isInteger(editingId) && editingId > 0;

  const data = await api(isEditing ? `/api/robot-instances/${editingId}` : "/api/robot-instances", {
    method: isEditing ? "PUT" : "POST",
    body: JSON.stringify({
      name,
      mode,
      broker_profile: brokerProfile,
      primary_symbol: primarySymbol,
      chart_timeframe: chartTimeframe,
      selected_symbols: selectedSymbols,
    }),
  });

  state.lastCreatedInstance = data;
  await Promise.all([loadInstances(), loadSummary(), loadAudit(Number(dom.auditLimit.value) || 50), loadParameters()]);
  renderDashboard();

  const refreshedInstance = getInstanceById(data.robot_instance_id) || data;
  state.lastCreatedInstance = { ...data, ...refreshedInstance };
  renderLastCreatedInstanceBox(state.lastCreatedInstance);

  if (isEditing) {
    fillInstanceForm(refreshedInstance);
    setTutorialActionStatus("Setup salvo. Se quiser, baixe um pacote novo com esse ajuste.", "ok");
    setStatus(`Setup de ${data.name} atualizado com sucesso.`, "ok");
    return;
  }

  resetInstanceForm();
  setTutorialActionStatus("Robô criado. Agora é só baixar o pacote pronto.", "ok");
  setStatus(`Robô ${data.name} criado. Agora baixe o pacote pronto.`, "ok");
}

async function handleSaveParameters() {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta antes de salvar as proteções.", "warn");
    return;
  }

  const payload = readParametersForm();
  state.parameters = await api(`/api/parameters${buildParametersQuery()}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });

  renderParameters();
  await Promise.all([loadInstances(), loadSummary(), loadAudit(Number(dom.auditLimit.value) || 50)]);
  renderDashboard();
  const scopeLabel = formatRobotReference(state.parameters);
  setStatus(
    state.parameters.parameter_scope === "robot"
      ? `Proteções de ${scopeLabel} atualizadas com sucesso.`
      : "Proteções da conta atualizadas com sucesso.",
    "ok",
  );
}

async function handleRefreshAudit() {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta para ver o histórico.", "warn");
    return;
  }

  const limit = Number(dom.auditLimit.value) || 50;
  await loadAudit(limit);
  renderDashboard();
  setStatus("Histórico atualizado.", "ok");
}

async function handleApplyInstanceFilters() {
  if (!isLoggedIn()) {
    setStatus("Entre na sua conta para filtrar os robôs.", "warn");
    return;
  }

  await loadInstances();
  setStatus("Lista de robôs atualizada.", "ok");
}

function bindEvents() {
  dom.navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      setView(btn.dataset.viewTarget);
      if (btn.dataset.viewTarget === "parameters" && isLoggedIn()) {
        void runGuarded(loadParameters);
      }
    });
  });

  if (dom.sidebarToggleBtn) {
    dom.sidebarToggleBtn.addEventListener("click", toggleSidebar);
  }
  if (dom.sidebarCloseBtn) {
    dom.sidebarCloseBtn.addEventListener("click", closeSidebar);
  }
  if (dom.sidebarOverlay) {
    dom.sidebarOverlay.addEventListener("click", closeSidebar);
  }
  window.addEventListener("resize", syncSidebarState);

  dom.registerBtn.addEventListener("click", () => runGuarded(handleRegister));
  dom.loginBtn.addEventListener("click", () => runGuarded(handleLogin));
  dom.logoutBtn.addEventListener("click", () => runGuarded(handleLogout));
  dom.refreshAllBtn.addEventListener("click", () => runGuarded(() => runRefreshCycle({ source: "manual" })));

  dom.createInstanceBtn.addEventListener("click", () => runGuarded(handleCreateInstance));
  if (dom.cancelInstanceEditBtn) {
    dom.cancelInstanceEditBtn.addEventListener("click", () => runGuarded(async () => {
      resetInstanceForm();
      await loadParameters();
      setStatus("Edição cancelada. As proteções voltaram para o padrão da conta.", "ok");
    }));
  }
  dom.refreshInstancesBtn.addEventListener("click", () => runGuarded(loadInstances, "Instâncias atualizadas."));
  if (dom.instanceBrokerProfile) {
    dom.instanceBrokerProfile.addEventListener("change", () => updateInstrumentProfileHint(true));
  }
  dom.applyInstanceFiltersBtn.addEventListener("click", () => runGuarded(handleApplyInstanceFilters));
  dom.instancesTableBody.addEventListener("click", (event) =>
    runGuarded(() => handleInstancesTableClick(event))
  );

  dom.loadParametersBtn.addEventListener("click", () => runGuarded(loadParameters, "Parâmetros carregados."));
  dom.saveParametersBtn.addEventListener("click", () => runGuarded(handleSaveParameters));

  dom.refreshAuditBtn.addEventListener("click", () => runGuarded(handleRefreshAudit));

  if (dom.tutorialOpenBtn) {
    dom.tutorialOpenBtn.addEventListener("click", openTutorial);
  }
  if (dom.tutorialCloseBtn) {
    dom.tutorialCloseBtn.addEventListener("click", closeTutorial);
  }
  if (dom.tutorialOverlay) {
    dom.tutorialOverlay.addEventListener("click", (event) => {
      if (event.target === dom.tutorialOverlay) closeTutorial();
    });
  }
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTutorial();
      closeSidebar();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (!isLoggedIn()) return;
    if (!document.hidden) {
      scheduleNextAutoRefresh();
      void runRefreshCycle({ silent: true, source: "auto" });
      return;
    }
    renderAutoRefreshStatus();
  });
  if (dom.downloadAgentPackageBtn) {
    dom.downloadAgentPackageBtn.dataset.defaultLabel = "Baixar robô pronto";
    dom.downloadAgentPackageBtn.addEventListener("click", () =>
      runGuarded(() => handleAgentPackageDownload(dom.downloadAgentPackageBtn))
    );
  }
  if (dom.tutorialDownloadPackageBtn) {
    dom.tutorialDownloadPackageBtn.dataset.defaultLabel = "Baixar robô pronto";
    dom.tutorialDownloadPackageBtn.addEventListener("click", () =>
      runGuarded(() => handleAgentPackageDownload(dom.tutorialDownloadPackageBtn))
    );
  }
}

async function runGuarded(fn, successMessage = "") {
  try {
    await fn();
    if (successMessage) setStatus(successMessage, "ok");
  } catch (err) {
    setStatus(err.message || "Falha inesperada.", "error");
  }
}

async function bootstrap() {
  bindEvents();
  syncSidebarState();

  try {
    await loadInstrumentProfiles();
  } catch (_err) {
    renderInstrumentProfiles();
  }

  resetInstanceForm();

  state.session = readSession();
  if (state.session?.user) {
    state.me = state.session.user;
    state.authenticated = true;
  }
  renderSession();
  renderLastCreatedInstanceBox();
  renderDashboard();
  renderInstances();
  renderAudit();
  renderParameters();

  if (!state.session?.user) {
    setStatus("Tudo pronto. Entre com sua conta para acompanhar.", "warn");
    return;
  }

  try {
    await runRefreshCycle({ silent: true, source: "restore" });
    startAutoRefresh();
    setStatus("Conta restaurada. A tela está acompanhando tudo sozinha.", "ok");
  } catch (err) {
    clearSession();
    setStatus("Sua sessão expirou. Entre novamente para continuar.", "warn");
  }
}

bootstrap();
