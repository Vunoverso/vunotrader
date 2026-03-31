"use client";

import { useState, useEffect } from "react";

export interface TradingProfile {
  name: string;
  description: string;
  max_global_positions: number;
  max_positions_per_symbol: number;
  max_correlated_positions: number;
  max_spread_points: number;
  min_atr_pct: number;
  default_volume: number;
  default_sl_points: number;
  default_tp_points: number;
  max_consecutive_losses: number;
  confidence_threshold: number;
}

interface TradingProfileSelectorProps {
  onProfileChange?: (profile: TradingProfile) => void;
}

export default function TradingProfileSelector({
  onProfileChange,
}: TradingProfileSelectorProps) {
  const [profiles, setProfiles] = useState<TradingProfile[]>([]);
  const [selected, setSelected] = useState<string>("moderado");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const loadProfiles = async () => {
      try {
        const res = await fetch("/api/profile/trading-profiles");
        if (res.ok) {
          const data = await res.json();
          setProfiles(data);
          const profileRes = await fetch("/api/profile/trading-profile");
          if (profileRes.ok) {
            const current = await profileRes.json();
            setSelected(current.name || "moderado");
          }
        }
      } catch (err) {
        console.error("Falha ao carregar perfis:", err);
      } finally {
        setLoading(false);
      }
    };
    loadProfiles();
  }, []);

  const handleSelectChange = async (profileName: string) => {
    setSelected(profileName);
    setSaving(true);
    try {
      const res = await fetch("/api/profile/trading-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_name: profileName }),
      });
      if (res.ok) {
        const savedProfile = await res.json();
        if (onProfileChange) {
          onProfileChange(savedProfile);
        }
      }
    } catch (err) {
      console.error("Falha ao salvar perfil:", err);
    } finally {
      setSaving(false);
    }
  };

  const selectedProfile = profiles.find((p) => p.name === selected);

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Perfil de Trading
        </label>
        <select
          value={selected}
          onChange={(e) => handleSelectChange(e.target.value)}
          disabled={loading || saving}
          className="w-full px-4 py-2.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-100 text-sm focus:outline-none focus:border-sky-500 focus:ring-1 focus:ring-sky-500/30 transition disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {profiles.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name.charAt(0).toUpperCase() + p.name.slice(1)} - {p.description.split(",")[0]}
            </option>
          ))}
        </select>
      </div>

      {selectedProfile && (
        <div className="p-4 rounded-lg border border-slate-700 bg-slate-800/50 space-y-2">
          <p className="text-sm text-slate-300 font-medium">{selectedProfile.description}</p>
          <div className="grid grid-cols-2 gap-3 text-xs text-slate-400">
            <div>
              <p className="text-slate-500">Posições globais</p>
              <p className="text-slate-100 font-mono">
                até {selectedProfile.max_global_positions}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Por símbolo</p>
              <p className="text-slate-100 font-mono">
                até {selectedProfile.max_positions_per_symbol}
              </p>
            </div>
            <div>
              <p className="text-slate-500">Spread máximo</p>
              <p className="text-slate-100 font-mono">
                {selectedProfile.max_spread_points.toFixed(1)} pts
              </p>
            </div>
            <div>
              <p className="text-slate-500">ATR mínimo</p>
              <p className="text-slate-100 font-mono">
                {(selectedProfile.min_atr_pct * 100).toFixed(3)}%
              </p>
            </div>
            <div>
              <p className="text-slate-500">Volume padrão</p>
              <p className="text-slate-100 font-mono">
                {selectedProfile.default_volume.toFixed(3)} lote
              </p>
            </div>
            <div>
              <p className="text-slate-500">Confiança mínima</p>
              <p className="text-slate-100 font-mono">
                {(selectedProfile.confidence_threshold * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {saving && (
        <p className="text-xs text-sky-400 text-center">Salvando perfil...</p>
      )}
    </div>
  );
}
