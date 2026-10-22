import type { NextConfig } from "next";

// GitHub Pages serves a project site under /<repo>/. Local builds and the CI
// build stay at the root; the Pages workflow sets NEXT_PUBLIC_BASE_PATH.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath,
  turbopack: { root: process.cwd() },
};

export default nextConfig;
