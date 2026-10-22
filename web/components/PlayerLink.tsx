import Link from "next/link";

/**
 * A current player's name links to their profile. Names without an href are
 * former players, rumour targets or fan-only mentions and stay plain text.
 */
export function PlayerLink({
  name,
  href,
  className,
}: {
  name: string;
  href?: string | null;
  className?: string;
}) {
  if (!href) {
    return <span className={className}>{name}</span>;
  }
  return (
    <Link href={href} className={className}>
      {name}
    </Link>
  );
}
