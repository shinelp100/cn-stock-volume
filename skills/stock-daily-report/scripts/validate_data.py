#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据验证模块
确保数据一致性和准确性
"""

import sys
from pathlib import Path

# 添加 config 路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.data_sources import VALIDATION_THRESHOLDS


def validate_index_data(index_data: dict, verbose: bool = True) -> bool:
    """
    验证大盘指数数据
    
    检查项：
    1. 四个市场数据完整
    2. 成交额为正数
    3. 涨跌幅在合理范围内（-10% ~ +10%）
    
    Args:
        index_data: 指数数据字典（来自 cn-stock-volume）
        verbose: 是否打印详细日志
    
    Returns:
        bool: 验证是否通过
    """
    required_markets = ["沪市", "深市", "创业板", "北交所"]
    is_valid = True
    
    def log(msg):
        if verbose:
            print(msg)
    
    # 检查数据是否存在
    if not index_data:
        log("  ❌ 指数数据为空")
        return False
    
    # 检查市场完整性
    markets = index_data.get("markets", {})
    for market in required_markets:
        if market not in markets:
            log(f"  ⚠ 缺少市场数据：{market}")
            is_valid = False
    
    if not is_valid:
        return False
    
    # 检查数据合理性
    for market_name, market_data in markets.items():
        # 成交额检查
        amount = market_data.get("amount", 0)
        if amount <= 0:
            log(f"  ❌ {market_name} 成交额异常：{amount}")
            is_valid = False
        
        # 收盘价检查
        close = market_data.get("close", 0)
        if close <= 0:
            log(f"  ❌ {market_name} 收盘价异常：{close}")
            is_valid = False
        
        # 涨跌幅检查
        change_pct = market_data.get("change_pct", 0)
        max_change = VALIDATION_THRESHOLDS["max_index_change_pct"]
        if abs(change_pct) > max_change:
            log(f"  ⚠ {market_name} 涨跌幅异常：{change_pct}% (阈值：{max_change}%)")
            # 涨跌幅异常不直接判定为失败，只警告
    
    # 检查汇总数据
    summary = index_data.get("summary", {})
    total = summary.get("total_fmt", "")
    if not total:
        log("  ⚠ 缺少总成交额数据")
    
    if is_valid and verbose:
        log("  ✓ 指数数据验证通过")
    
    return is_valid


def validate_gainers_data(gainers: list, verbose: bool = True) -> bool:
    """
    验证涨幅股票数据
    
    检查项：
    1. 无 ST 股票
    2. 涨幅在合理范围内
    3. 数据字段完整
    
    Args:
        gainers: 股票列表
        verbose: 是否打印详细日志
    
    Returns:
        bool: 验证是否通过
    """
    is_valid = True
    
    def log(msg):
        if verbose:
            print(msg)
    
    if not gainers:
        log("  ❌ 涨幅股票数据为空")
        return False
    
    for stock in gainers:
        name = stock.get("股票简称", "")
        code = stock.get("股票代码", "")
        
        # ST 检查
        if VALIDATION_THRESHOLDS.get("st_check_enabled", True):
            if "ST" in name.upper():
                log(f"  ❌ 检测到 ST 股票：{name} ({code})")
                is_valid = False
        
        # 涨幅检查
        gain = stock.get("10 日涨幅", stock.get("区间涨幅", 0))
        max_gain = VALIDATION_THRESHOLDS["max_stock_gain_pct"]
        if gain < -50 or gain > max_gain:
            log(f"  ⚠ {name} ({code}) 涨幅异常：{gain}% (阈值：{max_gain}%)")
            # 涨幅异常不直接判定为失败，只警告
        
        # 字段完整性检查
        required_fields = ["股票代码", "股票简称"]
        for field in required_fields:
            if field not in stock or not stock[field]:
                log(f"  ⚠ {name} 缺少字段：{field}")
                is_valid = False
    
    if is_valid and verbose:
        log(f"  ✓ 涨幅股票数据验证通过（共{len(gainers)}只）")
    
    return is_valid


def validate_themes_data(themes_data: dict, verbose: bool = True) -> bool:
    """
    验证题材概念数据
    
    检查项：
    1. 数据格式正确
    2. 概念字符串非空
    
    Args:
        themes_data: 题材数据字典
        verbose: 是否打印详细日志
    
    Returns:
        bool: 验证是否通过
    """
    is_valid = True
    
    def log(msg):
        if verbose:
            print(msg)
    
    if not themes_data:
        log("  ⚠ 题材数据为空（可能无法获取）")
        return True  # 题材数据可选，不作为硬性失败
    
    # 检查数据格式
    for code, data in themes_data.items():
        if not isinstance(data, dict):
            log(f"  ⚠ 股票 {code} 数据格式错误")
            is_valid = False
    
    if is_valid and verbose:
        log(f"  ✓ 题材数据验证通过（共{len(themes_data)}只）")
    
    return is_valid


def run_all_validations(index_data: dict = None, gainers: list = None, 
                        themes_data: dict = None) -> bool:
    """
    运行所有数据验证
    
    Args:
        index_data: 指数数据
        gainers: 涨幅股票数据
        themes_data: 题材数据
    
    Returns:
        bool: 所有验证是否通过
    """
    print("\n=== 数据验证 ===")
    
    results = []
    
    if index_data:
        results.append(validate_index_data(index_data))
    
    if gainers:
        results.append(validate_gainers_data(gainers))
    
    if themes_data:
        results.append(validate_themes_data(themes_data))
    
    all_passed = all(results) if results else False
    
    if all_passed:
        print("\n✅ 所有数据验证通过")
    else:
        print("\n⚠ 部分数据验证未通过，请检查")
    
    return all_passed


if __name__ == "__main__":
    # 测试模式
    print("数据验证模块测试")
    print("=" * 50)
    
    # 测试数据
    test_index_data = {
        "markets": {
            "沪市": {"close": 3957.05, "amount": 9648.6, "change_pct": -1.24},
            "深市": {"close": 13866.20, "amount": 13220.0, "change_pct": -0.25},
            "创业板": {"close": 3352.10, "amount": 6633.05, "change_pct": 1.30},
            "北交所": {"close": 1234.56, "amount": 120.5, "change_pct": 0.84},
        },
        "summary": {"total_fmt": "29632.2 亿"}
    }
    
    test_gainers = [
        {"股票代码": "688295", "股票简称": "中复神鹰", "10 日涨幅": 99.97},
        {"股票代码": "600726", "股票简称": "华电能源", "10 日涨幅": 81.88},
        {"股票代码": "301396", "股票简称": "宏景科技", "10 日涨幅": 80.24},
    ]
    
    validate_index_data(test_index_data)
    validate_gainers_data(test_gainers)
