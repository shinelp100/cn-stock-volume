#!/usr/bin/env python3
"""
cn-stock-volume v1.4.0: 获取中国股市四市成交金额（Browser 首选方案）

数据源优先级：
1️⃣ 首选：Browser 工具（东方财富网网页版）
2️⃣ 备用 1：东方财富网 K 线 API
3️⃣ 备用 2：新浪财经 API
4️⃣ 备用 3：腾讯财经 API

用法：
    python3 fetch_volume_browser.py <YYYY-MM-DD>
    python3 fetch_volume_browser.py --with-browser  # 使用 Browser 方案
"""

import sys
import os
import json

# 添加脚本目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from fetch_browser import fetch_from_snapshot, get_browser_url, MARKET_MAPPING
from fetch_volume import (
    query_market_volume as api_query_market_volume,
    build_summary,
    build_advance_decline_summary,
    query_market_advance_decline,
    print_report,
    parse_date,
    fmt_amount,
    MARKETS,
)


def query_with_browser_priority(target_date, browser_snapshot=None):
    """
    使用 Browser 优先策略查询四市数据
    
    参数：
        target_date: 目标日期
        browser_snapshot: browser snapshot 文本（可选）
    
    返回：
        { market_name: { status, amount, close, ... } }
    """
    all_results = {}
    
    # 1️⃣ 首选：Browser 方案
    if browser_snapshot:
        print(f"  🌐 使用 Browser 方案（首选）...")
        browser_result = fetch_from_snapshot(browser_snapshot)
        
        if browser_result["status"] in ["ok", "partial"]:
            browser_data = browser_result.get("data", {})
            
            for market_name in MARKETS.keys():
                if market_name in browser_data:
                    data = browser_data[market_name]
                    all_results[market_name] = {
                        "status":       "ok",
                        "index_name":   MARKETS[market_name]["name"],
                        "date":         target_date,
                        "amount":       data["amount"],
                        "amount_fmt":   fmt_amount(data["amount"]),
                        "close":        data["close"],
                        "change_pct":   data.get("change_pct"),
                        "source":       "browser",
                    }
                    print(f"  ✅ Browser 成功：{market_name} = {all_results[market_name]['amount_fmt']}")
            
            if browser_result["status"] == "ok":
                print(f"  📌 Browser 方案获取全部 4 个市场数据")
                return all_results
    
    # 2️⃣-4️⃣ 备用：API 方案
    print(f"  🔄 Browser 方案不可用，使用 API 降级方案...")
    api_results = api_query_market_volume(target_date)
    
    # 合并结果（Browser 成功的保留，失败的用 API 补充）
    for market_name in MARKETS.keys():
        if market_name not in all_results:
            all_results[market_name] = api_results.get(market_name, {
                "status": "error",
                "index_name": MARKETS[market_name]["name"],
                "message": "数据获取失败",
            })
    
    return all_results


def main():
    if len(sys.argv) < 2:
        print("用法：python3 fetch_volume_browser.py <YYYY-MM-DD> [--snapshot <file>]")
        print()
        print("选项:")
        print("  --snapshot <file>  从文件读取 browser snapshot（可选）")
        print()
        print("示例:")
        print("  python3 fetch_volume_browser.py 2026-03-21")
        print("  python3 fetch_volume_browser.py 2026-03-21 --snapshot snapshot.txt")
        sys.exit(1)
    
    target_date = parse_date(sys.argv[1])
    if not target_date:
        print(f"❌ 无效日期：{sys.argv[1]}")
        print("支持格式：YYYY-MM-DD, YYYYMMDD, YYYY/MM/DD")
        sys.exit(1)
    
    # 检查是否有 --snapshot 参数
    browser_snapshot = None
    if "--snapshot" in sys.argv:
        idx = sys.argv.index("--snapshot")
        if idx + 1 < len(sys.argv):
            snapshot_file = sys.argv[idx + 1]
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    browser_snapshot = f.read()
                print(f"  📄 已读取 browser snapshot: {snapshot_file}")
            except Exception as e:
                print(f"  ⚠️  读取 snapshot 失败：{e}")
    
    print(f"\n{'='*70}")
    print(f"  📊 中国股市成交报告（Browser 首选方案 v1.4.0）")
    print(f"  目标日期：{target_date}")
    print(f"{'='*70}\n")
    
    # 查询成交数据
    print("正在查询成交数据...")
    results = query_with_browser_priority(target_date, browser_snapshot)
    
    # 查询涨跌家数
    print("正在查询涨跌家数...")
    advance_decline_results = query_market_advance_decline(target_date)
    advance_decline_summary = build_advance_decline_summary(advance_decline_results)
    
    # 构建汇总
    summary = build_summary(results)
    
    # 输出报告
    print_report(target_date, results, summary, advance_decline_summary)
    
    # JSON 输出（如果请求）
    if "--json" in sys.argv:
        output = {
            "target_date": target_date,
            "summary": summary,
            "markets": results,
            "advance_decline_summary": advance_decline_summary,
        }
        print("\n" + "="*70)
        print("JSON 输出:")
        print("="*70)
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
