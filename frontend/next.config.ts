import type {NextConfig} from "next";

const nextConfig: NextConfig = {
  images: {remotePatterns: []},
  skipTrailingSlashRedirect: true,
  async redirects(){return[{source:"/chat",destination:"/notifications",permanent:false}]},
};

export default nextConfig;
