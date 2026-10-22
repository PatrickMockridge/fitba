"use client";

import { useEffect, useState } from "react";

const THEMES = [
  { value: "auto", label: "Auto" },
  { value: "merkland", label: "Merkland" },
  { value: "red-matchday", label: "Red Matchday" },
  { value: "aurora", label: "Aurora" },
  { value: "floodlight", label: "Floodlight" },
];

const ALLOWED = new Set(THEMES.map((theme) => theme.value));

export function ThemeSwitcher() {
  const [theme, setTheme] = useState("auto");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("fitba-theme");
      if (stored && ALLOWED.has(stored)) {
        setTheme(stored);
      }
    } catch {
      // Storage can be unavailable in private or restricted contexts.
    }
  }, []);

  function choose(next: string) {
    setTheme(next);
    try {
      const root = document.documentElement;
      if (next === "auto") {
        root.removeAttribute("data-theme");
        window.localStorage.removeItem("fitba-theme");
      } else {
        root.setAttribute("data-theme", next);
        window.localStorage.setItem("fitba-theme", next);
      }
    } catch {
      // The visual selection still applies for this page view.
    }
  }

  return (
    <label className="theme-switcher">
      <span>Theme</span>
      <select
        value={theme}
        onChange={(event) => choose(event.target.value)}
        aria-label="Colour theme"
      >
        {THEMES.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </select>
    </label>
  );
}
