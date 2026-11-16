/** @type {import('next').NextConfig} */
const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5000";
// On Vercel the site reads pre-exported JSON from public/data (NEXT_PUBLIC_STATIC_DATA=1),
// so no proxy to Flask is needed there.
const STATIC_MODE = process.env.NEXT_PUBLIC_STATIC_DATA === "1";

const nextConfig = {
  reactStrictMode: true,
  // Local development: proxy /api/* to the Flask backend, so the browser never deals with CORS.
  async rewrites() {
    if (STATIC_MODE) return [];
    return [{ source: "/api/:path*", destination: `${FLASK_URL}/api/:path*` }];
  },
};

export default nextConfig;
