import Link from "next/link";
import { getDefinitions } from "@/lib/data";

/**
 * A first-use definition link. Server component only: `getDefinitions` reads the
 * published payload at build time. Missing ids render plain text, never a dead
 * link.
 */
export function DefinitionTerm({
  id,
  children,
}: {
  id: string;
  children?: React.ReactNode;
}) {
  const document = getDefinitions();
  const target = document?.entries.find(
    (entry) =>
      entry.id === id || entry.id === `def.${id}` || entry.id === `metric.${id}`,
  );
  if (!target) return <>{children ?? id}</>;
  return (
    <Link
      className="text-link definition-term"
      href={target.href}
      data-definition-term={target.id}
    >
      {children ?? target.term}
    </Link>
  );
}
