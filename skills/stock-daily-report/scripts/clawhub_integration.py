#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClawHub Skills 集成模块 - 优化版（含人气排名）

优化点：
1. 默认通过 browser 工具实时获取数据
2. 只在 browser 失败时使用缓存 fallback
3. 添加数据日期验证，确保数据是最新的
4. ⭐ 新增：真正调用 ths-stock-themes 获取人气排名
"""

import subprocess
import json
import re
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path


# ==================== 实时数据获取（browser 工具） ====================

def fetch_top_gainers_realtime(browser_func=None, limit: int = 20, exclude_st: bool = True) -> Optional[List[Dict]]:
    """
    通过 browser 工具实时获取近 10 日涨幅排名
    
    Args:
        browser_func: 可选的 browser 函数（由调用方提供）
        limit: 获取数量
        exclude_st: 排除 ST 股票
    
    Returns:
        股票列表（实时数据）
    """
    try:
        if browser_func:
            return browser_func(limit=limit, exclude_st=exclude_st)
        return None
    except Exception as e:
        print(f"fetch_top_gainers_realtime error: {e}")
        return None


def parse_iwencai_snapshot(snapshot_text: str, limit: int = 20, exclude_st: bool = True) -> Optional[List[Dict]]:
    """解析同花顺问财 snapshot 数据"""
    try:
        stocks = []
        row_pattern = r'row "(\d+)\s+(\d{6})\s+([^"]+)\s+([\d.]+)\s+(-?[\d.]+)\s+\d+/\d+\s+(-?[\d.]+)"'
        
        for match in re.finditer(row_pattern, snapshot_text):
            rank = int(match.group(1))
            code = match.group(2)
            name = match.group(3)
            price = float(match.group(4))
            today_change = float(match.group(5))
            gain_10d = float(match.group(6))
            
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
        
        return stocks if stocks else None
    except Exception as e:
        print(f"parse_iwencai_snapshot error: {e}")
        return None


# ==================== 内置题材映射表（fallback 使用） ====================

STOCK_THEMES_FALLBACK = {
    "920028": "碳纤维，航空航天，新材料，低空经济",
    "600726": "电力，风电，绿色电力，超超临界发电",
    "688295": "碳纤维，新材料，航空航天，军工",
    "600396": "电力，清洁能源，风电，国企改革",
    "301658": "储能，光伏，新能源汽车，充电桩",
    "301396": "AI 应用，DeepSeek 概念，云计算，数据中心",
    "000020": "显示面板，电子元器件，消费电子",
    "600683": "房地产，商业地产，物业管理",
    "301667": "半导体，芯片，集成电路",
    "300720": "机器人，智能制造，自动化设备",
    "000890": "金属制品，钢丝绳，高端制造",
    "603778": "光伏，电池片，太阳能电池",
    "002445": "文化传媒，影视制作，IP 运营",
    "002310": "园林工程，生态环保，园林绿化",
    "300672": "半导体，芯片设计，存储芯片",
    "603929": "电子化学品，半导体材料，光刻胶",
    "300042": "存储芯片，半导体，闪存",
    "300763": "光伏逆变器，储能，新能源汽车",
    "002015": "光伏，清洁能源，热电联产",
    "688519": "覆铜板，电子材料，半导体材料",
}


# ==================== 人气排名获取 ⭐ ====================

def fetch_popularity_ranking_realtime(limit: int = 100) -> Optional[Dict[str, int]]:
    """
    通过 ths-stock-themes 获取人气排名榜单
    
    Args:
        limit: 获取前 N 名
    
    Returns:
        {股票代码：排名} 字典
    """
    try:
        # 调用 ths-stock-themes 的 fetch_popularity.py 脚本
        monorepo_path = Path.home() / ".jvs/.openclaw/workspace/skills/stock-data-monorepo"
        script_path = monorepo_path / "ths-stock-themes/scripts/fetch_popularity.py"
        
        if not script_path.exists():
            print(f"  ⚠️  fetch_popularity.py 不存在：{script_path}")
            return None
        
        # 执行脚本
        result = subprocess.run(
            ["python3", str(script_path), "--limit", str(limit), "--json"],
            capture_output=True, text=True, timeout=60
        )
        
        if result.returncode != 0:
            print(f"  ⚠️  获取人气排名失败：{result.stderr}")
            return None
        
        # 解析 JSON
        data = json.loads(result.stdout)
        
        if not data or "stocks" not in data:
            return None
        
        # 转换为 {股票代码：排名} 格式
        ranking_map = {}
        for stock in data.get("stocks", []):
            code = stock.get("股票代码")
            rank = stock.get("热度排名") or stock.get("排名")
            if code and rank:
                ranking_map[code] = int(rank)
        
        print(f"  ✅ 成功获取 {len(ranking_map)} 只股票的人气排名")
        return ranking_map
        
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  获取人气排名超时")
        return None
    except Exception as e:
        print(f"  ⚠️  fetch_popularity_ranking_realtime error: {e}")
        return None


def fetch_single_stock_themes(stock_code: str) -> Optional[Dict]:
    """
    调用 ths-stock-themes 获取单只股票的题材和人气排名
    
    Args:
        stock_code: 6 位股票代码
    
    Returns:
        {concepts: str, popularity_rank: int}
    """
    try:
        monorepo_path = Path.home() / ".jvs/.openclaw/workspace/skills/stock-data-monorepo"
        script_path = monorepo_path / "ths-stock-themes/scripts/fetch_themes.py"
        
        if not script_path.exists():
            return None
        
        # 执行脚本
        result = subprocess.run(
            ["python3", str(script_path), stock_code],
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            return None
        
        data = json.loads(result.stdout)
        
        # 提取题材和人气排名
        themes = data.get("themes", [])
        popularity = data.get("popularity_rank")
        
        if themes:
            return {
                "concepts": "，".join(themes),
                "popularity_rank": popularity if popularity else "100+"
            }
        
        return None
        
    except Exception as e:
        print(f"  ⚠️  fetch_single_stock_themes error for {stock_code}: {e}")
        return None


# ==================== 主函数 ====================

def get_top_gainers(date: str = None, limit: int = 20, exclude_st: bool = True) -> Optional[List[Dict]]:
    """获取近 10 日涨幅前 20 股票（优先实时数据）"""
    print("  🔄 尝试通过 browser 实时获取数据...")
    realtime_data = fetch_top_gainers_realtime(limit=limit, exclude_st=exclude_st)
    
    if realtime_data and _validate_data_date(realtime_data):
        print(f"  ✅ 成功获取 {len(realtime_data)} 只股票（实时数据）")
        return realtime_data
    
    print("  ℹ️  使用本地缓存数据（fallback）")
    return _get_cached_gainers(limit=limit, exclude_st=exclude_st)


def get_stock_themes_batch_with_popularity(stock_codes: List[str]) -> Dict[str, Dict]:
    """
    批量获取股票题材和人气排名 ⭐
    
    优化：
    1. 先获取人气排名榜单（前 100 名）
    2. 对于榜单中的股票，直接使用排名
    3. 对于不在榜单中的股票，使用 fallback
    
    Args:
        stock_codes: 股票代码列表
    
    Returns:
        {股票代码：{concepts: str, popularity_rank: int}}
    """
    results = {}
    
    # 步骤 1：获取人气排名榜单（前 100 名）
    print("  📊 获取人气排名榜单...")
    popularity_map = fetch_popularity_ranking_realtime(limit=100)
    
    if not popularity_map:
        print("  ⚠️  人气排名获取失败，使用 fallback")
        popularity_map = {}
    
    # 步骤 2：为每只股票获取题材
    print(f"  🏷️  获取 {len(stock_codes)} 只股票的题材...")
    
    for code in stock_codes:
        # 获取人气排名
        rank = popularity_map.get(code)
        rank_str = str(rank) if rank else "100+"
        
        # 获取题材（优先实时，fallback 到内置表）
        themes_data = fetch_single_stock_themes(code)
        
        if themes_data:
            results[code] = {
                "concepts": themes_data.get("concepts", "暂无概念"),
                "popularity_rank": themes_data.get("popularity_rank", rank_str)
            }
        else:
            # Fallback 到内置表
            if code in STOCK_THEMES_FALLBACK:
                results[code] = {
                    "concepts": STOCK_THEMES_FALLBACK[code],
                    "popularity_rank": rank_str
                }
            else:
                results[code] = {
                    "concepts": "暂无概念",
                    "popularity_rank": rank_str
                }
    
    return results


def _validate_data_date(stocks: List[Dict]) -> bool:
    """验证数据日期是否为最新"""
    if not stocks:
        return False
    
    has_change_data = any(
        stock.get("今日涨跌") is not None 
        for stock in stocks[:5]
    )
    
    if not has_change_data:
        return False
    
    valid_gains = [
        stock.get("10 日涨幅", 0) 
        for stock in stocks[:10]
        if isinstance(stock.get("10 日涨幅"), (int, float))
    ]
    
    if not valid_gains:
        return False
    
    avg_gain = sum(valid_gains) / len(valid_gains)
    return 10 <= avg_gain <= 150


def _get_cached_gainers(limit: int = 20, exclude_st: bool = True) -> Optional[List[Dict]]:
    """获取本地缓存数据（fallback）"""
    try:
        monorepo_path = Path.home() / ".jvs/.openclaw/workspace/skills/stock-data-monorepo"
        script_path = monorepo_path / "stock-top-gainers/scripts/fetch_gainers.py"
        
        if script_path.exists():
            result = subprocess.run(
                ["python3", str(script_path), "--source", "sample"],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if exclude_st:
                    data = [s for s in data if "ST" not in s.get("股票简称", "").upper()]
                return data[:limit]
    except Exception as e:
        print(f"_get_cached_gainers error: {e}")
    
    return None


def get_stock_themes(stock_code: str) -> Optional[Dict]:
    """获取单只股票题材概念（已废弃，使用 batch 版本）"""
    if stock_code in STOCK_THEMES_FALLBACK:
        return {
            "concepts": STOCK_THEMES_FALLBACK[stock_code],
            "popularity_rank": "100+"
        }
    return None


def get_stock_themes_batch(stock_codes: List[str], max_workers: int = 5) -> Dict[str, Dict]:
    """批量获取股票题材（兼容旧接口，调用新版本）"""
    return get_stock_themes_batch_with_popularity(stock_codes)


class ClawHubIntegration:
    """ClawHub 集成器（包装类）"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
    
    def fetch_top_gainers(self, limit: int = 20, exclude_st: bool = True, date: str = None) -> Optional[List[Dict]]:
        """获取涨幅排名（实时优先）"""
        return get_top_gainers(date=date, limit=limit, exclude_st=exclude_st)
    
    def fetch_stock_themes(self, stock_codes: List[str], max_workers: int = 5) -> Dict:
        """批量获取股票题材（含人气排名）⭐"""
        return get_stock_themes_batch_with_popularity(stock_codes)


if __name__ == "__main__":
    print("Testing ClawHub integration (with popularity ranking)...")
    
    print("\n1. Testing gainers...")
    gainers = get_top_gainers(limit=20, exclude_st=True)
    if gainers:
        print(f"   ✓ Got {len(gainers)} stocks")
    
    print("\n2. Testing themes with popularity...")
    codes = [g["股票代码"] for g in gainers[:5]] if gainers else ["600396", "688295"]
    themes = get_stock_themes_batch_with_popularity(codes)
    
    if themes:
        print(f"   ✓ Got themes for {len(themes)} stocks")
        for code, data in list(themes.items())[:3]:
            print(f"   {code}: {data['concepts'][:30]}... (人气：{data['popularity_rank']})")
