import type { ReactNode } from "react";

function initials(name: string): string {
  const parts = name.replace(/\./g, "").split(/\s+/).filter(Boolean);
  return (
    parts
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?"
  );
}

export function ProfileHeader({
  eyebrow,
  name,
  lede,
  badges,
  attributes,
  mark,
}: {
  eyebrow: string;
  name: string;
  lede: ReactNode;
  badges?: ReactNode;
  attributes?: ReactNode;
  mark?: string;
}) {
  return (
    <section className="club-head player-identity" data-contract="player-profile.header">
      <div className="club-identity">
        <span className="club-roundel large" aria-hidden="true">
          {mark ?? initials(name)}
        </span>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{name}</h1>
          <p className="lede">{lede}</p>
          {attributes ? <p className="player-attributes">{attributes}</p> : null}
          {badges ? <div className="hero-actions">{badges}</div> : null}
        </div>
      </div>
    </section>
  );
}
