"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Componente invisível que força um refresh dos dados a cada 5 minutos
 * para manter o servidor Render acordado (evitar hibernação).
 */
export function DashboardRefresher() {
  const router = useRouter();

  useEffect(() => {
    // Refresh a cada 5 minutos (300.000 ms)
    const interval = setInterval(() => {
      console.log("[Vuno] Refreshing dashboard to keep-alive...");
      router.refresh();
    }, 300000);

    return () => clearInterval(interval);
  }, [router]);

  return null;
}
