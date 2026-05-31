import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hide the floating Next.js dev-tools indicator (the logo button).
  devIndicators: false,
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
