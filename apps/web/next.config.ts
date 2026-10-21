import type { NextConfig } from "next";

const apiPort = process.env.API_PORT ?? "8085";
if (!/^\d+$/.test(apiPort) || Number(apiPort) < 1024 || Number(apiPort) > 65535) {
  throw new Error("API_PORT 必须为 1024–65535");
}

const config: NextConfig = {
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `http://127.0.0.1:${apiPort}/api/v1/:path*` }];
  },
};
export default config;
