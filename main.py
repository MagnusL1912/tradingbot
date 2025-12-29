import ccxt
import time
import requests
import pandas as pd

# =========================
# 🔧 SKAL DU ÆNDRE
# =========================
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1450907994002034748/bkVfSwMdq9V9fxVBR2QpfjUBbVcLpDxoTXhXq_u9F6YAWbGNrMeCYr4SYAyE8UaWso2t"

# 20 coins (spot)
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "LTC/USDT", "UNI/USDT", "ATOM/USDT", "ETC/USDT",
    "FIL/USDT", "APT/USDT", "ARB/USDT", "OP/USDT", "NEAR/USDT"
]

TIMEFRAME = "5m"
CANDLE_LIMIT = 100
SCAN_DELAY = 60  # sekunder mellem scanninger

# =========================
# 📡 DISCORD
# =========================
def send_discord(msg):
    data = {"content": msg}
    requests.post(DISCORD_WEBHOOK_URL, json=data)

# =========================
# 📊 INDIKATORER
# =========================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# =========================
# 🔌 BINANCE (SPOT ONLY)
# =========================
exchange = ccxt.binance({
    "enableRateLimit": True,
    "options": {
        "defaultType": "spot",   # 🚫 ingen futures
    }
})

exchange.load_markets()

send_discord("🤖 **Scanner bot startet (paper trading)**")

# =========================
# 🔄 MAIN LOOP
# =========================
while True:
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=CANDLE_LIMIT)
            df = pd.DataFrame(
                ohlcv,
                columns=["time", "open", "high", "low", "close", "volume"]
            )

            df["rsi"] = rsi(df["close"])
            df["ema50"] = ema(df["close"], 50)
            df["ema200"] = ema(df["close"], 200)

            last = df.iloc[-1]
            price = round(last["close"], 4)
            rsi_val = round(last["rsi"], 2)

            # 🔔 SIMPEL SIGNAL LOGIK
            if rsi_val < 30 and last["ema50"] > last["ema200"]:
                send_discord(
                    f"🟢 **PAPER BUY SIGNAL**\n"
                    f"{symbol}\n"
                    f"Pris: {price}\n"
                    f"RSI: {rsi_val}"
                )

            elif rsi_val > 70:
                send_discord(
                    f"🔴 **PAPER SELL SIGNAL**\n"
                    f"{symbol}\n"
                    f"Pris: {price}\n"
                    f"RSI: {rsi_val}"
                )

        except Exception:
            # 🚫 ingen Binance fejl spam
            pass

    time.sleep(SCAN_DELAY)
