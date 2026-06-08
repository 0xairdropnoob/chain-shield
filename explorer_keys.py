"""
Chain Sentinel - Blockchain Explorer API Keys (Optional)
Register for free API keys to enable wallet tracking.

Free tiers:
- Etherscan: 5 calls/sec, supports ALL chains via V2
  -> https://etherscan.io/myapikey
- BscScan: 5 calls/sec, BSC only
  -> https://bscscan.com/myapikey  
- Moralis: 100k CU/day, excellent wallet history
  -> https://moralis.com
"""

import os

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")


def get_explorer_key(chain: str) -> str:
    if chain == "bsc":
        return BSCSCAN_API_KEY or ETHERSCAN_API_KEY
    return ETHERSCAN_API_KEY


def has_explorer_key(chain: str = "eth") -> bool:
    if chain == "bsc":
        return bool(BSCSCAN_API_KEY or ETHERSCAN_API_KEY)
    return bool(ETHERSCAN_API_KEY)
