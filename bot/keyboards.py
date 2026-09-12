from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.settings import get_user_settings

def get_main_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Auto-Scanner", callback_data="menu_autoscanner")],
        [InlineKeyboardButton(text="🎯 Target-Sniper", callback_data="menu_targetsniper")]
    ])
    return kb

def get_autoscanner_keyboard(chat_id: str) -> InlineKeyboardMarkup:
    settings = get_user_settings(chat_id)
    status_text = "🟢 ON" if settings.get("auto_scanner_enabled", False) else "🔴 OFF"
    mayhem_text = "🟢 ON" if settings.get("filter_mayhem", True) else "🔴 OFF"
    socials_text = "🟢 ON" if settings.get("require_socials", False) else "🔴 OFF"
    
    # 0 means disabled
    max_age = settings.get("max_age_minutes", 5)
    max_age_str = str(max_age) if max_age > 0 else "OFF"
    
    max_idle = settings.get("max_idle_seconds", 60)
    max_idle_str = str(max_idle) if max_idle > 0 else "OFF"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Scanner Status: {status_text}", callback_data="toggle_scanner")],
        [
            InlineKeyboardButton(text=f"Min Dev Buy: {settings.get('min_dev_buy_sol', 0.1)} SOL", callback_data="set_devbuy"),
            InlineKeyboardButton(text=f"Min MC: ${settings.get('min_market_cap', 5000)}", callback_data="set_mcap")
        ],
        [
            InlineKeyboardButton(text=f"Min Vol (5m): ${settings.get('min_volume_m5', 1000)}", callback_data="set_volume_m5"),
            InlineKeyboardButton(text=f"Min Txns (5m): {settings.get('min_txns_m5', 10)}", callback_data="set_txns_m5")
        ],
        [
            InlineKeyboardButton(text=f"Max Age: {max_age_str}", callback_data="set_maxage"),
            InlineKeyboardButton(text=f"Max Idle: {max_idle_str}", callback_data="set_maxidle")
        ],
        [
            InlineKeyboardButton(text=f"Filter Mayhem: {mayhem_text}", callback_data="toggle_mayhem"),
            InlineKeyboardButton(text=f"Req. Socials: {socials_text}", callback_data="toggle_socials")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")]
    ])
    return kb

def get_target_sniper_keyboard(chat_id: str) -> InlineKeyboardMarkup:
    settings = get_user_settings(chat_id)
    is_on = "🟢 ON" if settings.get("target_sniper_enabled", False) else "🔴 OFF"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Sniper Status: {is_on}", callback_data="toggle_targetsniper")],
        [InlineKeyboardButton(text="➕ Add Target (Mint)", callback_data="add_target")],
        [
            InlineKeyboardButton(text="📋 My Targets", callback_data="list_targets"),
            InlineKeyboardButton(text="🔙 Back", callback_data="menu_main")
        ]
    ])
    return kb
