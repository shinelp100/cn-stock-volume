#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人气热度获取 v2.1.2（无缓存版）

使用 akshare 获取 A 股涨幅排名数据
不依赖缓存，每次获取实时数据

使用方式：
    python3 scripts/fetch_popularity_v2.py
"""

import sys
from typing import List, Dict

# 配置
LIMIT = 20


def fetch_via_akshare() -> List[Dict]:
    """
    使用 akshare 获取近 10 日涨幅排名
    
    Returns:
        股票列表
    """
    try:
        import akshare as ak
        
        # 获取连续上涨排行
        df = ak.stock_rank_lxsz_ths()
        
        stocks = []
        for _, row in df.head(LIMIT).iterrows():
            # 正确的列名映射
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
                '今日涨跌': 0,  # akshare 不提供今日涨跌
            })
        
        return stocks
    
    except Exception as e:
        print(f"[WARN] akshare 获取失败：{e}")
        return []





def fetch_popularity_ranking(limit: int = 20) -> List[Dict]:
    """
    获取人气排名（主函数）
    
    直接使用 akshare 获取实时数据，无缓存
    
    Args:
        limit: 返回数量限制
    
    Returns:
        人气排名股票列表
    """
    print(f"[INFO] 获取涨幅排名（限制：{limit}）...")
    
    # 使用 akshare 获取
    stocks = fetch_via_akshare()
    
    if stocks:
        print(f"[INFO] ✅ 涨幅排名获取成功（{len(stocks)}只股票）")
        return stocks
    
    # 返回空列表
    print("[WARN] ⚠️  涨幅排名获取失败，返回空列表")
    return []


def main():
    """命令行入口"""
    print("="*60)
    print("涨幅排名获取工具 v2.1.2（无缓存）")
    print("="*60)
    
    stocks = fetch_popularity_ranking(limit=20)
    
    if stocks:
        print(f"\n✅ 获取到 {len(stocks)} 只股票：")
        for stock in stocks[:10]:
            print(f"  {stock['排名']}. {stock['股票代码']} {stock['股票简称']} "
                  f"({stock['收盘价']}元) +{stock['10 日涨幅']}%")
        if len(stocks) > 10:
            print(f"  ... 还有 {len(stocks) - 10} 只")
    else:
        print("\n❌ 未获取到涨幅排名数据")
    
    return stocks


if __name__ == "__main__":
    main()
