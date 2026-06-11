#!/bin/bash
# Chain Sentinel — Deployment Script
# This script helps deploy to Vercel

echo "🛡️ Chain Sentinel Deployment Script"
echo "=================================="
echo ""

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

echo "🚀 Deploying to Vercel..."
echo ""

# Deploy to Vercel
vercel --prod

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "1. Configure your domain in Vercel dashboard"
echo "2. Set up environment variables if needed"
echo "3. Test the API endpoints"
echo ""
echo "🔗 Useful links:"
echo "- Vercel Dashboard: https://vercel.com/dashboard"
echo "- GitHub Repo: https://github.com/ChainShieldSn/chain-shield"
echo "- Documentation: https://github.com/ChainShieldSn/chain-shield#readme"
