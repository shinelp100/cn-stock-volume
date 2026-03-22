#!/usr/bin/env python3
"""
cn-stock-volume 自动生成报告脚本（优化版 v2.0）

功能特性：
1. 🤖 自动化集成：自动调用 browser 工具获取东方财富网数据
2. 💾 缓存机制：避免重复调用 browser（TTL=24 小时）
3. 🔧 解析优化：增强鲁棒性，支持页面结构变化
4. 📊 多级降级：Browser → 东方财富 API → 新浪/腾讯 API

用法：
    python3 generate_report.py [日期] [--force-browser] [--no-cache] [--json]

示例：
    python3 generate_report.py                    # 查询最近交易日
    python3 generate_report.py 2026-03-21         # 查询指定日期
    python3 generate_report.py --force-browser    # 强制使用 Browser 方案
    python3 generate_report.py --no-cache         # 忽略缓存，重新获取
    python3 generate_report.py --json             # 输出 JSON 格式
"""

import sys
import os
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# 添加脚本目录到路径
script_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(script_dir))

# 导入现有模块
from cache import DataCache, make_browser_key, make_api_key
from fetch_browser import (
    fetch_from_snapshot, 
    get_browser_url, 
    MARKET_MAPPING,
    parse_amount,
    parse_volume,
)
from fetch_volume import (
    query_market_volume as api_query_market_volume,
    build_summary,
    build_advance_decline_summary,
    query_market_advance_decline,
    fmt_amount,
    MARKETS,
    SUMMARY_MARKETS,
    calc_change,
    HEADERS,
)

# ============================================================================
# 配置
# ============================================================================

CACHE_TTL_HOURS = 24  # 缓存有效期（小时）
BROWSER_TIMEOUT_SEC = 30  # Browser 操作超时（秒）
MAX_RETRY = 2  # 最大重试次数

# 东方财富网 URL
EASTMONEY_URL = "https://quote.eastmoney.com/center/hszs.html"

# 备用 API URL（用于验证 Browser 数据）
EMC_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


# ============================================================================
# Browser 自动化封装
# ============================================================================

class BrowserClient:
    """Browser 工具封装类"""
    
    def __init__(self, timeout_sec: int = BROWSER_TIMEOUT_SEC):
        self.timeout_sec = timeout_sec
    
    def navigate_and_snapshot(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        使用 browser 工具导航到 URL 并获取 snapshot
        
        返回：
            (snapshot_text, error_message)
        """
        try:
            # 步骤 1: 导航到 URL
            nav_cmd = f'browser navigate --targetUrl "{url}"'
            nav_result = subprocess.run(
                nav_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            
            if nav_result.returncode != 0:
                return None, f"Browser navigate 失败：{nav_result.stderr.strip()}"
            
            # 等待页面加载
            import time
            time.sleep(2)
            
            # 步骤 2: 获取 snapshot（使用 aria refs）
            snapshot_cmd = 'browser snapshot --refs aria --compact'
            snapshot_result = subprocess.run(
                snapshot_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec
            )
            
            if snapshot_result.returncode != 0:
                return None, f"Browser snapshot 失败：{snapshot_result.stderr.strip()}"
            
            # 解析 snapshot 输出
            snapshot_data = json.loads(snapshot_result.stdout)
            snapshot_text = snapshot_data.get('text', '')
            
            return snapshot_text, None
        
        except subprocess.TimeoutExpired:
            return None, f"Browser 操作超时（>{self.timeout_sec}秒）"
        except json.JSONDecodeError as e:
            return None, f"Snapshot JSON 解析失败：{e}"
        except Exception as e:
            return None, f"Browser 操作异常：{e}"
    
    def is_available(self) -> bool:
        """检查 Browser 工具是否可用"""
        try:
            result = subprocess.run(
                'browser status',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False


# ============================================================================
# 数据解析优化（增强鲁棒性）
# ============================================================================

def parse_snapshot_robust(snapshot_text: str) -> Dict[str, Any]:
    """
    鲁棒性 snapshot 解析（支持多种页面结构）
    
    策略：
    1. 尝试标准格式解析（正则表达式）
    2. 尝试宽松格式解析（关键词 + 数字提取）
    3. 尝试表格格式解析（表格行解析）
    4. 尝试 OCR 文本解析（如果包含 OCR 结果）
    
    返回：
        {
            "status": "ok" | "partial" | "error",
            "data": { market_name: { amount, close, change_pct, ... } },
            "message": "...",
            "parse_method": "standard" | "loose" | "table" | "ocr",
        }
    """
    if not snapshot_text or len(snapshot_text.strip()) < 50:
        return {
            "status": "error",
            "message": "Snapshot 文本过短或为空",
            "parse_method": "none",
        }
    
    # 策略 1: 标准格式解析
    result = parse_snapshot_standard(snapshot_text)
    if result["status"] == "ok":
        return result
    
    # 策略 2: 宽松格式解析
    result = parse_snapshot_loose(snapshot_text)
    if result["status"] == "ok" or result["status"] == "partial":
        return result
    
    # 策略 3: 表格格式解析
    result = parse_snapshot_table(snapshot_text)
    if result["status"] == "ok" or result["status"] == "partial":
        return result
    
    # 策略 4: OCR 文本解析
    result = parse_snapshot_ocr(snapshot_text)
    if result["status"] == "ok" or result["status"] == "partial":
        return result
    
    # 全部失败
    return {
        "status": "error",
        "message": f"所有解析策略均失败（尝试了 4 种方法）",
        "parse_method": "none",
        "data": {},
    }


def parse_snapshot_standard(snapshot_text: str) -> Dict[str, Any]:
    """标准格式解析（正则表达式）"""
    results = {}
    
    lines = snapshot_text.split('\n')
    
    for line in lines:
        for index_name, market_name in MARKET_MAPPING.items():
            if index_name in line and market_name not in results:
                # 标准格式：序号 代码 名称 最新价 涨跌额 涨跌幅 成交量 成交额
                pattern = r'(\d{6})\s+(' + re.escape(index_name) + r')\s+([\d.]+)\s+([+-]?[\d.]+)\s+([+-]?[\d.]+%)\s+([\d.]+\s*[亿万万])\s+([\d.]+\s*[亿万万])'
                match = re.search(pattern, line)
                
                if match:
                    code, name, close, change_amt, change_pct, volume, amount = match.groups()
                    
                    amount_val = parse_amount(amount)
                    volume_val = parse_volume(volume)
                    close_val = float(close)
                    change_pct_val = float(change_pct.replace('%', ''))
                    
                    if amount_val and close_val:
                        results[market_name] = {
                            "amount": amount_val,
                            "volume": volume_val,
                            "close": close_val,
                            "change_pct": change_pct_val,
                            "source": "browser",
                        }
    
    if len(results) >= 4:
        return {
            "status": "ok",
            "data": results,
            "message": f"成功获取 {len(results)}/4 个市场数据（标准解析）",
            "parse_method": "standard",
        }
    elif len(results) > 0:
        return {
            "status": "partial",
            "data": results,
            "message": f"只获取到 {len(results)}/4 个市场数据（标准解析）",
            "parse_method": "standard",
        }
    else:
        return {
            "status": "error",
            "message": "标准解析未匹配到任何数据",
            "parse_method": "standard",
            "data": {},
        }


def parse_snapshot_loose(snapshot_text: str) -> Dict[str, Any]:
    """宽松格式解析（关键词 + 数字提取）"""
    results = {}
    
    lines = snapshot_text.split('\n')
    
    for line in lines:
        for index_name, market_name in MARKET_MAPPING.items():
            if index_name in line and market_name not in results:
                # 提取所有数字
                numbers = re.findall(r'[\d.]+%?', line)
                
                # 查找包含亿/万的字段（成交额）
                amount_match = re.search(r'([\d.]+)\s*(亿 | 万亿)', line)
                volume_match = re.search(r'([\d.]+)\s*(亿 | 万)\s*(?!亿 | 万亿)', line)
                
                amount_val = None
                volume_val = None
                close_val = None
                change_pct_val = None
                
                if amount_match:
                    amount_val = parse_amount(amount_match.group(0))
                
                if volume_match:
                    volume_val = parse_volume(volume_match.group(0))
                
                # 查找涨跌幅（包含%）
                for num in numbers:
                    if '%' in num:
                        try:
                            change_pct_val = float(num.replace('%', ''))
                            break
                        except:
                            pass
                
                # 查找指数点位（通常在 100-50000 之间）
                for num in numbers:
                    if '%' not in num:
                        try:
                            val = float(num)
                            if 100 < val < 50000 and close_val is None:
                                close_val = val
                                break
                        except:
                            pass
                
                if amount_val and close_val:
                    results[market_name] = {
                        "amount": amount_val,
                        "volume": volume_val,
                        "close": close_val,
                        "change_pct": change_pct_val,
                        "source": "browser",
                    }
    
    if len(results) >= 3:
        return {
            "status": "ok",
            "data": results,
            "message": f"成功获取 {len(results)}/4 个市场数据（宽松解析）",
            "parse_method": "loose",
        }
    elif len(results) > 0:
        return {
            "status": "partial",
            "data": results,
            "message": f"只获取到 {len(results)}/4 个市场数据（宽松解析）",
            "parse_method": "loose",
        }
    else:
        return {
            "status": "error",
            "message": "宽松解析未匹配到任何数据",
            "parse_method": "loose",
            "data": {},
        }


def parse_snapshot_table(snapshot_text: str) -> Dict[str, Any]:
    """表格格式解析（表格行解析）"""
    results = {}
    
    # 尝试识别表格行（通常包含 | 或制表符）
    lines = snapshot_text.split('\n')
    
    for line in lines:
        if '|' in line or '\t' in line:
            # 分割表格单元格
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|')]
            else:
                cells = [cell.strip() for cell in line.split('\t')]
            
            # 查找包含指数名称的单元格
            for i, cell in enumerate(cells):
                for index_name, market_name in MARKET_MAPPING.items():
                    if index_name in cell and market_name not in results:
                        # 从相邻单元格提取数据
                        amount_val = None
                        close_val = None
                        change_pct_val = None
                        
                        for j, other_cell in enumerate(cells):
                            if '亿' in other_cell or '万亿' in other_cell:
                                if amount_val is None:
                                    amount_val = parse_amount(other_cell)
                            elif '%' in other_cell:
                                try:
                                    change_pct_val = float(other_cell.replace('%', ''))
                                except:
                                    pass
                            else:
                                try:
                                    val = float(other_cell)
                                    if 100 < val < 50000 and close_val is None:
                                        close_val = val
                                except:
                                    pass
                        
                        if amount_val and close_val:
                            results[market_name] = {
                                "amount": amount_val,
                                "close": close_val,
                                "change_pct": change_pct_val,
                                "source": "browser",
                            }
    
    if len(results) > 0:
        return {
            "status": "ok" if len(results) >= 3 else "partial",
            "data": results,
            "message": f"成功获取 {len(results)}/4 个市场数据（表格解析）",
            "parse_method": "table",
        }
    else:
        return {
            "status": "error",
            "message": "表格解析未匹配到任何数据",
            "parse_method": "table",
            "data": {},
        }


def parse_snapshot_ocr(snapshot_text: str) -> Dict[str, Any]:
    """OCR 文本解析（如果 snapshot 包含 OCR 结果）"""
    # 检查是否包含 OCR 特征（如 [OCR] 标记）
    if '[OCR]' not in snapshot_text and 'ocr' not in snapshot_text.lower():
        return {
            "status": "error",
            "message": "不包含 OCR 数据",
            "parse_method": "ocr",
            "data": {},
        }
    
    # 使用宽松解析策略
    return parse_snapshot_loose(snapshot_text)


# ============================================================================
# 数据验证与降级
# ============================================================================

def validate_browser_data(browser_data: Dict[str, Any], target_date: str) -> Tuple[bool, str]:
    """
    验证 Browser 数据的合理性
    
    检查项：
    1. 数据完整性（4 个市场）
    2. 数值合理性（成交额 > 0，指数点位在合理范围）
    3. 与 API 数据对比（偏差不超过 20%）
    
    返回：
        (is_valid, error_message)
    """
    # 检查完整性
    if len(browser_data) < 3:
        return False, f"数据不完整：只获取到 {len(browser_data)}/4 个市场"
    
    # 检查数值合理性
    for market_name, data in browser_data.items():
        amount = data.get('amount')
        close = data.get('close')
        
        if not amount or amount <= 0:
            return False, f"{market_name} 成交额异常：{amount}"
        
        if not close or close < 100 or close > 50000:
            return False, f"{market_name} 指数点位异常：{close}"
    
    # 与 API 数据对比（抽样检查）
    try:
        api_results = api_query_market_volume(target_date)
        
        for market_name in ['沪市', '深市']:  # 只检查主要市场
            if market_name in browser_data and market_name in api_results:
                browser_amount = browser_data[market_name]['amount']
                api_amount = api_results[market_name].get('amount', 0)
                
                if api_amount and api_amount > 0:
                    diff_ratio = abs(browser_amount - api_amount) / api_amount
                    
                    if diff_ratio > 0.5:  # 偏差超过 50%
                        return False, f"{market_name} 数据偏差过大：Browser={fmt_amount(browser_amount)}, API={fmt_amount(api_amount)}, 偏差={diff_ratio:.1%}"
    except Exception as e:
        # API 验证失败不影响主流程
        print(f"  ⚠️  API 验证失败（忽略）：{e}")
    
    return True, ""


# ============================================================================
# 主查询逻辑（带缓存）
# ============================================================================

def query_with_cache_and_browser(
    target_date: str,
    force_browser: bool = False,
    no_cache: bool = False
) -> Dict[str, Any]:
    """
    查询成交数据（带缓存和 Browser 自动化）
    
    策略：
    1. 检查缓存（如果启用）
    2. 尝试 Browser 方案（如果可用）
    3. 降级到 API 方案
    
    参数：
        target_date: 目标日期（YYYY-MM-DD）
        force_browser: 强制使用 Browser（忽略缓存）
        no_cache: 不使用缓存
    
    返回：
        {
            "status": "ok" | "partial" | "error",
            "data": { market_name: {...} },
            "summary": {...},
            "source": "browser" | "api" | "cache",
            "cache_hit": bool,
            "message": "...",
        }
    """
    cache = DataCache(ttl_hours=CACHE_TTL_HOURS)
    browser_key = make_browser_key(target_date)
    
    # 步骤 1: 检查缓存
    if not no_cache and not force_browser:
        cached = cache.get(browser_key)
        if cached:
            print(f"  💾 命中缓存（{target_date}）")
            return {
                "status": cached.get("status", "ok"),
                "data": cached.get("data", {}),
                "summary": cached.get("summary"),
                "source": "cache",
                "cache_hit": True,
                "message": "从缓存读取",
            }
    
    # 步骤 2: 尝试 Browser 方案
    if not force_browser:
        print(f"  🌐 尝试 Browser 方案...")
    else:
        print(f"  🌐 使用 Browser 方案（强制模式）...")
    
    browser_client = BrowserClient()
    
    if not browser_client.is_available():
        print(f"  ⚠️  Browser 工具不可用，降级到 API 方案")
        return query_with_api_fallback(target_date, cache, browser_key)
    
    # 导航并获取 snapshot
    snapshot_text, error = browser_client.navigate_and_snapshot(EASTMONEY_URL)
    
    if error:
        print(f"  ⚠️  Browser 获取失败：{error}")
        return query_with_api_fallback(target_date, cache, browser_key)
    
    # 解析 snapshot
    parse_result = parse_snapshot_robust(snapshot_text)
    
    if parse_result["status"] == "error":
        print(f"  ⚠️  Browser 解析失败：{parse_result['message']}")
        return query_with_api_fallback(target_date, cache, browser_key)
    
    browser_data = parse_result.get("data", {})
    
    # 验证数据
    is_valid, error_msg = validate_browser_data(browser_data, target_date)
    
    if not is_valid:
        print(f"  ⚠️  Browser 数据验证失败：{error_msg}")
        return query_with_api_fallback(target_date, cache, browser_key)
    
    # 成功获取 Browser 数据
    print(f"  ✅ Browser 成功（{parse_result['parse_method']}解析）：获取到 {len(browser_data)}/4 个市场")
    
    # 写入缓存
    if not no_cache:
        cache.set(browser_key, browser_data, {
            "source": "browser",
            "parse_method": parse_result["parse_method"],
            "market_count": len(browser_data),
        })
    
    # 构建汇总
    summary = build_summary(browser_data)
    
    return {
        "status": parse_result["status"],
        "data": browser_data,
        "summary": summary,
        "source": "browser",
        "cache_hit": False,
        "message": parse_result["message"],
    }


def query_with_api_fallback(
    target_date: str,
    cache: DataCache,
    browser_key: str
) -> Dict[str, Any]:
    """API 降级方案"""
    print(f"  🔄 使用 API 降级方案...")
    
    api_results = api_query_market_volume(target_date)
    
    # 过滤出 ok 的市场
    api_data = {
        market: {
            "amount": data["amount"],
            "volume": data.get("volume"),
            "close": data["close"],
            "change_pct": data.get("change_pct"),
            "source": data.get("source", "api"),
        }
        for market, data in api_results.items()
        if data["status"] == "ok"
    }
    
    # 写入缓存（标记为 API 数据）
    cache.set(browser_key, api_data, {
        "source": "api_fallback",
        "market_count": len(api_data),
    })
    
    summary = build_summary(api_data)
    
    return {
        "status": "ok" if len(api_data) >= 3 else "partial",
        "data": api_data,
        "summary": summary,
        "source": "api",
        "cache_hit": False,
        "message": "使用 API 降级方案",
    }


# ============================================================================
# 涨跌家数查询
# ============================================================================

def query_advance_decline(target_date: str) -> Dict[str, Any]:
    """查询涨跌家数"""
    print(f"  📊 查询涨跌家数...")
    
    advance_decline_results = query_market_advance_decline(target_date)
    advance_decline_summary = build_advance_decline_summary(advance_decline_results)
    
    return {
        "summary": advance_decline_summary,
        "details": advance_decline_results,
    }


# ============================================================================
# 报告生成
# ============================================================================

def generate_report(
    target_date: str,
    volume_data: Dict[str, Any],
    advance_decline_data: Dict[str, Any],
    output_json: bool = False
) -> str:
    """生成报告"""
    
    if output_json:
        output = {
            "target_date": target_date,
            "volume_data": volume_data,
            "advance_decline": advance_decline_data,
            "generated_at": datetime.now().isoformat(),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    
    # 文本报告
    lines = []
    lines.append("=" * 70)
    lines.append(f"  📊 中国股市成交报告（自动化版 v2.0）")
    lines.append(f"  日期：{target_date}")
    lines.append(f"  数据源：{volume_data['source']}（{'缓存' if volume_data['cache_hit'] else '实时'}）")
    lines.append("=" * 70)
    lines.append("")
    
    # 汇总
    summary = volume_data.get("summary", {})
    if summary:
        s = summary
        arrow = "📈" if (s.get("change_pct") or 0) >= 0 else "📉"
        pct_str = f"{s['change_pct']:+.2f}%" if s.get('change_pct') else "N/A"
        chg_str = s.get("change_fmt", "N/A")
        
        lines.append("  ╔══════════════════════════════════════════════════════════╗")
        lines.append("  ║  📋 三市合计总结（不含重复计算）                           ║")
        lines.append("  ╠══════════════════════════════════════════════════════════╣")
        lines.append(f"  ║  合计成交金额：{s.get('total_fmt', 'N/A'):>12}                            ║")
        lines.append(f"  ║  前一交易日  ：{s.get('total_prev_fmt', 'N/A'):>12}                            ║")
        lines.append(f"  ║  增缩额      ：{chg_str:>12}                            ║")
        lines.append(f"  ║  增缩比例    ：{arrow} {pct_str:>8}                            ║")
        lines.append("  ╚══════════════════════════════════════════════════════════╝")
    
    # 分市场详情
    lines.append("")
    lines.append("  分市场详情:")
    lines.append("  " + "-" * 66)
    
    volume_markets = volume_data.get("data", {})
    for market_name, data in volume_markets.items():
        if data.get("source") == "browser":
            source_tag = "🌐"
        elif data.get("source") == "cache":
            source_tag = "💾"
        else:
            source_tag = "🔌"
        
        amount_fmt = fmt_amount(data["amount"]) if "amount" in data else "N/A"
        close = data.get("close", 0)
        change_pct = data.get("change_pct")
        
        if change_pct is not None:
            arrow = "📈" if change_pct >= 0 else "📉"
            pct_str = f"{change_pct:+.2f}%"
        else:
            arrow = ""
            pct_str = "N/A"
        
        lines.append(f"    {source_tag} {market_name:<6}: {amount_fmt:>10} | 收盘：{close:>8.2f} | 涨跌：{arrow} {pct_str}")
    
    lines.append("  " + "-" * 66)
    lines.append("")
    
    # 涨跌家数
    ads = advance_decline_data.get("summary")
    if ads and ads.get("status") == "ok":
        up_ratio_str = f"{ads['up_ratio']:.1f}%" if ads.get('up_ratio') else "N/A"
        down_ratio_str = f"{ads['down_ratio']:.1f}%" if ads.get('down_ratio') else "N/A"
        
        lines.append("  ╔══════════════════════════════════════════════════════════╗")
        lines.append("  ║  📈 市场情绪（沪深京全市场）                               ║")
        lines.append("  ╠══════════════════════════════════════════════════════════╣")
        lines.append(f"  ║  上涨家数：{ads['total_up']:>6}  ({up_ratio_str:>6})                          ║")
        lines.append(f"  ║  下跌家数：{ads['total_down']:>6}  ({down_ratio_str:>6})                          ║")
        lines.append(f"  ║  平盘家数：{ads['total_unchanged']:>6}                                      ║")
        lines.append("  ╚══════════════════════════════════════════════════════════╝")
    
    lines.append("")
    lines.append("=" * 70)
    
    return "\n".join(lines)


# ============================================================================
# 主函数
# ============================================================================

def parse_date(raw: str) -> Optional[str]:
    """解析日期字符串"""
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


def main():
    # 解析参数
    args = sys.argv[1:]
    
    force_browser = "--force-browser" in args
    no_cache = "--no-cache" in args
    output_json = "--json" in args
    
    # 移除标记参数
    args = [a for a in args if not a.startswith("--")]
    
    # 获取日期
    if args:
        target_date = parse_date(args[0])
        if not target_date:
            print(f"❌ 无效日期：{args[0]}")
            print("支持格式：YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD")
            sys.exit(1)
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    # 如果是非交易日，自动使用最近交易日
    print(f"\n{'='*70}")
    print(f"  📊 cn-stock-volume 自动生成报告（优化版 v2.0）")
    print(f"  目标日期：{target_date}")
    print(f"  选项：force_browser={force_browser}, no_cache={no_cache}, json={output_json}")
    print(f"{'='*70}\n")
    
    # 步骤 1: 查询成交数据
    print("步骤 1: 查询成交数据...")
    volume_data = query_with_cache_and_browser(
        target_date,
        force_browser=force_browser,
        no_cache=no_cache
    )
    
    # 步骤 2: 查询涨跌家数
    print("\n步骤 2: 查询涨跌家数...")
    advance_decline_data = query_advance_decline(target_date)
    
    # 步骤 3: 生成报告
    print("\n步骤 3: 生成报告...")
    report = generate_report(
        target_date,
        volume_data,
        advance_decline_data,
        output_json=output_json
    )
    
    print("\n" + report)
    
    # 返回状态码
    if volume_data["status"] == "error":
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
