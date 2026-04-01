"use client";

import React, { useState } from "react";
import AppSidebar from "./app-sidebar";

interface DashboardShellProps {
  children: React.ReactNode;
  isAdmin: boolean;
  hasActivePlan: boolean;
  userEmail?: string;
  motorOnline: boolean;
  motorLabel: string;
  subscriptionAccess: {
    hasActivePlan: boolean;
    isTrialing: boolean;
    trialDaysLeft: number;
  };
}

export default function DashboardShell({
  children,
  isAdmin,
  hasActivePlan,
  userEmail,
  motorOnline,
  motorLabel,
  subscriptionAccess,
}: DashboardShellProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      {/* Sidebar (Responsiva) */}
      <AppSidebar
        isAdmin={isAdmin}
        hasActivePlan={hasActivePlan}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      {/* Conteúdo principal */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900 px-4 md:px-6 shrink-0">
          <div className="flex items-center gap-3">
            {/* Botão Hambúrguer (Mobile) */}
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 md:hidden"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="h-6 w-6"
              >
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            <div className="hidden text-xs text-slate-400 sm:block">
              {subscriptionAccess.hasActivePlan ? (
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-emerald-300">
                  Plano ativo
                </span>
              ) : subscriptionAccess.isTrialing ? (
                <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-amber-300">
                  Trial: {subscriptionAccess.trialDaysLeft} dia(s)
                </span>
              ) : (
                <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-1 text-slate-400">
                  Sem plano ativo
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Status do motor */}
            <div
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] md:text-xs ${
                motorOnline
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-slate-700 bg-slate-800 text-slate-400"
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  motorOnline ? "bg-emerald-400 animate-pulse" : "bg-slate-600"
                }`}
              />
              <span className="hidden xs:inline">{motorLabel}</span>
              {!motorOnline && <span className="xs:hidden">Off</span>}
              {motorOnline && <span className="xs:hidden">On</span>}
            </div>
            {/* Avatar / email */}
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-600/20 text-sky-400 text-xs font-bold select-none shrink-0">
              {userEmail?.[0]?.toUpperCase() ?? "U"}
            </div>
          </div>
        </header>

        {/* Área de scroll */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-950">
          {children}
        </main>
      </div>
    </div>
  );
}
