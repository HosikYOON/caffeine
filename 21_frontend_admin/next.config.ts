import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,  // /analysis → /analysis/index.html 로 접근 가능하게
};

export default nextConfig;
