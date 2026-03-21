#!/usr/bin/env python3
"""
通过 Browser 工具获取东方财富网成交金额数据（首选方案）
数据源：https://quote.eastmoney.com/center/hszs.html

返回格式：
{
    "沪市": { "amount": 964863000000, "close": 3957.05, "change_pct": -1.24, "volume": "6.67 亿" },
    "深市": { "amount": 13200000000000, "close": 13866.20, "change_pct": -0.25, "volume": "7.34 亿" },
    "创业板": { "amount": 663305000000, "close": 3352.10, "change_pct": 1.30, "volume": "2.32 亿" },
    "北交所": { "amount": 16230000000, "close": 1316.14, "change_pct": -1.01, "volume": "738.80 万" },
}
"""

import json
import re
import sys

# 市场映射（东方财富网显示名称 → 标准名称）
MARKET_MAPPING = {
    "上证指数": "沪市",
    "深证成指": "深市",
    "创业板指": "创业板",
    "北证 50": "北交所",
}

# 指数代码映射
INDEX_CODES = {
    "沪市": "000001",
    "深市": "399001",
    "创业板": "399006",
    "北交所": "899050",
}

# 指数名称到代码的反向映射
NAME_TO_CODE = {
    "上证指数": "000001",
    "深证成指": "399001",
    "创业板指": "399006",
    "北证 50": "899050",
}


def parse_amount(amount_str):
    """
    解析成交额字符串为数值（元）
    支持格式：'9648.63 亿', '1.32 万亿', '162.30 亿', '1.82 亿'
    """
    if not amount_str:
        return None
    
    amount_str = amount_str.strip()
    
    # 万亿
    if "万亿" in amount_str:
        num = float(amount_str.replace("万亿", "").strip())
        return num * 1e12
    
    # 亿
    if "亿" in amount_str:
        num = float(amount_str.replace("亿", "").strip())
        return num * 1e8
    
    # 万
    if "万" in amount_str:
        num = float(amount_str.replace("万", "").strip())
        return num * 1e4
    
    return None


def parse_volume(volume_str):
    """
    解析成交量字符串
    支持格式：'6.67 亿', '738.80 万'
    """
    if not volume_str:
        return None
    
    volume_str = volume_str.strip()
    
    if "亿" in volume_str:
        num = float(volume_str.replace("亿", "").strip())
        return num * 1e8
    
    if "万" in volume_str:
        num = float(volume_str.replace("万", "").strip())
        return num * 1e4
    
    return None


def parse_snapshot_text(snapshot_text):
    """
    从 browser snapshot 文本中解析四市数据
    
    查找格式如：
    "1 000001 上证指数 3957.05 -49.50 -1.24% 6.67 亿 9648.63 亿 4006.55 4004.57 4022.70 3955.71"
    
    字段顺序：序号 代码 名称 最新价 涨跌额 涨跌幅 成交量 成交额 昨收 今开 最高 最低
    """
    results = {}
    
    # 按行分割
    lines = snapshot_text.split('\n')
    
    for line in lines:
        # 检查是否包含指数名称
        for index_name, market_name in MARKET_MAPPING.items():
            if index_name in line and market_name not in results:
                # 使用正则表达式提取数据
                # 匹配模式：序号 代码 名称 最新价 涨跌额 涨跌幅 成交量 成交额
                pattern = r'(\d+)\s+(\d{6})\s+(' + index_name + r')\s+([\d.]+)\s+([+-]?[\d.]+)\s+([+-]?[\d.]+%)\s+([\d.]+\s*[亿万万])\s+([\d.]+\s*[亿万万])'
                match = re.search(pattern, line)
                
                if match:
                    seq, code, name, close, change_amt, change_pct, volume, amount = match.groups()
                    
                    amount_val = parse_amount(amount)
                    volume_val = parse_volume(volume)
                    close_val = float(close)
                    change_pct_val = float(change_pct.replace('%', ''))
                    
                    results[market_name] = {
                        "amount": amount_val,
                        "volume": volume_val,
                        "close": close_val,
                        "change_pct": change_pct_val,
                        "source": "browser",
                    }
    
    # 如果上面的正则没匹配到，尝试更宽松的匹配
    if len(results) < 4:
        for line in lines:
            for index_name, market_name in MARKET_MAPPING.items():
                if index_name in line and market_name not in results:
                    # 尝试从行中提取数字
                    parts = line.split()
                    
                    # 查找包含%的字段（涨跌幅）
                    change_pct = None
                    amount = None
                    volume = None
                    close = None
                    
                    for i, part in enumerate(parts):
                        if '%' in part:
                            try:
                                change_pct = float(part.replace('%', ''))
                            except:
                                pass
                        
                        # 查找成交额（通常包含亿或万亿，且在成交量之后）
                        if ('亿' in part or '万亿' in part) and amount is None:
                            amt_val = parse_amount(part)
                            if amt_val and amt_val > 1e8:  # 至少 1 亿
                                amount = amt_val
                        
                        # 查找成交量（通常在前面的位置）
                        if ('亿' in part or '万' in part) and volume is None and amount is None:
                            vol_val = parse_volume(part)
                            if vol_val:
                                volume = vol_val
                        
                        # 查找最新价（指数点位通常在 100-50000 之间）
                        if close is None:
                            try:
                                val = float(part)
                                if 100 < val < 50000:
                                    close = val
                            except:
                                pass
                    
                    if amount and close:
                        results[market_name] = {
                            "amount": amount,
                            "volume": volume,
                            "close": close,
                            "change_pct": change_pct,
                            "source": "browser",
                        }
    
    return results


def fetch_from_snapshot(snapshot_text):
    """
    从 snapshot 文本中提取数据
    
    参数：
        snapshot_text: browser snapshot 返回的文本
    
    返回：
        {
            "status": "ok" | "error",
            "data": { ... },  # 如果成功
            "message": "..."  # 如果失败
        }
    """
    if not snapshot_text:
        return {
            "status": "error",
            "message": "snapshot 文本为空",
        }
    
    data = parse_snapshot_text(snapshot_text)
    
    if len(data) == 0:
        return {
            "status": "error",
            "message": "未能从 snapshot 中解析出任何数据",
        }
    
    if len(data) < 4:
        missing = set(MARKET_MAPPING.values()) - set(data.keys())
        return {
            "status": "partial",
            "data": data,
            "message": f"只获取到 {len(data)}/4 个市场数据，缺失：{missing}",
        }
    
    return {
        "status": "ok",
        "data": data,
        "message": f"成功获取 {len(data)}/4 个市场数据",
    }


def get_browser_url():
    """获取 Browser 数据源 URL"""
    return "https://quote.eastmoney.com/center/hszs.html"


if __name__ == "__main__":
    print("Browser 数据获取脚本（首选方案）")
    print("=" * 60)
    print()
    print("数据源：东方财富网 - 沪深京指数")
    print(f"URL: {get_browser_url()}")
    print()
    print("使用方法:")
    print("1. 使用 browser 工具打开 URL")
    print("2. 获取 snapshot (refs='aria')")
    print("3. 调用 fetch_from_snapshot() 解析数据")
    print()
    print("示例数据（2026-03-21）:")
    print("  沪市：9648.63 亿 (-1.24%)")
    print("  深市：1.32 万亿 (-0.25%)")
    print("  创业板：6633.05 亿 (+1.30%)")
    print("  北交所：162.30 亿 (-1.01%)")
    print()
    print("=" * 60)
