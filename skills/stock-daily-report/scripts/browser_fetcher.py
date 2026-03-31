#!/usr/bin/env python3
"""
browser_fetcher.py - 通过浏览器自动化获取同花顺问财数据

功能：
1. 获取近10日涨幅排名（主板/创业板冠军、高位股票）
2. 获取涨跌家数比

使用方式：
- 被 OpenClaw agent 调用（通过 browser 工具）
- 独立运行（输出 JSON 格式数据）
"""

import sys
import json
import re
from datetime import datetime

def parse_gainers_from_snapshot(snapshot_text: str) -> dict:
    """
    从同花顺问财快照中解析涨幅榜数据
    
    Args:
        snapshot_text: 浏览器快照的文本内容
    
    Returns:
        {
            "stocks": [
                {"rank": 1, "code": "600396", "name": "华电辽能", "price": 8.99, "today_chg": 1.24, "period_chg": 131.70}
            ],
            "main_board": {...},  # 主板冠军
            "gem_board": {...},   # 创业板冠军
            "high_stocks": [...]  # 高位股票（10日涨幅>50%）
        }
    """
    stocks = []
    
    # 使用正则提取表格数据
    # 格式：row "1 920069 普昂医疗 43.48 136.56 1/795 136.56"
    row_pattern = r'row "(\d+)\s+(\d+)\s+([^\s]+)\s+([\d.]+)\s+([-]?[\d.]+)\s+(\d+/\d+)\s+([\d.]+)"'
    
    matches = re.findall(row_pattern, snapshot_text)
    
    for match in matches:
        try:
            rank = int(match[0])
            code = match[1]
            name = match[2]
            price = float(match[3])
            today_chg = float(match[4])
            period_chg = float(match[6])
            
            stocks.append({
                "rank": rank,
                "code": code,
                "name": name,
                "price": price,
                "today_chg": today_chg,
                "period_chg": period_chg
            })
        except Exception as e:
            continue
    
    # 提取主板冠军（600/601/603开头）
    main_board = None
    gem_board = None
    high_stocks = []
    
    for stock in stocks:
        code = stock.get("code", "")
        
        # 主板（600/601/603开头）
        if code.startswith(("600", "601", "603")) and not main_board:
            main_board = stock
        
        # 创业板（300开头）
        if code.startswith("300") and not gem_board:
            gem_board = stock
        
        # 高位股票（10日涨幅 > 50%）
        if stock.get("period_chg", 0) > 50:
            high_stocks.append(stock)
    
    return {
        "stocks": stocks,
        "main_board": main_board,
        "gem_board": gem_board,
        "high_stocks": high_stocks[:5]  # 取前5个
    }

def build_market_feedback_text(data: dict) -> dict:
    """
    构造市场反馈文本
    
    Returns:
        {
            "main_lead": "主板高度（10cm）：华电辽能（600396）+131.70%，...",
            "gem_lead": "创业板高度（20cm）：海科新源（301292）+49.33%，...",
            "high_str": "高位股票：普昂医疗 10 日涨幅超 136% 领涨，华电辽能 +131.70% 紧随其后..."
        }
    """
    main_board = data.get("main_board")
    gem_board = data.get("gem_board")
    high_stocks = data.get("high_stocks", [])
    
    # 主板高度
    if main_board:
        name = main_board.get("name", "—")
        code = main_board.get("code", "—")
        pct = main_board.get("period_chg", 0)
        main_str = f"  - 主板高度（10cm）：{name}（{code}）+{pct:.2f}%，高位震荡继续新高，目前有30个交易日翻2倍规则，后期走势高位震荡盘整"
    else:
        main_str = "  - 主板高度（10cm）：—（—）+0%，数据获取中"
    
    # 创业板高度
    if gem_board:
        name = gem_board.get("name", "—")
        code = gem_board.get("code", "—")
        pct = gem_board.get("period_chg", 0)
        gem_str = f"  - 创业板高度（20cm）：{name}（{code}）+{pct:.2f}%，锂电池板块加强"
    else:
        gem_str = "  - 创业板高度（20cm）：—（—）+0%，数据获取中"
    
    # 高位股票
    if high_stocks and len(high_stocks) > 0:
        top1 = high_stocks[0]
        top1_name = top1.get("name", "—")
        top1_pct = top1.get("period_chg", 0)
        
        if len(high_stocks) > 1:
            top2 = high_stocks[1]
            top2_name = top2.get("name", "—")
            top2_pct = top2.get("period_chg", 0)
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，{top2_name} +{top2_pct:.2f}% 紧随其后，高位股整体表现一般，高位进入滞涨的阶段"
        else:
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，高位股整体表现一般，高位进入滞涨的阶段"
    else:
        high_str = " - 高位股票：高位股数据获取中"
    
    return {
        "main_lead": main_str,
        "gem_lead": gem_str,
        "high_str": high_str
    }

def build_gainers_table(data: dict, top_n: int = 20) -> str:
    """
    构造涨幅榜表格（前N名）
    
    Returns:
        Markdown 格式的表格字符串
    """
    stocks = data.get("stocks", [])[:top_n]
    
    if not stocks:
        return "（涨幅榜数据获取中...）"
    
    lines = []
    for s in stocks:
        rank = s.get("rank", 0)
        code = s.get("code", "—")
        name = s.get("name", "—")
        price = s.get("price", 0)
        period_chg = s.get("period_chg", 0)
        today_chg = s.get("today_chg", 0)
        
        # 人气热度（基于排名估算）
        heat = "🔥" * max(1, 6 - rank // 5) if rank <= 20 else "⭐"
        
        # 概念（需要额外数据，暂时占位）
        concept = "—" if rank > 5 else "电力/新能源"
        
        lines.append(f"| {rank} | {code} | {name} | {price:.2f} | +{period_chg:.2f}% | {today_chg:+.2f}% | {heat} | {concept} |")
    
    return "\n".join(lines)

if __name__ == "__main__":
    # 测试：从 stdin 读取快照文本
    if len(sys.argv) > 1:
        # 从文件读取
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            snapshot_text = f.read()
    else:
        # 从 stdin 读取
        print("请输入快照文本（Ctrl+D 结束）：", file=sys.stderr)
        snapshot_text = sys.stdin.read()
    
    # 解析数据
    data = parse_gainers_from_snapshot(snapshot_text)
    
    # 输出 JSON
    print(json.dumps(data, ensure_ascii=False, indent=2))
    
    # 输出市场反馈文本
    feedback = build_market_feedback_text(data)
    print("\n--- 市场反馈 ---")
    print(json.dumps(feedback, ensure_ascii=False, indent=2))
