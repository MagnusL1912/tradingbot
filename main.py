# =========================
# ADVANCED PAPER TRADING BOT
# RSI + EMA + TREND
# STOP LOSS & TAKE PROFIT
# =========================

import ccxt
import pandas as pd
import ta
import time
import requests
from datetime import datetime

# ===== SETTINGS =====
DISCORD_WEBHOOK_URL = "DIN_DISCORD_WEBHOOK"

START_BALANCE = 100000.0
TRADE_PERCENT = 0.03

TIMEFRAME = "5m"
LIMIT = 200

RSI_BUY = 35
RSI_SELL = 65

EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 200

STOP_LOSS_PCT = 0.02     # 2%
TAKE_PROFIT_PCT = 0.04  # 4%

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "BNB/USDT", "XRP/USDT", "AVAX/USDT"
]

# ===== EXCHANGE (PUBLIC DATA) =====
exchange = ccxt.bybit({"enableRateLimit": True})

# ===== STATE =====
balance = START_BALANCE
positions = {}

# ===== HELPERS =====
def send_discord(msg):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except:
        pass

def indicators(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])

    df["rsi"] = ta.momentum.RSIIndicator(df["c"], 14).rsi()
    df["ema_fast"] = ta.trend.EMAIndicator(df["c"], EMA_FAST).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["c"], EMA_SLOW).ema_indicator()
    df["ema_trend"] = ta.trend.EMAIndicator(df["c"], EMA_TREND).ema_indicator()

    return df.iloc[-1]

# ===== START =====
send_discord("🤖 Bot startet (Paper)\nBalance: 100,000 USD")
print("Bot kører...")

# ===== LOOP =====
while True:
    for symbol in SYMBOLS:
        try:
            data = indicators(symbol)
            price = data["c"]

            rsi = data["rsi"]
            ema_fast = data["ema_fast"]
            ema_slow = data["ema_slow"]
            ema_trend = data["ema_trend"]

            uptrend = price > ema_trend

            # ===== BUY =====
            if symbol not in positions and uptrend:
                if rsi < RSI_BUY and ema_fast > ema_slow:
                    usd = balance * TRADE_PERCENT
                    amount = usd / price

                    balance -= usd
                    positions[symbol] = {
                        "entry": price,
                        "amount": amount,
                        "sl": price * (1 - STOP_LOSS_PCT),
                        "tp": price * (1 + TAKE_PROFIT_PCT)
                    }

                    send_discord(
                        f"🟢 BUY {symbol}\n"
                        f"Pris: {price:.2f}\n"
                        f"SL: {positions[symbol]['sl']:.2f}\n"
                        f"TP: {positions[symbol]['tp']:.2f}"
                    )

            # ===== MANAGE POSITION =====
            elif symbol in positions:
                pos = positions[symbol]

                # STOP LOSS
                if price <= pos["sl"]:
                    value = pos["amount"] * price
                    pnl = value - (pos["amount"] * pos["entry"])
                    balance += value
                    del positions[symbol]

                    send_discord(
                        f"🛑 STOP LOSS {symbol}\n"
                        f"P/L: {pnl:.2f}\nBalance: {balance:.2f}"
                    )

                # TAKE PROFIT
                elif price >= pos["tp"]:
                    value = pos["amount"] * price
                    pnl = value - (pos["amount"] * pos["entry"])
                    balance += value
                    del positions[symbol]

                    send_discord(
                        f"💰 TAKE PROFIT {symbol}\n"
                        f"P/L: {pnl:.2f}\nBalance: {balance:.2f}"
                    )

            time.sleep(1)

        except Exception as e:
            print(f"{symbol} fejl: {e}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Balance: {balance:.2f}")
    time.sleep(60)
