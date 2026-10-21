import Link from "next/link";
import { getManifest } from "@/lib/data";

export const metadata = { title: "Scouting · fitba" };

const POSITION_GROUPS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"];
const POOL = [
  "Scotland — all four tiers",
  "England — Championship, League One",
  "Netherlands, Belgium, Portugal, Switzerland, Austria",
  "Denmark, Norway, Sweden, Finland, Iceland",
  "Poland, Czechia, Slovakia, Hungary, Slovenia, Croatia, Serbia, Romania, Bulgaria, Albania",
  "Greece, Türkiye, Ukraine, Russia",
  "Ireland, Northern Ireland",
];

export default function ScoutingPage() {
  const manifest = getManifest();
  const coverage = manifest?.coverage.competitions ?? [];
  return (
    <>
      <section className="page-head">
        <p className="eyebrow">Recruitment</p>
        <h1>Players who fit Aberdeen</h1>
        <p className="lede">
          A position-aware, explainable shortlist — not a list of the biggest numbers.
          Quality, style, squad need, budget, age, reliability and availability are scored
          separately so you can see why a player ranks where they do.
        </p>
        <span className="badge badge-warn">Method published · player data not yet published</span>
      </section>

      <div className="grid three-col">
        <section className="card">
          <p className="eyebrow">01 · Quality</p>
          <h2>League-adjusted percentiles</h2>
          <p>
            Per-90 metrics are winsorised, robustly standardised within league and position,
            shrunk toward the positional mean by effective minutes, then adjusted for league
            strength. Raw and adjusted percentiles are shown side by side.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">02 · Style</p>
          <h2>Aberdeen&apos;s style vector</h2>
          <p>
            Possession, directness, pressing, line height, width, tempo, crossing, build-up
            and transition. The target is 60% current style and 40% the analyst&apos;s intent,
            with similarity reported on a 0–100 scale.
          </p>
        </section>
        <section className="card">
          <p className="eyebrow">03 · Fit</p>
          <h2>Budget, need and reliability</h2>
          <p>
            Fit combines 32% quality, 18% style, 16% squad need, 12% budget, 10% age, 7%
            reliability and 5% availability. Known unknowns lower confidence; they never
            silently become zero.
          </p>
        </section>
      </div>

      <div className="grid two-col">
        <section className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Universe</p>
              <h2>Where we look</h2>
            </div>
          </div>
          <ul className="plain-list">
            {POOL.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <p className="fine-print">
            Fringe markets are included because Aberdeen have recruited there. Coverage is
            labelled per league; a value-only league is never compared as if it had event data.
          </p>
        </section>

        <section className="card">
          <div className="card-head">
            <div>
              <p className="eyebrow">Position groups</p>
              <h2>Role-aware scoring</h2>
            </div>
          </div>
          <div className="pill-row">
            {POSITION_GROUPS.map((group) => (
              <span className="pill" key={group}>
                {group}
              </span>
            ))}
          </div>
          <p>
            Each group has a separate feature registry and signed weights. Missing features
            are removed and the remaining weights renormalised; if more than 40% of the
            weight is missing, the player is not ranked.
          </p>
        </section>
      </div>

      <section className="card">
        <div className="card-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What the current data can support</h2>
          </div>
        </div>
        <div className="table-wrap">
          <table className="league-table compact">
            <thead>
              <tr>
                <th>Competition</th>
                <th className="num">Matches</th>
                <th className="num">Expected</th>
                <th>Data depth</th>
                <th className="num">Event matches</th>
              </tr>
            </thead>
            <tbody>
              {coverage.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td className="num">{row.matches}</td>
                  <td className="num">{row.expected_matches}</td>
                  <td>{row.coverage}</td>
                  <td className="num">{row.events}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine-print">
          The results foundation is live. Player percentiles arrive with the verified event
          layer; until then this page deliberately shows no rankings.
        </p>
        <Link className="text-link" href="/methodology/">
          Read the method and source policy →
        </Link>
      </section>
    </>
  );
}
