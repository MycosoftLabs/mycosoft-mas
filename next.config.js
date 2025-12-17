/** @type {import('next').NextConfig} */
const path = require('path')

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  turbopack: {
    resolveAlias: {
      '@': path.resolve(__dirname),
    },
  },
}

module.exports = nextConfig 