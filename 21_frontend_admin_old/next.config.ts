import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",   // ★ 정적 사이트 Export 활성화 (S3 배포용 필수)
};

export default nextConfig;
