/** @type {import('next').NextConfig} */
const isExport = process.env.NEXT_OUTPUT === "export";

const nextConfig = {
  reactStrictMode: true,
  // Monolith build: `NEXT_OUTPUT=export next build` emits a static site to
  // frontend/out, which FastAPI serves from the same origin (single Render app).
  ...(isExport ? { output: "export", images: { unoptimized: true } } : {}),
  // Dev / split-deploy: proxy /api to the FastAPI backend. Not used in export
  // mode, where the app is same-origin with the API.
  ...(isExport
    ? {}
    : {
        async rewrites() {
          const base = process.env.API_PROXY_TARGET || "http://127.0.0.1:8000";
          return [{ source: "/api/:path*", destination: `${base}/api/:path*` }];
        },
      }),
};
export default nextConfig;
