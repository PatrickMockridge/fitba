import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Season overview (moved) · fitba",
  description: "The themes page has moved to Season overview.",
  alternates: { canonical: "/analysis/" },
  robots: { index: false, follow: true },
};

export default function ThemesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
