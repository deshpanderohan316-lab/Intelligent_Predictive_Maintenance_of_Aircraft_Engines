/** @type {import('next').NextConfig} */
const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5000";

// Build modes
//  * local dev (npm run dev): proxy /api/* to Flask on :5000
//  * NEXT_OUTPUT=export (Docker / Render): plain HTML/JS in frontend/out, served by Flask on the same origin
//  * NEXT_PUBLIC_STATIC_DATA=1 (Vercel): read pre-exported JSON from public/data, no backend
const EXPORT_MODE = process.env.NEXT_OUTPUT === "export";
const STATIC_MODE = process.env.NEXT_PUBLIC_STATIC_DATA === "1";

const nextConfig = {
  reactStrictMode: true,
  ...(EXPORT_MODE ? { output: "export", trailingSlash: true, images: { unoptimized: true } } : {}),
  ...(EXPORT_MODE
    ? {}
    : {
        async rewrites() {
          if (STATIC_MODE) return [];
          return [{ source: "/api/:path*", destination: `${FLASK_URL}/api/:path*` }];
        },
      }),
};

export default nextConfig;
