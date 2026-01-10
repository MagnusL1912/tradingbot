# =========================
# PAPER TRADING BOT v5
# MULTI-TIMEFRAME + RISK MGMT
# =========================

import ccxt
import pandas as pd
import ta
import time
import requests
from datetime import datetime, timedelta

# ===== SETTINGS =====
DISCORD_WEBHOOK_URL = "DIN_DISCORD_WEBHOOK"

START_BALANCE = 100000.0
TRADE_PERCENT = 0.03

ENTRY_TF = "5m"
TREND_TF = "1h"
LIMIT = 200

RSI_BUY = 35

EMA_FAST = 9
EMA_SLOW = 21
EMA_TREND = 200

STOP_LOSS = 0.02
TAKE_PROFIT = 0.04

MAX_OPEN_TRADES = 2
MAX_LOSSES_IN_ROW = 3
LOSS_COOLDOWN_MIN = 15
GLOBAL_PAUSE_MIN = 30

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "BNB/USDT", "XRP/USDT", "AVAX/USDT"
]

# ===== EXCHANGE =====
exchange = ccxt.bybit({"enableRateLimit": True})

# ===== STATE =====
balance = START_BALANCE
positions = {}
trades = 0
wins = 0
losses = 0
loss_streak = 0
last_loss_time = None
global_pause_until = None

# ===== HELPERS =====
def send_discord(msg):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": msg})
    except:
        pass

def fetch_tf(symbol, tf):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=LIMIT)
    df = pd.DataFrame(ohlcv, columns=["t","o","h","l","c","v"])
    return df

# ===== START =====
send_discord("🤖 **Bot v5 startet (RISK MGMT ON)**")
print("Bot kører...")

# ===== LOOP =====
while True:
    now = datetime.utcnow()

    # GLOBAL PAUSE
    if global_pause_until and now < global_pause_until:
        time.sleep(30)
        continue

    for symbol in SYMBOLS:
        try:
            # MAX OPEN TRADES
            if len(positions) >= MAX_OPEN_TRADES:
                break

            # LOSS COOLDOWN
            if last_loss_time and now < last_loss_time + timedelta(minutes=LOSS_COOLDOWN_MIN):
                continue

            # ===== TREND (1H) =====
            df_trend = fetch_tf(symbol, TREND_TF)
            df_trend["ema200"] = ta.trend.EMAIndicator(df_trend["c"], EMA_TREND).ema_indicator()
            trend = df_trend.iloc[-1]

            if trend["c"] <= trend["ema200"]:
                continue

            # ===== ENTRY (5M) =====
            df = fetch_tf(symbol, ENTRY_TF)
            df["rsi"] = ta.momentum.RSIIndicator(df["c"], 14).rsi()
            df["ema_fast"] = ta.trend.EMAIndicator(df["c"], EMA_FAST).ema_indicator()
            df["ema_slow"] = ta.trend.EMAIndicator(df["c"], EMA_SLOW).ema_indicator()

            row = df.iloc[-1]
            price = row["c"]

            # ===== BUY =====
            if symbol not in positions:
                if row["rsi"] < RSI_BUY and row["ema_fast"] > row["ema_slow"]:
                    usd = balance * TRADE_PERCENT
                    amount = usd / price

                    balance -= usd
                    positions[symbol] = {
                        "entry": price,
                        "amount": amount,
                        "sl": price * (1 - STOP_LOSS),
                        "tp": price * (1 + TAKE_PROFIT)
                    }

                    send_discord(f"🟢 BUY {symbol} @ {price:.2f}")

            # ===== SELL =====
            elif symbol in positions:
                pos = positions[symbol]

                if price <= pos["sl"] or price >= pos["tp"]:
                    value = pos["amount"] * price
                    pnl = value - (pos["amount"] * pos["entry"])

                    balance += value
                    trades += 1

                    if pnl > 0:
                        wins += 1
                        loss_streak = 0
                    else:
                        losses += 1
                        loss_streak += 1
                        last_loss_time = now

                    del positions[symbol]

                    send_discord(
                        f"🔴 SELL {symbol}\n"
                        f"P/L: {pnl:.2f}\n"
                        f"Balance: {balance:.2f}"
                    )

                    # GLOBAL PAUSE
                    if loss_streak >= MAX_LOSSES_IN_ROW:
                        global_pause_until = now + timedelta(minutes=GLOBAL_PAUSE_MIN)
                        loss_streak = 0
                        send_discord("⏸️ **Bot paused (3 losses in a row)**")

            time.sleep(1)

        except Exception as e:
            print(symbol, e)

    winrate = (wins / trades * 100) if trades > 0 else 0
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Balance: {balance:.2f} | Winrate: {winrate:.2f}%")
    time.sleep(60)
