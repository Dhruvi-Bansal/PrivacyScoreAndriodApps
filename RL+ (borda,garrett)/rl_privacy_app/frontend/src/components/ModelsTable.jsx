import { pct } from "../api.js";

export default function ModelsTable({ categories }) {
  if (!categories.length) return null;
  return (
    <section id="models" className="mx-auto mt-16 max-w-6xl scroll-mt-20 px-4">
      <h2 className="text-2xl font-bold tracking-tight text-slate-900">Category models</h2>
      <p className="mt-1 text-slate-600">Results on each category's held-out test set.</p>
      <div className="card mt-6 overflow-x-auto">
        <table className="w-full min-w-[420px] text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              {["Category", "Precision", "Accuracy", "Recall"].map((h) => (
                <th key={h} className="whitespace-nowrap px-5 py-3 font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {categories.map((c) => (
              <tr key={c.key} className="hover:bg-slate-50/60">
                <td className="px-5 py-3 font-medium text-slate-900">{c.label}</td>
                <td className="px-5 py-3 font-semibold text-slate-900">{pct(c.test_metrics.Precision)}</td>
                <td className="px-5 py-3 text-slate-600">{pct(c.test_metrics.Accuracy)}</td>
                <td className="px-5 py-3 text-slate-600">{pct(c.test_metrics.Recall)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
