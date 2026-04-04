import InstallationOverview from "@/components/app/installation-overview";
import Mt5ConnectionChecker from "@/components/app/mt5-connection-checker";
import Mt5CredentialsGenerator from "@/components/app/mt5-credentials-generator";
import Mt5RobotInstancesPanel from "@/components/app/mt5-robot-instances-panel";
import RobotInstallationLanes from "@/components/app/robot-installation-lanes";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionAccess } from "@/lib/subscription-access";

export default async function InstalacaoPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const access = user ? await getSubscriptionAccess(supabase, user.id) : null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <InstallationOverview access={access} />

      <section id="gerar-pacote">
        <Mt5CredentialsGenerator access={access} />
      </section>

      <section id="instancias">
        <Mt5RobotInstancesPanel />
      </section>

      {user ? <Mt5ConnectionChecker userId={user.id} /> : null}

      <RobotInstallationLanes access={access} />
    </div>
  );
}
