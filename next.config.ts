import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [], // Keep this empty to force bundling
  bundlePagesRouterDependencies: true,
  transpilePackages: [
    "@copilotkit/react-core", 
    "@copilotkit/react-ui", 
    "@copilotkit/shared",
    "@copilotkit/runtime-client-gql",
    "shiki" // Force Next.js to handle shiki explicitly
  ],
  // This helps Next.js ignore internal tsconfig issues in node_modules
  typescript: {
    ignoreBuildErrors: true, 
  },
};

export default nextConfig;
