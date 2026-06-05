#!/usr/bin/env bash
# Chain Sentinel Twitter Reply Bot — launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🛡️  Chain Sentinel Reply Bot"
echo "────────────────────────────"
echo "Config  : $SCRIPT_DIR/config_reply_bot.yaml"
echo "Script  : $SCRIPT_DIR/twitter_reply_bot.py"
echo ""

# Ensure dependencies
pip install --quiet requests pyyaml 2>/dev/null || true

# Verify xurl is available
if ! command -v xurl &>/dev/null; then
    echo "❌ xurl CLI not found — install it first."
    exit 1
fi

exec python3 "$SCRIPT_DIR/twitter_reply_bot.py"
