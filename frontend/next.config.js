/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ["p3-sign.douyinpic.com", "p9-sign.douyinpic.com", "p6-sign.douyinpic.com", "p26-sign.douyinpic.com"],
    unoptimized: true,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
