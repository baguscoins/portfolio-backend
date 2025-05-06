
import ccxt
import pandas as pd
import numpy as np
import time
import requests
from ta import trend, momentum, volatility

# Konfigurasi
api_key = 'V9405LlmXnWkdu6D5fJZDdirM4Xgz7k1mQODCyO3qQoE1b7e99US04Zyz6HUfDbU'
api_secret = 'R4VuEWTyeRwXL2CrG8QPA09LSRO0y3JbvqRS8dbqn5aJ47X0BavLwv2yjhYxCkHo'
symbol = 'BTC/USDT'
leverage = 50
capital = 0.5  # modal kecil

# Telegram Notif
TELEGRAM_TOKEN = '7530501429:AAHfydazLZivvPR-vUCqBXuT-9Dc9_SahrI'
CHAT_ID = '6493878565'

def send_telegram(msg):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def fetch_data(symbol, timeframe='5m', limit=100):
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def add_indicators(df):
    df['rsi'] = momentum.RSIIndicator(df['close']).rsi()
    df['ema20'] = trend.EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema50'] = trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['cci'] = trend.CCIIndicator(df['high'], df['low'], df['close']).cci()
    bb = volatility.BollingerBands(df['close'])
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    df['sar'] = trend.PSARIndicator(df['high'], df['low'], df['close']).psar()
    df['stoch_k'] = momentum.StochasticOscillator(df['high'], df['low'], df['close']).stoch()
    df['stoch_d'] = momentum.StochasticOscillator(df['high'], df['low'], df['close']).stoch_signal()
    return df

def signal(df):
    last = df.iloc[-1]
    if last['rsi'] < 30 and last['close'] < last['bb_low'] and last['cci'] < -100:
        return 'buy'
    elif last['rsi'] > 70 and last['close'] > last['bb_high'] and last['cci'] > 100:
        return 'sell'
    return ''

def calculate_qty(price):
    usdt_amount = capital
    return round(usdt_amount * leverage / price, 3)

def place_order(order_type, symbol, qty):
    side = 'buy' if order_type == 'buy' else 'sell'
    print(f"[+] Placing {side.upper()} order at qty {qty}...")
    send_telegram(f"📢 Order {side.upper()} dibuka: {symbol} | Qty: {qty}")
    return exchange.create_market_order(symbol, side, qty)

while True:
    try:
        df = fetch_data(symbol)
        df = add_indicators(df)
        sig = signal(df)
        price = df['close'].iloc[-1]
        qty = calculate_qty(price)
        print(f"[~] Price: {price} | Signal: {sig} | Qty: {qty}")

        if sig == 'buy':
            place_order('buy', symbol, qty)
        elif sig == 'sell':
            place_order('sell', symbol, qty)

        time.sleep(60)

    except Exception as e:
        print(f"[ERROR] {e}")
        send_telegram(f"[ERROR] {str(e)}")
        time.sleep(60)
