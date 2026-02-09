/** @type {import('next').NextConfig} */
const nextConfig = {
    // Enable React strict mode
    reactStrictMode: true,

    // Image optimization domains
    images: {
        remotePatterns: [
            {
                protocol: 'https',
                hostname: '**',
            },
        ],
    },

    // Environment variables exposed to browser
    env: {
        NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'StudyABHI',
    },

    // Redirect API calls to backend
    async rewrites() {
        return [
            {
                source: '/api/:path*',
                destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
            },
        ];
    },
};

module.exports = nextConfig;
