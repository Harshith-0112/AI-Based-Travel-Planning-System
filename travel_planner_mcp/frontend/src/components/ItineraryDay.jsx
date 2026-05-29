import { formatMoney, sourceLabel } from "../utils/format";

export default function ItineraryDay({ day, destination }) {
  return (
    <section className="glass-card p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-teal-200">Day {day.day_number}</p>
          <h3 className="text-xl font-black text-white">{day.theme}</h3>
          {day.date && <p className="text-sm text-slate-400">{day.date}</p>}
        </div>
        <span className="soft-badge">Estimated {formatMoney(day.estimated_cost || 0)}</span>
      </div>

      <div className="mt-6 space-y-4">
        {(day.activities || []).map((activity, index) => {
          const category = activity.category?.replace("_", " ") || "travel";
          const description =
            activity.description ||
            `A recommended ${category} stop in ${destination || "this destination"}, suitable for this part of the day.`;
          return (
            <div
              key={`${activity.time_slot}-${index}`}
              className="relative rounded-3xl border border-white/10 bg-slate-950/35 p-5 transition hover:-translate-y-1 hover:border-teal-300/30 hover:bg-slate-950/50"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.2em] text-teal-200">{activity.time_slot}</p>
                  <h4 className="mt-1 text-lg font-bold text-white">{activity.title}</h4>
                  <p className="mt-2 text-sm leading-6 text-slate-300">{description}</p>
                </div>
                <span className="soft-badge">{formatMoney(activity.estimated_cost || 0)}</span>
              </div>
              {activity.highlights?.length > 0 && (
                <ul className="mt-4 list-inside list-disc space-y-1 text-sm text-slate-300">
                  {activity.highlights.slice(0, 3).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              )}
              {activity.visit_tips?.length > 0 && (
                <div className="mt-4 rounded-2xl border border-teal-300/15 bg-teal-300/10 px-4 py-3">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-200">Visit tips</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-300">
                    {activity.visit_tips.slice(0, 3).map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-4 flex flex-wrap gap-2">
                {activity.place_name && <span className="soft-badge">{activity.place_name}</span>}
                {activity.category && <span className="soft-badge">{activity.category.replace("_", " ")}</span>}
                {activity.best_time && <span className="soft-badge">Best time: {activity.best_time}</span>}
                {(activity.tags || []).slice(0, 4).map((tag) => (
                  <span key={tag} className="soft-badge">{tag}</span>
                ))}
                {activity.cost_source === "estimated" && <span className="soft-badge">Estimated cost</span>}
                {activity.source && <span className="soft-badge">{sourceLabel(activity.source)}</span>}
              </div>
            </div>
          );
        })}
        {(!day.activities || day.activities.length === 0) && (
          <p className="rounded-2xl border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            No verified activities are available for this day.
          </p>
        )}
      </div>

      {(day.warnings || []).map((warning, index) => (
        <p key={index} className="mt-4 rounded-2xl border border-amber-300/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
          {warning}
        </p>
      ))}
    </section>
  );
}
