import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  pageExtensions: ['tsx', 'ts', 'jsx', 'js'],
  reactStrictMode: true,
  
  // Optimize for CI/test builds
  ...(process.env.CI && {
    // Disable source maps in CI (faster builds, not needed for tests)
    productionBrowserSourceMaps: false,
    
    // Optimize images (if using next/image) - skip optimization in CI
    images: {
      unoptimized: true,
    },
    
    // Use SWC minification (faster than Terser, default in Next.js 15)
    swcMinify: true,
    
    // Compiler optimizations
    compiler: {
      removeConsole: process.env.CI ? {
        exclude: ['error', 'warn'], // Keep errors/warnings for debugging
      } : false,
    },
  }),
};

export default nextConfig;
