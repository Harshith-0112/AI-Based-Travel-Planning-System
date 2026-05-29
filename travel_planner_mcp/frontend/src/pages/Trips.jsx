import { useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";

import Alert from "../components/Alert";
import { useTrip } from "../context/TripContext";
import { formatMoney } from "../utils/format";

function TripCard({ entry, onOpen, onFavorite, onDelete }) {
  return (
    <article className="glass-card p-6 transition hover:-translate-y-1 hover:bg-white/[0.09]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-teal-200">{entry.destination}</p>
          <h2 className="mt-2 text-2xl font-black text-white">{entry.destination} Trip</h2>
        </div>
        <button
          type="button"
          onClick={() => onFavorite(entry.id)}
          className={`rounded-2xl border px-3 py-2 text-lg transition ${
            entry.is_favorite ? "border-amber-300/50 bg-amber-300/15 text-amber-200" : "border-white/10 bg-white/10 text-slate-300"
          }`}
          aria-label={entry.is_favorite ? "Remove from favourites" : "Add to favourites"}
        >
          {entry.is_favorite ? "★" : "☆"}
        </button>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-slate-500">Days</p>
          <p className="font-bold text-white">{entry.days}</p>
        </div>
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-slate-500">Budget</p>
          <p className="font-bold text-white">{formatMoney(entry.budget)}</p>
        </div>
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-slate-500">Hotel</p>
          <p className="font-bold capitalize text-white">{entry.hotel_preference}</p>
        </div>
        <div className="rounded-2xl bg-white/[0.05] p-3">
          <p className="text-slate-500">Total</p>
          <p className="font-bold text-white">{formatMoney(entry.total_estimated_cost)}</p>
        </div>
      </div>

      <p className="mt-4 text-xs text-slate-500">Created {new Date(entry.created_at).toLocaleString()}</p>
      <button type="button" onClick={() => onOpen(entry)} className="primary-button mt-5 w-full">
        Open Trip
      </button>
      <button type="button" onClick={() => onDelete(entry.id)} className="secondary-button mt-3 w-full">
        Delete
      </button>
    </article>
  );
}

export default function Trips() {
  const navigate = useNavigate();
  const {
    recentTrips,
    favouriteTrips,
    libraryLoading,
    libraryError,
    openTrip,
    toggleFavorite,
    deleteTripById,
  } = useTrip();
  const [tab, setTab] = useState("recent");
  const [actionError, setActionError] = useState("");
  const trips = tab === "recent" ? recentTrips : favouriteTrips;

  function handleOpen(entry) {
    openTrip(entry);
    navigate("/trip-result");
  }

  async function handleFavorite(id) {
    setActionError("");
    try {
      const entry = await toggleFavorite(id);
      toast.success(entry?.is_favorite ? "Added to favourites." : "Removed from favourites.");
    } catch (error) {
      setActionError(error.message);
      toast.error(error.message || "Could not update favourite.");
    }
  }

  async function handleDelete(id) {
    setActionError("");
    try {
      await deleteTripById(id);
      toast.success("Trip deleted.");
    } catch (error) {
      setActionError(error.message);
      toast.error(error.message || "Could not delete trip.");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Trips</p>
        <h1 className="mt-2 text-4xl font-black text-white">Recent and favourites.</h1>
        <p className="mt-3 text-slate-400">
          Recent and favourite trips are loaded from the database for your account.
        </p>
      </div>

      {libraryError && <Alert type="error">{libraryError}</Alert>}
      {actionError && <Alert type="error">{actionError}</Alert>}

      <div className="glass-card inline-flex gap-2 p-2">
        <button
          type="button"
          onClick={() => setTab("recent")}
          className={`rounded-2xl px-5 py-3 text-sm font-bold transition ${tab === "recent" ? "bg-teal-300 text-slate-950" : "text-slate-300 hover:bg-white/10"}`}
        >
          Recent
        </button>
        <button
          type="button"
          onClick={() => setTab("favourites")}
          className={`rounded-2xl px-5 py-3 text-sm font-bold transition ${tab === "favourites" ? "bg-teal-300 text-slate-950" : "text-slate-300 hover:bg-white/10"}`}
        >
          Favourites
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {trips.map((entry) => (
          <TripCard
            key={entry.id}
            entry={entry}
            onOpen={handleOpen}
            onFavorite={handleFavorite}
            onDelete={handleDelete}
          />
        ))}
      </div>

      {libraryLoading && <Alert>Loading trips from your account...</Alert>}

      {!libraryLoading && trips.length === 0 && (
        <Alert>
          {tab === "recent"
            ? "No recent trips yet. Generate an itinerary to add one here."
            : "No favourites yet. Mark a trip with the star button to keep it here."}
        </Alert>
      )}
    </div>
  );
}
