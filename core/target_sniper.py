import asyncio
import json
import logging
import os
import aiohttp
from typing import Dict, List, Optional
from utils.settings import get_user_settings

logger = logging.getLogger(__name__)

TARGETS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'targets.json')

# Target data structure: {chat_id: [{mint: str, target_mc: float, name: str}]}

def load_targets() -> Dict[str, List[dict]]:
    if not os.path.exists(TARGETS_FILE):
        os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
        return {}
    with open(TARGETS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_targets(targets: Dict[str, List[dict]]):
    with open(TARGETS_FILE, 'w') as f:
        json.dump(targets, f, indent=4)

def add_target(chat_id: str, mint: str, target_mc: float):
    targets = load_targets()
    chat_id_str = str(chat_id)
    if chat_id_str not in targets:
        targets[chat_id_str] = []
    
    # Check if already exists
    for t in targets[chat_id_str]:
        if t['mint'] == mint:
            t['target_mc'] = target_mc
            save_targets(targets)
            return
            
    targets[chat_id_str].append({'mint': mint, 'target_mc': target_mc, 'name': 'Unknown'})
    save_targets(targets)

def remove_target(chat_id: str, mint: str):
    targets = load_targets()
    chat_id_str = str(chat_id)
    if chat_id_str in targets:
        targets[chat_id_str] = [t for t in targets[chat_id_str] if t['mint'] != mint]
        save_targets(targets)

async def check_target_price(session: aiohttp.ClientSession, mint: str) -> Optional[dict]:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    pair = pairs[0]
                    return {
                        "name": pair.get("baseToken", {}).get("name", "Unknown"),
                        "symbol": pair.get("baseToken", {}).get("symbol", "UNK"),
                        "mc": pair.get("fdv", 0),
                        "price": pair.get("priceUsd", "0")
                    }
    except Exception as e:
        logger.error(f"Error checking {mint}: {e}")
    return None

async def target_sniper_loop(bot):
    while True:
        try:
            targets = load_targets()
            if not targets:
                await asyncio.sleep(60)
                continue
                
            async with aiohttp.ClientSession() as session:
                for chat_id, user_targets in targets.items():
                    # Check if user has target sniper enabled
                    settings = get_user_settings(chat_id)
                    if not settings.get("target_sniper_enabled", False):
                        continue
                        
                    for target in list(user_targets):
                        mint = target['mint']
                        target_mc = target['target_mc']
                        
                        token_data = await check_target_price(session, mint)
                        if token_data:
                            current_mc = token_data['mc']
                            
                            if current_mc >= target_mc:
                                # Target reached!
                                message = (
                                    f"🎯 <b>TARGET REACHED!</b>\n\n"
                                    f"<b>{token_data['name']} ({token_data['symbol']})</b>\n"
                                    f"Mint: <code>{mint}</code>\n\n"
                                    f"📈 Target MC: ${target_mc:,.0f}\n"
                                    f"🔥 Current MC: <b>${current_mc:,.0f}</b>\n"
                                    f"💲 Price: ${token_data['price']}\n\n"
                                    f"🔗 <a href='https://photon-sol.tinyastro.io/en/lp/{mint}'>Buy on Photon</a>"
                                )
                                await bot.send_message(chat_id, message, parse_mode='HTML')
                                
                                # Remove target after hit
                                remove_target(chat_id, mint)
                                
            # Poll every 5 minutes
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Target Sniper Loop Error: {e}")
            await asyncio.sleep(60)
