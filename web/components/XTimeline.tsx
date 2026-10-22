"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";

declare global {
  interface Window {
    twttr?: {
      widgets: {
        load: (element?: HTMLElement) => void;
      };
    };
  }
}

type Status = "loading" | "ready" | "blocked";

export function XTimeline({
  handle = "AberdeenFC",
  height = 620,
}: {
  handle?: string;
  height?: number;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [status, setStatus] = useState<Status>("loading");

  useEffect(() => {
    const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setTheme(dark ? "dark" : "light");
  }, []);

  useEffect(() => {
    const element = container.current;
    if (!element) return;

    const observer = new MutationObserver(() => {
      if (element.querySelector("iframe")) setStatus("ready");
    });
    observer.observe(element, { childList: true, subtree: true });

    const timer = window.setTimeout(() => {
      if (!element.querySelector("iframe")) setStatus("blocked");
    }, 6000);

    return () => {
      observer.disconnect();
      window.clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    window.twttr?.widgets.load(container.current ?? undefined);
  }, [theme]);

  return (
    <div className="x-embed" ref={container}>
      <a
        className="twitter-timeline"
        href={`https://x.com/${handle}?ref_src=twsrc%5Etfw`}
        data-theme={theme}
        data-height={height}
        data-chrome="noheader nofooter"
        data-dnt="true"
        data-lang="en"
      >
        Posts by {handle}
      </a>

      {status === "loading" ? (
        <p className="x-loading">Loading the X timeline…</p>
      ) : null}

      {status === "blocked" ? (
        <div className="x-fallback">
          <p>
            <strong>The X timeline did not load.</strong> Brave Shields, an ad
            blocker or a privacy extension may be blocking X&apos;s embed. X may
            also require a login to display the profile timeline.
          </p>
          <a
            className="button"
            href={`https://x.com/${handle}`}
            target="_blank"
            rel="noreferrer"
          >
            Open @{handle} on X
          </a>
          <p className="fine-print">
            To render the inline timeline, allow <code>platform.x.com</code> for
            this site and reload. fitba does not bypass content blockers.
          </p>
        </div>
      ) : null}

      <Script
        id="x-widgets"
        src="https://platform.x.com/widgets.js"
        charSet="utf-8"
        strategy="afterInteractive"
        onLoad={() => window.twttr?.widgets.load(container.current ?? undefined)}
        onError={() => setStatus("blocked")}
      />

      <p className="fine-print">
        Embedded from X; not ingested or stored by fitba.{" "}
        <a href={`https://x.com/${handle}`} target="_blank" rel="noreferrer">
          Open @{handle} on X →
        </a>
      </p>
    </div>
  );
}
