import { pct } from "../api.js";
import { PERMISSION_INFO } from "../permissions.js";

function reason(step) {
  if (step.decision === "deny") {
    if (step.rules_completed.length) {
      const combo = step.rules_completed_permissions[0] || [];
      return `Would complete a risky combination with ${combo.filter((p) => p !== step.permission).join(" + ")}`;
    }
    if (step.reward_deny > step.reward_allow) return "Risk is higher than the benefit for this app";
    return "Policy learned to deny this in similar apps";
  }
  if (step.utility >= 0.5) return "Commonly needed by safe apps in this category";
  if (step.reward_allow >= step.reward_deny) return "Benefit outweighs the risk for this app";
  return "Policy learned to allow this in similar apps";
}

function ScoreBar({ score, threshold }) {
  return (
    <div>
      <div className="relative h-3 rounded-full bg-gradient-to-r from-emerald-400 via-amber-300 to-red-500">
        <div className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-white bg-slate-900 shadow"
             style={{ left: `${Math.min(100, Math.max(0, score * 100))}%` }} />
        <div className="absolute -top-1.5 h-6 w-0.5 bg-slate-900/70" style={{ left: `${threshold * 100}%` }} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-500">
        <span>0 · safe</span>
        <span>threshold {threshold.toFixed(2)}</span>
        <span>1 · risky</span>
      </div>
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  );
}

// How much the recommended denials cut the data the app can reach (Data access, 0-100).
function accessReduction(r) {
  const { all_allowed: before, score: after } = r.data_access;
  const n = r.denied.length;
  if (!before) return { value: "0%", hint: "the app requests none of the 12 controlled permissions" };
  if (!n) return { value: "0%", hint: "every requested permission is needed" };
  const cut = (before - after) / before;
  return { value: `${Math.round(cut * 100)}%`,
           hint: `${Math.round(before)} → ${Math.round(after)} · ${n} permission${n > 1 ? "s" : ""} denied` };
}

export default function Results({ response }) {
  const { result: r, input, store } = response;
  const bad = r.verdict === "malicious";
  return (
    <section className="mx-auto mt-10 max-w-6xl space-y-6 px-4">
      <div className={`card overflow-hidden border-2 ${bad ? "border-red-200" : "border-emerald-200"}`}>
        <div className={`flex flex-col gap-6 p-6 sm:flex-row sm:items-center sm:p-8 ${bad ? "bg-red-50/60" : "bg-emerald-50/60"}`}>
          {store?.icon ? <img src={store.icon} alt="" className="h-20 w-20 rounded-2xl shadow" />
            : <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-white text-3xl font-bold text-slate-400 shadow">
                {(input.app_name || "?").slice(0, 1).toUpperCase()}</div>}
          <div className="min-w-0 flex-1">
            <p className="text-sm text-slate-500">{r.category}{input.genre ? ` · ${input.genre}` : ""}{store?.developer ? ` · ${store.developer}` : ""}</p>
            <h2 className="truncate text-2xl font-bold text-slate-900">{input.app_name || input.package || "Unnamed app"}</h2>
            {store?.url && <a href={store.url} target="_blank" rel="noreferrer" className="text-sm text-brand-700 hover:underline">View on Google Play ↗</a>}
          </div>
          <div className="text-left sm:text-right">
            <span className={`chip px-4 py-1.5 text-sm ${bad ? "bg-red-600 text-white" : "bg-emerald-600 text-white"}`}>
              {bad ? "⚠ Likely malicious" : "✓ Likely safe"}
            </span>
            <p className="mt-2 text-xs text-slate-500">Privacy score {r.privacy_score.toFixed(3)} vs threshold {r.threshold.toFixed(2)}</p>
          </div>
        </div>
        <div className="space-y-6 p-6 sm:p-8">
          <ScoreBar score={r.privacy_score} threshold={r.threshold} />
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Malicious probability" value={pct(r.malicious_probability_all_allowed)} hint="if every permission is allowed" />
            <Stat label="Data access reduced by" {...accessReduction(r)} />
            <Stat label="Permissions" value={`${r.allowed.length} / ${r.decisions.length}`} hint="allowed / requested" />
          </div>
        </div>
      </div>

        <div className="card overflow-hidden">
          <div className="border-b border-slate-200 px-6 py-4">
            <h3 className="font-semibold text-slate-900">Permission recommendations</h3>
            <p className="text-sm text-slate-500">Decided step by step by the reinforcement-learning agent for this category.</p>
          </div>
          {r.decisions.length === 0 ? (
            <p className="p-6 text-sm text-slate-500">The app does not request any of the 12 permission groups the model controls.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {r.decisions.map((s) => (
                <li key={s.permission} className="flex items-start gap-4 px-6 py-4">
                  <span className={`chip mt-0.5 w-16 justify-center ${s.decision === "allow" ? "bg-emerald-100 text-emerald-800" : "bg-red-100 text-red-800"}`}>
                    {s.decision === "allow" ? "Allow" : "Deny"}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-slate-900">
                      {s.permission}
                      {PERMISSION_INFO[s.permission] && (
                        <span className="ml-2 text-sm font-normal text-slate-500">· {PERMISSION_INFO[s.permission]}</span>
                      )}
                    </p>
                    <p className="text-sm text-slate-600">{reason(s)}</p>
                    {s.raw_permissions.length > 0 && (
                      <p className="mt-1 truncate text-xs text-slate-400" title={s.raw_permissions.join("\n")}>
                        Covers: {s.raw_permissions.map((p) => p.split(" : ")[1]).join(", ")}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
    </section>
  );
}
