/** @type {import('next').NextConfig} */
const nextConfig = {
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

module.exports = nextConfig;
