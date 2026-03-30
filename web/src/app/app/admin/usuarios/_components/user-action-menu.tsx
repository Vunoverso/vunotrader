"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { createPortal } from "react-dom";

type ActionFn = (formData: FormData) => Promise<void>;

type OrgRole = "owner" | "admin" | "analyst" | "viewer";
type BillingCycle = "monthly" | "yearly";

type ConfirmState = "admin" | "unadmin" | "ban" | "unban" | "delete" | "plan" | "org" | null;

export function UserActionMenu({
  profileId,
  authUserId,
  userName,
  organizationId,
  currentRole,
  currentPlan,
  currentBillingCycle,
  isAdmin,
  isBanned,
  toggleAdminAction,
  banUserAction,
  deleteUserAction,
  changePlanAction,
  changeBillingCycleAction,
  createOrganizationForUserAction,
  updateMemberRoleAction,
  removeUserFromOrganizationAction,
}: {
  profileId?: string;
  authUserId: string;
  userName: string;
  organizationId: string | null;
  currentRole: OrgRole | null;
  currentPlan: string;
  currentBillingCycle: BillingCycle;
  isAdmin: boolean;
  isBanned: boolean;
  toggleAdminAction: ActionFn;
  banUserAction: ActionFn;
  deleteUserAction: ActionFn;
  changePlanAction: ActionFn;
  changeBillingCycleAction: ActionFn;
  createOrganizationForUserAction: ActionFn;
  updateMemberRoleAction: ActionFn;
  removeUserFromOrganizationAction: ActionFn;
}) {
  const [open, setOpen]       = useState(false);
  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [selectedCycle, setSelectedCycle] = useState<BillingCycle>(currentBillingCycle);
  const [confirmRemoveOrg, setConfirmRemoveOrg] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const MENU_WIDTH = 208; // w-52

  useEffect(() => {
    setSelectedCycle(currentBillingCycle);
  }, [currentBillingCycle]);

  useEffect(() => {
    if (!open) return;

    const updateMenuPosition = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const viewportPadding = 8;
      const gap = 6;
      const bottomLimit = window.innerHeight - viewportPadding;
      const menuHeight = menuRef.current?.offsetHeight ?? 360;
      const openBelowTop = rect.bottom + gap;
      const openAboveTop = rect.top - gap - menuHeight;
      const nextTop = openBelowTop + menuHeight <= bottomLimit
        ? openBelowTop
        : Math.max(viewportPadding, openAboveTop);
      const nextLeft = Math.max(
        viewportPadding,
        Math.min(rect.right - MENU_WIDTH, window.innerWidth - MENU_WIDTH - viewportPadding)
      );

      setMenuPos({ top: nextTop, left: nextLeft });
    };

    updateMenuPosition();
    window.addEventListener("resize", updateMenuPosition);
    window.addEventListener("scroll", updateMenuPosition, true);

    return () => {
      window.removeEventListener("resize", updateMenuPosition);
      window.removeEventListener("scroll", updateMenuPosition, true);
    };
  }, [open]);

  const close = () => {
    setOpen(false);
    setConfirm(null);
    setConfirmRemoveOrg(false);
  };

  const run = (action: ActionFn, extra: Record<string, string>) => {
    const fd = new FormData();
    fd.set("auth_user_id", authUserId);
    for (const [k, v] of Object.entries(extra)) fd.set(k, v);
    close();
    startTransition(() => action(fd));
  };

  const confirmLabels: Record<Exclude<NonNullable<ConfirmState>, "plan" | "org">, { label: string; danger: boolean }> = {
    admin:   { label: `Tornar "${userName}" administrador?`, danger: false },
    unadmin: { label: `Remover admin de "${userName}"?`,     danger: false },
    ban:     { label: `Bloquear conta de "${userName}"?`,   danger: true  },
    unban:   { label: `Desbloquear "${userName}"?`,         danger: false },
    delete:  { label: `Excluir permanentemente "${userName}"? Esta ação não pode ser desfeita.`, danger: true },
  };

  if (!authUserId) return null;

  const menuContent = (
    <>
      <div className="fixed inset-0 z-40" onClick={close} />

      <div
        ref={menuRef}
        className="fixed z-50 mt-1 w-52 overflow-y-auto rounded-lg border border-slate-700 bg-slate-800 shadow-xl shadow-black/40"
        style={{ top: menuPos.top, left: menuPos.left, maxHeight: "calc(100vh - 16px)" }}
      >
        {!confirm ? (
          <>
            <div className="border-b border-slate-700 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                {userName}
              </p>
            </div>

            {/* Toggle admin */}
            <button
              onClick={() => setConfirm(isAdmin ? "unadmin" : "admin")}
              className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-slate-300 hover:bg-slate-700 transition-colors"
            >
              <svg className="h-3.5 w-3.5 text-violet-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              {isAdmin ? "Remover admin" : "Tornar Admin"}
            </button>

            {/* Toggle ban */}
            <button
              onClick={() => setConfirm(isBanned ? "unban" : "ban")}
              className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-amber-400 hover:bg-slate-700 transition-colors"
            >
              <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
              {isBanned ? "Desbloquear conta" : "Bloquear conta"}
            </button>

            {organizationId ? (
              <>
                {/* Plano */}
                <button
                  onClick={() => setConfirm("plan")}
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-sky-300 hover:bg-slate-700 transition-colors"
                >
                  <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4zm0 0V3m0 18v-5m9-4h-5M8 12H3" />
                  </svg>
                  Trocar plano
                </button>

                <button
                  onClick={() => setConfirm("org")}
                  disabled={!profileId}
                  className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-teal-300 hover:bg-slate-700 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Gerenciar vínculo
                </button>
              </>
            ) : (
              <div className="px-3 pb-2 space-y-2">
                <p className="text-[11px] text-slate-500">Para liberar plano/vínculo, crie a organização primeiro.</p>
                <p className="text-[11px] text-slate-500">Sem organização vinculada</p>
                <button
                  onClick={() => {
                    if (!profileId) return;
                    run(createOrganizationForUserAction, {
                      profile_id: profileId,
                      org_name: `Org ${userName}`,
                    });
                  }}
                  disabled={!profileId}
                  className="w-full rounded border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-1.5 text-left text-[11px] font-medium text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                >
                  Criar organização e vincular
                </button>
              </div>
            )}

            <div className="my-1 border-t border-slate-700" />

            {/* Delete */}
            <button
              onClick={() => setConfirm("delete")}
              className="flex w-full items-center gap-2.5 px-3 py-2.5 text-left text-xs text-red-400 hover:bg-slate-700 transition-colors"
            >
              <svg className="h-3.5 w-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Excluir conta
            </button>
          </>
        ) : confirm === "plan" ? (
          <div className="px-3 py-3 space-y-3">
            <p className="text-xs leading-snug text-slate-300">
              Plano atual: <span className="font-semibold text-slate-100">{currentPlan}</span>
            </p>
            <div className="rounded-md border border-slate-700 p-1 grid grid-cols-2 gap-1">
              <button
                onClick={() => setSelectedCycle("monthly")}
                className={`rounded px-2 py-1 text-[11px] ${selectedCycle === "monthly" ? "bg-slate-600 text-slate-100" : "text-slate-400 hover:bg-slate-700"}`}
              >
                Mensal
              </button>
              <button
                onClick={() => setSelectedCycle("yearly")}
                className={`rounded px-2 py-1 text-[11px] ${selectedCycle === "yearly" ? "bg-slate-600 text-slate-100" : "text-slate-400 hover:bg-slate-700"}`}
              >
                Anual
              </button>
            </div>

            <button
              onClick={() => organizationId && run(changeBillingCycleAction, { organization_id: organizationId, billing_cycle: selectedCycle })}
              disabled={!organizationId}
              className="w-full rounded border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-left text-xs font-medium text-cyan-200 hover:bg-cyan-500/20 disabled:opacity-50"
            >
              Aplicar ciclo {selectedCycle === "monthly" ? "mensal" : "anual"} ao plano atual
            </button>

            <div className="grid grid-cols-1 gap-2">
              <button
                onClick={() => organizationId && run(changePlanAction, { organization_id: organizationId, plan_code: "starter", billing_cycle: selectedCycle })}
                disabled={!organizationId}
                className="rounded border border-slate-600 bg-slate-700 px-3 py-1.5 text-left text-xs font-medium text-slate-200 hover:bg-slate-600 disabled:opacity-50"
              >
                Starter ({selectedCycle === "monthly" ? "mensal" : "anual"})
              </button>
              <button
                onClick={() => organizationId && run(changePlanAction, { organization_id: organizationId, plan_code: "pro", billing_cycle: selectedCycle })}
                disabled={!organizationId}
                className="rounded border border-sky-500/40 bg-sky-500/15 px-3 py-1.5 text-left text-xs font-medium text-sky-200 hover:bg-sky-500/25 disabled:opacity-50"
              >
                Pro ({selectedCycle === "monthly" ? "mensal" : "anual"})
              </button>
              <button
                onClick={() => organizationId && run(changePlanAction, { organization_id: organizationId, plan_code: "scale", billing_cycle: selectedCycle })}
                disabled={!organizationId}
                className="rounded border border-violet-500/40 bg-violet-500/15 px-3 py-1.5 text-left text-xs font-medium text-violet-200 hover:bg-violet-500/25 disabled:opacity-50"
              >
                Scale ({selectedCycle === "monthly" ? "mensal" : "anual"})
              </button>
            </div>
            <button
              onClick={() => setConfirm(null)}
              className="rounded px-1 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Voltar
            </button>
          </div>
        ) : confirm === "org" ? (
          <div className="px-3 py-3 space-y-3">
            <p className="text-xs leading-snug text-slate-300">
              Papel atual: <span className="font-semibold text-slate-100">{currentRole ?? "sem papel"}</span>
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(["owner", "admin", "analyst", "viewer"] as OrgRole[]).map((role) => (
                <button
                  key={role}
                  onClick={() => organizationId && profileId && run(updateMemberRoleAction, { organization_id: organizationId, profile_id: profileId, role })}
                  disabled={!organizationId || !profileId}
                  className={`rounded border px-2 py-1.5 text-[11px] font-medium ${currentRole === role ? "border-teal-400/50 bg-teal-500/20 text-teal-200" : "border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"} disabled:opacity-50`}
                >
                  {role}
                </button>
              ))}
            </div>

            {!confirmRemoveOrg ? (
              <button
                onClick={() => setConfirmRemoveOrg(true)}
                disabled={!organizationId || !profileId}
                className="w-full rounded border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-left text-xs font-medium text-red-300 hover:bg-red-500/20 disabled:opacity-50"
              >
                Remover usuário da organização
              </button>
            ) : (
              <div className="space-y-2 rounded border border-red-500/30 bg-red-500/10 p-2">
                <p className="text-[11px] leading-snug text-red-200">
                  Confirma remover <span className="font-semibold">{userName}</span> desta organização?
                </p>
                <div className="flex gap-2">
                  <button
                    onClick={() => organizationId && profileId && run(removeUserFromOrganizationAction, { organization_id: organizationId, profile_id: profileId })}
                    disabled={!organizationId || !profileId}
                    className="rounded bg-red-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Confirmar remoção
                  </button>
                  <button
                    onClick={() => setConfirmRemoveOrg(false)}
                    className="rounded px-2.5 py-1 text-[11px] text-slate-300 hover:text-white"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            <p className="text-[11px] text-slate-500">
              Remove o vínculo do usuário com esta organização (tenant), revogando acesso aos dados da org.
            </p>

            <button
              onClick={() => {
                setConfirm(null);
                setConfirmRemoveOrg(false);
              }}
              className="rounded px-1 py-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
            >
              Voltar
            </button>
          </div>
        ) : confirm === "delete" ? (
          <div className="px-3 py-3 space-y-3">
            <div className="space-y-2 rounded border border-red-500/30 bg-red-500/10 p-2">
              <p className="text-[11px] leading-snug text-red-200">
                Confirma excluir permanentemente <span className="font-semibold">{userName}</span>? Esta ação não pode ser desfeita.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => run(deleteUserAction, {})}
                  className="rounded bg-red-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-red-700"
                >
                  Confirmar exclusão
                </button>
                <button
                  onClick={() => setConfirm(null)}
                  className="rounded px-2.5 py-1 text-[11px] text-slate-300 hover:text-white"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Confirmação */
          <div className="px-3 py-3 space-y-3">
            <p className="text-xs leading-snug text-slate-300">
              {confirmLabels[confirm as Exclude<NonNullable<ConfirmState>, "plan" | "org">].label}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  if (confirm === "admin")   run(toggleAdminAction, { make_admin: "true" });
                  if (confirm === "unadmin") run(toggleAdminAction, { make_admin: "false" });
                  if (confirm === "ban")     run(banUserAction, { ban: "true" });
                  if (confirm === "unban")   run(banUserAction, { ban: "false" });
                }}
                className={`rounded px-3 py-1.5 text-xs font-semibold text-white transition-colors ${
                  confirmLabels[confirm as Exclude<NonNullable<ConfirmState>, "plan" | "org">].danger
                    ? "bg-red-600 hover:bg-red-700"
                    : "bg-violet-600 hover:bg-violet-700"
                }`}
              >
                Confirmar
              </button>
              <button
                onClick={() => setConfirm(null)}
                className="rounded px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );

  return (
    <div className="relative inline-block">
      {/* Trigger */}
      <button
        ref={triggerRef}
        onClick={() => setOpen((v) => !v)}
        disabled={isPending}
        title="Ações do usuário"
        className="flex h-7 w-7 items-center justify-center rounded text-slate-500 hover:bg-slate-700 hover:text-slate-200 transition-colors disabled:opacity-40"
      >
        {isPending ? (
          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" d="M12 2a10 10 0 1 0 10 10" strokeWidth={2} />
          </svg>
        ) : (
          <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
            <circle cx="10" cy="10" r="1.5"/>
            <circle cx="10" cy="4"  r="1.5"/>
            <circle cx="10" cy="16" r="1.5"/>
          </svg>
        )}
      </button>

      {open && createPortal(menuContent, document.body)}
    </div>
  );
}
