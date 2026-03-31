#!/usr/bin/env python3
"""
browser_fetch.py - 通过浏览器自动化获取同花顺问财数据
需要 OpenClaw 浏览器工具支持

功能：
1. 获取近10日涨幅排名
2. 提取主板/创业板冠军
3. 提取高位股票
"""

import sys
import json
import re
import time

def parse_iwencai_table(snapshot_text: str) -> list:
    """
    从同花顺问财快照中解析股票表格数据
    
    快照格式示例：
    row "1 920069 普昂医疗 43.48 136.56 1/795 136.56" [ref=e212]
    
    提取字段：
    - 排名
    - 代码
    - 名称
    - 现价
    - 当日涨跌幅
    - 区间涨跌幅排名
    - 区间涨跌幅
    """
    stocks = []
    
    # 匹配 row 模式
    # row "1 920069 普昂医疗 43.48 136.56 1/795 136.56" [ref=e212]
    row_pattern = r'row "(\d+)\s+(\d+)\s+([^\s]+)\s+([0-9,.]+)\s+([-\d.]+)\s+(\d+/\d+)\s+([-\d.]+)"'
    
    matches = re.findall(row_pattern, snapshot_text)
    
    for match in matches:
        try:
            rank, code, name, price, today_chg, period_rank, period_chg = match
            
            # 清理数字格式
            price = float(price.replace(',', ''))
            today_chg = float(today_chg)
            period_chg = float(period_chg)
            
            stocks.append({
                "rank": int(rank),
                "code": code,
                "name": name,
                "price": price,
                "today_chg": today_chg,
                "period_rank": period_rank,
                "period_chg": period_chg
            })
        except Exception as e:
            print(f"⚠️ 解析失败: {e}, match={match}")
            continue
    
    return stocks

def get_main_board_champion(stocks: list) -> dict:
    """
    获取主板冠军（600/601/603开头，排除ST）
    """
    for stock in stocks:
        code = stock.get("code", "")
        name = stock.get("name", "")
        
        # 主板代码：600/601/603/605
        # 排除 ST 股票
        if code.startswith(("600", "601", "603", "605")) and not name.startswith("ST") and "*ST" not in name:
            return stock
    
    return None

def get_gem_champion(stocks: list) -> dict:
    """
    获取创业板冠军（300开头）
    """
    for stock in stocks:
        code = stock.get("code", "")
        
        if code.startswith("300"):
            return stock
    
    return None

def get_high_stocks(stocks: list, threshold: float = 40.0) -> list:
    """
    获取高位股票（10日涨幅超过阈值，排除ST）
    """
    high_stocks = []
    
    for stock in stocks:
        period_chg = stock.get("period_chg", 0)
        name = stock.get("name", "")
        
        # 排除 ST 股票
        if period_chg >= threshold and not name.startswith("ST") and "*ST" not in name:
            high_stocks.append(stock)
    
    return high_stocks

def build_browser_data(stocks: list) -> dict:
    """
    构建完整的浏览器数据结构
    """
    if not stocks:
        return {
            "success": False,
            "error": "未获取到股票数据",
            "main_board_champion": None,
            "gem_champion": None,
            "high_stocks": [],
            "total_count": 0
        }
    
    main_board = get_main_board_champion(stocks)
    gem_board = get_gem_champion(stocks)
    high_stocks = get_high_stocks(stocks, threshold=40.0)
    
    return {
        "success": True,
        "main_board_champion": main_board,
        "gem_champion": gem_board,
        "high_stocks": high_stocks[:5],  # 取前5个
        "total_count": len(stocks)
    }

def print_market_feedback(data: dict):
    """
    打印市场反馈数据（用于调试）
    """
    print("\n" + "="*60)
    print("📊 市场反馈数据")
    print("="*60)
    
    # 主板冠军
    main = data.get("main_board_champion")
    if main:
        print(f"\n🏆 主板冠军：")
        print(f"   {main['name']}（{main['code']}）")
        print(f"   现价：{main['price']}")
        print(f"   当日涨跌：{main['today_chg']:+.2f}%")
        print(f"   10日涨幅：{main['period_chg']:+.2f}%")
    else:
        print("\n🏆 主板冠军：未找到")
    
    # 创业板冠军
    gem = data.get("gem_champion")
    if gem:
        print(f"\n🚀 创业板冠军：")
        print(f"   {gem['name']}（{gem['code']}）")
        print(f"   现价：{gem['price']}")
        print(f"   当日涨跌：{gem['today_chg']:+.2f}%")
        print(f"   10日涨幅：{gem['period_chg']:+.2f}%")
    else:
        print("\n🚀 创业板冠军：未找到")
    
    # 高位股票
    high_stocks = data.get("high_stocks", [])
    if high_stocks:
        print(f"\n🔥 高位股票（10日涨幅 > 40%）：")
        for i, stock in enumerate(high_stocks, 1):
            print(f"   {i}. {stock['name']}（{stock['code']}）- 10日涨幅：{stock['period_chg']:+.2f}%")
    else:
        print("\n🔥 高位股票：未找到")

if __name__ == "__main__":
    # 从文件读取快照（用于测试）
    if len(sys.argv) > 1:
        snapshot_file = sys.argv[1]
        
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot_text = f.read()
        
        # 解析股票数据
        stocks = parse_iwencai_table(snapshot_text)
        print(f"✅ 解析到 {len(stocks)} 只股票")
        
        # 构建浏览器数据
        data = build_browser_data(stocks)
        
        # 打印市场反馈
        print_market_feedback(data)
        
        # 输出 JSON
        print("\n" + "="*60)
        print("📄 JSON 输出")
        print("="*60)
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 browser_fetch.py <snapshot_file>")
        print("\n快照文件格式：同花顺问财页面的浏览器快照文本")
