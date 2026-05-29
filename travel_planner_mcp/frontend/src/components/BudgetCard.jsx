import { formatMoney } from "../utils/format";

export default function BudgetCard({ label, value, tone = "default" }) {
  const toneClass = {
    default: "from-white/10 to-white/[0.03]",
    good: "from-emerald-400/20 to-emerald-400/[0.04]",
    warn: "from-amber-400/20 to-amber-400/[0.04]",
    bad: "from-red-400/20 to-red-400/[0.04]",
  }[tone];

  return (
    <div className={`rounded-3xl border border-white/10 bg-gradient-to-br ${toneClass} p-5`}>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-black text-white">{formatMoney(value)}</p>
    </div>
  );
}
