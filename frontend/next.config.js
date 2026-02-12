/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    eslint: {
        ignoreDuringBuilds: true,
    },
    typescript: {
        ignoreBuildErrors: true,
    },
    async rewrites() {
        return [
            {
                source: "/api/v1/:path*",
                destination: "http://backend:8000/api/v1/:path*",
            },
        ];
    },
};

module.exports = nextConfig;
