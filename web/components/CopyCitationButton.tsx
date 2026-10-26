"use client";

import { useState } from "react";

export function CopyCitationButton({
  title,
  datasetVersion,
  generatedAt,
  sources,
  metrics,
}: {
  title: string;
  datasetVersion: string;
  generatedAt: string;
  sources: string[];
  metrics: string[];
}) {
  const [state, setState] = useState<"idle" | "copied" | "error">("idle");

  async function copy() {
    const url = window.location.href;
    const lines = [
      `${title}. fitba. ${url}`,
      `Dataset ${datasetVersion}, as of ${generatedAt}.`,
      sources.length ? `Sources: ${sources.join("; ")}.` : null,
      metrics.length ? `Definitions: ${metrics.join("; ")}.` : null,
      "Independent, non-commercial public record. Check the page for basis and coverage.",
    ].filter(Boolean);
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setState("copied");
      window.setTimeout(() => setState("idle"), 2500);
    } catch {
      setState("error");
    }
  }

  return (
    <button type="button" className="button button-ghost" onClick={copy}>
      {state === "copied"
        ? "Citation copied"
        : state === "error"
          ? "Copy failed"
          : "Copy citation"}
    </button>
  );
}
