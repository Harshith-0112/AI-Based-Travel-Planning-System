import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";

import { createTrip, saveTrip } from "../api/tripApi";
import Alert from "../components/Alert";
import LoadingState from "../components/LoadingState";
import PreferenceSelector from "../components/PreferenceSelector";
import { useTrip } from "../context/TripContext";
import { formatMoney } from "../utils/format";

const today = new Date().toISOString().slice(0, 10);
const steps = ["Route", "Budget", "Preferences", "Style", "Review"];

function stableHotelOptions(plan) {
  const seen = new Set();
  return [plan?.hotel, ...(plan?.alternative_hotels || [])].filter((hotel) => {
    if (!hotel) return false;
    const key = `${hotel.name}|${hotel.address}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export default function CreateTrip() {
  const navigate = useNavigate();
  const { setCurrentTrip, addRecentTrip } = useTrip();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    destination: "Varanasi",
    starting_location: "",
    budget: 15000,
    days: 3,
    travelers: 2,
    start_date: today,
    preferences: ["history", "food"],
    hotel_preference: "standard",
    transport_mode: "auto",
  });
  const [error, setError] = useState("");
  const [validationErrors, setValidationErrors] = useState([]);
  const [loading, setLoading] = useState(false);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function stepErrors(targetStep = step) {
    const errors = [];
    if (targetStep === 0 && !form.destination.trim()) errors.push("Destination is required.");
    if (targetStep === 1) {
      if (Number(form.budget) <= 0) errors.push("Budget must be greater than 0.");
      if (Number(form.days) < 1) errors.push("Days must be at least 1.");
      if (Number(form.travelers) < 1) errors.push("Travelers must be at least 1.");
    }
    if (targetStep === 2 && !form.preferences.length) errors.push("Select at least one preference.");
    return errors;
  }

  const allErrors = useMemo(() => steps.flatMap((_, index) => stepErrors(index)), [form]);
  const canGenerate = allErrors.length === 0;

  function handleEnterKey(event) {
    if (event.key !== "Enter") return;
    event.preventDefault();
  }

  function nextStep() {
    const errors = stepErrors();
    setValidationErrors(errors);
    if (errors.length) return;
    setStep((current) => Math.min(current + 1, steps.length - 1));
  }

  async function handleGenerate() {
    setValidationErrors(allErrors);
    if (allErrors.length) return;

    setError("");
    setLoading(true);
    try {
      const payload = {
        ...form,
        budget: Number(form.budget),
        days: Number(form.days),
        travelers: Number(form.travelers),
        starting_location: form.starting_location || null,
        start_date: form.start_date || null,
      };
      const plan = await createTrip(payload);
      const options = stableHotelOptions(plan);
      const planWithId = {
        ...plan,
        _hotel_options: options,
        selected_hotel_key: options[0] ? `${options[0].name}|${options[0].address}` : "",
        local_trip_id: plan.generated_at || `${payload.destination}-${Date.now()}`,
      };
      const backendRecord = await saveTrip(planWithId);
      const savedPlan = {
        ...planWithId,
        backend_trip_id: backendRecord.id,
        backend_id: backendRecord.id,
        is_favorite: backendRecord.is_favorite,
      };
      setCurrentTrip(savedPlan);
      addRecentTrip(savedPlan, backendRecord);
      toast.success("Trip generated and saved to Recent.");
      navigate("/trip-result", { state: { plan: savedPlan } });
    } catch (err) {
      setError(err.message);
      toast.error(err.message || "Could not generate trip.");
      setLoading(false);
    }
  }

  if (loading) return <LoadingState />;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Create Trip</p>
        <h1 className="mt-2 text-4xl font-black text-white">Build the trip in five focused steps.</h1>
        <p className="mt-3 text-slate-400">Enter details calmly, review them, then generate your itinerary.</p>
      </div>

      <div className="glass-card p-3">
        <div className="grid gap-2 sm:grid-cols-5">
          {steps.map((label, index) => (
            <button
              key={label}
              type="button"
              onClick={() => index <= step && setStep(index)}
              className={`rounded-2xl px-3 py-3 text-sm font-bold transition ${
                index === step ? "bg-teal-300 text-slate-950" : index < step ? "bg-white/10 text-teal-100" : "bg-white/[0.04] text-slate-500"
              }`}
            >
              {index + 1}. {label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={(event) => event.preventDefault()} onKeyDown={handleEnterKey} className="glass-card space-y-6 p-6 md:p-8">
        <Alert type="error">{error}</Alert>
        {validationErrors.length > 0 && (
          <Alert type="warning">
            <ul className="list-inside list-disc">
              {validationErrors.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </Alert>
        )}

        {step === 0 && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Destination</span>
              <input className="input-field" value={form.destination} onChange={(e) => updateField("destination", e.target.value)} required />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Starting location</span>
              <input className="input-field" value={form.starting_location} onChange={(e) => updateField("starting_location", e.target.value)} placeholder="Optional" />
            </label>
          </div>
        )}

        {step === 1 && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Budget</span>
              <input className="input-field" type="number" min="1000" step="500" value={form.budget} onChange={(e) => updateField("budget", e.target.value)} required />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Start date</span>
              <input className="input-field" type="date" value={form.start_date} onChange={(e) => updateField("start_date", e.target.value)} />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Days</span>
              <input className="input-field" type="number" min="1" max="14" value={form.days} onChange={(e) => updateField("days", e.target.value)} required />
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Travelers</span>
              <input className="input-field" type="number" min="1" max="10" value={form.travelers} onChange={(e) => updateField("travelers", e.target.value)} required />
            </label>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <span className="text-sm font-semibold text-slate-300">Preferences</span>
            <PreferenceSelector value={form.preferences} onChange={(value) => updateField("preferences", value)} />
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Hotel preference</span>
              <select className="input-field" value={form.hotel_preference} onChange={(e) => updateField("hotel_preference", e.target.value)}>
                <option value="budget">Budget</option>
                <option value="standard">Standard</option>
                <option value="luxury">Luxury</option>
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-sm font-semibold text-slate-300">Transport mode</span>
              <select className="input-field" value={form.transport_mode} onChange={(e) => updateField("transport_mode", e.target.value)}>
                <option value="auto">Auto</option>
                <option value="flight">Flight</option>
                <option value="train">Train</option>
                <option value="bus">Bus</option>
                <option value="car">Car</option>
              </select>
            </label>
          </div>
        )}

        {step === 4 && (
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-3xl border border-white/10 bg-white/[0.05] p-5">
              <p className="text-sm text-slate-500">Route</p>
              <p className="mt-2 text-xl font-black text-white">{form.starting_location || "Flexible start"} → {form.destination}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.05] p-5">
              <p className="text-sm text-slate-500">Budget</p>
              <p className="mt-2 text-xl font-black text-white">{formatMoney(form.budget)} · {form.days} days · {form.travelers} travelers</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.05] p-5">
              <p className="text-sm text-slate-500">Preferences</p>
              <p className="mt-2 text-xl font-black capitalize text-white">{form.preferences.join(", ")}</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.05] p-5">
              <p className="text-sm text-slate-500">Style</p>
              <p className="mt-2 text-xl font-black capitalize text-white">{form.hotel_preference} hotel · {form.transport_mode} transport</p>
            </div>
          </div>
        )}

        <div className="flex flex-wrap justify-between gap-3">
          <button type="button" onClick={() => setStep((current) => Math.max(current - 1, 0))} disabled={step === 0} className="secondary-button">
            Back
          </button>
          {step < steps.length - 1 ? (
            <button type="button" onClick={nextStep} className="primary-button">
              Next
            </button>
          ) : (
            <button type="button" onClick={handleGenerate} disabled={!canGenerate} className="primary-button">
              Generate Itinerary
            </button>
          )}
        </div>
      </form>

      {step === 4 && (
        <div className="sticky bottom-4 z-20 glass-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-bold text-white">Ready to generate?</p>
            <p className="text-xs text-slate-400">Review looks good, then let the planning agents work.</p>
          </div>
          <button type="button" onClick={handleGenerate} disabled={!canGenerate} className="primary-button">
            Generate Itinerary
          </button>
        </div>
      )}
    </div>
  );
}
