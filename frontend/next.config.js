/** @type {import('next').NextConfig} */
const nextConfig = {
    // Proxy API requests to FastAPI backend
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: 'http://localhost:8000/api/:path*',
            },
        ];
    },

    // Enable React strict mode for better development
    reactStrictMode: true,

    // Configure for production deployment
    output: 'standalone',
};

module.exports = nextConfig;
