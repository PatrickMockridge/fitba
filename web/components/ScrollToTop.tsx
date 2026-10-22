"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Internal navigation lands at the top of the next page.
 *
 * A deliberate in-page anchor (for example /analysis/#claim-defence) keeps its
 * target; every other internal link resets the document scroll. The same rule
 * covers links to the current path, which do not trigger a pathname change.
 */
export function ScrollToTop() {
  const pathname = usePathname();

  useEffect(() => {
    if (window.location.hash) return;
    window.scrollTo(0, 0);
  }, [pathname]);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) return;
      const next = new URL(anchor.href, window.location.href);
      if (next.origin !== window.location.origin) return;
      if (next.pathname !== window.location.pathname) return;
      if (next.hash) return;
      window.scrollTo(0, 0);
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, []);

  return null;
}
