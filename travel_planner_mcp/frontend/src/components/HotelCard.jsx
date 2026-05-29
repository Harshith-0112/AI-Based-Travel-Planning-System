import { formatMoney, hotelCost } from "../utils/format";

export default function HotelCard({ hotel, days = 1, selected = false, badges = [], onSelect }) {
  if (!hotel) return null;
  const total = hotelCost(hotel, days);

  return (
    <button
      type="button"
      onClick={(event) => {
        event.preventDefault();
        event.stopPropagation();
        onSelect?.();
      }}
      className={`w-full rounded-3xl border p-5 text-left transition hover:-translate-y-1 ${
        selected
          ? "border-teal-300/70 bg-teal-300/10 shadow-glow"
          : "border-white/10 bg-white/[0.06] hover:border-white/20 hover:bg-white/[0.09]"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-black text-white">{hotel.name}</h3>
          <p className="mt-1 text-sm text-slate-400">{hotel.address || "Address not available"}</p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {selected && <span className="soft-badge bg-teal-300/15 text-teal-100">Selected</span>}
          {badges.map((badge) => (
            <span key={badge} className="soft-badge">{badge}</span>
          ))}
        </div>
      </div>
      <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
        <div>
          <p className="text-slate-500">Nightly</p>
          <p className="font-bold text-slate-100">{formatMoney(hotel.nightly_price)}</p>
        </div>
        <div>
          <p className="text-slate-500">Total</p>
          <p className="font-bold text-slate-100">{formatMoney(total)}</p>
        </div>
        <div>
          <p className="text-slate-500">Rating</p>
          <p className="font-bold text-slate-100">{hotel.rating || "N/A"}</p>
        </div>
      </div>
    </button>
  );
}
