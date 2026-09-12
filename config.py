import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Helius RPC API Key
RPC_URL = os.getenv("RPC_URL", "https://api.mainnet-beta.solana.com")

MAX_TOP10_SHARE = 30.0
