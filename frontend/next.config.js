/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/static/:path*',
        destination: 'http://localhost:8000/static/:path*', // Live এ থাকলে Render backend URL
      },
    ];
  },
};

module.exports = nextConfig;