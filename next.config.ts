import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable image optimization (we don't use the Next image optimizer here)
  images: {
    unoptimized: true,
  },
  eslint: {
    // Don't fail builds on lint errors
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
