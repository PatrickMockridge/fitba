import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Data analysis (moved) · fitba",
  description: "The themes page has moved to Data analysis.",
  alternates: { canonical: "/analysis/" },
  robots: { index: false, follow: true },
};

export default function ThemesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
