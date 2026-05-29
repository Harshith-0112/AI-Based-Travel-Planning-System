import { apiClient, getApiError } from "./client";

export async function createTrip(payload) {
  try {
    const { data } = await apiClient.post("/plan-trip", payload);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getSavedTrips() {
  try {
    const { data } = await apiClient.get("/itineraries/");
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getSavedTrip(id) {
  try {
    const { data } = await apiClient.get(`/itineraries/${id}`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function saveTrip(plan) {
  const request = plan?.trip_request || {};
  try {
    const { data } = await apiClient.post("/trips", {
      destination: request.destination || "Unknown",
      request_json: request,
      response_json: plan,
      selected_hotel_json: plan?.hotel || null,
      budget_breakdown_json: plan?.budget_breakdown || null,
    });
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getRecentTrips() {
  try {
    const { data } = await apiClient.get("/trips/recent");
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getFavouriteTrips() {
  try {
    const { data } = await apiClient.get("/trips/favourites");
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getTripById(id) {
  try {
    const { data } = await apiClient.get(`/trips/${id}`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function favoriteTrip(id) {
  try {
    const { data } = await apiClient.post(`/trips/${id}/favorite`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function unfavoriteTrip(id) {
  try {
    const { data } = await apiClient.post(`/trips/${id}/unfavorite`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function deleteTrip(id) {
  try {
    const { data } = await apiClient.delete(`/trips/${id}`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function deleteSavedTrip(id) {
  try {
    const { data } = await apiClient.delete(`/itineraries/${id}`);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}
