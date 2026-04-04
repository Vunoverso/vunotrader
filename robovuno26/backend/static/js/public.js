const dom = {
  publicNav: document.getElementById("publicNav"),
  opsLink: document.getElementById("opsLink"),
  sessionCard: document.getElementById("sessionCard"),
  sessionGreeting: document.getElementById("sessionGreeting"),
  sessionMeta: document.getElementById("sessionMeta"),
  heroPrimaryAction: document.getElementById("heroPrimaryAction"),
  plansGrid: document.getElementById("plansGrid"),
  authTitle: document.getElementById("authTitle"),
  authCopy: document.getElementById("authCopy"),
  loginCard: document.getElementById("loginCard"),
  registerCard: document.getElementById("registerCard"),
  loginEmail: document.getElementById("loginEmail"),
  loginPassword: document.getElementById("loginPassword"),
  registerEmail: document.getElementById("registerEmail"),
  registerPassword: document.getElementById("registerPassword"),
  registerTenant: document.getElementById("registerTenant"),
  loginBtn: document.getElementById("loginBtn"),
  registerBtn: document.getElementById("registerBtn"),
  authStatus: document.getElementById("authStatus"),
};

const PAGE_INTENT = {
  "/": "home",
  "/login": "login",
  "/cadastro": "cadastro",
  "/planos": "planos",
  "/trial": "trial",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatCurrencyBrl(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value || 0));
}

function humanizeToken(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (match) => match.toUpperCase());
}

function setStatus(message, tone = "") {
  if (!dom.authStatus) return;
  dom.authStatus.className = "status";
  if (tone) dom.authStatus.classList.add(tone);
  dom.authStatus.textContent = message;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    credentials: "include",
    body: options.body,
  });
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const payload = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === "object" && payload ? payload.detail : payload;
    throw new Error(detail || `Falha ${response.status}`);
  }
  return payload;
}

function highlightIntent(intent) {
  for (const link of dom.publicNav?.querySelectorAll("[data-nav]") || []) {
    link.classList.toggle("is-active", link.dataset.nav === intent);
  }
}

function syncSurfaceForIntent(intent) {
  highlightIntent(intent);
  if (intent === "login") {
    dom.authTitle.textContent = "Login para abrir a área de Ops";
    dom.authCopy.textContent = "Use sua conta existente para seguir direto para /ops. A sessão é mantida por cookie do backend.";
    dom.heroPrimaryAction.textContent = "Entrar agora";
    document.getElementById("auth")?.scrollIntoView({ behavior: "smooth", block: "start" });
    dom.loginEmail.focus({ preventScroll: true });
    return;
  }
  if (intent === "cadastro") {
    dom.authTitle.textContent = "Cadastro com trial provisionado";
    dom.authCopy.textContent = "Criamos tenant, perfil padrão e assinatura trial. Na sequência, você já entra em /ops.";
    dom.heroPrimaryAction.textContent = "Criar conta";
    document.getElementById("auth")?.scrollIntoView({ behavior: "smooth", block: "start" });
    dom.registerEmail.focus({ preventScroll: true });
    return;
  }
  if (intent === "planos") {
    document.getElementById("planos")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  if (intent === "trial") {
    document.getElementById("trial")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
}

function renderPlans(plans) {
  if (!dom.plansGrid) return;
  if (!plans.length) {
    dom.plansGrid.innerHTML = `
      <article class="plan-card panel">
        <span class="badge">Catálogo vazio</span>
        <h3>Nenhum plano ativo</h3>
        <div class="plan-meta">O catálogo admin ainda não expôs planos ativos para a superfície pública.</div>
      </article>
    `;
    return;
  }

  const cheapestCode = plans[0]?.code;
  dom.plansGrid.innerHTML = plans
    .map((plan) => {
      const featured = plan.code === cheapestCode ? " is-featured" : "";
      const yearly = plan.yearly_price ? `<div class="muted">Anual: ${escapeHtml(formatCurrencyBrl(plan.yearly_price))}</div>` : "";
      const bullets = [
        "Provisionamento imediato do tenant",
        plan.code === "starter" ? "Entrada rápida para validar setup e heartbeat" : "Mais capacidade para robôs, equipe e operação contínua",
        "Área interna em /ops com auditoria e gestão",
      ];
      return `
        <article class="plan-card panel${featured}">
          <span class="badge">${escapeHtml(humanizeToken(plan.code))}</span>
          <div>
            <h3>${escapeHtml(plan.name)}</h3>
            <div class="plan-meta">${escapeHtml(plan.description || "Plano comercial conectado ao backend operacional do Vuno.")}</div>
          </div>
          <div class="plan-price">
            <strong>${escapeHtml(formatCurrencyBrl(plan.monthly_price))}</strong>
            <span class="muted">por mês</span>
          </div>
          ${yearly}
          <ul class="plan-list">
            ${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
          <a class="cta ghost" href="#auth">Começar com ${escapeHtml(plan.name)}</a>
        </article>
      `;
    })
    .join("");
}

async function loadPlans() {
  const plans = await api("/api/subscription/plans");
  renderPlans(plans);
}

async function loadSession() {
  try {
    const me = await api("/api/auth/me");
    dom.sessionCard.hidden = false;
    dom.sessionGreeting.textContent = `Sessão ativa para ${me.email}`;
    dom.sessionMeta.textContent = `Tenant ${me.tenant_name}. Você já pode seguir para a área interna em /ops.`;
    dom.opsLink.textContent = "Abrir Ops";
    setStatus("Sessão ativa encontrada. Você pode seguir direto para a área interna.", "ok");
    return me;
  } catch {
    dom.sessionCard.hidden = true;
    return null;
  }
}

async function handleLogin() {
  const email = dom.loginEmail.value.trim();
  const password = dom.loginPassword.value;
  if (!email || !password) {
    setStatus("Preencha email e senha para entrar.", "warn");
    return;
  }
  setStatus("Validando suas credenciais...");
  await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setStatus("Login concluído. Abrindo a área de Ops...", "ok");
  window.location.href = "/ops";
}

async function handleRegister() {
  const email = dom.registerEmail.value.trim();
  const password = dom.registerPassword.value;
  const tenantName = dom.registerTenant.value.trim();
  if (!email || !password) {
    setStatus("Informe email e senha para criar a conta.", "warn");
    return;
  }
  setStatus("Criando tenant e assinatura trial...");
  await api("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, tenant_name: tenantName || null }),
  });
  await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setStatus("Conta criada com trial ativo. Abrindo a área de Ops...", "ok");
  window.location.href = "/ops";
}

function bindEvents() {
  dom.loginBtn?.addEventListener("click", () => {
    void handleLogin().catch((error) => setStatus(error.message || "Falha no login.", "error"));
  });
  dom.registerBtn?.addEventListener("click", () => {
    void handleRegister().catch((error) => setStatus(error.message || "Falha no cadastro.", "error"));
  });
  dom.loginPassword?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      dom.loginBtn.click();
    }
  });
  dom.registerTenant?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      dom.registerBtn.click();
    }
  });
}

async function bootstrap() {
  bindEvents();
  await Promise.all([loadPlans(), loadSession()]);
  const intent = PAGE_INTENT[window.location.pathname] || "home";
  syncSurfaceForIntent(intent);
}

void bootstrap().catch((error) => {
  setStatus(error.message || "Nao foi possivel carregar a superficie publica.", "error");
});