// The browser only ever talks to this origin; /api/* is forwarded to the FastAPI backend (same origin: no CORS, cookies just work).
const API_ORIGIN = process.env.API_ORIGIN || "http://127.0.0.1:8100";

/** @type {import('next').NextConfig} */
const nextConfig = {
  distDir: process.env.NEXT_DIST_DIR || ".next",
  poweredByHeader: false,
  reactStrictMode: true,
  compress: true,
  experimental: {
    middlewareClientMaxBodySize: "50mb",
    proxyTimeout: 600000, // OCR of a scanned textbook can take a few minutes; the default proxy gives up after 30 s
    optimizePackageImports: ["lucide-react", "recharts", "framer-motion", "@tanstack/react-table"],
  },
  async headers() {
    return [{ source: "/sw.js", headers: [{ key: "Cache-Control", value: "no-cache, no-store, must-revalidate" }, { key: "Service-Worker-Allowed", value: "/" }] }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
