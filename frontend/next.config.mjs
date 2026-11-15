/** @type {import('next').NextConfig} */
const FLASK_URL = process.env.FLASK_URL || "http://127.0.0.1:5000";

const nextConfig = {
  reactStrictMode: true,
  // Proxy /api/* to the Flask backend, so the browser never deals with CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${FLASK_URL}/api/:path*` }];
  },
};

export default nextConfig;
