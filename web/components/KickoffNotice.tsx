"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export function KickoffNotice({
  date,
  kickoff,
}: {
  date: string;
  kickoff?: string | null;
}) {
  const [passed, setPassed] = useState(false);
  useEffect(() => {
    if (!kickoff) return;
    const target = new Date(`${date}T${kickoff}:00`);
    if (Number.isNaN(target.getTime())) return;
    const check = () => setPassed(Date.now() > target.getTime() + 2 * 3600 * 1000);
    check();
    const timer = window.setInterval(check, 60_000);
    return () => window.clearInterval(timer);
  }, [date, kickoff]);

  if (!passed) return null;
  return (
    <p className="kickoff-notice">
      This fixture may have kicked off.{" "}
      <Link className="text-link" href="/fixtures/">
        Check the latest results →
      </Link>
    </p>
  );
}
