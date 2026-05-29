export function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "Not available";
  }
  return `Rs ${Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  })}`;
}

export function hotelCost(hotel, days = 1) {
  if (!hotel) return 0;
  if (hotel.total_price) return Number(hotel.total_price);
  if (hotel.nightly_price) return Number(hotel.nightly_price) * Math.max(Number(days) - 1, 1);
  return 0;
}

export function sourceLabel(source) {
  const labels = {
    openstreetmap: "OpenStreetMap",
    fallback_cache: "Offline fallback",
    verified_cache: "Verified cache",
    verified_ai: "AI verified",
    curated_fallback: "Curated Fallback",
    maps: "Maps",
  };
  return labels[source] || source;
}

export function cleanNotes(notes = []) {
  return notes.filter((note) => {
    const lower = String(note).toLowerCase();
    return !lower.includes("llm destination insight") && !lower.includes("provider") && !lower.includes("debug");
  });
}
