import numpy as np
import pandas as pd

def generate_signals(df):
    ma_f = df['收盘'].rolling(73).mean()
    ma_s = df['收盘'].rolling(142).mean()
    buy_signal = (ma_f > ma_s) & (ma_f.shift(1) <= ma_s.shift(1))
    
    tr1 = df['最高'] - df['最低']
    tr2 = (df['最高'] - df['收盘'].shift(1)).abs()
    tr3 = (df['最低'] - df['收盘'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    
    stop_distance = atr * 3.60
    return buy_signal, stop_distance
