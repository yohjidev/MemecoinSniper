import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import config
from bot.keyboards import get_main_keyboard, get_autoscanner_keyboard, get_target_sniper_keyboard
from bot.states import TargetSniperStates, ScannerSettingsStates
from utils.settings import get_user_settings, update_user_setting, load_users, save_users
from core.target_sniper import add_target, load_targets, target_sniper_loop
from core.auto_scanner import start_scanner

logger = logging.getLogger(__name__)

bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Global reference to the scanner task
scanner_task = None

async def manage_scanner_task():
    global scanner_task
    users = load_users()
    any_enabled = any(s.get("auto_scanner_enabled", False) for s in users.values())
    
    if any_enabled and (scanner_task is None or scanner_task.done()):
        logger.info("Starting Auto-Scanner task...")
        scanner_task = asyncio.create_task(start_scanner(bot))
    elif not any_enabled and scanner_task is not None and not scanner_task.done():
        logger.info("Stopping Auto-Scanner task...")
        scanner_task.cancel()
        scanner_task = None

async def on_startup(bot: Bot):
    logger.info("Bot started! Launching background tasks...")
    users = load_users()
    for chat_id, settings in users.items():
        settings["auto_scanner_enabled"] = False
    save_users(users)
    asyncio.create_task(target_sniper_loop(bot))

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if str(message.chat.id) != config.TELEGRAM_CHAT_ID:
        await message.answer("Access denied.")
        return
    await message.answer(
        "👋 <b>Welcome to Memecoin Sniper!</b>\n\nSelect a tool below:",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

# --- CALLBACK HANDLERS ---
@dp.callback_query(F.data == "menu_main")
async def process_menu_main(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.edit_text("Main Menu:", reply_markup=get_main_keyboard())
    except Exception:
        pass

@dp.callback_query(F.data == "menu_autoscanner")
async def process_menu_autoscanner(callback: CallbackQuery):
    await callback.message.edit_text("⚙️ <b>Auto-Scanner Settings:</b>\nHere you can configure filters and start parsing new tokens.", reply_markup=get_autoscanner_keyboard(callback.message.chat.id), parse_mode='HTML')

@dp.callback_query(F.data == "toggle_scanner")
async def toggle_scanner(callback: CallbackQuery):
    await callback.answer()
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    is_on = settings.get("auto_scanner_enabled", False)
    
    # Toggle it
    update_user_setting(chat_id, "auto_scanner_enabled", not is_on)
    
    # Update UI
    try:
        await callback.message.edit_reply_markup(reply_markup=get_autoscanner_keyboard(chat_id))
    except Exception:
        pass
        
    await manage_scanner_task()

@dp.callback_query(F.data == "menu_targetsniper")
async def process_menu_targetsniper(callback: CallbackQuery):
    await callback.message.edit_text("🎯 <b>Target-Sniper</b>\nTracks specific tokens.", reply_markup=get_target_sniper_keyboard(callback.message.chat.id), parse_mode='HTML')

@dp.callback_query(F.data == "toggle_targetsniper")
async def toggle_targetsniper(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    new_val = not settings.get("target_sniper_enabled", False)
    update_user_setting(chat_id, "target_sniper_enabled", new_val)
    
    if new_val:
        logger.info("Target-Sniper started")
        await callback.answer("✅ Target-Sniper STARTED in background!", show_alert=True)
    else:
        logger.info("Target-Sniper stopped")
        await callback.answer("🛑 Target-Sniper STOPPED.", show_alert=True)
        
    await callback.message.edit_reply_markup(reply_markup=get_target_sniper_keyboard(chat_id))

@dp.callback_query(F.data == "toggle_jito")
async def toggle_jito_filter(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    update_user_setting(chat_id, "jito_filter", not settings["jito_filter"])
    await callback.message.edit_reply_markup(reply_markup=get_autoscanner_keyboard(chat_id))

# --- FSM SCANNER SETTINGS ---
@dp.callback_query(F.data == "set_devbuy")
async def set_devbuy_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the minimum amount (in SOL) the developer must buy (e.g., 0.1 or 0.5):")
    await state.set_state(ScannerSettingsStates.waiting_for_devbuy)

@dp.message(ScannerSettingsStates.waiting_for_devbuy)
async def process_devbuy(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        update_user_setting(message.chat.id, "min_dev_buy_sol", val)
        await message.answer("✅ `Min Dev Buy` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter a valid number (e.g., 0.1).")

@dp.callback_query(F.data == "set_holders")
async def set_holders_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the minimum number of holders for a token (e.g., 20):")
    await state.set_state(ScannerSettingsStates.waiting_for_holders)

@dp.message(ScannerSettingsStates.waiting_for_holders)
async def process_holders(message: Message, state: FSMContext):
    try:
        val = int(message.text)
        update_user_setting(message.chat.id, "min_holders", val)
        await message.answer("✅ `Min Holders` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter an integer.")

@dp.callback_query(F.data == "set_mcap")
async def set_mcap_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the minimum Market Cap ($) for a token (e.g., 5000):")
    await state.set_state(ScannerSettingsStates.waiting_for_mcap)

@dp.message(ScannerSettingsStates.waiting_for_mcap)
async def process_mcap(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        update_user_setting(message.chat.id, "min_market_cap", val)
        await message.answer("✅ `Min Market Cap` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter a valid number.")

@dp.callback_query(F.data == "set_volume_m5")
async def set_volume_m5_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the minimum 5-minute volume ($) (e.g., 1000):")
    await state.set_state(ScannerSettingsStates.waiting_for_volume_m5)

@dp.message(ScannerSettingsStates.waiting_for_volume_m5)
async def process_volume_m5(message: Message, state: FSMContext):
    try:
        val = float(message.text)
        update_user_setting(message.chat.id, "min_volume_m5", val)
        await message.answer("✅ `Min Vol (5m)` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter a valid number.")

@dp.callback_query(F.data == "set_txns_m5")
async def set_txns_m5_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the minimum number of transactions in the last 5 minutes (e.g., 10):")
    await state.set_state(ScannerSettingsStates.waiting_for_txns_m5)

@dp.message(ScannerSettingsStates.waiting_for_txns_m5)
async def process_txns_m5(message: Message, state: FSMContext):
    try:
        val = int(message.text)
        update_user_setting(message.chat.id, "min_txns_m5", val)
        await message.answer("✅ `Min Txns (5m)` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter an integer.")

@dp.callback_query(F.data == "set_maxage")
async def set_maxage_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Enter the maximum allowed age of the token in minutes (e.g., 3, 5):")
    await state.set_state(ScannerSettingsStates.waiting_for_maxage)

@dp.message(ScannerSettingsStates.waiting_for_maxage)
async def process_maxage(message: Message, state: FSMContext):
    try:
        val = int(message.text)
        update_user_setting(message.chat.id, "max_age_minutes", val)
        await message.answer("✅ `Max Age` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter an integer.")

@dp.callback_query(F.data == "set_maxidle")
async def set_maxidle_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Enter the maximum allowed idle time (seconds since last tx) (e.g., 30, 60):")
    await state.set_state(ScannerSettingsStates.waiting_for_maxidle)

@dp.message(ScannerSettingsStates.waiting_for_maxidle)
async def process_maxidle(message: Message, state: FSMContext):
    try:
        val = int(message.text)
        update_user_setting(message.chat.id, "max_idle_seconds", val)
        await message.answer("✅ `Max Idle` setting updated!", reply_markup=get_autoscanner_keyboard(message.chat.id))
        await state.clear()
    except ValueError:
        await message.answer("Error! Please enter an integer.")

@dp.callback_query(F.data == "toggle_mayhem")
async def toggle_mayhem_filter(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    update_user_setting(chat_id, "filter_mayhem", not settings.get("filter_mayhem", True))
    await callback.message.edit_reply_markup(reply_markup=get_autoscanner_keyboard(chat_id))

@dp.callback_query(F.data == "toggle_socials")
async def toggle_socials_filter(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    settings = get_user_settings(chat_id)
    update_user_setting(chat_id, "require_socials", not settings.get("require_socials", False))
    await callback.message.edit_reply_markup(reply_markup=get_autoscanner_keyboard(chat_id))

# --- FSM TARGET SNIPER ---
@dp.callback_query(F.data == "add_target")
async def add_target_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Enter the contract address (Mint) of the token:")
    await state.set_state(TargetSniperStates.waiting_for_mint)

@dp.message(TargetSniperStates.waiting_for_mint)
async def process_target_mint(message: Message, state: FSMContext):
    await state.update_data(mint=message.text)
    await message.answer("At what Market Cap ($) should I alert you? Enter a number (e.g., 50000):")
    await state.set_state(TargetSniperStates.waiting_for_market_cap)

@dp.message(TargetSniperStates.waiting_for_market_cap)
async def process_target_mc(message: Message, state: FSMContext):
    try:
        mc = float(message.text)
        data = await state.get_data()
        mint = data['mint']
        
        # Check current market cap before adding
        import aiohttp
        from core.target_sniper import check_target_price
        async with aiohttp.ClientSession() as session:
            token_data = await check_target_price(session, mint)
            if token_data:
                current_mc = token_data['mc']
                if current_mc >= mc:
                    await message.answer(f"⚠️ Token already reached this market cap! Current MC is ${current_mc:,.0f}.\nPlease enter a higher target.")
                    return
        
        add_target(message.chat.id, mint, mc)
        await message.answer(f"✅ Target added!\nToken: {mint}\nTarget: ${mc:,.0f}")
        await state.clear()
    except ValueError:
        await message.answer("Please enter a valid number.")

@dp.callback_query(F.data == "list_targets")
async def list_user_targets(callback: CallbackQuery):
    targets = load_targets().get(str(callback.message.chat.id), [])
    if not targets:
        await callback.message.answer("You have no active targets.")
        return
    res = "<b>Your Targets:</b>\n\n"
    for t in targets:
        res += f"🔹 <code>{t['mint']}</code> -> ${t['target_mc']:,.0f}\n"
    await callback.message.answer(res, parse_mode='HTML')

async def start_bot():
    global scanner_task
    logger.info("Starting Telegram Bot...")
    
    logger.info("Target-Sniper loaded")
    # Start target sniper loop in background
    asyncio.create_task(target_sniper_loop(bot))
    
    logger.info("Auto-Scanner loaded")
    
    await dp.start_polling(bot)
