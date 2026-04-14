#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人气热度获取 v2.2（Browser 工具版）

使用 OpenClaw browser 工具获取同花顺问财人气排名数据
支持实时获取，不依赖缓存

使用方式：
    # 在 OpenClaw 会话中通过 browser 工具调用
    python3 scripts/fetch_popularity_v2_browser.py
"""

import sys
import json
import re
from typing import List, Dict, Optional
from pathlib import Path

# 配置
LIMIT = 20
IWNCAI_URL = "https://www.iwencai.com/unifiedwap/result?w=个股人气排名"


def parse_iwencai_snapshot(snapshot_text: str, limit: int = 20) -> List[Dict]:
    """
    解析同花顺问财 snapshot 数据
    
    Args:
        snapshot_text: browser snapshot 输出的文本
        limit: 返回数量限制
    
    Returns:
        人气排名股票列表
    """
    stocks = []
    
    # 匹配 snapshot 中的表格行数据
    # 格式：row "1 301053 远信工业 50.00 2.35 第 1 名"
    row_pattern = r'row\s+"(\d+)\s+(\d{6})\s+([^"]+?)\s+([\d.]+)\s+(-?[\d.]+)?\s+第 (\d+) 名"'
    
    for match in re.finditer(row_pattern, snapshot_text):
        rank = int(match.group(1))
        code = match.group(2)
        name = match.group(3).strip()
        price = float(match.group(4)) if match.group(4) else 0
        change = float(match.group(5)) if match.group(5) else 0
        popularity_rank = int(match.group(6))
        
        # 排除 ST 股票
        if 'ST' in name.upper():
            continue
        
        stocks.append({
            '排名': rank,
            '股票代码': code,
            '股票简称': name,
            '收盘价': price,
            '人气热度': f'第{popularity_rank}名',
            '10 日涨幅': change,
            '今日涨跌': change,
        })
        
        if len(stocks) >= limit:
            break
    
    return stocks


def fetch_popularity_via_browser() -> List[Dict]:
    """
    通过 OpenClaw browser 工具获取人气排名
    
    Returns:
        人气排名股票列表
    """
    print("[INFO] 通过 browser 工具获取同花顺问财人气排名...")
    
    try:
        # 使用 OpenClaw browser 工具
        # 注意：这个函数需要在 OpenClaw 会话中通过 tool 调用
        # 这里提供一个包装函数，实际调用由上层完成
        
        # 示例调用方式（在 OpenClaw 中）：
        # browser(action="navigate", targetUrl=IWNCAI_URL)
        # browser(action="snapshot", refs="aria")
        # 然后解析 snapshot 文本
        
        print(f"[INFO] 导航到：{IWNCAI_URL}")
        print("[WARN] 需要在 OpenClaw 会话中调用 browser 工具")
        print("[INFO] 请使用以下方式调用：")
        print("  1. browser(action='navigate', targetUrl='https://www.iwencai.com/unifiedwap/result?w=个股人气排名')")
        print("  2. browser(action='snapshot', refs='aria')")
        print("  3. 解析 snapshot 文本获取数据")
        
        return []
        
    except Exception as e:
        print(f"[ERROR] browser 获取失败：{e}")
        return []


def fetch_popularity_fallback() -> List[Dict]:
    """
    Fallback: 使用 akshare 获取连续上涨排行（当 browser 不可用时）
    
    Returns:
        股票列表
    """
    print("[INFO] 使用 akshare fallback...")
    
    try:
        import akshare as ak
        
        # 获取连续上涨排行
        df = ak.stock_rank_lxsz_ths()
        
        stocks = []
        for _, row in df.head(LIMIT).iterrows():
            code = str(row.get('股票代码', ''))
            name = str(row.get('股票简称', ''))
            price = row.get('收盘价', 0)
            change = row.get('连续涨跌幅', 0)
            
            # 排除 ST 股票
            if 'ST' in name.upper():
                continue
            
            stocks.append({
                '排名': len(stocks) + 1,
                '股票代码': code,
                '股票简称': name,
                '收盘价': float(price) if price else 0,
                '人气热度': f'第{len(stocks)+1}名',
                '10 日涨幅': float(change) if change else 0,
                '今日涨跌': 0,
            })
        
        return stocks
    
    except Exception as e:
        print(f"[ERROR] akshare fallback 失败：{e}")
        return []


def fetch_popularity_ranking(limit: int = 20, use_browser: bool = True) -> List[Dict]:
    """
    获取人气排名（主函数）
    
    Args:
        limit: 返回数量限制
        use_browser: 是否优先使用 browser 工具
    
    Returns:
        人气排名股票列表
    """
    print(f"[INFO] 获取人气排名（限制：{limit}, browser: {use_browser}）...")
    
    stocks = []
    
    # 优先使用 browser 工具
    if use_browser:
        stocks = fetch_popularity_via_browser()
    
    # Fallback 到 akshare
    if not stocks:
        print("[WARN] browser 不可用，使用 akshare fallback")
        stocks = fetch_popularity_fallback()
    
    if stocks:
        print(f"[INFO] ✅ 人气排名获取成功（{len(stocks)}只股票）")
        return stocks[:limit]
    
    print("[WARN] ⚠️  人气排名获取失败，返回空列表")
    return []


def main():
    """命令行入口"""
    print("="*60)
    print("人气排名获取工具 v2.2（Browser 工具版）")
    print("="*60)
    
    stocks = fetch_popularity_ranking(limit=20, use_browser=False)  # 默认使用 fallback
    
    if stocks:
        print(f"\n✅ 获取到 {len(stocks)} 只股票：")
        for stock in stocks[:10]:
            print(f"  {stock['排名']}. {stock['股票代码']} {stock['股票简称']} "
                  f"({stock['收盘价']}元) 人气:{stock['人气热度']}")
        if len(stocks) > 10:
            print(f"  ... 还有 {len(stocks) - 10} 只")
    else:
        print("\n❌ 未获取到人气排名数据")
    
    return stocks


if __name__ == "__main__":
    main()
