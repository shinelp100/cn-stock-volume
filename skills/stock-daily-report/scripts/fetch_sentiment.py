#!/usr/bin/env python3
"""
fetch_sentiment.py - 市场情绪（涨跌家数、涨停跌停数）
数据来源：AkShare
"""

import sys
import json
from datetime import datetime

AKSHARE_AVAILABLE = False
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    pass


def get_sentiment():
    """
    返回：
    {
        "up": int,        # 上涨家数
        "down": int,      # 下跌家数
        "limit_up": int,  # 涨停数（>=9.9%）
        "limit_down": int,# 跌停数（<=-9.9%）
        "flat": int,      # 平盘家数
        "ratio_str": str, # 涨跌比字符串 "1:6.4"
        "emotion_label": str  # 情绪标签
    }
    """
    if not AKSHARE_AVAILABLE:
        return _fallback_sentiment()

    try:
        df = ak.stock_zh_a_spot_em()
        df = df[df["最新价"] > 0]

        up   = len(df[df["涨跌幅"] > 0])
        down = len(df[df["涨跌幅"] < 0])
        flat = len(df[df["涨跌幅"] == 0])
        zt   = len(df[df["涨跌幅"] >= 9.9])
        dt   = len(df[df["涨跌幅"] <= -9.9])

        ratio = down / up if up > 0 else 0
        ratio_str = f"1:{ratio:.1f}"

        if up > down * 2:
            emotion = "市场情绪偏暖"
        elif up > down:
            emotion = "涨跌互现，分歧加大"
        elif down > up * 1.5:
            emotion = "跌多涨少，亏钱效应明显"
        else:
            emotion = "涨跌家数相对均衡"

        return {
            "up": up,
            "down": down,
            "flat": flat,
            "limit_up": zt,
            "limit_down": dt,
            "ratio": ratio,
            "ratio_str": ratio_str,
            "emotion_label": emotion,
            "status": "ok",
        }
    except Exception as e:
        print(f"⚠️ AkShare情绪数据获取失败: {e}")
        return _fallback_sentiment()


def _fallback_sentiment():
    return {
        "up": 0, "down": 0, "flat": 0,
        "limit_up": 0, "limit_down": 0,
        "ratio": 0, "ratio_str": "（数据获取中）",
        "emotion_label": "情绪数据获取中",
        "status": "fallback",
    }


if __name__ == "__main__":
    result = get_sentiment()
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"上涨: {result['up']} | 下跌: {result['down']} | 平盘: {result['flat']}")
        print(f"涨停: {result['limit_up']} | 跌停: {result['limit_down']}")
        print(f"涨跌比: {result['ratio_str']} | 情绪: {result['emotion_label']}")
