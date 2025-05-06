
from binance.client import Client

import pandas as pd
from ta.momentum import RSIIndicator
from datetime import datetime
import time
import threading
import requests
import math

api_key = 'V9405LlmXnWkdu6D5fJZDdirM4Xgz7k1mQODCyO3qQoE1b7e99US04Zyz6HUfDbU'
api_secret = 'R4VuEWTyeRwXL2CrG8QPA09LSRO0y3JbvqRS8dbqn5aJ47X0BavLwv2yjhYxCkHo'
client = Client(api_key, api_secret)

interval = '1m'
qty_usdt = 0.5
leverage = 125
rsi_window = 7
symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']

TELEGRAM_TOKEN = '7530501429:AAHfydazLZivvPR-vUCqBXuT-9Dc9_SahrI'
TELEGRAM_CHAT_ID = '6493878565'

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})

def log(symbol, msg, notify=False):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    filename = f"scalp_final_{symbol}.txt"
    full_msg = f"[{timestamp}] [{symbol}] {msg}"
    with open(filename, "a") as f:
        f.write(full_msg + "\n")
    print(full_msg)
    if notify:
        send_telegram(full_msg)

def get_price(symbol):
    ticker = client.futures_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def get_ohlcv(symbol):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=20)
    df = pd.DataFrame(klines, columns=['time','o','h','l','c','v','ct','qv','ntrd','tbb','tbq','ignore'])
    df['c'] = df['c'].astype(float)
    df['o'] = df['o'].astype(float)
    return df

def get_signal(df):
    rsi = RSIIndicator(close=df['c'], window=rsi_window).rsi().iloc[-1]
    candle_bull = df['c'].iloc[-1] > df['o'].iloc[-1]
    candle_bear = df['c'].iloc[-1] < df['o'].iloc[-1]
    if rsi < 30 and candle_bull:
        return rsi, 'LONG'
    elif rsi > 70 and candle_bear:
        return rsi, 'SHORT'
    else:
        return rsi, 'WAIT'

def has_open_position(symbol, position):
    positions = client.futures_position_information(symbol=symbol)
    for pos in positions:
        if pos['positionSide'] == position and float(pos['positionAmt']) != 0:
            return True
    return False

def adjust_quantity(symbol, qty):
    info = client.futures_exchange_info()
    for s in info['symbols']:
        if s['symbol'] == symbol:
            step_size = float([f['stepSize'] for f in s['filters'] if f['filterType'] == 'LOT_SIZE'][0])
            precision = int(round(-math.log(step_size, 10), 0))
            return round(qty, precision)
    return qty

def place_order(symbol, position):
    mark_price = get_price(symbol)
    raw_qty = qty_usdt * leverage / mark_price
    qty = adjust_quantity(symbol, raw_qty)

    side = 'BUY' if position == 'LONG' else 'SELL'
    opposite = 'SELL' if position == 'LONG' else 'BUY'

    # Market order
    client.futures_create_order(
        symbol=symbol,
        side=side,
        positionSide=position,
        type='MARKET',
        quantity=qty
    )
    log(symbol, f"{position} EXECUTED at {mark_price:.2f} qty {qty}", notify=True)

    tp = round(mark_price * (1.006 if position == 'LONG' else 0.994), 2)
    sl = round(mark_price * (0.997 if position == 'LONG' else 1.003), 2)

    # TP
    client.futures_create_order(
        symbol=symbol,
        side=opposite,
        positionSide=position,
        type='STOP_MARKET',
        stopPrice=tp,
        closePosition=True,
        timeInForce='GTC'
    )

    # SL
    client.futures_create_order(
        symbol=symbol,
        side=opposite,
        positionSide=position,
        type='STOP_MARKET',
        stopPrice=sl,
        closePosition=True,
        timeInForce='GTC'
    )

    log(symbol, f"TP at {tp}, SL at {sl}", notify=True)

def bot_worker(symbol):
    log(symbol, "Final bot started (Fast+Notify+Fix+Hedge)")
    while True:
        try:
            df = get_ohlcv(symbol)
            rsi_val, signal = get_signal(df)
            log(symbol, f"RSI: {rsi_val:.2f} | Signal: {signal}")
            if signal in ['LONG', 'SHORT'] and not has_open_position(symbol, signal):
                place_order(symbol, signal)
            time.sleep(30)
        except Exception as e:
            log(symbol, f"Error: {str(e)}", notify=True)
            time.sleep(60)

for symbol in symbols:
    threading.Thread(target=bot_worker, args=(symbol,), daemon=True).start()

while True:
    time.sleep(3600)
