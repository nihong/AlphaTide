import pytest
import pandas as pd
import numpy as np
from src.bullwhip_engine import BullwhipEngine
from unittest.mock import patch

class TestBullwhipEngine:
    def setup_method(self):
        self.engine = BullwhipEngine()

    @patch('src.bullwhip_engine.fetch_a_stock_hist_cached')
    def test_evaluate_exit_not_triggered(self, mock_fetch):
        # 伪造一段平稳上涨的 K 线数据
        data = {
            '最高': [100.0] * 20,
            '最低': [98.0] * 20,
            '收盘': [99.0] * 20
        }
        mock_df = pd.DataFrame(data)
        mock_fetch.return_value = mock_df

        # 最高价 100，现价 99。TR = 2，ATR_14 = 2。
        # 追踪止损位 = 100 - (2.5 * 2) = 95。
        # 现价 99 > 95，不应触发退出。
        should_exit = self.engine.evaluate_exit('sh600519', entry_price=90.0, highest_price=100.0)
        assert should_exit is False, "正常波动范围内不应触发斩仓"

    @patch('src.bullwhip_engine.fetch_a_stock_hist_cached')
    def test_evaluate_exit_triggered_by_atr(self, mock_fetch):
        # 伪造一段前期平稳，最后一日暴跌的 K 线
        data = {
            '最高': [100.0] * 19 + [90.0],
            '最低': [98.0] * 19 + [88.0],
            '收盘': [99.0] * 19 + [89.0] # 最后一天收盘暴跌到 89
        }
        mock_df = pd.DataFrame(data)
        mock_fetch.return_value = mock_df
        
        # 历史最高价 100，现价 89。ATR大约在 2 左右。
        # 追踪止损位 = 100 - (2.5 * 2) = 95。
        # 现价 89 < 95，必须触发退出！
        should_exit = self.engine.evaluate_exit('sh600519', entry_price=90.0, highest_price=100.0)
        assert should_exit is True, "暴跌跌破 2.5 倍 ATR，必须强制触发斩仓"

    @patch('src.bullwhip_engine.fetch_a_stock_hist_cached')
    def test_evaluate_exit_triggered_by_ema50(self, mock_fetch):
        # 伪造一段长期阴跌，现价跌破 50 日均线的 K 线
        closes = list(np.linspace(100, 80, 60)) # 60天内从 100 跌到 80
        data = {
            '最高': [c + 1 for c in closes],
            '最低': [c - 1 for c in closes],
            '收盘': closes
        }
        mock_df = pd.DataFrame(data)
        mock_fetch.return_value = mock_df

        # 最后一日收盘价 80，远低于前 50 日均线
        should_exit = self.engine.evaluate_exit('sh600519', entry_price=100.0, highest_price=100.0)
        assert should_exit is True, "跌破 50 日均线，必须强制触发斩仓"
