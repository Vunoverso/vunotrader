"use client";

import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useCallback, useTransition } from "react";

export function UsuariosFilters({
  initialQ,
  initialPlano,
  total,
}: {
  initialQ: string;
  initialPlano: string;
  total: number;
}) {
  const router     = useRouter();
  const pathname   = usePathname();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) params.set(key, value);
      else params.delete(key);
      params.delete("pagina"); // reset pagination on filter change
      startTransition(() => {
        router.push(`${pathname}?${params.toString()}`);
      });
    },
    [router, pathname, searchParams],
  );

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      {/* Search */}
      <div className="relative flex-1">
        <div className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-slate-500">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="search"
          defaultValue={initialQ}
          placeholder="Buscar por nome ou e-mail..."
          onChange={(e) => updateParam("q", e.target.value)}
          className={`w-full rounded-lg border border-slate-700 bg-slate-800 py-2.5 pl-9 pr-4 text-sm text-slate-200 placeholder:text-slate-500 outline-none transition-colors focus:border-violet-500 focus:ring-1 focus:ring-violet-500/50 ${isPending ? "opacity-60" : ""}`}
        />
        {isPending && (
          <div className="absolute inset-y-0 right-3 flex items-center">
            <svg className="h-4 w-4 animate-spin text-violet-400" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path strokeLinecap="round" d="M12 2a10 10 0 1 0 10 10" strokeWidth={2} />
            </svg>
          </div>
        )}
      </div>

      {/* Plan filter */}
      <select
        defaultValue={initialPlano}
        onChange={(e) => updateParam("plano", e.target.value)}
        className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none transition-colors focus:border-violet-500 sm:w-44"
      >
        <option value="">Todos os planos</option>
        <option value="Starter">Starter</option>
        <option value="Pro">Pro</option>
        <option value="Scale">Scale</option>
      </select>

      <p className="text-xs text-slate-500 sm:ml-2 whitespace-nowrap">{total} resultado{total !== 1 ? "s" : ""}</p>
    </div>
  );
}
