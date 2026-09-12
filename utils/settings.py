import json
import os
from typing import Dict

USERS_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'users.json')

DEFAULT_SETTINGS = {
    "auto_scanner_enabled": False,
    "target_sniper_enabled": False,
    "min_dev_buy_sol": 0.1,
    "jito_filter": False,
    "min_market_cap": 5000,
    "min_holders": 20,
    "min_volume_m5": 1000,
    "min_txns_m5": 10,
    "max_age_minutes": 5,
    "max_idle_seconds": 60,
    "filter_mayhem": True,
    "require_socials": False
}

def load_users() -> Dict[str, dict]:
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        return {}
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users: Dict[str, dict]):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def get_user_settings(chat_id: str) -> dict:
    users = load_users()
    chat_id_str = str(chat_id)
    if chat_id_str not in users:
        users[chat_id_str] = DEFAULT_SETTINGS.copy()
        save_users(users)
    return users[chat_id_str]

def update_user_setting(chat_id: str, key: str, value):
    users = load_users()
    chat_id_str = str(chat_id)
    if chat_id_str not in users:
        users[chat_id_str] = DEFAULT_SETTINGS.copy()
    
    users[chat_id_str][key] = value
    save_users(users)
