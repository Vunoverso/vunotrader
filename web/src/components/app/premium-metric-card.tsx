"use client";

import { ReactNode } from "react";

interface PremiumMetricCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  trend?: "up" | "down" | "neutral";
  accent?: "emerald" | "rose" | "sky" | "amber" | "slate";
  icon?: ReactNode;
  tooltip?: string;
}

export function PremiumMetricCard({
  label,
  value,
  subtitle,
  accent = "slate",
  icon,
}: PremiumMetricCardProps) {
  const accentColors = {
    emerald: "text-emerald-400 glow-emerald",
    rose: "text-rose-400 glow-rose",
    sky: "text-sky-400 glow-sky",
    amber: "text-amber-400",
    slate: "text-slate-300",
  };

  const glowClass = accent !== "slate" && accent !== "amber" ? `glow-${accent}` : "";

  return (
    <div className={`glass-card group rounded-2xl p-5 transition-all duration-300 hover:scale-[1.02] hover:bg-slate-800/40 ${glowClass}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {icon && <div className={`text-lg ${accentColors[accent]}`}>{icon}</div>}
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-slate-400 transition-colors">
            {label}
          </span>
        </div>
      </div>

      <div className="flex flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span className={`text-2xl font-black tracking-tight ${accentColors[accent]}`}>
            {value}
          </span>
        </div>
        {subtitle && (
          <p className="text-[10px] font-medium text-slate-500/80 uppercase tracking-widest">
            {subtitle}
          </p>
        )}
      </div>

      {/* Decorative background pulse */}
      <div className={`absolute -right-2 -top-2 h-16 w-16 rounded-full blur-3xl opacity-10 transition-opacity group-hover:opacity-20 ${
        accent === "emerald" ? "bg-emerald-500" :
        accent === "rose" ? "bg-rose-500" :
        accent === "sky" ? "bg-sky-500" : "bg-slate-500"
      }`} />
    </div>
  );
}
