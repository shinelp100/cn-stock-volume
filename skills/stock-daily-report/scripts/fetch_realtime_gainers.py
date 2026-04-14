#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时获取同花顺问财数据（独立脚本）

可以直接运行，也可以被其他脚本导入使用。
不依赖 openclaw CLI，而是通过浏览器自动化获取数据。

使用方式：
    python3 fetch_realtime_gainers.py
"""

import sys
import json
import subprocess
from pathlib import Path

# 配置
IWINCAI_URL = "https://www.iwencai.com/unifiedwap/result?w=近 10 日涨幅排名"
LIMIT = 20
EXCLUDE_ST = True


def fetch_via_browser() -> dict:
    """
    通过 browser 工具获取数据
    
    Returns:
        browser 操作结果
    """
    # 使用 openclaw browser 工具
    # 注意：这个脚本应该在 OpenClaw 会话中运行，可以访问 browser 工具
    
    # 打开页面
    print(f"🌐 访问同花顺问财...")
    
    # 返回需要执行的操作（由调用方执行）
    return {
        "action": "browser_fetch",
        "url": IWINCAI_URL,
        "limit": LIMIT,
        "exclude_st": EXCLUDE_ST,
    }


def parse_snapshot_to_stocks(snapshot_text: str, limit: int = 20, exclude_st: bool = True) -> list:
    """
    解析 browser snapshot 数据
    
    从 snapshot 中提取表格行数据
    """
    import re
    
    stocks = []
    
    # 查找表格行（格式：row "1 600396 华电辽能 6.89 10.06 1/487 89.81"）
    row_pattern = r'row "(\d+)\s+(\d{6})\s+([^"]+)\s+([\d.]+)\s+(-?[\d.]+)\s+\d+/\d+\s+(-?[\d.]+)"'
    
    for match in re.finditer(row_pattern, snapshot_text):
        rank = int(match.group(1))
        code = match.group(2)
        name = match.group(3)
        price = float(match.group(4))
        today_change = float(match.group(5))
        gain_10d = float(match.group(6))
        
        # 排除 ST 股票
        if exclude_st and "ST" in name.upper():
            continue
        
        stocks.append({
            "排名": rank,
            "股票代码": code,
            "股票简称": name,
            "收盘价": price,
            "10 日涨幅": gain_10d,
            "今日涨跌": today_change,
        })
        
        if len(stocks) >= limit:
            break
    
    return stocks


def main():
    """主函数"""
    print("="*60)
    print("实时获取同花顺问财数据")
    print("="*60)
    
    # 这个脚本需要配合 browser 工具使用
    # 输出 browser 操作指令
    
    result = fetch_via_browser()
    
    print(f"\n需要执行以下 browser 操作：")
    print(f"  1. browser open --url {result['url']}")
    print(f"  2. 等待 3 秒")
    print(f"  3. browser snapshot --refs aria")
    print(f"  4. 解析 snapshot 提取数据")
    
    print("\n⚠️  注意：这个脚本需要在 OpenClaw 会话中运行，以便访问 browser 工具")
    print("   或者手动执行上述 browser 命令，然后使用 parse_snapshot_to_stocks() 解析结果")
    
    return result


if __name__ == "__main__":
    main()
