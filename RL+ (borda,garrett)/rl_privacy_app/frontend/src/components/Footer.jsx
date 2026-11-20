import { Logo } from "./Navbar.jsx";

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <Logo className="h-6 w-6" />
          <span className="font-semibold text-slate-700">PermiSense</span>
          <span>· Research prototype</span>
        </div>
        <p className="max-w-xl sm:text-right">
          Predictions come from models trained on a historical Android permission dataset and are guidance only, not a
          security guarantee.
        </p>
      </div>
    </footer>
  );
}
