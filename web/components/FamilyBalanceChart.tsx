import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { ThemeFamilyGroup } from "@/lib/data";

export function FamilyBalanceChart({
  groups,
  squadRating,
}: {
  groups: ThemeFamilyGroup[];
  squadRating: number | null;
}) {
  return (
    <div className="family-balance">
      <div className="section-head">
        <div>
          <p className="eyebrow">Provider match ratings · minutes-weighted</p>
          <h3>Role-family balance</h3>
        </div>
        <span className="badge badge-neutral">
          Squad mean {squadRating ?? "—"}
        </span>
      </div>
      <div className="family-bars">
        {groups.map((group) => {
          const width =
            group.provider_rating === null
              ? 0
              : Math.max(2, Math.min(100, (group.provider_rating / 10) * 100));
          return (
            <div className="family-row" key={group.family}>
              <span className="family-name">{group.family}</span>
              <span className="family-track">
                <span className="family-fill" style={{ width: `${width}%` }} />
              </span>
              <span className="family-value">
                {group.provider_rating ?? "—"}
              </span>
              <span className="family-meta">
                {group.starts} starts · {group.starter_minutes} min ·{" "}
                {group.rating_sample.minutes} rated min
              </span>
              <ConfidenceBadge confidence={group.confidence} compact />
            </div>
          );
        })}
      </div>
      <div className="table-wrap">
        <table className="league-table compact">
          <thead>
            <tr>
              <th>Family</th>
              <th className="num">Rating</th>
              <th className="num">Median</th>
              <th className="num">25th</th>
              <th className="num">vs squad</th>
              <th className="num">G</th>
              <th className="num">A</th>
              <th className="num">Starts</th>
              <th className="num">Minutes</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <tr key={group.family}>
                <td className="strong">{group.family}</td>
                <td className="num">{group.provider_rating ?? "—"}</td>
                <td className="num">{group.rating_median ?? "—"}</td>
                <td className="num">{group.rating_p25 ?? "—"}</td>
                <td className="num">
                  {group.squad_rating_delta === null
                    ? "—"
                    : `${group.squad_rating_delta > 0 ? "+" : ""}${group.squad_rating_delta}`}
                </td>
                <td className="num">{group.goals}</td>
                <td className="num">{group.assists}</td>
                <td className="num">{group.starts}</td>
                <td className="num">{group.starter_minutes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="fine-print">
        Provider ratings, not a fitba rating and not position-adjusted. Family
        means can hide a high-variance unit; the 25th percentile is shown for
        that reason. Ratings are Premiership-only; starts and minutes include
        cup fixtures.
      </p>
    </div>
  );
}
