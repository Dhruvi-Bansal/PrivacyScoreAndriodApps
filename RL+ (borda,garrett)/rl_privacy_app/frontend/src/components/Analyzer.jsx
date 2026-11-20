import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";

const TABS = [
  { id: "link", label: "Google Play link" },
  { id: "manual", label: "Enter details" },
  { id: "examples", label: "Try an example" },
];

function Spinner() {
  return <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />;
}

function ErrorBox({ children }) {
  return <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{children}</div>;
}

function CategorySelect({ categories, value, onChange, placeholder = "Select a category" }) {
  return (
    <select className="input" value={value} onChange={(e) => onChange(e.target.value)} required>
      <option value="">{placeholder}</option>
      {categories.map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
    </select>
  );
}

function LinkForm({ categories, busy, onAnalyzeUrl, pending }) {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("");
  return (
    <form onSubmit={(e) => { e.preventDefault(); onAnalyzeUrl(url, category || null); }}>
      <label className="label" htmlFor="url">Google Play link or package id</label>
      <div className="flex flex-col gap-3 sm:flex-row">
        <input id="url" className="input flex-1" placeholder="https://play.google.com/store/apps/details?id=com.example.app"
               value={url} onChange={(e) => setUrl(e.target.value)} required />
        <button className="btn-primary sm:w-40" disabled={busy || !url.trim()}>{busy ? <Spinner /> : null}Analyze</button>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        The app's title, description, genre, rating, price and permissions are read from Google Play. Live permission labels are
        matched to the training dataset, so results for new apps are an estimate.
      </p>
      {pending && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p>{pending.message}</p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <CategorySelect categories={categories} value={category} onChange={setCategory} />
            <button type="button" className="btn-primary sm:w-48" disabled={!category || busy}
                    onClick={() => onAnalyzeUrl(url, category)}>Analyze with category</button>
          </div>
        </div>
      )}
    </form>
  );
}

function ManualForm({ categories, catalog, busy, onAnalyze }) {
  const [form, setForm] = useState({ category: "", genre: "", app_name: "", package: "", description: "",
                                     rating: "", num_ratings: "", price: "0" });
  const [groups, setGroups] = useState([]);
  const [exact, setExact] = useState([]);
  const [showExact, setShowExact] = useState(false);
  const [query, setQuery] = useState("");
  const cat = categories.find((c) => c.key === form.category);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  useEffect(() => { if (cat) setForm((f) => ({ ...f, genre: cat.genres[0] })); }, [form.category]);

  const filtered = useMemo(() => {
    if (!catalog) return [];
    const q = query.trim().toLowerCase();
    return Object.entries(catalog)
      .map(([section, items]) => [section, items.filter((i) => !q || `${section} ${i.label}`.toLowerCase().includes(q))])
      .filter(([, items]) => items.length);
  }, [catalog, query]);

  const toggle = (list, setList, v) => setList(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const groupList = cat ? cat.permissions.map((p) => p.name) : categories[0]?.permissions.map((p) => p.name) || [];

  function submit(e) {
    e.preventDefault();
    onAnalyze({ ...form, rating: +form.rating || 0, num_ratings: +form.num_ratings || 0, price: +form.price || 0,
                permission_groups: groups, permissions: exact });
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label">Category *</label>
          <CategorySelect categories={categories} value={form.category} onChange={(v) => setForm({ ...form, category: v })} />
        </div>
        <div>
          <label className="label">Genre</label>
          <select className="input" value={form.genre} onChange={set("genre")} disabled={!cat}>
            {(cat?.genres || []).map((g) => <option key={g}>{g}</option>)}
          </select>
        </div>
        <div>
          <label className="label">App name</label>
          <input className="input" value={form.app_name} onChange={set("app_name")} placeholder="e.g. Quick Notes PDF" />
        </div>
        <div>
          <label className="label">Package name</label>
          <input className="input" value={form.package} onChange={set("package")} placeholder="com.example.notes" />
        </div>
        <div className="sm:col-span-2">
          <label className="label">Description</label>
          <textarea className="input min-h-[96px]" value={form.description} onChange={set("description")}
                    placeholder="Paste the store description – it is one of the strongest signals for the model." />
        </div>
        <div className="grid grid-cols-3 gap-3 sm:col-span-2">
          <div>
            <label className="label">Rating (0–5)</label>
            <input className="input" type="number" min="0" max="5" step="0.1" value={form.rating} onChange={set("rating")} />
          </div>
          <div>
            <label className="label">Number of ratings</label>
            <input className="input" type="number" min="0" value={form.num_ratings} onChange={set("num_ratings")} />
          </div>
          <div>
            <label className="label">Price (USD)</label>
            <input className="input" type="number" min="0" step="0.01" value={form.price} onChange={set("price")} />
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-end justify-between">
          <div>
            <p className="label mb-0">Requested permissions</p>
            <p className="text-xs text-slate-500">Select every permission group the app asks for.</p>
          </div>
          <span className="text-xs text-slate-500">{groups.length + exact.length} selected</span>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {groupList.map((g) => (
            <button type="button" key={g} onClick={() => toggle(groups, setGroups, g)}
                    className={`rounded-lg border px-3 py-2 text-left text-sm font-medium transition ${
                      groups.includes(g) ? "border-brand-500 bg-brand-50 text-brand-800 ring-2 ring-brand-100"
                                         : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"}`}>
              {g}
            </button>
          ))}
        </div>
        <button type="button" className="mt-3 text-sm font-semibold text-brand-700 hover:underline"
                onClick={() => setShowExact(!showExact)}>
          {showExact ? "Hide" : "Add"} exact Android permissions (optional, more accurate)
        </button>
        {showExact && (
          <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3">
            <input className="input" placeholder="Search permissions, e.g. SMS, contacts, boot…" value={query}
                   onChange={(e) => setQuery(e.target.value)} />
            <div className="mt-3 max-h-72 space-y-3 overflow-y-auto pr-1">
              {filtered.map(([section, items]) => (
                <div key={section}>
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{section}</p>
                  <div className="mt-1 grid gap-1 sm:grid-cols-2">
                    {items.map((i) => (
                      <label key={i.id} className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1 text-sm hover:bg-white">
                        <input type="checkbox" className="mt-0.5 accent-brand-600" checked={exact.includes(i.id)}
                               onChange={() => toggle(exact, setExact, i.id)} />
                        <span>{i.label}{i.group && <span className="ml-1 text-xs text-brand-700">({i.group})</span>}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      <div className="flex justify-end">
        <button className="btn-primary w-full sm:w-48" disabled={busy || !form.category}>{busy ? <Spinner /> : null}Analyze app</button>
      </div>
    </form>
  );
}

function Examples({ categories, busy, onAnalyze }) {
  const [key, setKey] = useState("");
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  useEffect(() => { if (!key && categories.length) setKey(categories[0].key); }, [categories]);
  useEffect(() => {
    if (!key) return;
    api.examples(key).then(setItems).catch((e) => setErr(e.message));
  }, [key]);
  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-600">Real apps from each category's held-out test set, with their true label.</p>
        <div className="sm:w-64"><CategorySelect categories={categories} value={key} onChange={setKey} /></div>
      </div>
      {err && <ErrorBox>{err}</ErrorBox>}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {items.map((ex, i) => (
          <button key={i} disabled={busy} onClick={() => onAnalyze(ex)}
                  className="group rounded-xl border border-slate-200 bg-white p-4 text-left transition hover:border-brand-400 hover:shadow-card">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-semibold text-slate-900 group-hover:text-brand-700">{ex.app_name}</p>
                <p className="truncate text-xs text-slate-500">{ex.genre} · {ex.permissions.length} permissions</p>
              </div>
              <span className={`chip shrink-0 ${ex.true_label ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
                {ex.true_label ? "Labelled malicious" : "Labelled benign"}
              </span>
            </div>
            <p className="mt-2 line-clamp-2 text-xs text-slate-500">
              {ex.description ? ex.description.replace(/<[^>]+>/g, " ") : "No description"}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function Analyzer({ categories, catalog, busy, error, onAnalyze, onAnalyzeUrl, pending }) {
  const [tab, setTab] = useState("link");
  return (
    <div className="card overflow-hidden">
      <div className="flex border-b border-slate-200 bg-slate-50/60 px-2 sm:px-4">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
                  className={`-mb-px border-b-2 px-3 py-4 text-sm font-semibold transition sm:px-5 ${
                    tab === t.id ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="p-5 sm:p-8">
        {tab === "link" && <LinkForm categories={categories} busy={busy} onAnalyzeUrl={onAnalyzeUrl} pending={pending} />}
        {tab === "manual" && <ManualForm categories={categories} catalog={catalog} busy={busy} onAnalyze={onAnalyze} />}
        {tab === "examples" && <Examples categories={categories} busy={busy} onAnalyze={onAnalyze} />}
        {error && <ErrorBox>{error}</ErrorBox>}
      </div>
    </div>
  );
}
