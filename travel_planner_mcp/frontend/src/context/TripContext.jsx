import { createContext, useContext, useEffect, useMemo, useState } from "react";

import {
  deleteTrip,
  favoriteTrip,
  getFavouriteTrips,
  getRecentTrips,
  unfavoriteTrip,
} from "../api/tripApi";
import { useAuth } from "./AuthContext";

const TripContext = createContext(null);

function readJson(key, fallback) {
  try {
    const value = localStorage.getItem(key);
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function scopedKeys(userKey) {
  if (!userKey) {
    return null;
  }
  return {
    currentTrip: `currentTrip:${userKey}`,
  };
}

function removeOldGlobalKeys() {
  [
    "currentTrip",
    "recentTrips",
    "favoriteTrips",
    "favouriteTrips",
    "ai_travel_current_trip",
    "ai_travel_recent_trips",
  ].forEach((key) => localStorage.removeItem(key));
}

function tripIdentity(plan) {
  return plan?.backend_trip_id || plan?.local_trip_id || plan?.generated_at || `${plan?.trip_request?.destination || "trip"}-${Date.now()}`;
}

function entryFromTripRecord(record) {
  const plan = record.response_json || {};
  const request = record.request_json || plan.trip_request || {};
  const budget = record.budget_breakdown_json || plan.budget_breakdown || {};
  const planWithBackend = {
    ...plan,
    backend_trip_id: record.id,
    backend_id: record.id,
    is_favorite: record.is_favorite,
  };
  return {
    id: record.id,
    backend_id: record.id,
    plan: planWithBackend,
    destination: request.destination || "Unknown",
    days: request.days || 1,
    budget: request.budget || budget.budget || 0,
    hotel_preference: request.hotel_preference || "standard",
    total_estimated_cost: budget.total_estimated_cost || 0,
    created_at: record.created_at,
    is_favorite: record.is_favorite,
  };
}

export function TripProvider({ children }) {
  const { user } = useAuth();
  const userKey = user?.id || user?.email || null;
  const keys = useMemo(() => scopedKeys(userKey), [userKey]);
  const [currentTrip, setCurrentTripState] = useState(null);
  const [recentTrips, setRecentTrips] = useState([]);
  const [favouriteTrips, setFavouriteTrips] = useState([]);
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryError, setLibraryError] = useState("");

  useEffect(() => {
    removeOldGlobalKeys();
    if (!keys) {
      setCurrentTripState(null);
      setRecentTrips([]);
      setFavouriteTrips([]);
      return;
    }

    setCurrentTripState(readJson(keys.currentTrip, null));
    refreshTrips();
  }, [keys]);

  async function refreshTrips() {
    if (!keys) return;
    setLibraryLoading(true);
    setLibraryError("");
    try {
      const [recent, favourites] = await Promise.all([getRecentTrips(), getFavouriteTrips()]);
      setRecentTrips(recent.map(entryFromTripRecord));
      setFavouriteTrips(favourites.map(entryFromTripRecord));
    } catch (error) {
      setLibraryError(error.message);
      setRecentTrips([]);
      setFavouriteTrips([]);
    } finally {
      setLibraryLoading(false);
    }
  }

  function setCurrentTrip(plan) {
    setCurrentTripState(plan);
    if (!keys) return;
    if (plan) {
      localStorage.setItem(keys.currentTrip, JSON.stringify(plan));
    } else {
      localStorage.removeItem(keys.currentTrip);
    }
  }

  function addRecentTrip(plan, backendRecord) {
    if (!backendRecord) return null;
    const entry = entryFromTripRecord(backendRecord);
    setRecentTrips((current) => [entry, ...current.filter((trip) => trip.id !== entry.id)]);
    return entry;
  }

  function updateCurrentTrip(plan) {
    setCurrentTrip(plan);
    const id = Number(plan?.backend_trip_id || plan?.backend_id);
    if (!id) return;
    setRecentTrips((current) =>
      current.map((trip) => (trip.id === id ? { ...trip, plan: { ...plan, is_favorite: trip.is_favorite } } : trip)),
    );
    setFavouriteTrips((current) =>
      current.map((trip) => (trip.id === id ? { ...trip, plan: { ...plan, is_favorite: trip.is_favorite } } : trip)),
    );
  }

  function discardCurrentTrip() {
    setCurrentTrip(null);
  }

  function openTrip(entry) {
    setCurrentTrip(entry.plan);
  }

  async function toggleFavorite(tripId) {
    const numericId = Number(tripId);
    if (!numericId) return null;
    const existing = recentTrips.find((trip) => trip.id === numericId) || favouriteTrips.find((trip) => trip.id === numericId);
    const updatedRecord = existing?.is_favorite
      ? await unfavoriteTrip(numericId)
      : await favoriteTrip(numericId);
    const entry = entryFromTripRecord(updatedRecord);

    setRecentTrips((current) => current.map((trip) => (trip.id === entry.id ? entry : trip)));
    setFavouriteTrips((current) => {
      if (entry.is_favorite) {
        return [entry, ...current.filter((trip) => trip.id !== entry.id)];
      }
      return current.filter((trip) => trip.id !== entry.id);
    });
    if (currentTrip && Number(currentTrip.backend_trip_id || currentTrip.backend_id) === entry.id) {
      setCurrentTrip(entry.plan);
    }
    return entry;
  }

  async function deleteTripById(tripId) {
    const numericId = Number(tripId);
    if (!numericId) return;
    await deleteTrip(numericId);
    setRecentTrips((current) => current.filter((trip) => trip.id !== numericId));
    setFavouriteTrips((current) => current.filter((trip) => trip.id !== numericId));
    if (currentTrip && Number(currentTrip.backend_trip_id || currentTrip.backend_id) === numericId) {
      setCurrentTrip(null);
    }
  }

  const value = useMemo(
    () => ({
      currentTrip,
      recentTrips,
      favouriteTrips,
      libraryLoading,
      libraryError,
      setCurrentTrip,
      updateCurrentTrip,
      discardCurrentTrip,
      addRecentTrip,
      openTrip,
      toggleFavorite,
      deleteTripById,
      refreshTrips,
      tripIdentity,
    }),
    [currentTrip, recentTrips, favouriteTrips, libraryLoading, libraryError],
  );

  return <TripContext.Provider value={value}>{children}</TripContext.Provider>;
}

export function useTrip() {
  const context = useContext(TripContext);
  if (!context) {
    throw new Error("useTrip must be used inside TripProvider");
  }
  return context;
}
