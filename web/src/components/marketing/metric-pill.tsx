type MetricPillProps = {
  value: string;
  label: string;
};

export function MetricPill({ value, label }: MetricPillProps) {
  return (
    <div className="rounded-[24px] border border-sky-100 bg-white/80 px-5 py-4 shadow-[0_14px_34px_rgba(14,116,144,0.10)] backdrop-blur">
      <div className="text-lg font-semibold text-slate-950">{value}</div>
      <div className="mt-1 text-sm leading-6 text-slate-600">{label}</div>
    </div>
  );
}