import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { saveTrip } from "../api/tripApi";
import Alert from "../components/Alert";
import BudgetCard from "../components/BudgetCard";
import HotelCard from "../components/HotelCard";
import ItineraryDay from "../components/ItineraryDay";
import { useTrip } from "../context/TripContext";
import { cleanNotes, formatMoney, hotelCost, sourceLabel } from "../utils/format";

function getInitialPlan(locationState) {
  if (locationState?.plan) return locationState.plan;
  return null;
}

function hotelKey(hotel) {
  return `${hotel?.name || ""}|${hotel?.address || ""}`;
}

function getHotelOptions(plan) {
  if (plan?._hotel_options?.length) {
    return plan._hotel_options;
  }
  const seen = new Set();
  return [plan?.hotel, ...(plan?.alternative_hotels || [])].filter((hotel) => {
    if (!hotel) return false;
    const key = `${hotel.name}|${hotel.address}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function recalculateBudget(plan, selectedHotel) {
  const days = plan?.trip_request?.days || 1;
  const original = plan?.budget_breakdown || {};
  const lodging = hotelCost(selectedHotel, days);
  const total = lodging + Number(original.transport_cost || 0) + Number(original.food_cost || 0) + Number(original.misc_cost || 0);
  const budget = Number(original.budget || plan?.trip_request?.budget || 0);

  return {
    ...original,
    lodging_cost: lodging,
    total_estimated_cost: total,
    within_budget: total <= budget,
    over_budget_amount: Math.max(total - budget, 0),
    budget_status: total <= budget ? "within_budget" : "over_budget",
  };
}

function buildHotelReason(hotel, request, lodgingCost) {
  const preference = request?.hotel_preference || "standard";
  const rating = hotel?.rating ? `a ${Number(hotel.rating).toFixed(1)} rating` : "limited rating information";
  const nightly = hotel?.nightly_price ? formatMoney(hotel.nightly_price) : "an unavailable nightly price";
  const total = formatMoney(lodgingCost);
  return `This hotel matches your ${preference} preference, has ${rating}, a nightly price of ${nightly}, and a total stay cost of ${total}.`;
}

function Bar({ label, value, max, tone = "bg-teal-300" }) {
  const percent = max > 0 ? Math.min((Number(value || 0) / max) * 100, 140) : 0;
  return (
    <div>
      <div className="mb-2 flex justify-between gap-3 text-sm">
        <span className="text-slate-300">{label}</span>
        <span className="font-bold text-white">{formatMoney(value)}</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
    </div>
  );
}

function hotelBadges(hotel, hotelOptions, preference) {
  const totals = hotelOptions.map((item) => hotelCost(item, 1)).filter((value) => value > 0);
  const cheapest = Math.min(...totals);
  const highestRating = Math.max(...hotelOptions.map((item) => Number(item.rating || 0)));
  const total = hotelCost(hotel, 1);
  const badges = [];
  if (total && total === cheapest) badges.push("Budget Friendly");
  if (Number(hotel.rating || 0) === highestRating && highestRating > 0) badges.push("Highest Rated");
  if (Number(hotel.rating || 0) >= 4.2 && total && total <= cheapest * 1.25) badges.push("Best Value");
  if (preference === "luxury" && Number(hotel.rating || 0) >= 4.5) badges.push("Luxury Pick");
  return badges.slice(0, 2);
}

export default function TripResult() {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentTrip, updateCurrentTrip, discardCurrentTrip, addRecentTrip, toggleFavorite, tripIdentity } = useTrip();
  const [plan, setPlan] = useState(() => currentTrip || getInitialPlan(location.state));
  const [saveStatus, setSaveStatus] = useState("");
  const [saveError, setSaveError] = useState("");

  const hotelOptions = useMemo(() => getHotelOptions(plan), [plan]);
  const days = plan?.trip_request?.days || 1;
  const budget = plan?.budget_breakdown || {};
  const notes = cleanNotes(plan?.notes || []);
  const attractionSources = new Set((plan?.attractions || []).map((item) => item.source));
  const attractionByName = useMemo(() => {
    return new Map((plan?.attractions || []).map((item) => [item.name, item]));
  }, [plan]);

  useEffect(() => {
    if (!plan && currentTrip) {
      setPlan(currentTrip);
    }
  }, [currentTrip, plan]);

  if (!plan) {
    return (
      <div className="glass-card p-8 text-center">
        <h1 className="text-3xl font-black text-white">No trip result loaded</h1>
        <p className="mt-3 text-slate-400">Create a new trip to see an itinerary here.</p>
        <Link to="/create-trip" className="primary-button mt-6">
          Create Trip
        </Link>
      </div>
    );
  }

  function selectHotel(hotel) {
    const updatedBudget = recalculateBudget(plan, hotel);
    const baseSummary = plan.summary?.replace(/^Selected hotel:.*?\.\s*/i, "") || "";
    const updatedPlan = {
      ...plan,
      hotel,
      _hotel_options: hotelOptions,
      selected_hotel_key: hotelKey(hotel),
      budget_breakdown: updatedBudget,
      hotel_selection_reason: buildHotelReason(hotel, plan.trip_request, updatedBudget.lodging_cost),
      summary: `Selected hotel: ${hotel.name}. ${baseSummary}`,
    };
    setPlan(updatedPlan);
    updateCurrentTrip(updatedPlan);
  }

  async function handleSave() {
    setSaveError("");
    setSaveStatus("");
    try {
      if (plan.backend_trip_id || plan.backend_id) {
        setSaveStatus("Trip is already saved in Recent.");
        return;
      }
      const backendRecord = await saveTrip(plan);
      const savedPlan = {
        ...plan,
        backend_trip_id: backendRecord.id,
        backend_id: backendRecord.id,
        is_favorite: backendRecord.is_favorite,
      };
      setPlan(savedPlan);
      updateCurrentTrip(savedPlan);
      addRecentTrip(savedPlan, backendRecord);
      setSaveStatus("Trip saved successfully.");
      toast.success("Trip saved.");
    } catch (err) {
      setSaveError(err.message);
      toast.error(err.message || "Could not save trip.");
    }
  }

  async function handleFavorite() {
    setSaveError("");
    try {
      const wasFavorite = Boolean(plan.is_favorite);
      const entry = await toggleFavorite(currentTripId);
      if (entry?.plan) {
        setPlan(entry.plan);
      }
      toast.success(wasFavorite ? "Removed from favourites." : "Added to favourites.");
    } catch (err) {
      setSaveError(err.message);
      toast.error(err.message || "Could not update favourite.");
    }
  }

  const budgetDelta = Number(budget.budget || 0) - Number(budget.total_estimated_cost || 0);
  const budgetTotal = Number(budget.budget || 0);
  const estimatedTotal = Number(budget.total_estimated_cost || 0);
  const percentUsed = budgetTotal > 0 ? Math.round((estimatedTotal / budgetTotal) * 100) : 0;
  const currentTripId = tripIdentity(plan);
  const sections = ["Overview", "Budget", "Hotels", "Transport", "Itinerary"];

  return (
    <div className="space-y-8">
      <nav className="glass-card sticky top-[82px] z-20 flex gap-2 overflow-x-auto p-2">
        {sections.map((section) => (
          <button
            key={section}
            type="button"
            onClick={() => document.getElementById(section.toLowerCase())?.scrollIntoView({ behavior: "smooth", block: "start" })}
            className="shrink-0 rounded-2xl px-4 py-2 text-sm font-bold text-slate-200 transition hover:bg-white/10"
          >
            {section}
          </button>
        ))}
      </nav>

      <section id="overview" className="glass-card scroll-mt-32 p-6 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Trip result</p>
            <h1 className="mt-2 text-4xl font-black text-white">{plan.trip_request?.destination}</h1>
            <p className="mt-4 max-w-3xl leading-8 text-slate-300">{plan.summary}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleFavorite}
              className={`secondary-button ${plan.is_favorite ? "border-amber-300/40 bg-amber-300/15 text-amber-100" : ""}`}
            >
              {plan.is_favorite ? "★ Favourite" : "☆ Favourite"}
            </button>
            <button onClick={handleSave} className="primary-button">
              Save trip
            </button>
            <button
              type="button"
              onClick={() => {
                discardCurrentTrip();
                navigate("/dashboard");
              }}
              className="secondary-button"
            >
              Discard Trip
            </button>
          </div>
        </div>
        <div className="mt-5 space-y-3">
          <Alert type="success">{saveStatus}</Alert>
          <Alert type="error">{saveError}</Alert>
          {budget.within_budget === false && (
            <Alert type="warning">This plan exceeds your budget by {formatMoney(budget.over_budget_amount || Math.abs(budgetDelta))}.</Alert>
          )}
          {(plan.daily_plans || []).some((day) => (day.warnings || []).length > 0) && (
            <Alert type="warning">Some days include planning warnings. Review the itinerary cards below.</Alert>
          )}
          {attractionSources.has("openstreetmap") && <Alert>Places loaded from OpenStreetMap fallback data.</Alert>}
          {attractionSources.has("fallback_cache") && <Alert>Places loaded from offline fallback data.</Alert>}
          {attractionSources.has("verified_cache") && <Alert>Places loaded from verified cache.</Alert>}
          {attractionSources.has("curated_fallback") && <Alert>Places loaded from curated fallback data.</Alert>}
          {notes.map((note, index) => (
            <Alert key={index} type="info">{note}</Alert>
          ))}
        </div>
      </section>

      <section id="budget" className="scroll-mt-32">
        <h2 className="mb-4 text-2xl font-black text-white">Budget breakdown</h2>
        <div className="glass-card mb-4 space-y-5 p-6">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-sm text-slate-400">Budget usage</p>
              <p className="text-3xl font-black text-white">{percentUsed}% used</p>
            </div>
            <p className={budgetDelta >= 0 ? "font-bold text-emerald-200" : "font-bold text-red-200"}>
              {budgetDelta >= 0 ? `${formatMoney(budgetDelta)} remaining` : `${formatMoney(Math.abs(budgetDelta))} over budget`}
            </p>
          </div>
          <Bar label={`${formatMoney(estimatedTotal)} of ${formatMoney(budgetTotal)}`} value={estimatedTotal} max={budgetTotal} tone={budgetDelta >= 0 ? "bg-teal-300" : "bg-red-300"} />
          <div className="grid gap-4 md:grid-cols-2">
            <Bar label="Lodging" value={budget.lodging_cost} max={estimatedTotal} tone="bg-cyan-300" />
            <Bar label="Transport" value={budget.transport_cost} max={estimatedTotal} tone="bg-indigo-300" />
            <Bar label="Food" value={budget.food_cost} max={estimatedTotal} tone="bg-emerald-300" />
            <Bar label="Misc" value={budget.misc_cost} max={estimatedTotal} tone="bg-amber-300" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <BudgetCard label="Budget" value={budget.budget} />
          <BudgetCard label="Estimated total" value={budget.total_estimated_cost} tone={budget.within_budget ? "good" : "bad"} />
          <BudgetCard label={budgetDelta >= 0 ? "Remaining" : "Over budget"} value={Math.abs(budgetDelta)} tone={budgetDelta >= 0 ? "good" : "bad"} />
          <BudgetCard label="Lodging" value={budget.lodging_cost} />
          <BudgetCard label="Transport" value={budget.transport_cost} />
          <BudgetCard label="Food" value={budget.food_cost} />
          <BudgetCard label="Misc" value={budget.misc_cost} />
        </div>
      </section>

      <section id="hotels" className="scroll-mt-32">
        <div className="mb-4">
          <h2 className="text-2xl font-black text-white">Choose your hotel</h2>
          <p className="mt-2 text-sm text-slate-400">Selecting another hotel updates lodging and total cost locally.</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-3">
          {hotelOptions.map((hotel) => (
            <HotelCard
              key={`${hotel.name}-${hotel.address}`}
              hotel={hotel}
              days={days}
              selected={hotelKey(hotel) === (plan.selected_hotel_key || hotelKey(plan.hotel))}
              badges={hotelBadges(hotel, hotelOptions, plan.trip_request?.hotel_preference)}
              onSelect={() => {
                selectHotel(hotel);
                toast.success("Hotel changed and budget updated.");
              }}
            />
          ))}
        </div>
        {plan.hotel_selection_reason && (
          <p className="mt-4 rounded-2xl border border-white/10 bg-white/[0.06] px-4 py-3 text-sm text-slate-300">
            {plan.hotel_selection_reason}
          </p>
        )}
      </section>

      {plan.transport && (
        <section id="transport" className="glass-card scroll-mt-32 p-6">
          <h2 className="text-2xl font-black text-white">Transport estimate</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <BudgetCard label="Cost" value={plan.transport.estimated_cost} />
            <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-5">
              <p className="text-sm text-slate-400">Mode</p>
              <p className="mt-2 text-2xl font-black capitalize text-white">{plan.transport.mode}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-5">
              <p className="text-sm text-slate-400">Duration</p>
              <p className="mt-2 text-2xl font-black text-white">{plan.transport.estimated_duration_hours} hrs</p>
            </div>
          </div>
          <p className="mt-4 text-sm text-slate-400">{plan.transport.reason}</p>
        </section>
      )}

      <section id="itinerary" className="scroll-mt-32 space-y-4">
        <div>
          <h2 className="text-2xl font-black text-white">Day-wise itinerary</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {[...attractionSources].map((source) => (
              <span key={source} className="soft-badge">{sourceLabel(source)}</span>
            ))}
          </div>
        </div>
        {(plan.daily_plans || []).map((day) => (
          <ItineraryDay
            key={day.day_number}
            destination={plan.trip_request?.destination}
            day={{
              ...day,
              activities: (day.activities || []).map((activity) => {
                const attraction = attractionByName.get(activity.place_name);
                return {
                  ...activity,
                  source: attraction?.source,
                  category: attraction?.category,
                  image_url: activity.image_url || attraction?.image_url,
                  tags: activity.tags?.length ? activity.tags : attraction?.tags,
                  best_time: activity.best_time || attraction?.best_time,
                };
              }),
            }}
          />
        ))}
      </section>
    </div>
  );
}
