"use client";

import { useEffect } from "react";

const KEEP_ALIVE_URL = process.env.NEXT_PUBLIC_KEEP_ALIVE_URL || "https://vunotrader-api.onrender.com/";

/**
 * Componente invisível que faz um ping silencioso no backend a cada 5 minutos
 * para manter o Render acordado, sem refrescar a UI do dashboard.
 */
export function DashboardRefresher() {
  useEffect(() => {
    let cancelled = false;

    async function pingBackend() {
      if (cancelled) return;
      try {
        await fetch(KEEP_ALIVE_URL, {
          method: "GET",
          mode: "no-cors",
          cache: "no-store",
        });
      } catch {
        // best effort only
      }
    }

    void pingBackend();

    const interval = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") {
        return;
      }
      void pingBackend();
    }, 300000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return null;
}
