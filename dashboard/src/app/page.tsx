import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <header className="mb-8">
        <p className="text-sm text-emerald-400">Fantasy Edge</p>
        <h1 className="text-4xl font-bold">Sports</h1>
      </header>
      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/fantasy"
          className="rounded-lg border border-slate-700 bg-slate-900 p-6 transition-colors hover:border-emerald-600"
        >
          <h2 className="text-xl font-semibold">Fantasy</h2>
          <p className="mt-2 text-sm text-slate-400">
            Sleeper multi-league workspace: lineup, waiver, matchup, and draft analysis.
          </p>
        </Link>
        <Link
          href="/board"
          className="rounded-lg border border-slate-700 bg-slate-900 p-6 transition-colors hover:border-emerald-600"
        >
          <h2 className="text-xl font-semibold">Board</h2>
          <p className="mt-2 text-sm text-slate-400">
            Moneyline and spread signals from a transparent Elo baseline, plus team rankings.
          </p>
        </Link>
      </div>
    </main>
  );
}
