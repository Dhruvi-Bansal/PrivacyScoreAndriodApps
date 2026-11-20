const STEPS = [
  { n: "1", title: "Read the app", text: "Category, permissions, description, rating, price and package name come from Google Play or your input." },
  { n: "2", title: "Score the risk", text: "A category classifier estimates how suspicious the app is; Borda–Garrett weights rate each permission." },
  { n: "3", title: "Check combinations", text: "Statistically significant decision-tree rules flag risky permission combinations." },
  { n: "4", title: "Decide each permission", text: "A Q-learning agent allows or denies every permission, balancing usefulness against risk." },
];

export default function HowItWorks() {
  return (
    <section id="how" className="mx-auto mt-20 max-w-6xl scroll-mt-20 px-4">
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">How it works</h2>
      <p className="mt-1 text-slate-600">One model per app category, trained and validated on the Android permission dataset.</p>
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((s) => (
          <div key={s.n} className="card p-5">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 font-bold text-brand-700">{s.n}</span>
            <h3 className="mt-3 font-semibold text-slate-900">{s.title}</h3>
            <p className="mt-1 text-sm text-slate-600">{s.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
