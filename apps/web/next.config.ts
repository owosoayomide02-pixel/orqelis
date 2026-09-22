import path from "path";
import type { NextConfig } from "next";

const backend = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
