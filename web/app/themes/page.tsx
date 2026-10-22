import Link from "next/link";
import { ThemeCard } from "@/components/ThemeCard";
import { ThemeMetrics } from "@/components/ThemeMetrics";
import { formatDate, getThemes } from "@/lib/data";

export const metadata = { title: "The bigger picture · fitba" };

export default function ThemesPage() {
  const data = getThemes();
  if (!data) {
    return (
      <section className="empty-state">
        <h1>No theme layer published</h1>
        <p>
          Run <code>uv run fitba publish</code> to build the themes from the
          local match, squad and history data.
        </p>
        <p>
          The next-match view is on <Link href="/matchday/">Matchday</Link>.
        </p>
      </section>
    );
  }

  const seasonThemes = data.themes.filter((theme) => theme.horizon === "season");
  const mission = data.themes.find((theme) => theme.horizon === "mission");

  return (
    <>
      <section className="page-head">
        <p className="eyebrow">The bridge · on-field, squad and recruitment</p>
        <h1>The bigger picture</h1>
        <p className="lede">
          The matchday page answers the next game. This page is the backdrop:
          the role-family balance, the shape trade-off, the defensive cover
          question, the attack-defence balance, and the trading-club mission
          behind them. It is where the fan argument and the backroom's day job
          meet the evidence.
        </p>
        <div className="hero-actions">
          <span className="badge badge-neutral">
            {data.scope.season_weight}% season · {data.scope.mission_weight}% mission
          </span>
          <Link className="button button-ghost" href="/matchday/">
            Next matchday
          </Link>
          <Link className="button button-ghost" href="/squad/">
            Squad
          </Link>
          <Link className="button button-ghost" href="/transfers/">
            Transfers
          </Link>
          <Link className="button button-ghost" href="/history/">
            The Cormack era
          </Link>
        </div>
        <p className="fine-print">
          Generated {formatDate(String(data.generated_at).slice(0, 10))} · state{" "}
          {data.state}. {data.scope.note}
        </p>
      </section>

      {data.state !== "fresh" ? (
        <p className="stale-banner">
          {data.state === "stale"
            ? "This theme layer is carried forward from an earlier publish."
            : data.state === "partial"
              ? "Some theme layers are partial; the missing pieces are labelled."
              : "The theme layer is unavailable for this publish."}
          {data.stale_reason ? ` ${data.stale_reason.replaceAll("_", " ")}.` : ""}
        </p>
      ) : null}

      <section className="card theme-howto">
        <div className="section-head">
          <div>
            <p className="eyebrow">How to read this</p>
            <h2>Measured, inferred, curated, unknown</h2>
          </div>
          <span className="badge badge-neutral">Not a verdict</span>
        </div>
        <div className="grid two-col">
          <ul className="plain-list">
            <li>
              <strong>Measured:</strong> starts, minutes, goals, shots, provider
              ratings and the shape/result record.
            </li>
            <li>
              <strong>Inferred:</strong> the role-family read, the shape
              association and the attack-defence balance.
            </li>
            <li>
              <strong>Curated:</strong> the Cormack-era mission pillars and the
              Tobers recovery note.
            </li>
            <li>
              <strong>Unknown:</strong> availability without a verified team-news
              entry, xG, channel location, possession and mid-game shape.
            </li>
          </ul>
          <ul className="plain-list">
            <li>
              Provider ratings are a measured input, not a fitba rating. They are
              Premiership-only, minutes-weighted and not position-adjusted.
            </li>
            <li>
              A family mean can hide a high-variance unit; the 25th percentile
              and the shape split are shown for that reason.
            </li>
            <li>
              “Trust” is not measured. The minutes pattern is consistent with
              limited rotation; the data cannot distinguish selection from
              availability.
            </li>
            <li>
              No blame narrative and no claim about the manager's private
              intent. The read is the evidence, stated plainly.
            </li>
          </ul>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <div>
            <p className="eyebrow">80% · the current season</p>
            <h2>The four season themes</h2>
          </div>
          <span className="badge badge-neutral">{seasonThemes.length} themes</span>
        </div>
        <div className="theme-stack">
          {seasonThemes.map((theme) => (
            <div className="theme-block" key={theme.theme_id}>
              <ThemeCard theme={theme} />
              <div className="card theme-metrics">
                <ThemeMetrics theme={theme} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {mission ? (
        <section className="mission-band">
          <div className="section-head">
            <div>
              <p className="eyebrow">20% · the longer mission</p>
              <h2>The chairman's trade-off</h2>
            </div>
            <span className="badge badge-warn">Cormack-era context</span>
          </div>
          <ThemeCard theme={mission} />
          <div className="card theme-metrics">
            <ThemeMetrics theme={mission} />
          </div>
        </section>
      ) : null}

      <section className="card coverage-card">
        <div className="section-head">
          <div>
            <p className="eyebrow">Coverage</p>
            <h2>What is measured and what is not</h2>
          </div>
          <span className="badge badge-neutral">{data.coverage.status}</span>
        </div>
        <div className="stat-row four">
          <div className="stat-tile">
            <span className="stat-label">Fixtures</span>
            <span className="stat-value">{data.coverage.fixtures_total ?? "—"}</span>
            <span className="stat-note">
              {data.coverage.fixtures_with_ratings ?? "—"} with ratings
            </span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Starts mapped</span>
            <span className="stat-value">
              {data.coverage.starts_with_role ?? "—"}/
              {data.coverage.starts_total ?? "—"}
            </span>
            <span className="stat-note">
              {data.coverage.role_start_coverage === null ||
              data.coverage.role_start_coverage === undefined
                ? "—"
                : `${Math.round(data.coverage.role_start_coverage * 100)}% role coverage`}
            </span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Rated minutes</span>
            <span className="stat-value">
              {data.coverage.provider_rating_minutes ?? "—"}
            </span>
            <span className="stat-note">
              {data.coverage.provider_rating_rows ?? "—"} player-match rows
            </span>
          </div>
          <div className="stat-tile">
            <span className="stat-label">Missing</span>
            <span className="stat-value">4</span>
            <span className="stat-note">
              xG · channels · availability · mid-game shape
            </span>
          </div>
        </div>
        <p className="fine-print">{data.coverage.note}</p>
        <p className="fine-print">
          Role basis: {data.coverage.role_basis}. Ratings:{" "}
          {data.coverage.provider_ratings}. Bench: {data.coverage.bench ?? "—"}.
        </p>
        <p className="fine-print">{data.notes}</p>
        <p className="back-link">
          <Link href="/matchday/">Next matchday</Link>
          {" · "}
          <Link href="/squad/">Squad</Link>
          {" · "}
          <Link href="/transfers/">Transfers</Link>
          {" · "}
          <Link href="/recruitment/">Recruitment</Link>
          {" · "}
          <Link href="/history/">The Cormack era</Link>
          {" · "}
          <Link href="/methodology/">Method</Link>
          {" · "}
          <Link href="/sources/">Sources</Link>
        </p>
      </section>
    </>
  );
}
