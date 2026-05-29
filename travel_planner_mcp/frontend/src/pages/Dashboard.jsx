import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useTrip } from "../context/TripContext";
import { formatMoney } from "../utils/format";

export default function Dashboard() {
  const { user } = useAuth();
  const { recentTrips, favouriteTrips, openTrip } = useTrip();
  const navigate = useNavigate();
  const trips = recentTrips.slice(0, 3);
  const averageBudget =
    recentTrips.length > 0
      ? recentTrips.reduce((sum, trip) => sum + Number(trip.budget || 0), 0) / recentTrips.length
      : 0;
  const stats = [
    ["Total trips", recentTrips.length],
    ["Favourite trips", favouriteTrips.length],
    ["Average budget", formatMoney(averageBudget)],
    ["Latest destination", recentTrips[0]?.destination || "None yet"],
  ];

  return (
    <div className="space-y-8">
      <section className="glass-card overflow-hidden p-8 md:p-12">
        <div className="max-w-3xl">
          <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">AI Travel Command Center</p>
          <h1 className="mt-4 text-4xl font-black leading-tight text-white md:text-6xl">
            Plan trips that balance places, hotels, transport, and budget.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300">
            Hello {user?.full_name || "traveler"}. Build a verified itinerary with hotel selection,
            fallback places, and budget-aware recommendations.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/create-trip" className="primary-button">
              Create New Trip
            </Link>
            <Link to="/trips" className="secondary-button">
              View Trips
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(([label, value]) => (
          <div key={label} className="glass-card p-5">
            <p className="text-sm text-slate-400">{label}</p>
            <p className="mt-2 text-2xl font-black text-white">{value}</p>
          </div>
        ))}
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-black text-white">Recent trips</h2>
          <Link className="text-sm font-bold text-teal-200 hover:text-teal-100" to="/trips">
            See all
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {trips.map((trip) => (
            <button
              key={trip.id}
              onClick={() => {
                openTrip(trip);
                navigate("/trip-result");
              }}
              className="glass-card p-5 text-left transition hover:-translate-y-1 hover:bg-white/[0.09]"
            >
              <p className="text-sm text-teal-200">{trip.destination}</p>
              <h3 className="mt-2 text-xl font-black text-white">{trip.destination} Trip</h3>
              <p className="mt-3 text-sm text-slate-400">
                {trip.days} days | {formatMoney(trip.total_estimated_cost)} | {new Date(trip.created_at).toLocaleDateString()}
              </p>
            </button>
          ))}
          {trips.length === 0 && (
            <div className="glass-card p-8 text-center md:col-span-3">
              <p className="text-2xl font-black text-white">No recent trips yet</p>
              <p className="mt-3 text-slate-400">Generate your first itinerary and it will appear here automatically.</p>
              <Link to="/create-trip" className="primary-button mt-6">
                Create Trip
              </Link>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
