#!/usr/bin/env python3
"""
fetch_browser_data.py - 通过浏览器获取盘面理解数据
获取：涨跌家数比、主板/创业板冠军、高位股票
"""

import sys
import json
import re
from datetime import datetime

def parse_iwencai_snapshot(html_text: str, query_type: str = "涨幅"):
    """
    解析同花顺问财快照数据
    query_type: "涨幅" | "涨跌家数" | "主板" | "创业板"
    """
    try:
        # 简单的正则提取（实际需要更复杂的HTML解析）
        if "涨幅" in query_type:
            # 提取涨幅排名表格
            rows = re.findall(r'<tr[^>]*>.*?</tr>', html_text, re.DOTALL)
            stocks = []
            for row in rows:
                cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
                if len(cells) >= 7:
                    try:
                        code = cells[1].strip()
                        name = cells[2].strip()
                        price = float(cells[3].strip())
                        today_chg = float(cells[4].strip().rstrip('%'))
                        period_chg = float(cells[6].strip().rstrip('%'))
                        
                        stocks.append({
                            "code": code,
                            "name": name,
                            "price": price,
                            "today_chg": today_chg,
                            "period_chg": period_chg
                        })
                    except:
                        pass
            return stocks
        
        elif "涨跌家数" in query_type:
            # 提取涨跌家数
            up_match = re.search(r'涨.*?(\d+)', html_text)
            down_match = re.search(r'跌.*?(\d+)', html_text)
            
            up = int(up_match.group(1)) if up_match else 0
            down = int(down_match.group(1)) if down_match else 0
            
            return {"up": up, "down": down}
        
        return None
    except Exception as e:
        print(f"⚠️ 解析失败: {e}")
        return None

def get_market_feedback_from_gainers(stocks: list) -> dict:
    """
    从涨幅榜中提取主板/创业板冠军和高位股票
    """
    if not stocks:
        return {
            "main_board": None,
            "gem_board": None,
            "high_stocks": []
        }
    
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
        
        # 高位股票（涨幅 > 50%）
        if stock.get("period_chg", 0) > 50:
            high_stocks.append(stock)
    
    return {
        "main_board": main_board,
        "gem_board": gem_board,
        "high_stocks": high_stocks[:3]  # 取前3个
    }

def build_market_feedback_text(feedback: dict) -> dict:
    """
    构造市场反馈文本
    """
    main_board = feedback.get("main_board")
    gem_board = feedback.get("gem_board")
    high_stocks = feedback.get("high_stocks", [])
    
    # 主板高度
    if main_board:
        main_name = main_board.get("name", "—")
        main_code = main_board.get("code", "—")
        main_pct = main_board.get("period_chg", 0)
        main_str = f"  - 主板高度（10cm）：{main_name}（{main_code}）{main_pct:+.2f}%，高位震荡继续新高，目前有30个交易日翻2倍规则，后期走势高位震荡盘整"
    else:
        main_str = "  - 主板高度（10cm）：—（—）+0%，数据获取中"
    
    # 创业板高度
    if gem_board:
        gem_name = gem_board.get("name", "—")
        gem_code = gem_board.get("code", "—")
        gem_pct = gem_board.get("period_chg", 0)
        gem_str = f"  - 创业板高度（20cm）：{gem_name}（{gem_code}）{gem_pct:+.2f}%，锂电池板块加强"
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
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，{top2_name} {top2_pct:+.2f}% 紧随其后，高位股整体表现一般，高位进入滞涨的阶段"
        else:
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，高位股整体表现一般，高位进入滞涨的阶段"
    else:
        high_str = " - 高位股票：高位股数据获取中"
    
    return {
        "main_lead": main_str,
        "gem_lead": gem_str,
        "high_str": high_str
    }

def get_sentiment_from_snapshot(html_text: str) -> dict:
    """
    从同花顺快照中提取涨跌家数比
    """
    try:
        # 尝试提取涨跌家数
        up_match = re.search(r'涨.*?(\d+)', html_text)
        down_match = re.search(r'跌.*?(\d+)', html_text)
        
        up = int(up_match.group(1)) if up_match else 0
        down = int(down_match.group(1)) if down_match else 0
        
        if up > 0 and down > 0:
            ratio = up / down
            ratio_str = f"{up}(涨) : {down}(跌) ≈ 1 : {ratio:.1f}"
        elif up > 0:
            ratio_str = f"{up}(涨) : 0(跌)"
        elif down > 0:
            ratio_str = f"0(涨) : {down}(跌)"
        else:
            ratio_str = "（数据获取中）"
        
        return {
            "up": up,
            "down": down,
            "ratio_str": ratio_str
        }
    except Exception as e:
        print(f"⚠️ 提取涨跌家数失败: {e}")
        return {
            "up": 0,
            "down": 0,
            "ratio_str": "（数据获取中）"
        }

if __name__ == "__main__":
    # 测试：从命令行读取 HTML 快照
    if len(sys.argv) > 1:
        html_file = sys.argv[1]
        with open(html_file, 'r', encoding='utf-8') as f:
            html_text = f.read()
        
        # 解析涨幅榜
        stocks = parse_iwencai_snapshot(html_text, "涨幅")
        print(json.dumps(stocks, ensure_ascii=False, indent=2))
        
        # 提取市场反馈
        feedback = get_market_feedback_from_gainers(stocks)
        market_text = build_market_feedback_text(feedback)
        print("\n市场反馈：")
        print(json.dumps(market_text, ensure_ascii=False, indent=2))
    else:
        print("用法: python3 fetch_browser_data.py <html_file>")
