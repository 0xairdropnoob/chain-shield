#!/usr/bin/env python3
"""
Chain Sentinel Twitter Reply Bot
Monitors crypto Twitter for token contract addresses and auto-replies
with safety scan results from chainshieldsentinel.tech.

Uses the `xurl` CLI tool for all Twitter operations.
"""

import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml
import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config_reply_bot.yaml"
DEFAULT_REPLIED_FILE = SCRIPT_DIR / "replied_tweets.json"
DEFAULT_LOG_FILE = SCRIPT_DIR / "reply_bot.log"

# Regex for Ethereum-style contract addresses
ADDRESS_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def setup_logging(log_path: str) -> logging.Logger:
    logger = logging.getLogger("reply_bot")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


def load_replied(path: str) -> dict:
    p = Path(path)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {}


def save_replied(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def xurl_search(query: str) -> list[dict]:
    """Run `xurl search <query>` and return parsed JSON list of tweets."""
    try:
        result = subprocess.run(
            ["xurl", "search", query],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return []
        return json.loads(result.stdout)
    except Exception:
        return []


def xurl_post(text: str, reply_to: str) -> bool:
    """Post a reply tweet via `xurl post <text> --reply-to <id>`."""
    try:
        result = subprocess.run(
            ["xurl", "post", text, "--reply-to", reply_to],
            capture_output=True, text=True, timeout=60,
        )
        return result.returncode == 0
    except Exception:
        return False


def scan_token(address: str, api_url: str) -> Optional[dict]:
    """Call the Chain Sentinel API to scan a token address."""
    try:
        resp = requests.get(
            f"{api_url}/{address}",
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def format_reply(scan: dict) -> str:
    name = scan.get("name", "Unknown")
    symbol = scan.get("symbol", "???")
    score = scan.get("safety_score", "?")
    level = scan.get("risk_level", "Unknown")
    honeypot = "Yes ⚠️" if scan.get("is_honeypot") else "No ✅"

    return (
        f"🛡️ Chain Sentinel Scan Report\n"
        f"\n"
        f"Token: {name} ({symbol})\n"
        f"Safety Score: {score}/100\n"
        f"Risk Level: {level}\n"
        f"Honeypot: {honeypot}\n"
        f"\n"
        f"Full report → chainshieldsentinel.tech\n"
        f"\n"
        f"⚠️ Not financial advice. Always DYOR."
    )


# ---------------------------------------------------------------------------
# Rate limiter (simple sliding window)
# ---------------------------------------------------------------------------

class RateLimiter:
    def __init__(self, max_per_hour: int):
        self.max_per_hour = max_per_hour
        self.timestamps: list[float] = []

    def can_proceed(self) -> bool:
        now = time.time()
        cutoff = now - 3600
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        return len(self.timestamps) < self.max_per_hour

    def record(self):
        self.timestamps.append(time.time())


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    logger = setup_logging(
        str(SCRIPT_DIR / config.get("log_file", "reply_bot.log")),
    )

    dry_run = config.get("dry_run", True)
    if dry_run:
        logger.info("🔒 DRY-RUN MODE — no tweets will be posted")

    replied_path = str(SCRIPT_DIR / config.get("replied_log_file", "replied_tweets.json"))
    replied = load_replied(replied_path)

    limiter = RateLimiter(config.get("max_replies_per_hour", 10))
    interval = config.get("search_interval", 300)
    min_followers = config.get("min_followers", 50)
    api_url = config.get("scan_api_url", "https://chainshieldsentinel.tech/api/scan")
    queries = config.get("search_queries", ["0x contract address"])

    logger.info("Bot started — polling every %ds", interval)

    while True:
        try:
            for query in queries:
                tweets = xurl_search(query)
                logger.info("Query '%s' → %d results", query, len(tweets))

                for tweet in tweets:
                    tid = tweet.get("id", "")
                    if tid in replied:
                        continue

                    followers = tweet.get("author_followers", 0)
                    if followers < min_followers:
                        continue

                    text = tweet.get("text", "")
                    addresses = ADDRESS_RE.findall(text)
                    if not addresses:
                        continue

                    if not limiter.can_proceed():
                        logger.warning("Rate limit reached — skipping rest")
                        break

                    for addr in addresses:
                        logger.info("Scanning %s (tweet %s)", addr, tid)
                        scan = scan_token(addr, api_url)
                        if scan is None:
                            logger.warning("Scan failed for %s", addr)
                            continue

                        reply_text = format_reply(scan)

                        if dry_run:
                            logger.info("[DRY-RUN] Would reply to %s:\n%s", tid, reply_text)
                        else:
                            success = xurl_post(reply_text, tid)
                            if success:
                                logger.info("Replied to %s", tid)
                                limiter.record()
                            else:
                                logger.error("Failed to reply to %s", tid)

                        replied[tid] = {
                            "address": addr,
                            "replied_at": datetime.utcnow().isoformat(),
                        }
                        save_replied(replied_path, replied)

                        # one address per tweet
                        break

        except KeyboardInterrupt:
            logger.info("Shutting down")
            sys.exit(0)
        except Exception:
            logger.exception("Unhandled error in main loop")

        logger.info("Sleeping %ds…", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
