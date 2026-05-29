const styles = {
  error: "border-red-300/30 bg-red-500/10 text-red-100",
  warning: "border-amber-300/30 bg-amber-500/10 text-amber-100",
  success: "border-emerald-300/30 bg-emerald-500/10 text-emerald-100",
  info: "border-sky-300/30 bg-sky-500/10 text-sky-100",
};

export default function Alert({ type = "info", children }) {
  if (!children) return null;
  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${styles[type] || styles.info}`}>
      {children}
    </div>
  );
}
