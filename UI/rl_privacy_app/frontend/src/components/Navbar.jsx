export function Logo({ className = "h-8 w-8" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#4459e3" />
      <path d="M16 6l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V9l8-3z" fill="#fff" />
      <path d="M12.5 16.2l2.4 2.4 4.8-5" stroke="#4459e3" strokeWidth="2.2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Navbar() {
  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-brand-900/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <a href="#" className="flex items-center gap-2.5">
          <Logo />
          <span className="text-lg font-bold tracking-tight text-white">PermiSense</span>
        </a>
        <nav className="flex items-center gap-1 text-sm font-medium text-brand-100">
          <a href="#analyze" className="rounded-md px-3 py-2 hover:bg-white/10">Analyze</a>
          <a href="#how" className="hidden sm:block rounded-md px-3 py-2 hover:bg-white/10">How it works</a>
          <a href="#models" className="hidden sm:block rounded-md px-3 py-2 hover:bg-white/10">Models</a>
          <a href="/docs" className="rounded-md px-3 py-2 hover:bg-white/10">API</a>
        </nav>
      </div>
    </header>
  );
}
