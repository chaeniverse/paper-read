/** @type {import('next').NextConfig} */
const nextConfig = {
  // math-heavy papers prerender a lot of KaTeX; give them headroom
  staticPageGenerationTimeout: 180,
};

export default nextConfig;
