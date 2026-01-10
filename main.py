# =========================
# PAPER TRADING BOT v3
# RSI + EMA + TREND
# STOP LOSS / TAKE PROFIT
# FULL STATISTICS
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

STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "SOL/USDT",
    "BNB/USDT", "XRP/USDT", "AVAX/USDT"
]

# ===== EXCHANGE (PUBLIC DATA) =====
exchange = ccxt.bybit({"enableRateLimit": True})

# ===== STATE =====
balance = START_BALANCE
peak_balance = START_BALANCE
positions = {}

# ===== STATS =====
total_trades = 0
wins = 0
losses = 0
total_pnl = 0.0
last_report = time.time()

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
send_discord("🤖 Bot startet (Paper Trading)\nBalance: 100,000 USD")
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

                    send_discord(f"🟢 BUY {symbol} @ {price:.2f}")

            # ===== MANAGE =====
            elif symbol in positions:
                pos = positions[symbol]

                exit_trade = False

                if price <= pos["sl"]:
                    exit_trade = True

                elif price >= pos["tp"]:
                    exit_trade = True

                if exit_trade:
                    value = pos["amount"] * price
                    pnl = value - (pos["amount"] * pos["entry"])

                    balance += value
                    total_trades += 1
                    total_pnl += pnl

                    if pnl > 0:
                        wins += 1
                    else:
                        losses += 1

                    del positions[symbol]

                    send_discord(
                        f"🔁 CLOSE {symbol}\n"
                        f"P/L: {pnl:.2f}\n"
                        f"Balance: {balance:.2f}"
                    )

            peak_balance = max(peak_balance, balance)
            time.sleep(1)

        except Exception as e:
            print(symbol, e)

    # ===== HOURLY REPORT =====
    if time.time() - last_report > 3600:
        winrate = (wins / total_trades * 100) if total_trades > 0 else 0
        drawdown = (peak_balance - balance)

        send_discord(
            f"📊 **BOT STATUS**\n"
            f"Trades: {total_trades}\n"
            f"Winrate: {winrate:.2f}%\n"
            f"P/L: {total_pnl:.2f} USD\n"
            f"Drawdown: {drawdown:.2f}\n"
            f"Balance: {balance:.2f}"
        )

        last_report = time.time()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Balance: {balance:.2f}")
    time.sleep(60)
