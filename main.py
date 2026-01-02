# =========================
# PAPER TRADING BOT (NO REAL MONEY)
# Start balance: 5000 USD
# Strategy: RSI + EMA
# Sends signals to Discord
# =========================

import ccxt
import pandas as pd
import ta
import time
import requests
from datetime import datetime

# ====== SETTINGS ======
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1450907994002034748/bkVfSwMdq9V9fxVBR2QpfjUBbVcLpDxoTXhXq_u9F6YAWbGNrMeCYr4SYAyE8UaWso2t"

START_BALANCE = 5000.0
TRADE_PERCENT = 0.05      # 5% per trade
TIMEFRAME = "5m"
LIMIT = 100

RSI_BUY = 30
RSI_SELL = 70

EMA_FAST = 9
EMA_SLOW = 21

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
    "LTC/USDT", "LINK/USDT", "ATOM/USDT", "OP/USDT", "ARB/USDT",
    "SUI/USDT", "APT/USDT", "TRX/USDT", "FIL/USDT", "NEAR/USDT"
]

# ====== EXCHANGE (PUBLIC DATA ONLY) ======
exchange = ccxt.binance({
    "enableRateLimit": True
})

# ====== STATE ======
balance = START_BALANCE
positions = {}  # symbol -> {entry_price, amount}

# ====== HELPERS ======
def send_discord(msg):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except:
        pass

def fetch_indicators(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=EMA_FAST).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=EMA_SLOW).ema_indicator()

    return df.iloc[-1]

# ====== START ======
send_discord("🤖 **Paper Trading Bot startet**\nStart balance: **5000 USD**")

print("Bot kører...")

# ====== MAIN LOOP ======
while True:
    for symbol in SYMBOLS:
        try:
            data = fetch_indicators(symbol)
            price = data["close"]
            rsi = data["rsi"]
            ema_fast = data["ema_fast"]
            ema_slow = data["ema_slow"]

            # ===== BUY =====
            if symbol not in positions:
                if rsi < RSI_BUY and ema_fast > ema_slow:
                    trade_usd = balance * TRADE_PERCENT
                    amount = trade_usd / price

                    if trade_usd > balance:
                        continue

                    balance -= trade_usd
                    positions[symbol] = {
                        "entry_price": price,
                        "amount": amount
                    }

                    send_discord(
                        f"🟢 **BUY (PAPER)** {symbol}\n"
                        f"Pris: {price:.2f}\n"
                        f"RSI: {rsi:.2f}\n"
                        f"Balance: {balance:.2f} USD"
                    )

            # ===== SELL =====
            else:
                entry = positions[symbol]["entry_price"]
                amount = positions[symbol]["amount"]

                if rsi > RSI_SELL and ema_fast < ema_slow:
                    trade_value = amount * price
                    pnl = trade_value - (amount * entry)
                    balance += trade_value

                    del positions[symbol]

                    send_discord(
                        f"🔴 **SELL (PAPER)** {symbol}\n"
                        f"Pris: {price:.2f}\n"
                        f"P/L: {pnl:.2f} USD\n"
                        f"Balance: {balance:.2f} USD"
                    )

            time.sleep(1)

        except Exception as e:
            print(f"Fejl på {symbol}: {e}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Balance: {balance:.2f} USD")
    time.sleep(60)
