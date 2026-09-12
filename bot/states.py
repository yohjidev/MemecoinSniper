from aiogram.fsm.state import State, StatesGroup

class TargetSniperStates(StatesGroup):
    waiting_for_mint = State()
    waiting_for_market_cap = State()

class ScannerSettingsStates(StatesGroup):
    waiting_for_devbuy = State()
    waiting_for_holders = State()
    waiting_for_mcap = State()
    waiting_for_volume_m5 = State()
    waiting_for_txns_m5 = State()
    waiting_for_maxage = State()
    waiting_for_maxidle = State()
