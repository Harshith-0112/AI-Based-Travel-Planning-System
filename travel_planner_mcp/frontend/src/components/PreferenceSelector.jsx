const preferences = [
  "nature",
  "food",
  "shopping",
  "adventure",
  "history",
  "temples",
  "beaches",
  "nightlife",
  "family",
  "relaxation",
];

export default function PreferenceSelector({ value, onChange }) {
  function togglePreference(preference) {
    if (value.includes(preference)) {
      onChange(value.filter((item) => item !== preference));
    } else {
      onChange([...value, preference]);
    }
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {preferences.map((preference) => {
        const selected = value.includes(preference);
        return (
          <button
            key={preference}
            type="button"
            onClick={() => togglePreference(preference)}
            className={`rounded-2xl border px-4 py-3 text-sm font-bold capitalize transition hover:-translate-y-0.5 ${
              selected
                ? "border-teal-300/60 bg-teal-300/15 text-teal-100"
                : "border-white/10 bg-white/[0.05] text-slate-300 hover:bg-white/10"
            }`}
          >
            {preference}
          </button>
        );
      })}
    </div>
  );
}
