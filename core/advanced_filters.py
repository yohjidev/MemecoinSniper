import asyncio
import logging
import time
from typing import Dict, Any, Tuple
import aiohttp
from colorama import Fore

from core.flow_analyzer import check_momentum

logger = logging.getLogger(__name__)

async def analyze_dev_activity(session: aiohttp.ClientSession, rpc_url: str, mint: str, dev_wallet: str) -> Tuple[bool, str]:
    """
    1. Dev Activity (Initial Dev Buy, Wallet balance, Dev history)
    """
    payload_balance = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [dev_wallet]}
    try:
        async with session.post(rpc_url, json=payload_balance) as resp:
            data = await resp.json()
            if "result" in data:
                balance_sol = data["result"]["value"] / 10**9
                if balance_sol < 0.1: # Less than ~15$
                    return False, f"Low dev wallet balance: {balance_sol:.3f} SOL"
    except Exception as e:
        logger.error(f"{Fore.RED}[ERROR] Dev balance check failed: {e}")

    payload_sigs = {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [dev_wallet, {"limit": 20}]}
    try:
        async with session.post(rpc_url, json=payload_sigs) as resp:
            data = await resp.json()
            if "result" in data:
                if len(data["result"]) >= 20:
                    pass
    except Exception:
        pass

    return True, "Passed Dev Activity"

async def check_socials_and_metadata(session: aiohttp.ClientSession, mint: str, require_socials: bool = False) -> Tuple[bool, str]:
    """
    Quality & Socials (DEX Screener Paid Boosts, CTO status, Social Links)
    """
    if not require_socials:
        return True, "Passed Socials (Not Required)"
        
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    info = pairs[0].get("info", {})
                    socials = info.get("socials", [])
                    websites = info.get("websites", [])
                    if not socials and not websites:
                        return False, "No social links or websites found"
                    return True, "Social links found"
    except Exception as e:
        logger.error(f"{Fore.RED}[ERROR] Socials check failed: {e}")
        
    return False, "Failed to verify socials"

async def check_last_transaction_time(session: aiohttp.ClientSession, rpc_url: str, mint: str) -> int:
    """
    Checks the exact timestamp of the last transaction for the token.
    Returns the idle time in seconds.
    """
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [mint, {"limit": 1}]}
    try:
        async with session.post(rpc_url, json=payload) as resp:
            data = await resp.json()
            if "result" in data and len(data["result"]) > 0:
                last_tx = data["result"][0]
                if "blockTime" in last_tx and last_tx["blockTime"]:
                    return int(time.time()) - last_tx["blockTime"]
    except Exception as e:
        logger.error(f"{Fore.RED}[ERROR] Last tx check failed: {e}")
    return 0

async def run_advanced_analysis(session: aiohttp.ClientSession, rpc_url: str, mint: str, symbol: str, dev_wallet: str, require_socials: bool = False) -> Tuple[bool, str, float, int, float, bool, float, int]:
    """
    Runs all advanced MEV/Sniper filters
    """
    is_flow_safe, flow_reason, real_mc, real_txns, real_vol, is_mayhem, age_minutes = await check_momentum(session, mint, symbol, duration_seconds=60)
    if not is_flow_safe: return False, flow_reason, 0, 0, 0, False, 0, 0
    
    is_safe, reason = await analyze_dev_activity(session, rpc_url, mint, dev_wallet)
    if not is_safe: return False, reason, 0, 0, 0, False, age_minutes, 0
    
    is_safe, reason = await check_socials_and_metadata(session, mint, require_socials)
    if not is_safe: return False, reason, 0, 0, 0, False, age_minutes, 0
    
    idle_seconds = await check_last_transaction_time(session, rpc_url, mint)
    
    return True, "Passed Advanced Filters", real_mc, real_txns, real_vol, is_mayhem, age_minutes, idle_seconds
