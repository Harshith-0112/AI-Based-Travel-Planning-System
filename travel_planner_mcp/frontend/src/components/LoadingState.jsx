export default function LoadingState({ title = "Planning your trip", subtitle = "Agents are checking hotels, places, routes, and budget." }) {
  return (
    <div className="grid min-h-[70vh] place-items-center px-4">
      <div className="glass-card max-w-md p-8 text-center">
        <div className="mx-auto h-16 w-16 animate-spin rounded-full border-4 border-teal-200/20 border-t-teal-200" />
        <h2 className="mt-6 text-2xl font-black text-white">{title}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}
