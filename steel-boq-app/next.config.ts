import type { NextConfig } from "next";

// Set NEXT_PUBLIC_BASE_PATH (e.g. "/Steel-Tech-Project/app") when deploying to GitHub Pages.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export",
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
