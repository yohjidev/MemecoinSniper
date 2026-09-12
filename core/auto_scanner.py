import asyncio
import json
import logging
import time
from typing import Dict, Any, Tuple, Optional
import aiohttp
import websockets
from colorama import init, Fore

import config
from core.advanced_filters import run_advanced_analysis
from utils.settings import load_users

init(autoreset=True)

logger = logging.getLogger(__name__)

SEEN_MINTS = {}
TTL_SECONDS = 3600

async def send_to_users(bot, message: str, symbol: str, mint: str, initial_buy: float, market_cap: float, holders: int, volume: float, is_mayhem: bool, age_minutes: float, idle_seconds: int):
    users = load_users()
    sent_any = False
    for chat_id, settings in users.items():
        if not settings.get("auto_scanner_enabled", False):
            continue
        max_age = settings.get("max_age_minutes", 5)
        if max_age > 0 and age_minutes > max_age:
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} is too old ({age_minutes:.1f}m) for {chat_id}")
            continue
        max_idle = settings.get("max_idle_seconds", 60)
        if max_idle > 0 and idle_seconds > max_idle:
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} is idle (last tx {idle_seconds}s ago) for {chat_id}")
            continue
        if initial_buy < settings.get("min_dev_buy_sol", 0.1):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} failed Min Dev Buy ({initial_buy}) for {chat_id}")
            continue
        if market_cap < settings.get("min_market_cap", 5000):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} failed Min MC ({market_cap}) for {chat_id}")
            continue
        if holders < settings.get("min_holders", 20):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} failed Min Holders ({holders}) for {chat_id}")
            continue
        if volume < settings.get("min_volume_m5", 1000):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} failed Min Vol ({volume}) for {chat_id}")
            continue
        if holders < settings.get("min_txns_m5", 10):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} failed Min Txns ({holders}) for {chat_id}")
            continue
        if is_mayhem and settings.get("filter_mayhem", True):
            logger.info(f"{Fore.YELLOW}[SKIPPED] {symbol} is Mayhem Mode for {chat_id}")
            continue
        
        try:
            await bot.send_message(chat_id, message, parse_mode='HTML')
            logger.info(f"{Fore.GREEN}[SENT] Alert for {symbol} ({mint}) sent to {chat_id}!")
            sent_any = True
        except Exception as e:
            logger.error(f"Failed to send to {chat_id}: {e}")

async def process_token(session: aiohttp.ClientSession, mint: str, name: str, symbol: str, dev_wallet: str, initial_buy: float, bot):
    logger.info(f"{Fore.CYAN}[NEW] Token detected: {name} ({symbol}) - {mint}")
    
    # 1. LAZY MOMENTUM CHECK (Zero RPC cost, takes 60s)
    # Get user settings to pass require_socials. 
    # Since process_token is generic, we'll check if ANY user requires socials.
    users = load_users()
    require_socials = any(s.get("require_socials", False) for s in users.values())
    
    is_flow_safe, flow_reason, real_mc, real_txns, real_vol, is_mayhem, age_minutes, idle_seconds = await run_advanced_analysis(
        session, config.RPC_URL, mint, symbol, dev_wallet, require_socials
    )
    if not is_flow_safe:
        return
        
    market_cap = real_mc
    holders = real_txns  # Rough proxy: number of buys is a proxy for holders in the first minute
    volume = real_vol
    
    message = (
        f"🚨 <b>New Safe Token Detected!</b>\n\n"
        f"<b>Name:</b> {name}\n"
        f"<b>Ticker:</b> {symbol}\n"
        f"<b>Mint:</b> <code>{mint}</code>\n\n"
        f"🔗 <b>Quick Links:</b>\n"
        f"• <a href='https://pump.fun/{mint}'>Pump.fun</a>\n"
        f"• <a href='https://photon-sol.tinyastro.io/en/lp/{mint}'>Photon</a>\n"
        f"• <a href='https://dexscreener.com/solana/{mint}'>DexScreener</a>"
    )
    
    await send_to_users(bot, message, symbol, mint, initial_buy, market_cap, holders, volume, is_mayhem, age_minutes, idle_seconds)

async def start_scanner(bot):
    ws_url = "wss://pumpportal.fun/api/data"
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                logger.info(f"{Fore.MAGENTA}Connecting to Auto-Scanner WebSocket...")
                async with websockets.connect(ws_url) as ws:
                    payload = {"method": "subscribeNewToken"}
                    await ws.send(json.dumps(payload))
                    logger.info(f"{Fore.GREEN}Subscribed to new token events!")
                    
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        mint = data.get("mint")
                        name = data.get("name", "Unknown")
                        symbol = data.get("symbol", "UNK")
                        trader_public_key = data.get("traderPublicKey", "")
                        initial_buy = data.get("initialBuy", 0)
                        
                        if not mint:
                            continue
                            
                        # NEW: Stop search entirely if no users have it enabled
                        users = load_users()
                        if not any(s.get("auto_scanner_enabled", False) for s in users.values()):
                            continue
                        # Quick global check to save resources
                        if initial_buy < 0.05:
                            continue
                            
                        if mint in SEEN_MINTS:
                            continue
                            
                        SEEN_MINTS[mint] = time.time()
                        
                        asyncio.create_task(process_token(session, mint, name, symbol, trader_public_key, initial_buy, bot))
                        
            except websockets.exceptions.ConnectionClosed as e:
                logger.error(f"{Fore.RED}[ERROR] WebSocket closed: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"{Fore.RED}[ERROR] Unexpected error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
