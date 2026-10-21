import { notFound } from "next/navigation";
import Link from "next/link";
import { FormStrip } from "@/components/FormStrip";
import { StatTile } from "@/components/StatTile";
import { formatDate, getAberdeen } from "@/lib/data";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ club: "aberdeen" }];
}

export const metadata = { title: "Aberdeen · fitba" };

function BarList({
  values,
  label,
}: {
  values: Record<string, number | string>;
  label: string;
}) {
  const entries = Object.entries(values).filter(
    ([key, value]) => key !== "notes" && typeof value === "number",
  ) as Array<[string, number]>;
  return (
    <div className="bar-list" aria-label={label}>
      {entries.map(([key, value]) => (
        <div className="bar-row" key={key}>
          <span className="bar-label">{key.replaceAll("_", " ")}</span>
          <span className="bar-track">
            <span className="bar-fill" style={{ width: `${Math.round(value * 100)}%` }} />
          </span>
          <span className="bar-value">{Math.round(value * 100)}</span>
        </div>
      ))}
    </div>
  );
}

export default async function ClubPage({ params }: { params: Promise<{ club: string }> }) {
  const { club } = await params;
  if (club !== "aberdeen") notFound();
  const data = getAberdeen();
  if (!data) notFound();
  const summary = data.summary;

  return (
    <>
      <section className="club-head">
        <div className="club-identity">
          <span className="club-roundel large">AFC</span>
          <div>
            <p className="eyebrow">
              {data.profile.city} · {data.profile.stadium}
            </p>
            <h1>{data.name}</h1>
            <p className="muted">
              {data.profile.nickname ? `${data.profile.nickname} · ` : ""}
              Founded {data.profile.founded ?? "—"} · Season {data.season}
            </p>
          </div>
        </div>
        <span className="badge badge-neutral">Coverage: {data.coverage}</span>
      </section>

      {summary ? (
        <section className="stat-row four">
          <StatTile
            label="League position"
            value={summary.position}
            note={summary.competition_name}
          />
          <StatTile
            label="Points"
            value={summary.points}
            note={summary.deduction > 0 ? `${summary.deduction} deducted` : `${summary.played} played`}
          />
          <StatTile
            label="Goals"
            value={`${summary.gf}–${summary.ga}`}
            note={`${summary.gd > 0 ? "+" : ""}${summary.gd} difference`}
          />
          <StatTile label="Form" value={<FormStrip form={summary.form} />} note="Most recent first" />
        </section>
      ) : null}

      <div className="grid two-col">
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Results</p>
              <h2>This season</h2>
            </div>
          </div>
          <ul className="match-list">
            {data.results.map((match) => (
              <li key={match.match_id}>
                <span className="match-date">{formatDate(match.date)}</span>
                <span className={`result-dot result-${match.result.toLowerCase()}`}>
                  {match.result}
                </span>
                <span className="match-venue">{match.venue}</span>
                <span className="match-opponent">{match.opponent_name}</span>
                <span className="match-score">
                  {match.goals_for}–{match.goals_against}
                </span>
              </li>
            ))}
          </ul>
        </section>

        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Trend</p>
              <h2>Season history</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table className="league-table compact">
              <thead>
                <tr>
                  <th>Season</th>
                  <th className="num">Pos</th>
                  <th className="num">Pld</th>
                  <th className="num">Pts</th>
                  <th className="num">GD</th>
                  <th>Form</th>
                </tr>
              </thead>
              <tbody>
                {data.history.map((row) => (
                  <tr key={row.season}>
                    <td>{row.season}</td>
                    <td className="num">{row.position}</td>
                    <td className="num">{row.played}</td>
                    <td className="num strong">{row.points}</td>
                    <td className="num">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                    <td>
                      <FormStrip form={row.form} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="grid two-col">
        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Recruitment model</p>
              <h2>Intended style</h2>
            </div>
            <span className="badge badge-neutral">Analyst-set</span>
          </div>
          <BarList values={data.style_intent} label="Aberdeen intended style, 0 to 100" />
          <p className="fine-print">{String(data.style_intent.notes ?? "")}</p>
        </section>

        <section className="card">
          <div className="section-head">
            <div>
              <p className="eyebrow">Recruitment model</p>
              <h2>Squad needs</h2>
            </div>
          </div>
          <BarList values={data.squad_needs} label="Aberdeen squad needs by position, 0 to 100" />
          <p className="fine-print">
            These weights feed the scouting fit score once player data is verified.
          </p>
        </section>
      </div>

      <section className="card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Budget</p>
            <h2>Fee-only until set</h2>
          </div>
          <span className="badge badge-warn">
            {data.budget.mode === "fee_only" ? "Fee-only" : data.budget.mode}
          </span>
        </div>
        <p>
          Transfer-fee ceiling:{" "}
          <strong>
            {data.budget.transfer_fee_ceiling_gbp
              ? `£${data.budget.transfer_fee_ceiling_gbp.toLocaleString("en-GB")}`
              : "not set"}
          </strong>
          . Wage ceiling:{" "}
          <strong>
            {data.budget.wage_ceiling_weekly_gbp
              ? `£${data.budget.wage_ceiling_weekly_gbp.toLocaleString("en-GB")}/week`
              : "not set — individual wages are not public"}
          </strong>
          . Age band: {data.budget.age_band[0]}–{data.budget.age_band[1]}.
        </p>
        <p className="fine-print">{data.budget.notes}</p>
      </section>

      <p className="back-link">
        <Link href="/scotland/premiership/">← Premiership table</Link>
      </p>
    </>
  );
}
