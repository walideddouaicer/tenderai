import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/django/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/api/rag/:path*",
        destination: "http://localhost:8001/api/rag/:path*",
      },
    ];
  },
};

export default nextConfig;
