import { slotColor } from "@/lib/roles";

export interface RoleMixShare {
  slot?: string;
  fm?: string;
  label: string;
  share: number;
  groups?: string[];
}

export function RoleMix({ shares }: { shares: RoleMixShare[] }) {
  const positive = shares.filter((share) => share.share > 0);
  if (!positive.length) return null;
  const top = positive.slice(0, 3);
  const other = Math.max(
    0,
    1 - top.reduce((total, share) => total + share.share, 0),
  );
  const label = [
    ...top.map(
      (share) => `${share.fm ?? share.label} ${Math.round(share.share * 100)}%`,
    ),
    ...(other > 0.005 ? [`Other ${Math.round(other * 100)}%`] : []),
  ].join(", ");
  return (
    <span className="role-mix" role="img" aria-label={`Career role mix: ${label}`} title={label}>
      {top.map((share) => (
        <span
          key={share.slot ?? share.label}
          className="role-mix-segment"
          style={{
            width: `${Math.max(share.share * 100, 2)}%`,
            backgroundColor: slotColor(share.groups ?? []),
          }}
        />
      ))}
      {other > 0.005 ? (
        <span
          className="role-mix-segment"
          style={{ width: `${other * 100}%`, backgroundColor: "#d1d5db" }}
        />
      ) : null}
    </span>
  );
}
