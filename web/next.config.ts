import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Type checking is enforced via `tsc --noEmit` (npm run typecheck) and during `next build`.
  // ESLint is kept as a separate dev command so lint warnings never mask build results.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
