import { pct } from "../api.js";

export default function Hero({ categories }) {
  const precisions = categories.map((c) => c.test_metrics.Precision);
  const [lo, hi] = [pct(Math.min(...precisions), 0), pct(Math.max(...precisions), 0)];
  const range = !precisions.length ? "—" : lo === hi ? lo : `${lo}–${hi}`;
  const stats = [
    { value: categories.length || 6, label: "category models" },
    { value: range, label: "test precision" },
    { value: "12", label: "permission groups per app" },
  ];
  return (
    <section className="relative overflow-hidden bg-gradient-to-br from-brand-900 via-brand-800 to-indigo-700 pb-28 pt-16 text-white">
      <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-500/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 left-10 h-80 w-80 rounded-full bg-indigo-400/20 blur-3xl" />
      <div className="relative mx-auto max-w-6xl px-4">
        <p className="chip bg-white/10 text-brand-100 ring-1 ring-white/20">Reinforcement learning · Borda–Garrett weights</p>
        <h1 className="mt-5 max-w-3xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl">
          Know what an Android app is asking for — before you install it.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-brand-100">
          Paste a Google Play link or enter the app details. PermiSense tells you whether the app looks malicious and
          which permissions to allow or deny, using a model trained for the app's category.
        </p>
        <dl className="mt-10 grid max-w-xl grid-cols-3 gap-6">
          {stats.map((s) => (
            <div key={s.label}>
              <dt className="text-2xl font-bold sm:text-3xl">{s.value}</dt>
              <dd className="mt-1 text-xs uppercase tracking-wide text-brand-200">{s.label}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
