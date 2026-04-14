#!/usr/bin/env python3
"""
browser_popularity.py - 通过 browser 工具获取人气排名

这个模块需要在 OpenClaw 主会话中运行，可以直接访问 browser 工具。
"""

import re
import time
from typing import Dict, Optional


def fetch_popularity_ranking(limit: int = 100) -> Dict[str, int]:
    """
    通过 browser 工具获取同花顺个股人气排名
    
    Args:
        limit: 获取前 N 名
    
    Returns:
        {股票代码：排名} 字典
    """
    try:
        # 导入 browser 工具（在主会话中可用）
        from browser import open as browser_open, snapshot as browser_snapshot
        
        url = "https://www.iwencai.com/unifiedwap/result?w=个股人气排名"
        
        print(f"  🌐 访问同花顺问财：{url}")
        
        # 打开页面
        browser_open(url=url)
        
        # 等待页面加载
        print(f"  ⏳ 等待页面加载...")
        time.sleep(3)
        
        # 获取 snapshot
        print(f"  📸 获取页面 snapshot...")
        snap = browser_snapshot(refs="aria")
        
        # 解析 snapshot
        popularity_map = parse_snapshot(snap, limit)
        
        if popularity_map:
            print(f"  ✅ 成功获取 {len(popularity_map)} 只股票的人气排名")
            return popularity_map
        else:
            print(f"  ⚠️  snapshot 解析失败")
            return {}
            
    except Exception as e:
        print(f"  ⚠️  fetch_popularity_ranking 失败：{e}")
        return {}


def parse_snapshot(snapshot_text: str, limit: int = 100) -> Dict[str, int]:
    """
    解析人气排名 snapshot
    
    期望格式：
    row "1 600396 华电辽能 6.26 10.02 1 16.79 万"
    
    Returns:
        {股票代码：排名}
    """
    try:
        popularity_map = {}
        
        # 查找表格行
        row_pattern = r'row "(\d+)\s+(\d{6})\s+([^"]+)\s+([\d.]+)\s+([+-]?\d+\.?\d*)\s+(\d+)\s+([^"]+)"'
        
        for match in re.finditer(row_pattern, snapshot_text):
            rank = int(match.group(1))
            code = match.group(2)
            
            popularity_map[code] = rank
            
            if len(popularity_map) >= limit:
                break
        
        return popularity_map
        
    except Exception as e:
        print(f"  ⚠️  parse_snapshot 失败：{e}")
        return {}


if __name__ == "__main__":
    # 测试
    print("测试人气排名获取...")
    result = fetch_popularity_ranking(limit=20)
    
    if result:
        print(f"\n前 10 名人气排名：")
        for i, (code, rank) in enumerate(sorted(result.items(), key=lambda x: x[1])[:10]):
            print(f"  {i+1}. {code}: 第{rank}名")
    else:
        print("获取失败")
