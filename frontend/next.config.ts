import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
  experimental: {
    // Aumentar el timeout del proxy para uploads grandes (ZIP con muchos PDFs).
    // Por defecto Next.js corta la conexión a los 30s → 530 en Cloudflare tunnel.
    proxyTimeout: 120_000,
  },
};

export default nextConfig;
