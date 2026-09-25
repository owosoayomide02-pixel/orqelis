import path from "path";
import type { NextConfig } from "next";

const backend = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const staticExport = process.env.ORQELIS_STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  ...(staticExport
    ? {
        output: "export" as const,
        images: { unoptimized: true },
        env: {
          NEXT_PUBLIC_STATIC_EXPORT: "1",
        },
      }
    : {
        async rewrites() {
          return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
        },
      }),
};

export default nextConfig;
