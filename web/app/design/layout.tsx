import type { Metadata } from "next";
import "./specimen.css";

export const metadata: Metadata = {
  title: "Design specimen · fitba",
  robots: { index: false, follow: false },
};

export default function DesignLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
