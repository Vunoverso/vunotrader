import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";
import Mt5ConnectionChecker from "@/components/app/mt5-connection-checker";
import Mt5CredentialsGenerator from "@/components/app/mt5-credentials-generator";
import Mt5RobotInstancesPanel from "@/components/app/mt5-robot-instances-panel";
import RobotInstallationLanes from "@/components/app/robot-installation-lanes";

const steps = [
  {
    description:
      "Nesta página, crie uma instância nova e baixe o zip pronto. Ele já sai com token, bridge local e os arquivos do conector MT5.",
    import InstallationOverview from "@/components/app/installation-overview";
  },
  {
    title: "2) Iniciar o agent-local",
    description:
          <div>
            <h1 className="text-2xl font-bold text-slate-100">Instalação e Conexão com MetaTrader 5</h1>
            <p className="mt-2 text-sm text-slate-400">
              Guia oficial para baixar o pacote da instância e conectar sua conta MT5 sem configurar URL manual.
            </p>
          </div>
          <span className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold text-sky-300">
        <div className="mx-auto max-w-6xl space-y-6">
          <InstallationOverview access={access} />

          <section id="gerar-pacote">
            <Mt5CredentialsGenerator access={access} />
          </section>

          <section id="instancias">
            <Mt5RobotInstancesPanel />
          </section>

            Sempre inicie em modo demo. Promova para real apenas após validação de risco e consistência.
          </div>
        </div>

  "agent-local iniciado em segundo plano",
