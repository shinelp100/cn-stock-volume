#!/usr/bin/env python3
"""
cn-stock-volume: 获取中国股市四市（沪市/深市/创业板/北交所）指定日期的成交金额、增缩量及比例
核心指标：成交金额（亿元）
数据来源：东方财富网（免费，无需 API Key）

注意：创业板是深交所的子板块，深市成交金额已包含创业板数据。
      合计计算时只统计：沪市 + 深市 + 北交所，避免重复计算。
"""

import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.eastmoney.com/",
}

MARKETS = {
    "沪市":    {"code": "000001", "market": "1", "name": "上证指数"},
    "深市":    {"code": "399001", "market": "0", "name": "深证成指"},
    "创业板":  {"code": "399006", "market": "0", "name": "创业板指"},
    "北交所":  {"code": "899050", "market": "0", "name": "北证 50"},
}

# 用于合计计算的市场（排除创业板，避免与深市重复计算）
SUMMARY_MARKETS = ["沪市", "深市", "北交所"]

EMC_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def fetch_kline(code, market, end_date, count=5):
    params = {
        "secid": f"{market}.{code}",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",   # 日线
        "fqt": "1",
        "end": end_date,
        "lmt": str(count),
        "cb": "",
    }
    url = EMC_KLINE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    klines = data.get("data", {}).get("klines", [])
    result = []
    for k in klines:
        parts = k.split(",")
        if len(parts) >= 7:
            result.append({
                "date":   parts[0],
                "open":   float(parts[1]),
                "close":  float(parts[2]),
                "high":   float(parts[3]),
                "low":    float(parts[4]),
                "volume": int(parts[5]),    # 成交量（手）
                "amount": float(parts[6]),   # 成交额（元）
            })
    result.sort(key=lambda x: x["date"])
    return result


def fmt_amount(yuan):
    """成交额（元）→ 简洁的亿元字符串"""
    亿 = yuan / 1e8
    if abs(亿) >= 100:
        return f"{亿:.1f}亿"
    elif abs(亿) >= 10:
        return f"{亿:.2f}亿"
    else:
        return f"{亿:.2f}亿"


def parse_date(raw):
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


def calc_change(curr, prev):
    """计算变化量和百分比"""
    if prev and prev != 0:
        chg = curr - prev
        pct = round(chg / prev * 100, 2)
        return chg, pct
    return None, None


def query_market_volume(target_date):
    """
    查询四市指定日期的成交金额数据
    返回：{ market_name: { status, index_name, date, amount, change... } }
    """
    end_date = target_date.replace("-", "")
    all_results = {}

    for market_name, info in MARKETS.items():
        try:
            klines = fetch_kline(info["code"], info["market"], end_date, count=5)

            if not klines:
                all_results[market_name] = {
                    "status": "no_data",
                    "index_name": info["name"],
                    "message": "API 返回为空",
                }
                continue

            today_rec  = klines[-1]
            prev_rec   = klines[-2] if len(klines) >= 2 else None

            if today_rec["date"] != target_date:
                all_results[market_name] = {
                    "status": "no_data",
                    "index_name": info["name"],
                    "message": f"未找到 {target_date} 的交易数据（可能为非交易日）。最近交易日为 {today_rec['date']}",
                    "nearest_date": today_rec["date"],
                }
                continue

            amt_today  = today_rec["amount"]
            amt_prev   = prev_rec["amount"]  if prev_rec else None
            amt_chg, amt_pct = calc_change(amt_today, amt_prev)

            all_results[market_name] = {
                "status":       "ok",
                "index_name":   info["name"],
                "date":         target_date,
                "prev_date":    prev_rec["date"] if prev_rec else None,
                # 成交金额
                "amount":       amt_today,
                "amount_fmt":   fmt_amount(amt_today),
                "amount_prev":  amt_prev,
                "prev_fmt":     fmt_amount(amt_prev) if amt_prev else "N/A",
                "change":       amt_chg,
                "change_fmt":   (("+" if amt_chg >= 0 else "") + fmt_amount(abs(amt_chg))) if amt_chg is not None else "N/A",
                "change_pct":   amt_pct,
                # 指数收盘
                "close":        today_rec["close"],
                "close_prev":   prev_rec["close"] if prev_rec else None,
            }

        except Exception as e:
            all_results[market_name] = {
                "status": "error",
                "index_name": info["name"],
                "message": str(e),
            }

    return all_results


def build_summary(results):
    """
    汇总市场数据，计算合计成交金额及环比变化
    
    注意：创业板是深交所的子板块，深市成交金额已包含创业板数据。
         合计计算时只统计：沪市 + 深市 + 北交所，避免重复计算。
    """
    ok_markets = {k: v for k, v in results.items() if v["status"] == "ok"}

    if not ok_markets:
        return None

    # 用于合计的市场（排除创业板，避免重复计算）
    summary_markets = {k: v for k, v in ok_markets.items() if k in SUMMARY_MARKETS}

    if not summary_markets:
        return None

    total_amount     = sum(v["amount"]      for v in summary_markets.values())
    total_prev      = sum(v["amount_prev"] for v in summary_markets.values() if v["amount_prev"])
    total_chg, total_pct = calc_change(total_amount, total_prev)

    # 各市场占总额比例（基于用于合计的市场）
    contributions = {}
    for k, v in summary_markets.items():
        pct = round(v["amount"] / total_amount * 100, 2) if total_amount else None
        contributions[k] = pct

    # 找最强/最弱市场（按成交额，基于用于合计的市场）
    sorted_markets = sorted(summary_markets.items(), key=lambda x: x[1]["amount"], reverse=True)

    return {
        "total_amount":    total_amount,
        "total_fmt":      fmt_amount(total_amount),
        "total_prev":      total_prev,
        "total_prev_fmt":  fmt_amount(total_prev) if total_prev else "N/A",
        "change":          total_chg,
        "change_fmt":      (("+" if total_chg >= 0 else "") + fmt_amount(abs(total_chg))) if total_chg is not None else "N/A",
        "change_pct":      total_pct,
        "contributions":   contributions,
        "largest_market": sorted_markets[0][0],
        "smallest_market": sorted_markets[-1][0],
        "market_count":    len(summary_markets),
    }


def print_report(target_date, results, summary):
    # ── 总结 ──
    print(f"\n{'='*70}")
    print(f"  📊 中国股市成交报告  |  日期：{target_date}")
    print(f"{'='*70}")

    if summary:
        s = summary
        arrow = "📈" if (s["change_pct"] or 0) >= 0 else "📉"
        pct_str = f"{s['change_pct']:+.2f}%" if s['change_pct'] is not None else "N/A"
        chg_str = f"{s['change_fmt']}" if s["change"] is not None else "N/A"

        print(f"""
  ╔══════════════════════════════════════════════════════════╗
  ║  📋 三市合计总结（不含重复计算）                           ║
  ╠══════════════════════════════════════════════════════════╣
  ║  合计成交金额：{s['total_fmt']:>12}                            ║
  ║  前一交易日  ：{s['total_prev_fmt']:>12}                            ║
  ║  增缩额      ：{chg_str:>12}                            ║
  ║  增缩比例    ：{arrow} {pct_str:>8}                            ║
  ╠══════════════════════════════════════════════════════════╣""")

        # 各市场占比
        contrib_lines = ""
        for market, pct in s["contributions"].items():
            contrib_lines += f"\n  ║    {market:<6}：{pct:>5.2f}%                               ║"
        print(f"  ║  各市场占比{contrib_lines}")
        print(f"""  ╠══════════════════════════════════════════════════════════╣
  ║  成交最大  ：{s['largest_market']:<6}（{s['contributions'][s['largest_market']]:.2f}%）                         ║
  ║  成交最小  ：{s['smallest_market']:<6}（{s['contributions'][s['smallest_market']]:.2f}%）                         ║
  ╠══════════════════════════════════════════════════════════╣
  ║  注：创业板已包含在深市中，合计不重复计算                  ║
  ╚══════════════════════════════════════════════════════════╝""")
    else:
        print("  ⚠️  所有市场数据均无法获取，无法生成总结。")

    # ── 分市场详情 ──
    print(f"\n  {'─'*66}")
    print(f"  {'市场':<8} {'指数收盘':>10}  {'前一收盘':>10}  {'成交金额 (亿)':>14}  {'前日金额':>12}  {'增缩额':>14}  {'比例':>8}")
    print(f"  {'─'*66}")

    for market_name, data in results.items():
        if data["status"] != "ok":
            label = f"{market_name} ⚠️"
            msg   = data.get("message", "数据获取失败")
            print(f"  {label:<8} {msg[:40]}")
            continue

        pct     = data["change_pct"]
        arrow   = "📈" if (pct or 0) >= 0 else "📉"
        pct_str = f"{pct:+.2f}%" if pct is not None else "N/A"
        chg_str = data["change_fmt"]
        prev_dt = data["prev_date"] or ""

        print(
            f"  {market_name:<8}"
            f" {data['close']:>10.2f}  "
            f" {data['close_prev'] or 0:>10.2f}  "
            f" {data['amount_fmt']:>14}  "
            f" {data['prev_fmt']:>12}  "
            f" {chg_str:>14}  "
            f" {arrow} {pct_str:>7}"
        )

    print(f"  {'─'*66}")
    print(f"  数据来源：东方财富网  |  成交额单位：亿元（1 亿 = 10⁸ 元）")
    print(f"{'='*70}\n")


def main():
    # 解析目标日期
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        raw_date = parse_date(sys.argv[1])
        if not raw_date:
            print(f"❌ 日期格式错误：{sys.argv[1]}，支持 YYYY-MM-DD 或 YYYYMMDD")
            sys.exit(1)
    else:
        raw_date = datetime.now().strftime("%Y-%m-%d")

    print(f"正在查询 {raw_date} 的成交数据...")
    results = query_market_volume(raw_date)
    summary = build_summary(results)

    if "--json" in sys.argv:
        output = {"target_date": raw_date, "summary": summary, "markets": results}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(raw_date, results, summary)


if __name__ == "__main__":
    main()
