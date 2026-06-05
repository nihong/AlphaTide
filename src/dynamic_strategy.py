import numpy as np
import pandas as pd

def generate_signals(df):
    df['ma5'] = df['收盘'].rolling(5).mean()
    df['ma10'] = df['收盘'].rolling(10).mean()
    df['ma20'] = df['收盘'].rolling(20).mean()
    df['ma60'] = df['收盘'].rolling(60).mean()
    ema12 = df['收盘'].ewm(span=12).mean()
    ema26 = df['收盘'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_sig'] = df['macd'].ewm(span=9).mean()
    delta = df['收盘'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    buy_signal = ((df['rsi'] < 30)) & ((df['macd'] > df['macd_sig']) & (df['macd'].shift(1) <= df['macd_sig'].shift(1)))
    tr1 = df['最高'] - df['最低']
    tr2 = (df['最高'] - df['收盘'].shift(1)).abs()
    tr3 = (df['最低'] - df['收盘'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    stop_distance = atr * 0.996960736116727
    return buy_signal, stop_distance
