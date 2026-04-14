#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
概念过滤与精选模块 v2.0

功能：
1. 过滤非题材类概念（制度性、地域性、交易属性等）
2. 从剩余概念中精选出最多 3 个最相关的核心题材
3. 优先展示与当前市场热点相关的题材

优化点：
- 从配置文件加载黑名单和优先级（便于动态调整）
- 添加概念标准化处理
- 支持批量处理
- 添加缓存机制

使用示例：
    python3 filter_concepts.py "AI 应用，深股通，DeepSeek 概念，乡村振兴，云计算"
    输出：人工智能、AI 应用、云计算
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from functools import lru_cache

# 添加路径
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

from config.concept_blacklist import CONCEPT_BLACKLIST
from config.theme_priority import CORE_THEMES_PRIORITY


@lru_cache(maxsize=1024)
def normalize_concept(concept: str) -> str:
    """
    标准化概念名称
    
    处理：
    - 去除前后空格
    - 统一大小写（英文）
    - 移除多余空格
    
    Args:
        concept: 原始概念
    
    Returns:
        标准化后的概念
    """
    if not concept:
        return ""
    
    # 去除空格
    concept = concept.strip()
    
    # 统一英文大小写（转大写便于匹配）
    # 但保留中文不变
    return concept


def parse_concepts(concepts_str: str) -> List[str]:
    """
    解析概念字符串为列表
    
    支持的分隔符：
    - 中文逗号（，）
    - 英文逗号（,）
    - 顿号（、）
    - 分号（；）
    
    Args:
        concepts_str: 概念字符串
    
    Returns:
        概念列表
    """
    if not concepts_str or not concepts_str.strip():
        return []
    
    # 统一分隔符
    normalized = concepts_str
    normalized = normalized.replace("，", ",").replace("、", ",").replace("；", ",")
    
    # 分割并清理
    concepts = [
        normalize_concept(c) 
        for c in normalized.split(",") 
        if c.strip()
    ]
    
    # 去重（保留顺序）
    seen = set()
    unique = []
    for c in concepts:
        if c and c not in seen:
            seen.add(c)
            unique.append(c)
    
    return unique


def is_blacklisted(concept: str) -> bool:
    """
    检查概念是否在黑名单中
    
    Args:
        concept: 概念名称
    
    Returns:
        bool: 是否在黑名单中
    """
    if not concept:
        return False
    
    # 精确匹配
    if concept in CONCEPT_BLACKLIST:
        return True
    
    # 部分匹配（长度>2 的黑名单词）
    for black in CONCEPT_BLACKLIST:
        if len(black) > 2 and black in concept:
            return True
    
    return False


@lru_cache(maxsize=512)
def score_concept(concept: str) -> int:
    """
    为概念评分（基于优先级表）
    
    评分规则：
    1. 精确匹配优先级表：返回对应分数
    2. 部分匹配：返回分数 -5
    3. 未匹配：返回默认分数（50 - 概念长度）
    
    Args:
        concept: 概念名称
    
    Returns:
        分数（0-100）
    """
    if not concept:
        return 0
    
    # 精确匹配
    if concept in CORE_THEMES_PRIORITY:
        return CORE_THEMES_PRIORITY[concept]
    
    # 部分匹配（概念包含优先级关键词）
    for keyword, score in CORE_THEMES_PRIORITY.items():
        if keyword in concept and keyword != concept:
            return max(0, score - 5)
    
    # 默认分数（短概念优先，假设更核心）
    return max(0, 50 - len(concept))


def filter_concepts(concepts: List[str]) -> List[str]:
    """
    过滤黑名单概念
    
    Args:
        concepts: 概念列表
    
    Returns:
        过滤后的概念列表
    """
    return [c for c in concepts if not is_blacklisted(c)]


def select_top_concepts(concepts: List[str], max_count: int = 3) -> List[str]:
    """
    按评分选择前 N 个概念
    
    Args:
        concepts: 概念列表
        max_count: 最多选择数量
    
    Returns:
        精选后的概念列表
    """
    if not concepts:
        return []
    
    # 评分排序
    scored = [(c, score_concept(c)) for c in concepts]
    scored.sort(key=lambda x: (-x[1], x[0]))  # 分数降序，概念名升序
    
    # 取前 N 个
    selected = [c for c, score in scored[:max_count]]
    
    return selected


def filter_and_select_concepts(concepts_str: str, max_count: int = 3) -> str:
    """
    完整流程：解析 → 过滤 → 评分 → 精选
    
    Args:
        concepts_str: 原始概念字符串
        max_count: 最多返回数量
    
    Returns:
        精选后的概念字符串（顿号分隔）
    """
    # 步骤 1：解析
    concepts = parse_concepts(concepts_str)
    
    if not concepts:
        return ""
    
    # 步骤 2：过滤黑名单
    filtered = filter_concepts(concepts)
    
    if not filtered:
        return "暂无题材概念"
    
    # 步骤 3：精选
    selected = select_top_concepts(filtered, max_count)
    
    if not selected:
        return "暂无题材概念"
    
    # 步骤 4：格式化输出（顿号分隔）
    return "、".join(selected)


def batch_filter(stock_concepts: List[Dict], max_count: int = 3) -> List[Dict]:
    """
    批量处理多只股票的概念过滤
    
    Args:
        stock_concepts: 列表，每项包含：
            - 股票代码
            - 股票简称
            - 原始概念
        max_count: 最多返回数量
    
    Returns:
        处理后的列表，新增字段：
            - 精选概念
            - 原始概念数
            - 精选后概念数
    """
    results = []
    
    for stock in stock_concepts:
        raw = stock.get("原始概念", stock.get("concepts", ""))
        filtered = filter_and_select_concepts(raw, max_count)
        
        # 计算原始概念数
        raw_list = parse_concepts(raw)
        
        results.append({
            **stock,
            "精选概念": filtered,
            "原始概念数": len(raw_list),
            "精选后概念数": len([c for c in filtered.split("、") if c.strip() and c != "暂无题材概念"]),
        })
    
    return results


def get_concept_stats(concepts_list: List[str]) -> Dict:
    """
    统计概念频次
    
    Args:
        concepts_list: 概念列表（可包含重复）
    
    Returns:
        统计结果：
            - total: 总概念数
            - unique: 去重后数量
            - top_10: 频次前 10 的概念
    """
    from collections import Counter
    
    if not concepts_list:
        return {"total": 0, "unique": 0, "top_10": []}
    
    # 统计频次
    counter = Counter(concepts_list)
    
    return {
        "total": sum(counter.values()),
        "unique": len(counter),
        "top_10": counter.most_common(10),
    }


def analyze_stocks(top_gainers: List[Dict]) -> Dict:
    """
    分析涨幅股票的题材分布
    
    Args:
        top_gainers: 涨幅股票列表（需包含"精选概念"字段）
    
    Returns:
        分析结果：
            - theme_count: 题材频次统计
            - top_3_themes: 前 3 大题材
            - theme_stocks: 每个题材对应的股票
    """
    from collections import Counter
    
    if not top_gainers:
        return {
            "theme_count": {},
            "top_3_themes": [],
            "theme_stocks": {},
        }
    
    # 收集所有概念
    all_concepts = []
    for stock in top_gainers:
        concepts = stock.get("精选概念", stock.get("涉及概念（精选）", ""))
        if concepts and concepts != "暂无题材概念":
            all_concepts.extend([c.strip() for c in concepts.split("、") if c.strip()])
    
    # 统计频次
    counter = Counter(all_concepts)
    top_3 = counter.most_common(3)
    
    # 匹配股票
    theme_stocks = {}
    for theme, count in top_3:
        stocks = [
            f"{s['股票简称']}（{s['股票代码']}）"
            for s in top_gainers
            if theme in s.get("精选概念", s.get("涉及概念（精选）", ""))
        ]
        theme_stocks[theme] = stocks[:5]  # 最多 5 只
    
    return {
        "theme_count": dict(counter),
        "top_3_themes": top_3,
        "theme_stocks": theme_stocks,
    }


if __name__ == "__main__":
    # 命令行模式
    if len(sys.argv) > 1:
        if sys.argv[1] in ["--help", "-h"]:
            print(__doc__)
            sys.exit(0)
        
        input_concepts = sys.argv[1]
        result = filter_and_select_concepts(input_concepts, max_count=3)
        
        print(f"\n{'='*50}")
        print(f"输入：{input_concepts}")
        print(f"输出：{result}")
        print(f"{'='*50}\n")
        
        # 显示详细分析
        concepts = parse_concepts(input_concepts)
        filtered = filter_concepts(concepts)
        selected = select_top_concepts(filtered, 3)
        
        print(f"解析概念数：{len(concepts)}")
        print(f"过滤后概念数：{len(filtered)}")
        print(f"精选概念数：{len(selected)}")
        
        if concepts:
            print(f"\n原始概念：{', '.join(concepts)}")
        if filtered:
            print(f"过滤后：{', '.join(filtered)}")
        if selected:
            print(f"精选后：{', '.join(selected)}")
        print()
    else:
        # 交互模式：从 stdin 读取 JSON
        try:
            input_data = json.load(sys.stdin)
            
            if isinstance(input_data, list):
                # 批量处理模式
                results = batch_filter(input_data)
                print(json.dumps(results, ensure_ascii=False, indent=2))
            elif isinstance(input_data, dict):
                # 单只股票模式
                raw = input_data.get("concepts", input_data.get("原始概念", ""))
                max_count = input_data.get("max_count", 3)
                result = filter_and_select_concepts(raw, max_count)
                print(json.dumps({
                    "input": raw,
                    "output": result,
                    "max_count": max_count
                }, ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(__doc__)
            print("\n用法：")
            print("  1. 命令行模式：python3 filter_concepts.py \"概念 1，概念 2，概念 3\"")
            print("  2. JSON 模式：echo '{\"concepts\": \"...\"}' | python3 filter_concepts.py")
            print("  3. 批量模式：echo '[{...}, {...}]' | python3 filter_concepts.py")
            print("  4. 帮助：python3 filter_concepts.py --help")
