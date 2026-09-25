/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
      },
      {
        source: '/uploads/:path*',
        destination: 'http://127.0.0.1:8000/uploads/:path*',
      },
      {
        source: '/results/:path*',
        destination: 'http://127.0.0.1:8000/results/:path*',
      },
      {
        source: '/dataset/:path*',
        destination: 'http://127.0.0.1:8000/dataset/:path*',
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: '127.0.0.1',
        port: '8000',
      },
    ],
  },
};

module.exports = nextConfig;
