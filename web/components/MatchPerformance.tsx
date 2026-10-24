import { PlayerLink } from "@/components/PlayerLink";
import type { FixtureDocument, FixturePerformancePlayer } from "@/lib/data";
import { formatDecimal, formatInteger } from "@/lib/format";

const SOURCE_LABELS: Record<string, string> = {
  api_football: "API-Football",
  football_data_uk: "football-data.co.uk",
};

function output(player: FixturePerformancePlayer): string {
  const parts = [
    player.goals ? `${formatInteger(player.goals)}G` : null,
    player.assists ? `${formatInteger(player.assists)}A` : null,
    player.shots_on !== null && player.shots_on !== undefined
      ? `${formatInteger(player.shots_on)} SoT`
      : null,
  ].filter(Boolean);
  return parts.length ? parts.join(" · ") : "no scoring output";
}

function plural(value: number, singular: string): string {
  return `${formatInteger(value)} ${singular}${value === 1 ? "" : "s"}`;
}

function PlayerLine({ player }: { player: FixturePerformancePlayer }) {
  return (
    <li>
      <PlayerLink name={player.player_name ?? "Unknown"} href={player.href ?? null} />{" "}
      {player.rating !== null && player.rating !== undefined ? (
        <>
          <span className="badge badge-neutral">
            rating {formatDecimal(player.rating, 1)}
          </span>{" "}
        </>
      ) : null}
      <span className="muted">
        {output(player)} · {formatInteger(player.minutes ?? 0)} mins
        {player.pass_accuracy !== null &&
        player.pass_accuracy !== undefined &&
        player.passes_total !== null &&
        player.passes_total !== undefined
          ? ` · ${formatInteger(player.pass_accuracy)}/${formatInteger(player.passes_total)} passes`
          : player.passes_total !== null && player.passes_total !== undefined
            ? ` · ${plural(player.passes_total, "pass")}`
            : ""}
        {player.tackles !== null && player.tackles !== undefined
          ? ` · ${plural(player.tackles, "tackle")}`
          : ""}
        {player.duels_won !== null && player.duels_won !== undefined
          ? ` · ${plural(player.duels_won, "duel")}`
          : ""}
      </span>
    </li>
  );
}

export function MatchPerformance({
  performance,
  home,
  away,
  aberdeenIsHome,
}: {
  performance: FixtureDocument["performance"];
  home: string;
  away: string;
  aberdeenIsHome: boolean;
}) {
  if (!performance?.available) {
    return (
      <section className="card" data-contract="match.performance">
        <div className="section-head">
          <div>
            <p className="eyebrow">Performance</p>
            <h2>Players who played well and what worked</h2>
          </div>
        </div>
        <p className="fine-print">
          Player ratings and the selected team comparison are unavailable for this
          fixture. The lineup, event record and match stats remain on the page.
        </p>
      </section>
    );
  }
  const opponentName = aberdeenIsHome ? away : home;
  const basisLabel = (basis: string) =>
    basis === "provider_rating" ? "Provider rating" : "Measured output";
  return (
    <section
      className="card"
      data-contract="match.performance"
      data-team-split="aberdeen-opponent"
    >
      <div className="section-head">
        <div>
          <p className="eyebrow">Performance</p>
          <h2>Players who played well and what worked</h2>
        </div>
        <span className="badge badge-neutral">Not a verdict</span>
      </div>

      <div className="grid two-col">
        <section className="mini-block">
          <p className="eyebrow">Aberdeen · {basisLabel(performance.aberdeen.basis)}</p>
          {performance.aberdeen.players.length ? (
            <ul className="plain-list">
              {performance.aberdeen.players.map((player, index) => (
                <PlayerLine
                  key={`${player.player_id ?? index}-aberdeen`}
                  player={player}
                />
              ))}
            </ul>
          ) : (
            <p className="muted">No Aberdeen player has a measured output row.</p>
          )}
        </section>
        <section className="mini-block">
          <p className="eyebrow">
            {opponentName} · {basisLabel(performance.opponent.basis)}
          </p>
          {performance.opponent.players.length ? (
            <ul className="plain-list">
              {performance.opponent.players.map((player, index) => (
                <PlayerLine
                  key={`${player.player_id ?? index}-opponent`}
                  player={player}
                />
              ))}
            </ul>
          ) : (
            <p className="muted">No opposition player has a measured output row.</p>
          )}
        </section>
      </div>

      <div className="section-head section-head-spaced">
        <div>
          <p className="eyebrow">What worked</p>
          <h3>Measured team strengths</h3>
        </div>
      </div>
      {performance.strengths.length ? (
        <ul className="plain-list">
          {performance.strengths.map((strength) => {
            const display = (value: number) =>
              strength.unit === "%"
                ? formatDecimal(value, 1)
                : formatInteger(value);
            return (
              <li key={strength.key}>
                <span>
                  {strength.label}: Aberdeen {display(strength.aberdeen)}
                  {strength.unit} · {opponentName} {display(strength.opponent)}
                  {strength.unit}
                </span>{" "}
                <span className="muted">
                  ·{" "}
                  {SOURCE_LABELS[strength.source ?? ""] ??
                    strength.source ??
                    "source unavailable"}
                </span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="fine-print">
          Aberdeen were not higher in any of the selected measured categories
          (shots, shots on target, shots inside the box, possession, pass accuracy).
        </p>
      )}
      <p className="fine-print">{performance.note}</p>
    </section>
  );
}
