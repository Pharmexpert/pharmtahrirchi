/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  // Cache headers: short for HTML (always revalidate), long for immutable chunks.
  // Ensures fresh deploys appear without hard refresh.
  async headers() {
    return [
      {
        source: '/:path((?!_next|api).*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=0, must-revalidate' },
        ],
      },
      {
        source: '/_next/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
// force redeploy 1775863679
// vercel-redeploy 1775901753
