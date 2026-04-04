state.subscriptionAccess = null;
state.adminBootstrapStatus = null;
state.adminOverview = null;
state.adminPlans = [];
state.adminBilling = null;
state.adminPlanChanges = [];
state.adminUsers = [];
state.adminManagedSubscriptions = [];

Object.assign(dom, {
  navAdminSaas: document.getElementById("navAdminSaas"),
  sessionPlan: document.getElementById("sessionPlan"),
  sessionPlanStatus: document.getElementById("sessionPlanStatus"),
  sessionPlanNote: document.getElementById("sessionPlanNote"),
  subscriptionCard: document.getElementById("subscriptionCard"),
  parametersPlanGate: document.getElementById("parametersPlanGate"),
  parametersPanel: document.getElementById("parametersPanel"),
  auditPlanGate: document.getElementById("auditPlanGate"),
  auditPanel: document.getElementById("auditPanel"),
  adminAccessGate: document.getElementById("adminAccessGate"),
  adminBootstrapPanel: document.getElementById("adminBootstrapPanel"),
  adminBootstrapMeta: document.getElementById("adminBootstrapMeta"),
  adminBootstrapBtn: document.getElementById("adminBootstrapBtn"),
  adminPanel: document.getElementById("adminPanel"),
  adminMetricTenants: document.getElementById("adminMetricTenants"),
  adminMetricPlans: document.getElementById("adminMetricPlans"),
  adminMetricSubscriptions: document.getElementById("adminMetricSubscriptions"),
  adminMetricTrials: document.getElementById("adminMetricTrials"),
  adminMetricCatalog: document.getElementById("adminMetricCatalog"),
  adminMetricMrr: document.getElementById("adminMetricMrr"),
  adminPlanCode: document.getElementById("adminPlanCode"),
  adminPlanName: document.getElementById("adminPlanName"),
  adminPlanDescription: document.getElementById("adminPlanDescription"),
  adminPlanMonthly: document.getElementById("adminPlanMonthly"),
  adminPlanYearly: document.getElementById("adminPlanYearly"),
  adminPlanUsers: document.getElementById("adminPlanUsers"),
  adminPlanBots: document.getElementById("adminPlanBots"),
  adminPlanTrades: document.getElementById("adminPlanTrades"),
  adminPlanTokens: document.getElementById("adminPlanTokens"),
  adminPlanStorage: document.getElementById("adminPlanStorage"),
  adminPlanActive: document.getElementById("adminPlanActive"),
  adminCreatePlanBtn: document.getElementById("adminCreatePlanBtn"),
  adminCreatePlanMeta: document.getElementById("adminCreatePlanMeta"),
  adminPlanCatalog: document.getElementById("adminPlanCatalog"),
  adminSubscriptionsEmpty: document.getElementById("adminSubscriptionsEmpty"),
  adminSubscriptionsWrap: document.getElementById("adminSubscriptionsWrap"),
  adminSubscriptionsBody: document.getElementById("adminSubscriptionsBody"),
  adminUsersSearch: document.getElementById("adminUsersSearch"),
  adminRefreshUsersBtn: document.getElementById("adminRefreshUsersBtn"),
  adminUsersEmpty: document.getElementById("adminUsersEmpty"),
  adminUsersWrap: document.getElementById("adminUsersWrap"),
  adminUsersBody: document.getElementById("adminUsersBody"),
  adminSubscriptionStatusFilter: document.getElementById("adminSubscriptionStatusFilter"),
  adminSubscriptionPlanFilter: document.getElementById("adminSubscriptionPlanFilter"),
  adminRefreshManagedSubscriptionsBtn: document.getElementById("adminRefreshManagedSubscriptionsBtn"),
  adminManagedSubscriptionsEmpty: document.getElementById("adminManagedSubscriptionsEmpty"),
  adminManagedSubscriptionsWrap: document.getElementById("adminManagedSubscriptionsWrap"),
  adminManagedSubscriptionsBody: document.getElementById("adminManagedSubscriptionsBody"),
  adminBillingStatus: document.getElementById("adminBillingStatus"),
  adminBillingProvider: document.getElementById("adminBillingProvider"),
  adminRefreshBillingBtn: document.getElementById("adminRefreshBillingBtn"),
  adminBillingMetricEvents: document.getElementById("adminBillingMetricEvents"),
  adminBillingMetricTrials: document.getElementById("adminBillingMetricTrials"),
  adminBillingMetricSucceeded: document.getElementById("adminBillingMetricSucceeded"),
  adminBillingMetricNet: document.getElementById("adminBillingMetricNet"),
  adminBillingMetricFailed: document.getElementById("adminBillingMetricFailed"),
  adminBillingMetricRefunds: document.getElementById("adminBillingMetricRefunds"),
  adminBillingMetricProviders: document.getElementById("adminBillingMetricProviders"),
  adminBillingEmpty: document.getElementById("adminBillingEmpty"),
  adminBillingWrap: document.getElementById("adminBillingWrap"),
  adminBillingBody: document.getElementById("adminBillingBody"),
  adminPlanHistoryFilter: document.getElementById("adminPlanHistoryFilter"),
  adminRefreshPlanChangesBtn: document.getElementById("adminRefreshPlanChangesBtn"),
  adminPlanChangesMetricTotal: document.getElementById("adminPlanChangesMetricTotal"),
  adminPlanChangesMetricPrices: document.getElementById("adminPlanChangesMetricPrices"),
  adminPlanChangesMetricLimits: document.getElementById("adminPlanChangesMetricLimits"),
  adminPlanChangesMetricMetadata: document.getElementById("adminPlanChangesMetricMetadata"),
  adminPlanChangesMetricStatus: document.getElementById("adminPlanChangesMetricStatus"),
  adminPlanChangesEmpty: document.getElementById("adminPlanChangesEmpty"),
  adminPlanChangesWrap: document.getElementById("adminPlanChangesWrap"),
  adminPlanChangesBody: document.getElementById("adminPlanChangesBody"),
});

const SAAS_REQUIRED_ACTIVE_PLAN_VIEWS = new Map([
  ["audit", "Historico"],
]);

function formatCurrencyBrl(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));
}

function formatSubscriptionStatus(status) {
  const normalized = String(status || "none").toLowerCase();
  const labels = {
    active: "Plano ativo",
    trialing: "Trial ativo",
    past_due: "Pagamento pendente",
    canceled: "Cancelado",
    paused: "Pausado",
    none: "Sem assinatura",
  };
  return labels[normalized] || humanizeToken(normalized);
}

function formatBootstrapReason(reason) {
  const labels = {
    available: "Bootstrap local disponivel.",
    already_admin: "Sua conta ja tem acesso admin.",
    admin_already_exists: "Ja existe um admin SaaS configurado na base.",
    disabled_outside_development: "Bootstrap desabilitado fora do ambiente de desenvolvimento.",
  };
  return labels[String(reason || "")] || "Bootstrap indisponivel neste momento.";
}

function formatBillingEventType(eventType) {
  const normalized = String(eventType || "").toLowerCase();
  const labels = {
    subscription_created: "Nova assinatura",
    subscription_plan_changed: "Troca de plano",
    subscription_status_changed: "Troca de status",
    charge_attempted: "Tentativa",
    charge_succeeded: "Sucesso",
    charge_failed: "Falha",
    refund_issued: "Reembolso",
    subscription_canceled: "Cancelada",
  };
  return labels[normalized] || humanizeToken(normalized);
}

function formatPlanChangeType(changeType) {
  const normalized = String(changeType || "").toLowerCase();
  const labels = {
    plan_created: "Plano criado",
    price_update: "Preco",
    limit_update: "Limite",
    metadata_update: "Metadado",
    status_change: "Status",
  };
  return labels[normalized] || humanizeToken(normalized);
}

function formatPlanFieldName(fieldName) {
  const normalized = String(fieldName || "").toLowerCase();
  const labels = {
    monthly_price: "Preco mensal",
    yearly_price: "Preco anual",
    max_users: "Max. usuarios",
    max_trades_per_month: "Trades/mes",
    max_ai_tokens_per_day: "Tokens/dia",
    max_storage_gb: "Storage GB",
    max_bots: "Robos",
    is_active: "Status",
    name: "Nome",
    code: "Codigo",
    description: "Descricao",
  };
  return labels[normalized] || humanizeToken(normalized);
}

function parseOptionalInt(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  return Number(raw);
}

function parseOptionalFloat(value) {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  return Number(raw);
}

function hasActivePlan() {
  return Boolean(state.subscriptionAccess?.has_active_plan);
}

function hasSaasAdminSurface() {
  return Boolean(state.me?.is_platform_admin || state.adminBootstrapStatus?.can_bootstrap);
}

function isSubscriptionAccessPending() {
  return isLoggedIn() && !state.subscriptionAccess;
}

function viewRequiresActivePlan(viewName) {
  return SAAS_REQUIRED_ACTIVE_PLAN_VIEWS.has(String(viewName || ""));
}

function syncSessionUserFromProfile() {
  if (!state.session?.user || !state.me) return;
  state.session.user = { ...state.session.user, ...state.me };
  persistSession(state.session);
}

function buildPlanGateMarkup(moduleName) {
  const access = state.subscriptionAccess;
  const planLabel = access?.plan_name || "trial local";
  const trialText = access?.is_trialing
    ? `Seu trial segue ativo por ${access.trial_days_left} dia(s), mas este modulo exige um plano ativo.`
    : "Este modulo exige um plano ativo antes da liberacao operacional.";
  return `
    <strong>Acesso bloqueado para ${escapeHtml(moduleName)}</strong>
    <p>${escapeHtml(trialText)}</p>
    <p>Plano atual: ${escapeHtml(planLabel)}. Status: ${escapeHtml(formatSubscriptionStatus(access?.status))}.</p>
  `;
}

function buildAdminAccessMarkup() {
  if (!isLoggedIn()) {
    return "<strong>Entre na conta para abrir o admin SaaS</strong><p>O painel admin fica disponivel apenas para usuarios autenticados com perfil de plataforma.</p>";
  }
  return `<strong>Acesso restrito ao admin SaaS</strong><p>${escapeHtml(formatBootstrapReason(state.adminBootstrapStatus?.reason))}</p>`;
}

function renderSubscriptionSurface() {
  if (!dom.sessionPlan || !dom.sessionPlanStatus || !dom.sessionPlanNote || !dom.subscriptionCard) return;

  if (!isLoggedIn()) {
    dom.sessionPlan.textContent = "-";
    dom.sessionPlanStatus.textContent = "-";
    dom.sessionPlanNote.textContent = "Entre na sua conta para ver o status SaaS da sua assinatura.";
    dom.subscriptionCard.innerHTML = "Entre na sua conta para carregar trial, plano, status e modulos liberados.";
    return;
  }

  if (!state.subscriptionAccess) {
    dom.sessionPlan.textContent = "Carregando";
    dom.sessionPlanStatus.textContent = "...";
    dom.sessionPlanNote.textContent = "Validando trial, plano e limites do tenant.";
    dom.subscriptionCard.innerHTML = "Validando camada SaaS desta conta.";
    return;
  }

  const access = state.subscriptionAccess;
  const planLabel = access.plan_name || "Sem plano";
  const normalizedStatus = String(access.status || "none").toLowerCase();
  const note = access.has_active_plan
    ? "Seu tenant esta com acesso completo aos modulos liberados por assinatura."
    : access.is_trialing
      ? `Trial em andamento por ${access.trial_days_left} dia(s). Historico segue bloqueado ate ativacao de plano.`
      : "Sem plano ativo no momento. Os modulos pagos permanecem bloqueados.";

  dom.sessionPlan.textContent = planLabel;
  dom.sessionPlanStatus.innerHTML = `<span class="subscription-chip ${escapeHtml(normalizedStatus)}">${escapeHtml(formatSubscriptionStatus(access.status))}</span>`;
  dom.sessionPlanNote.textContent = note;
  dom.subscriptionCard.innerHTML = `
    <div class="stack">
      <div><strong>${escapeHtml(planLabel)}</strong></div>
      <div class="muted">Status atual: ${escapeHtml(formatSubscriptionStatus(access.status))}.</div>
      <div class="muted">Ciclo: ${escapeHtml(access.billing_cycle || "-")}.</div>
      <div class="muted">Trial restante: ${escapeHtml(String(access.trial_days_left || 0))} dia(s).</div>
      <div>${escapeHtml(note)}</div>
    </div>
  `;
}

function renderSidebarPlanAccess() {
  for (const button of dom.navButtons || []) {
    if (button.dataset.planRequired !== "active") continue;
    const isLocked = isLoggedIn() && (isSubscriptionAccessPending() || !hasActivePlan());
    button.classList.toggle("is-locked", isLocked);
    button.setAttribute("aria-disabled", isLocked ? "true" : "false");
    if (isLocked) {
      button.dataset.lockLabel = isSubscriptionAccessPending() ? "Validando" : "Plano";
      button.title = isSubscriptionAccessPending()
        ? "Validando seu acesso por assinatura."
        : "Seu trial nao libera este modulo. Ative um plano para entrar.";
    } else {
      button.removeAttribute("data-lock-label");
      button.removeAttribute("title");
    }
  }
}

function renderPlanGates() {
  if (dom.parametersPlanGate && dom.parametersPanel) {
    dom.parametersPlanGate.hidden = true;
    dom.parametersPanel.hidden = false;
  }

  if (!dom.auditPlanGate || !dom.auditPanel) return;
  if (isSubscriptionAccessPending()) {
    dom.auditPlanGate.hidden = false;
    dom.auditPanel.hidden = true;
    dom.auditPlanGate.innerHTML = "<strong>Validando acesso SaaS</strong><p>Conferindo trial e plano antes de liberar este modulo.</p>";
    return;
  }

  const shouldBlockAudit = isLoggedIn() && viewRequiresActivePlan("audit") && !hasActivePlan();
  dom.auditPlanGate.hidden = !shouldBlockAudit;
  dom.auditPanel.hidden = shouldBlockAudit;
  if (shouldBlockAudit) {
    dom.auditPlanGate.innerHTML = buildPlanGateMarkup("Historico");
  }
}

function renderAdminNav() {
  if (!dom.navAdminSaas) return;
  dom.navAdminSaas.hidden = !isLoggedIn() || !hasSaasAdminSurface();
  if (dom.navAdminSaas.hidden && document.getElementById("view-admin")?.classList.contains("active")) {
    setView("dashboard");
  }
}

function renderAdminMetrics() {
  const metrics = state.adminOverview?.metrics || {};
  if (dom.adminMetricTenants) dom.adminMetricTenants.textContent = formatNumber(metrics.tenants_total || 0);
  if (dom.adminMetricPlans) dom.adminMetricPlans.textContent = formatNumber(metrics.plans_active || 0);
  if (dom.adminMetricSubscriptions) dom.adminMetricSubscriptions.textContent = formatNumber(metrics.subscriptions_active || 0);
  if (dom.adminMetricTrials) dom.adminMetricTrials.textContent = formatNumber(metrics.subscriptions_trialing || 0);
  if (dom.adminMetricCatalog) dom.adminMetricCatalog.textContent = formatNumber(metrics.plans_total || 0);
  if (dom.adminMetricMrr) dom.adminMetricMrr.textContent = formatCurrencyBrl(metrics.estimated_mrr || 0);
}

function buildEditablePlanCard(plan) {
  const activeLabel = plan.is_active ? "Ativo" : "Inativo";
  const activeTone = plan.is_active ? "live" : "off";
  return `
    <div class="admin-plan-card" data-plan-id="${plan.plan_id}">
      <div class="admin-plan-head">
        <div class="admin-plan-title">
          <strong>${escapeHtml(plan.name)}</strong>
          <span>${escapeHtml(plan.code)} • ${escapeHtml(formatCurrencyBrl(plan.monthly_price))}/mes</span>
        </div>
        <span class="pill-inline ${activeTone}">${escapeHtml(activeLabel)}</span>
      </div>
      <div class="admin-form-grid">
        <div class="field"><label>Codigo</label><input data-plan-field="code" type="text" value="${escapeHtml(plan.code)}"></div>
        <div class="field"><label>Nome</label><input data-plan-field="name" type="text" value="${escapeHtml(plan.name)}"></div>
        <div class="field full"><label>Descricao</label><input data-plan-field="description" type="text" value="${escapeHtml(plan.description || "")}"></div>
        <div class="field"><label>Mensal</label><input data-plan-field="monthly_price" type="number" min="0" step="0.01" value="${escapeHtml(String(plan.monthly_price))}"></div>
        <div class="field"><label>Anual</label><input data-plan-field="yearly_price" type="number" min="0" step="0.01" value="${escapeHtml(plan.yearly_price == null ? "" : String(plan.yearly_price))}"></div>
        <div class="field"><label>Max. usuarios</label><input data-plan-field="max_users" type="number" min="1" value="${escapeHtml(plan.max_users == null ? "" : String(plan.max_users))}"></div>
        <div class="field"><label>Max. robos</label><input data-plan-field="max_bots" type="number" min="1" value="${escapeHtml(plan.max_bots == null ? "" : String(plan.max_bots))}"></div>
        <div class="field"><label>Trades/mes</label><input data-plan-field="max_trades_per_month" type="number" min="1" value="${escapeHtml(plan.max_trades_per_month == null ? "" : String(plan.max_trades_per_month))}"></div>
        <div class="field"><label>Tokens IA/dia</label><input data-plan-field="max_ai_tokens_per_day" type="number" min="1" value="${escapeHtml(plan.max_ai_tokens_per_day == null ? "" : String(plan.max_ai_tokens_per_day))}"></div>
        <div class="field"><label>Storage GB</label><input data-plan-field="max_storage_gb" type="number" min="0.1" step="0.1" value="${escapeHtml(plan.max_storage_gb == null ? "" : String(plan.max_storage_gb))}"></div>
        <div class="field"><label>Status</label><select data-plan-field="is_active"><option value="true" ${plan.is_active ? "selected" : ""}>Ativo</option><option value="false" ${!plan.is_active ? "selected" : ""}>Inativo</option></select></div>
      </div>
      <div class="button-row"><button type="button" class="ghost" data-admin-plan-save="${plan.plan_id}">Salvar plano</button></div>
    </div>
  `;
}

function renderAdminPlanCatalog() {
  if (!dom.adminPlanCatalog) return;
  if (!state.adminPlans.length) {
    dom.adminPlanCatalog.innerHTML = '<div class="empty">Nenhum plano encontrado no catalogo.</div>';
    return;
  }
  dom.adminPlanCatalog.innerHTML = state.adminPlans.map(buildEditablePlanCard).join("");
}

function renderAdminSubscriptions() {
  if (!dom.adminSubscriptionsBody || !dom.adminSubscriptionsEmpty || !dom.adminSubscriptionsWrap) return;
  const rows = state.adminOverview?.recent_subscriptions || [];
  dom.adminSubscriptionsBody.innerHTML = "";
  if (!rows.length) {
    dom.adminSubscriptionsEmpty.hidden = false;
    dom.adminSubscriptionsWrap.hidden = true;
    return;
  }

  dom.adminSubscriptionsEmpty.hidden = true;
  dom.adminSubscriptionsWrap.hidden = false;
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.tenant_name)}</td>
      <td>${escapeHtml(row.plan_name)} <span class="muted">(${escapeHtml(row.plan_code)})</span></td>
      <td><span class="subscription-chip ${escapeHtml(String(row.status).toLowerCase())}">${escapeHtml(formatSubscriptionStatus(row.status))}</span></td>
      <td>${escapeHtml(row.billing_cycle || "-")}</td>
      <td>${escapeHtml(formatDate(row.current_period_end))}</td>
      <td>${escapeHtml(formatDate(row.trial_ends_at))}</td>
      <td>${escapeHtml(formatDate(row.created_at))}</td>
    `;
    dom.adminSubscriptionsBody.appendChild(tr);
  }
}

function renderAdminUsers() {
  if (!dom.adminUsersBody || !dom.adminUsersEmpty || !dom.adminUsersWrap) return;
  const rows = state.adminUsers || [];
  dom.adminUsersBody.innerHTML = "";
  if (!rows.length) {
    dom.adminUsersEmpty.hidden = false;
    dom.adminUsersWrap.hidden = true;
    return;
  }

  dom.adminUsersEmpty.hidden = true;
  dom.adminUsersWrap.hidden = false;
  for (const row of rows) {
    const tr = document.createElement("tr");
    const adminBadge = row.is_platform_admin ? '<span class="pill-inline warn">Platform admin</span>' : "";
    tr.innerHTML = `
      <td><div>${escapeHtml(row.email)}</div><div class="muted">ID ${escapeHtml(String(row.user_id))}</div></td>
      <td><div>${escapeHtml(row.tenant_name || "-")}</div><div class="muted">${escapeHtml(row.tenant_id ? `Tenant ${row.tenant_id}` : "Sem tenant")}</div></td>
      <td><div>${escapeHtml(row.plan_name || "-")}</div><div class="muted">${escapeHtml(row.subscription_status ? formatSubscriptionStatus(row.subscription_status) : "Sem assinatura")}</div></td>
      <td><div>${escapeHtml(row.role || "-")}</div>${adminBadge}</td>
      <td>${escapeHtml(formatDate(row.last_session_at))}</td>
      <td>${escapeHtml(formatDate(row.created_at))}</td>
    `;
    dom.adminUsersBody.appendChild(tr);
  }
}

function renderManagedSubscriptionFilterOptions() {
  if (!dom.adminSubscriptionPlanFilter) return;
  const currentValue = dom.adminSubscriptionPlanFilter.value;
  dom.adminSubscriptionPlanFilter.innerHTML = [
    '<option value="">Todos os planos</option>',
    ...state.adminPlans.map((plan) => `<option value="${plan.plan_id}">${escapeHtml(plan.name)} (${escapeHtml(plan.code)})</option>`),
  ].join("");
  dom.adminSubscriptionPlanFilter.value = state.adminPlans.some((plan) => String(plan.plan_id) === currentValue)
    ? currentValue
    : "";
}

function buildManagedSubscriptionPlanOptions(selectedPlanId) {
  return state.adminPlans
    .map(
      (plan) => `<option value="${plan.plan_id}" ${String(plan.plan_id) === String(selectedPlanId) ? "selected" : ""}>${escapeHtml(plan.name)}</option>`,
    )
    .join("");
}

function renderAdminManagedSubscriptions() {
  if (!dom.adminManagedSubscriptionsBody || !dom.adminManagedSubscriptionsEmpty || !dom.adminManagedSubscriptionsWrap) return;
  renderManagedSubscriptionFilterOptions();

  const rows = state.adminManagedSubscriptions || [];
  dom.adminManagedSubscriptionsBody.innerHTML = "";
  if (!rows.length) {
    dom.adminManagedSubscriptionsEmpty.hidden = false;
    dom.adminManagedSubscriptionsWrap.hidden = true;
    return;
  }

  dom.adminManagedSubscriptionsEmpty.hidden = true;
  dom.adminManagedSubscriptionsWrap.hidden = false;
  for (const row of rows) {
    const tr = document.createElement("tr");
    tr.dataset.subscriptionId = String(row.subscription_id);
    tr.innerHTML = `
      <td><div>${escapeHtml(row.tenant_name)}</div><div class="muted">ID ${escapeHtml(String(row.subscription_id))}</div></td>
      <td>
        <select data-subscription-field="plan_id">
          ${buildManagedSubscriptionPlanOptions(row.plan_id)}
        </select>
      </td>
      <td>
        <select data-subscription-field="status">
          <option value="trialing" ${row.status === "trialing" ? "selected" : ""}>Trial</option>
          <option value="active" ${row.status === "active" ? "selected" : ""}>Ativo</option>
          <option value="past_due" ${row.status === "past_due" ? "selected" : ""}>Pendente</option>
          <option value="paused" ${row.status === "paused" ? "selected" : ""}>Pausado</option>
          <option value="canceled" ${row.status === "canceled" ? "selected" : ""}>Cancelado</option>
        </select>
      </td>
      <td>
        <select data-subscription-field="billing_cycle">
          <option value="monthly" ${row.billing_cycle === "monthly" ? "selected" : ""}>Mensal</option>
          <option value="yearly" ${row.billing_cycle === "yearly" ? "selected" : ""}>Anual</option>
        </select>
      </td>
      <td><div>${escapeHtml(String(row.users_total || 0))} usuário(s)</div><div class="muted">${escapeHtml(String(row.active_robots || 0))} robô(s) ativo(s)</div></td>
      <td><div>${escapeHtml(formatDate(row.updated_at || row.created_at))}</div><div class="muted">Fim: ${escapeHtml(formatDate(row.current_period_end))}</div></td>
      <td><button type="button" class="ghost" data-admin-subscription-save="${row.subscription_id}">Salvar</button></td>
    `;
    dom.adminManagedSubscriptionsBody.appendChild(tr);
  }
}

function renderBillingProviderOptions() {
  if (!dom.adminBillingProvider) return;
  const currentValue = dom.adminBillingProvider.value;
  const providers = state.adminBilling?.providers || [];
  dom.adminBillingProvider.innerHTML = [
    '<option value="">Todos</option>',
    ...providers.map((provider) => `<option value="${escapeHtml(provider)}">${escapeHtml(humanizeToken(provider))}</option>`),
  ].join("");
  dom.adminBillingProvider.value = providers.includes(currentValue) ? currentValue : "";
}

function renderPlanHistoryFilterOptions() {
  if (!dom.adminPlanHistoryFilter) return;
  const currentValue = dom.adminPlanHistoryFilter.value;
  dom.adminPlanHistoryFilter.innerHTML = [
    '<option value="">Todos os planos</option>',
    ...state.adminPlans.map((plan) => `<option value="${plan.plan_id}">${escapeHtml(plan.name)} (${escapeHtml(plan.code)})</option>`),
  ].join("");
  dom.adminPlanHistoryFilter.value = state.adminPlans.some((plan) => String(plan.plan_id) === currentValue)
    ? currentValue
    : "";
}

function renderAdminBilling() {
  if (!dom.adminBillingBody || !dom.adminBillingEmpty || !dom.adminBillingWrap) return;
  renderBillingProviderOptions();

  const metrics = state.adminBilling?.metrics || {};
  if (dom.adminBillingMetricEvents) dom.adminBillingMetricEvents.textContent = formatNumber(metrics.total_events || 0);
  if (dom.adminBillingMetricTrials) dom.adminBillingMetricTrials.textContent = formatNumber(metrics.trial_events || 0);
  if (dom.adminBillingMetricSucceeded) dom.adminBillingMetricSucceeded.textContent = formatCurrencyBrl(metrics.successful_charges || 0);
  if (dom.adminBillingMetricNet) dom.adminBillingMetricNet.textContent = formatCurrencyBrl(metrics.net_revenue || 0);
  if (dom.adminBillingMetricFailed) dom.adminBillingMetricFailed.textContent = formatCurrencyBrl(metrics.failed_charges || 0);
  if (dom.adminBillingMetricRefunds) dom.adminBillingMetricRefunds.textContent = formatCurrencyBrl(metrics.refunds || 0);
  if (dom.adminBillingMetricProviders) dom.adminBillingMetricProviders.textContent = formatNumber(metrics.providers_total || 0);

  const rows = state.adminBilling?.events || [];
  dom.adminBillingBody.innerHTML = "";
  if (!rows.length) {
    dom.adminBillingEmpty.hidden = false;
    dom.adminBillingWrap.hidden = true;
    return;
  }

  dom.adminBillingEmpty.hidden = true;
  dom.adminBillingWrap.hidden = false;
  for (const row of rows) {
    const tone = ["charge_succeeded", "subscription_plan_changed"].includes(row.event_type)
      ? "live"
      : ["charge_failed", "refund_issued"].includes(row.event_type)
        ? "off"
        : "warn";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(formatDate(row.created_at))}</td>
      <td><span class="pill-inline ${tone}">${escapeHtml(formatBillingEventType(row.event_type))}</span></td>
      <td>${escapeHtml(row.tenant_name || "-")}</td>
      <td><div>${escapeHtml(row.plan_name || "-")}</div><div class="muted">${escapeHtml(row.plan_code || "-")}</div></td>
      <td>${escapeHtml(formatCurrencyBrl(row.amount || 0))}</td>
      <td><span class="subscription-chip ${escapeHtml(String(row.status || "recorded").toLowerCase())}">${escapeHtml(humanizeToken(row.status || "recorded"))}</span></td>
      <td><div>${escapeHtml(row.provider || "-")}</div><div class="muted">${escapeHtml(row.provider_event_id || row.billing_cycle || "-")}</div></td>
    `;
    dom.adminBillingBody.appendChild(tr);
  }
}

function renderAdminPlanChanges() {
  if (!dom.adminPlanChangesBody || !dom.adminPlanChangesEmpty || !dom.adminPlanChangesWrap) return;
  renderPlanHistoryFilterOptions();

  const rows = state.adminPlanChanges || [];
  if (dom.adminPlanChangesMetricTotal) dom.adminPlanChangesMetricTotal.textContent = formatNumber(rows.length);
  if (dom.adminPlanChangesMetricPrices) dom.adminPlanChangesMetricPrices.textContent = formatNumber(rows.filter((item) => item.change_type === "price_update").length);
  if (dom.adminPlanChangesMetricLimits) dom.adminPlanChangesMetricLimits.textContent = formatNumber(rows.filter((item) => item.change_type === "limit_update").length);
  if (dom.adminPlanChangesMetricMetadata) dom.adminPlanChangesMetricMetadata.textContent = formatNumber(rows.filter((item) => item.change_type === "metadata_update").length);
  if (dom.adminPlanChangesMetricStatus) dom.adminPlanChangesMetricStatus.textContent = formatNumber(rows.filter((item) => item.change_type === "status_change").length);

  dom.adminPlanChangesBody.innerHTML = "";
  if (!rows.length) {
    dom.adminPlanChangesEmpty.hidden = false;
    dom.adminPlanChangesWrap.hidden = true;
    return;
  }

  dom.adminPlanChangesEmpty.hidden = true;
  dom.adminPlanChangesWrap.hidden = false;
  for (const row of rows) {
    const tone = row.change_type === "price_update"
      ? "live"
      : row.change_type === "status_change"
        ? "warn"
        : "off";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(formatDate(row.created_at))}</td>
      <td><div>${escapeHtml(row.plan_name)}</div><div class="muted">${escapeHtml(row.plan_code)}</div></td>
      <td><span class="pill-inline ${tone}">${escapeHtml(formatPlanChangeType(row.change_type))}</span></td>
      <td>${escapeHtml(formatPlanFieldName(row.field_name))}</td>
      <td>${escapeHtml(row.old_value || "-")}</td>
      <td>${escapeHtml(row.new_value || "-")}</td>
      <td>${escapeHtml(row.changed_by_email || "Sistema")}</td>
    `;
    dom.adminPlanChangesBody.appendChild(tr);
  }
}

function renderAdminView() {
  if (!dom.adminAccessGate || !dom.adminBootstrapPanel || !dom.adminPanel || !dom.adminBootstrapMeta) return;

  dom.adminAccessGate.hidden = true;
  dom.adminBootstrapPanel.hidden = true;
  dom.adminPanel.hidden = true;

  if (!isLoggedIn()) {
    dom.adminAccessGate.hidden = false;
    dom.adminAccessGate.innerHTML = buildAdminAccessMarkup();
    return;
  }

  if (state.me?.is_platform_admin) {
    dom.adminPanel.hidden = false;
    renderAdminMetrics();
    renderAdminPlanCatalog();
    renderAdminSubscriptions();
    renderAdminUsers();
    renderAdminManagedSubscriptions();
    renderAdminBilling();
    renderAdminPlanChanges();
    return;
  }

  if (state.adminBootstrapStatus?.can_bootstrap) {
    dom.adminBootstrapPanel.hidden = false;
    dom.adminBootstrapMeta.innerHTML = `<div class="stack"><strong>Bootstrap liberado</strong><div>${escapeHtml(formatBootstrapReason(state.adminBootstrapStatus.reason))}</div><div class="muted">Admins existentes: ${escapeHtml(String(state.adminBootstrapStatus.admin_count || 0))}</div></div>`;
    return;
  }

  dom.adminAccessGate.hidden = false;
  dom.adminAccessGate.innerHTML = buildAdminAccessMarkup();
}

async function loadSubscriptionAccessState() {
  if (!isLoggedIn()) {
    state.subscriptionAccess = null;
    return;
  }
  state.subscriptionAccess = await api("/api/subscription/access");
}

async function loadAdminBootstrapState() {
  if (!isLoggedIn()) {
    state.adminBootstrapStatus = null;
    return;
  }
  state.adminBootstrapStatus = await api("/api/admin/bootstrap-status");
}

function buildAdminBillingQuery() {
  const params = new URLSearchParams();
  params.set("limit", "50");
  if (dom.adminBillingStatus?.value) params.set("status", dom.adminBillingStatus.value);
  if (dom.adminBillingProvider?.value) params.set("provider", dom.adminBillingProvider.value);
  return params.toString();
}

function buildAdminPlanChangesQuery() {
  const params = new URLSearchParams();
  params.set("limit", "50");
  if (dom.adminPlanHistoryFilter?.value) params.set("plan_id", dom.adminPlanHistoryFilter.value);
  return params.toString();
}

function buildAdminUsersQuery() {
  const params = new URLSearchParams();
  params.set("limit", "80");
  if ((dom.adminUsersSearch?.value?.trim() || "").length >= 2) params.set("search", dom.adminUsersSearch.value.trim());
  return params.toString();
}

function buildAdminSubscriptionsQuery() {
  const params = new URLSearchParams();
  params.set("limit", "80");
  if (dom.adminSubscriptionStatusFilter?.value) params.set("status", dom.adminSubscriptionStatusFilter.value);
  if (dom.adminSubscriptionPlanFilter?.value) params.set("plan_id", dom.adminSubscriptionPlanFilter.value);
  return params.toString();
}

async function loadAdminSaasBundle() {
  if (!isLoggedIn() || !state.me?.is_platform_admin) {
    state.adminOverview = null;
    state.adminPlans = [];
    state.adminBilling = null;
    state.adminPlanChanges = [];
    state.adminUsers = [];
    state.adminManagedSubscriptions = [];
    return;
  }

  const [overview, plans, billing, planChanges, users, subscriptions] = await Promise.all([
    api("/api/admin/saas/overview"),
    api("/api/admin/saas/plans"),
    api(`/api/admin/saas/billing?${buildAdminBillingQuery()}`),
    api(`/api/admin/saas/plan-changes?${buildAdminPlanChangesQuery()}`),
    api(`/api/admin/saas/users?${buildAdminUsersQuery()}`),
    api(`/api/admin/saas/subscriptions?${buildAdminSubscriptionsQuery()}`),
  ]);
  state.adminOverview = overview;
  state.adminPlans = plans;
  state.adminBilling = billing;
  state.adminPlanChanges = planChanges.changes || [];
  state.adminUsers = users.users || [];
  state.adminManagedSubscriptions = subscriptions.subscriptions || [];
}

function readNewPlanPayload() {
  return {
    code: dom.adminPlanCode.value.trim(),
    name: dom.adminPlanName.value.trim(),
    description: dom.adminPlanDescription.value.trim(),
    monthly_price: Number(dom.adminPlanMonthly.value),
    yearly_price: parseOptionalFloat(dom.adminPlanYearly.value),
    is_active: dom.adminPlanActive.value === "true",
    max_users: parseOptionalInt(dom.adminPlanUsers.value),
    max_bots: parseOptionalInt(dom.adminPlanBots.value),
    max_trades_per_month: parseOptionalInt(dom.adminPlanTrades.value),
    max_ai_tokens_per_day: parseOptionalInt(dom.adminPlanTokens.value),
    max_storage_gb: parseOptionalFloat(dom.adminPlanStorage.value),
  };
}

function readPlanCardPayload(card) {
  const read = (name) => card.querySelector(`[data-plan-field="${name}"]`);
  return {
    code: read("code").value.trim(),
    name: read("name").value.trim(),
    description: read("description").value.trim(),
    monthly_price: Number(read("monthly_price").value),
    yearly_price: parseOptionalFloat(read("yearly_price").value),
    is_active: read("is_active").value === "true",
    max_users: parseOptionalInt(read("max_users").value),
    max_bots: parseOptionalInt(read("max_bots").value),
    max_trades_per_month: parseOptionalInt(read("max_trades_per_month").value),
    max_ai_tokens_per_day: parseOptionalInt(read("max_ai_tokens_per_day").value),
    max_storage_gb: parseOptionalFloat(read("max_storage_gb").value),
  };
}

function clearNewPlanForm() {
  dom.adminPlanCode.value = "";
  dom.adminPlanName.value = "";
  dom.adminPlanDescription.value = "";
  dom.adminPlanMonthly.value = "";
  dom.adminPlanYearly.value = "";
  dom.adminPlanUsers.value = "";
  dom.adminPlanBots.value = "";
  dom.adminPlanTrades.value = "";
  dom.adminPlanTokens.value = "";
  dom.adminPlanStorage.value = "";
  dom.adminPlanActive.value = "true";
}

async function handleAdminBootstrap() {
  await api("/api/admin/bootstrap-platform-admin", { method: "POST" });
  await loadMe();
  syncSessionUserFromProfile();
  await loadAdminBootstrapState();
  await loadAdminSaasBundle();
  renderSession();
  renderAdminView();
  setStatus("Admin SaaS local ativado para esta conta.", "ok");
}

async function handleCreatePlan() {
  const payload = readNewPlanPayload();
  await api("/api/admin/saas/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  clearNewPlanForm();
  if (dom.adminCreatePlanMeta) {
    dom.adminCreatePlanMeta.textContent = "Plano criado. O catalogo foi recarregado com os novos limites.";
  }
  await loadAdminSaasBundle();
  renderAdminView();
  setStatus(`Plano ${payload.name} criado com sucesso.`, "ok");
}

async function handlePlanCatalogClick(event) {
  const button = event.target.closest("[data-admin-plan-save]");
  if (!button) return;
  const card = button.closest("[data-plan-id]");
  if (!card) return;

  const planId = Number(card.dataset.planId);
  const payload = readPlanCardPayload(card);
  await api(`/api/admin/saas/plans/${planId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  await loadAdminSaasBundle();
  renderAdminView();
  setStatus(`Plano ${payload.name} atualizado com sucesso.`, "ok");
}

function readManagedSubscriptionPayload(row) {
  const read = (name) => row.querySelector(`[data-subscription-field="${name}"]`);
  return {
    plan_id: Number(read("plan_id").value),
    status: read("status").value,
    billing_cycle: read("billing_cycle").value,
  };
}

async function handleManagedSubscriptionClick(event) {
  const button = event.target.closest("[data-admin-subscription-save]");
  if (!button) return;
  const row = button.closest("tr[data-subscription-id]");
  if (!row) return;

  const subscriptionId = Number(row.dataset.subscriptionId);
  const payload = readManagedSubscriptionPayload(row);
  await api(`/api/admin/saas/subscriptions/${subscriptionId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  await Promise.all([loadSubscriptionAccessState(), loadAdminSaasBundle()]);
  renderSubscriptionSurface();
  renderSidebarPlanAccess();
  renderPlanGates();
  renderAdminView();
  setStatus(`Assinatura ${subscriptionId} atualizada com sucesso.`, "ok");
}

async function refreshAdminActivityViews(message = "") {
  await loadAdminSaasBundle();
  renderAdminView();
  if (message) setStatus(message, "ok");
}

const originalSetView = setView;
setView = function setViewWithSaasGuards(viewName) {
  const targetView = String(viewName || "dashboard");
  if (viewRequiresActivePlan(targetView) && isLoggedIn()) {
    if (isSubscriptionAccessPending()) {
      originalSetView("dashboard");
      renderSidebarPlanAccess();
      renderPlanGates();
      setStatus("Validando seu plano antes de liberar este modulo.", "warn");
      return;
    }
    if (!hasActivePlan()) {
      originalSetView("dashboard");
      renderSidebarPlanAccess();
      renderPlanGates();
      setStatus(`Seu trial ainda nao libera ${SAAS_REQUIRED_ACTIVE_PLAN_VIEWS.get(targetView)}. Ative um plano para abrir este modulo.`, "warn");
      return;
    }
  }
  if (targetView === "admin" && !hasSaasAdminSurface()) {
    originalSetView("dashboard");
    setStatus("Acesso restrito ao admin SaaS.", "warn");
    return;
  }
  originalSetView(targetView);
};

const originalClearSession = clearSession;
clearSession = function clearSessionWithSaasReset() {
  originalClearSession();
  state.subscriptionAccess = null;
  state.adminBootstrapStatus = null;
  state.adminOverview = null;
  state.adminPlans = [];
  state.adminBilling = null;
  state.adminPlanChanges = [];
  state.adminUsers = [];
  state.adminManagedSubscriptions = [];
  renderSubscriptionSurface();
  renderPlanGates();
  renderSidebarPlanAccess();
  renderAdminNav();
  renderAdminView();
};

const originalRenderSession = renderSession;
renderSession = function renderSessionWithSaas() {
  originalRenderSession();
  renderSubscriptionSurface();
  renderSidebarPlanAccess();
  renderAdminNav();
  renderAdminView();
};

const originalRenderDashboard = renderDashboard;
renderDashboard = function renderDashboardWithSaas() {
  originalRenderDashboard();
  renderSubscriptionSurface();
};

const originalRenderParameters = renderParameters;
renderParameters = function renderParametersWithSaas() {
  originalRenderParameters();
  renderPlanGates();
};

const originalRenderAudit = renderAudit;
renderAudit = function renderAuditWithSaas() {
  originalRenderAudit();
  renderPlanGates();
};

const originalRefreshDashboardBundle = refreshDashboardBundle;
refreshDashboardBundle = async function refreshDashboardBundleWithSaas(options = {}) {
  await originalRefreshDashboardBundle(options);
  syncSessionUserFromProfile();
  if (isLoggedIn()) {
    await Promise.all([loadSubscriptionAccessState(), loadAdminBootstrapState()]);
    await loadAdminSaasBundle();
  } else {
    state.subscriptionAccess = null;
    state.adminBootstrapStatus = null;
    state.adminOverview = null;
    state.adminPlans = [];
    state.adminBilling = null;
    state.adminPlanChanges = [];
    state.adminUsers = [];
    state.adminManagedSubscriptions = [];
  }
  renderSubscriptionSurface();
  renderPlanGates();
  renderSidebarPlanAccess();
  renderAdminNav();
  renderAdminView();
};

function bindSaasAdminEvents() {
  if (dom.adminBootstrapBtn) {
    dom.adminBootstrapBtn.addEventListener("click", () => runGuarded(handleAdminBootstrap));
  }
  if (dom.adminCreatePlanBtn) {
    dom.adminCreatePlanBtn.addEventListener("click", () => runGuarded(handleCreatePlan));
  }
  if (dom.adminPlanCatalog) {
    dom.adminPlanCatalog.addEventListener("click", (event) => runGuarded(() => handlePlanCatalogClick(event)));
  }
  if (dom.adminRefreshUsersBtn) {
    dom.adminRefreshUsersBtn.addEventListener("click", () => runGuarded(() => refreshAdminActivityViews("Usuários recarregados.")));
  }
  if (dom.adminUsersSearch) {
    dom.adminUsersSearch.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void runGuarded(() => refreshAdminActivityViews("Usuários recarregados."));
      }
    });
  }
  if (dom.adminRefreshManagedSubscriptionsBtn) {
    dom.adminRefreshManagedSubscriptionsBtn.addEventListener("click", () => runGuarded(() => refreshAdminActivityViews("Assinaturas recarregadas.")));
  }
  if (dom.adminSubscriptionStatusFilter) {
    dom.adminSubscriptionStatusFilter.addEventListener("change", () => runGuarded(() => refreshAdminActivityViews()));
  }
  if (dom.adminSubscriptionPlanFilter) {
    dom.adminSubscriptionPlanFilter.addEventListener("change", () => runGuarded(() => refreshAdminActivityViews()));
  }
  if (dom.adminManagedSubscriptionsBody) {
    dom.adminManagedSubscriptionsBody.addEventListener("click", (event) => runGuarded(() => handleManagedSubscriptionClick(event)));
  }
  if (dom.adminRefreshBillingBtn) {
    dom.adminRefreshBillingBtn.addEventListener("click", () => runGuarded(() => refreshAdminActivityViews("Faturamento recarregado.")));
  }
  if (dom.adminBillingStatus) {
    dom.adminBillingStatus.addEventListener("change", () => runGuarded(() => refreshAdminActivityViews()));
  }
  if (dom.adminBillingProvider) {
    dom.adminBillingProvider.addEventListener("change", () => runGuarded(() => refreshAdminActivityViews()));
  }
  if (dom.adminRefreshPlanChangesBtn) {
    dom.adminRefreshPlanChangesBtn.addEventListener("click", () => runGuarded(() => refreshAdminActivityViews("Historico de planos recarregado.")));
  }
  if (dom.adminPlanHistoryFilter) {
    dom.adminPlanHistoryFilter.addEventListener("change", () => runGuarded(() => refreshAdminActivityViews()));
  }
}

bindSaasAdminEvents();
renderSubscriptionSurface();
renderPlanGates();
renderSidebarPlanAccess();
renderAdminNav();
renderAdminView();

if (isLoggedIn()) {
  void runGuarded(async () => {
    await Promise.all([loadSubscriptionAccessState(), loadAdminBootstrapState()]);
    await loadAdminSaasBundle();
    renderSubscriptionSurface();
    renderPlanGates();
    renderSidebarPlanAccess();
    renderAdminNav();
    renderAdminView();
  });
}
