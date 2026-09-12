import asyncio
import logging
import aiohttp
from colorama import Fore

logger = logging.getLogger(__name__)

async def check_momentum(session: aiohttp.ClientSession, mint: str, symbol: str, duration_seconds: int = 40):
    logger.info(f"{Fore.LIGHTBLACK_EX}[FLOW] Waiting {duration_seconds}s for {symbol} to build volume and index on DexScreener...")
    await asyncio.sleep(duration_seconds)
    
    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                pairs = data.get("pairs", [])
                
                if not pairs:
                    return False, "Мертвый токен (не проиндексирован / нет торгов)", 0, 0, 0, False, 0
                
                # Take first pair (usually Raydium or Pump)
                pair = pairs[0]
                
                # Check Age
                created_at = pair.get("pairCreatedAt", 0) # ms
                age_minutes = 0
                if created_at > 0:
                    import time
                    current_time_ms = int(time.time() * 1000)
                    age_minutes = (current_time_ms - created_at) / 60000
                        
                volume_m5 = pair.get("volume", {}).get("m5", 0)
                txns_m5 = pair.get("txns", {}).get("m5", {}).get("buys", 0)
                market_cap = pair.get("fdv", 0)
                
                # Check for Mayhem mode or risk labels
                is_mayhem = False
                raw_pair_str = str(pair).lower()
                if "mayhem" in raw_pair_str or "honeypot" in raw_pair_str:
                    is_mayhem = True
                    
                return True, f"Активный токен: MC ${market_cap:,.0f}, ${volume_m5} объем", market_cap, txns_m5, volume_m5, is_mayhem, age_minutes
    except Exception as e:
        return False, f"Ошибка API: {e}", 0, 0, 0, False, 0
        
    return False, "Мертвый токен (API не вернул данные)", 0, 0, 0, False, 0
