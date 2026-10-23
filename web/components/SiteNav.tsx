"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/matchday/", label: "Matchday" },
  { href: "/matches/", label: "Matches" },
  { href: "/analysis/", label: "Data analysis" },
  { href: "/squad/", label: "Squad" },
  { href: "/scouting/", label: "Scouting" },
  { href: "/recruitment/", label: "Off the pitch" },
  { href: "/history/", label: "The Cormack era" },
  { href: "/news/", label: "News & rumours" },
];

export function SiteNav() {
  const pathname = usePathname();
  return (
    <nav className="nav" aria-label="Main">
      {LINKS.map((link) => {
        const active = pathname === link.href || pathname.startsWith(link.href);
        return (
          <Link key={link.href} href={link.href} aria-current={active ? "page" : undefined}>
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
