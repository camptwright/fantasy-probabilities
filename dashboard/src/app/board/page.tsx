type Signal = {
  id: string;
  sport: string;
  market: string;
  selection: string;
  bookmaker: string;
  price_american: number | null;
  model_probability: number;
  fair_probability: number | null;
  implied_probability: number | null;
  ev_percent: number;
  matchup: string;
  game_time: string | null;
  game_status: string;
};

type Ranking = { team_id: string; team_name: string; rating: number };

const SPORTS = ["nfl", "ncaaf"] as const;

// Static generation happens during the image build, before the API and its
// database are available - same reasoning as the Fantasy page.
export const dynamic = "force-dynamic";

function apiUrl(): string {
  return process.env.FANTASY_API_URL || "http://api:8000";
}

async function signals(sport: string): Promise<Signal[]> {
  const res = await fetch(`${apiUrl()}/signals?sport=${sport}`, { cache: "no-store" });
  return res.ok ? res.json() : [];
}

async function rankings(sport: string): Promise<Ranking[]> {
  const res = await fetch(`${apiUrl()}/rankings/${sport}`, { cache: "no-store" });
  return res.ok ? res.json() : [];
}

function formatPrice(price: number | null): string {
  if (price === null) return "—";
  return price > 0 ? `+${price}` : `${price}`;
}

function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

export default async function BoardPage() {
  const [nflSignals, ncaafSignals, nflRankings, ncaafRankings] = await Promise.all([
    signals("nfl"),
    signals("ncaaf"),
    rankings("nfl"),
    rankings("ncaaf"),
  ]);

  return (
    <main className="mx-auto max-w-6xl p-8">
      <header className="mb-8">
        <p className="text-sm text-emerald-400">Elo baseline - not calibrated, not a claim of accuracy</p>
        <h1 className="text-4xl font-bold">Board</h1>
        <p className="mt-2 text-slate-400">
          Moneyline and spread signals from a transparent team-rating model, plus current
          rankings. Totals are omitted: a rating gap alone says nothing honest about total
          points.
        </p>
      </header>

      {SPORTS.map((sport) => {
        const sportSignals = sport === "nfl" ? nflSignals : ncaafSignals;
        const sportRankings = sport === "nfl" ? nflRankings : ncaafRankings;
        return (
          <section key={sport} className="mb-10">
            <h2 className="mb-3 text-2xl font-semibold uppercase">{sport}</h2>
            <div className="grid gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                {sportSignals.length === 0 ? (
                  <p className="rounded-lg border border-slate-700 p-6 text-slate-400">
                    No priced signals yet for {sport}.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-slate-700">
                    <table className="w-full min-w-[700px] text-left text-sm">
                      <thead className="border-b border-slate-700 text-xs uppercase text-slate-500">
                        <tr>
                          <th className="px-3 py-3">Matchup</th>
                          <th className="px-3 py-3">Selection</th>
                          <th className="px-3 py-3">Price</th>
                          <th className="px-3 py-3">Model</th>
                          <th className="px-3 py-3">Implied</th>
                          <th className="px-3 py-3">EV%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sportSignals.map((signal) => (
                          <tr key={signal.id} className="border-b border-slate-800 last:border-0">
                            <td className="px-3 py-3 text-slate-300">{signal.matchup}</td>
                            <td className="px-3 py-3 font-medium text-slate-100">{signal.selection}</td>
                            <td className="px-3 py-3 font-mono text-slate-300">{formatPrice(signal.price_american)}</td>
                            <td className="px-3 py-3 font-mono text-slate-300">{formatPercent(signal.model_probability)}</td>
                            <td className="px-3 py-3 font-mono text-slate-300">{formatPercent(signal.implied_probability)}</td>
                            <td className="px-3 py-3 font-mono text-emerald-400">{signal.ev_percent.toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-sm uppercase text-slate-500">Rankings</h3>
                {sportRankings.length === 0 ? (
                  <p className="rounded-lg border border-slate-700 p-4 text-sm text-slate-400">
                    No ratings yet.
                  </p>
                ) : (
                  <ol className="space-y-1 rounded-lg border border-slate-700 p-4 text-sm">
                    {sportRankings.slice(0, 15).map((team, index) => (
                      <li key={team.team_id} className="flex justify-between">
                        <span className="text-slate-300">
                          {index + 1}. {team.team_name}
                        </span>
                        <span className="font-mono text-slate-500">{team.rating.toFixed(0)}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </div>
          </section>
        );
      })}
    </main>
  );
}
