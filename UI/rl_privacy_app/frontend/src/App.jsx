import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Navbar from "./components/Navbar.jsx";
import Hero from "./components/Hero.jsx";
import Analyzer from "./components/Analyzer.jsx";
import Results from "./components/Results.jsx";
import HowItWorks from "./components/HowItWorks.jsx";
import ModelsTable from "./components/ModelsTable.jsx";
import Footer from "./components/Footer.jsx";

export default function App() {
  const [categories, setCategories] = useState([]);
  const [catalog, setCatalog] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [response, setResponse] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const resultsRef = useRef(null);

  useEffect(() => {
    Promise.all([api.categories(), api.permissions()])
      .then(([cats, perms]) => { setCategories(cats); setCatalog(perms.sections); })
      .catch((e) => setLoadError(e.message));
  }, []);

  // Bring a new result into view once it has rendered.
  useEffect(() => {
    if (response?.result) resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [response]);

  async function run(task) {
    setBusy(true); setError("");
    try {
      setResponse(await task());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Hero categories={categories} />
        <section id="analyze" className="mx-auto max-w-6xl px-4 -mt-16 relative z-10">
          {loadError ? (
            <div className="card p-6 text-sm text-red-700">
              Could not reach the API: {loadError}. Start the backend (see README) and reload the page.
            </div>
          ) : (
            <Analyzer
              categories={categories}
              catalog={catalog}
              busy={busy}
              error={error}
              onAnalyze={(app) => run(() => api.analyze(app))}
              onAnalyzeUrl={(url, category) => run(() => api.analyzeUrl(url, category))}
              pending={response && !response.result ? response : null}
            />
          )}
        </section>
        <div ref={resultsRef} className="scroll-mt-20">
          {response?.result && <Results response={response} />}
        </div>
        <HowItWorks />
        <ModelsTable categories={categories} />
      </main>
      <Footer />
    </div>
  );
}
