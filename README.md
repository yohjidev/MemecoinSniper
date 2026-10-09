# Memecoin Sniper Bot

An automated Telegram bot for monitoring, scanning, and sniping memecoins on Solana (Pump.fun / Raydium) using Helius RPC & DexScreener APIs.

## Features

- **Auto-Scanner**: Real-time WebSocket connection to Pump.fun for new token launches.
- **Target-Sniper**: Custom target tracking alert system based on Market Cap threshold.
- **Advanced Filters**: Dev wallet activity checks, volume & transaction liquidity analysis, mayhem/honeypot filtering, and social link requirements.
- **Interactive Telegram UI**: Easily toggle settings, filters, and thresholds directly from Telegram keyboards.

## Project Structure

```
memecoin-sniper/
├── bot/
│   ├── keyboards.py       # Telegram inline keyboards
│   ├── main.py            # Main Telegram bot handlers & dispatcher
│   └── states.py           # FSM state definitions
├── core/
│   ├── advanced_filters.py # Dev activity, socials & idle time checks
│   ├── auto_scanner.py     # Pump.fun WebSocket scanner loop
│   ├── flow_analyzer.py    # DexScreener momentum & volume analyzer
│   └── target_sniper.py    # Target market cap alert loop
├── data/                  # Runtime storage for users & targets
├── utils/
│   └── settings.py        # Settings management & JSON persistence
├── config.py              # Configuration & Environment loader
├── main.py                # Main application entry point
├── .env.example           # Environment variables template
├── requirements.txt       # Python dependencies
└── README.md
```

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/your-username/memecoin-sniper.git
cd memecoin-sniper
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your details:
```bash
cp .env.example .env
```

Edit `.env`:
```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_api_key
```

### 4. Run the Bot
```bash
python main.py
```

## License
MIT License
