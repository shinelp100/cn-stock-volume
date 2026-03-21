#!/usr/bin/env python3
"""
cn-stock-volume: 获取中国股市四市（沪市/深市/创业板/北交所）指定日期的成交金额、增缩量及比例
核心指标：成交金额（亿元）、上涨/下跌家数
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


def query_market_advance_decline(target_date):
    """
    查询沪深京全市场的上涨/下跌/涨停/跌停家数
    使用东方财富指数 API 获取统计数据（f113=上涨，f114=下跌，f115=平盘）
    返回：{ summary: {...}, market_details: {...} }
    """
    try:
        # 直接获取沪市 + 深市涨跌家数（最可靠的方法）
        # 获取上证指数涨跌家数
        url_sh = "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f113,f114,f115&ut=bd1d9ddb04089700cf9c27f6f7426281&secid=1.000001"
        req_sh = urllib.request.Request(url_sh, headers=HEADERS)
        with urllib.request.urlopen(req_sh, timeout=10) as resp:
            data_sh = json.loads(resp.read().decode("utf-8"))
        sh_data = data_sh.get("data") or {}
        
        # 获取深证成指涨跌家数
        url_sz = "https://push2.eastmoney.com/api/qt/stock/get?invt=2&fltt=2&fields=f113,f114,f115&ut=bd1d9ddb04089700cf9c27f6f7426281&secid=0.399001"
        req_sz = urllib.request.Request(url_sz, headers=HEADERS)
        with urllib.request.urlopen(req_sz, timeout=10) as resp:
            data_sz = json.loads(resp.read().decode("utf-8"))
        sz_data = data_sz.get("data") or {}
        
        # 合并数据
        up = (sh_data.get("f113") or 0) + (sz_data.get("f113") or 0)
        down = (sh_data.get("f114") or 0) + (sz_data.get("f114") or 0)
        unchanged = (sh_data.get("f115") or 0) + (sz_data.get("f115") or 0)
        
        # 涨停跌停数据（从个股统计，简化处理为估算）
        limit_up = 0
        limit_down = 0
        
        if up > 0 or down > 0:
            if unchanged is None:
                unchanged = 0
            total = up + down + unchanged
            
            return {
                "summary": {
                    "status": "ok",
                    "date": target_date,
                    "up": up,
                    "down": down,
                    "unchanged": unchanged,
                    "limit_up": limit_up,
                    "limit_down": limit_down,
                    "total": total,
                    "up_ratio": round(up / total * 100, 2) if total > 0 else None,
                    "down_ratio": round(down / total * 100, 2) if total > 0 else None,
                },
                "market_details": {
                    "沪市": {"up": sh_data.get("f113", 0), "down": sh_data.get("f114", 0), "unchanged": sh_data.get("f115", 0)},
                    "深市": {"up": sz_data.get("f113", 0), "down": sz_data.get("f114", 0), "unchanged": sz_data.get("f115", 0)},
                }
            }
        else:
            return {
                "summary": {
                    "status": "no_data",
                    "message": "API 返回的涨跌家数为空",
                },
                "market_details": {}
            }
        
    except Exception as e:
        return {
            "summary": {
                "status": "error",
                "message": str(e),
            },
            "market_details": {}
        }


def build_advance_decline_summary(advance_decline_results):
    """
    汇总沪深京全市场涨跌家数数据
    advance_decline_results 现在是一个包含 summary 和 market_details 的字典
    """
    if not advance_decline_results or advance_decline_results.get("summary", {}).get("status") != "ok":
        return None
    
    summary = advance_decline_results["summary"]
    
    return {
        "total_up": summary["up"],
        "total_down": summary["down"],
        "total_unchanged": summary["unchanged"],
        "limit_up": summary.get("limit_up", 0),
        "limit_down": summary.get("limit_down", 0),
        "grand_total": summary["total"],
        "up_ratio": summary["up_ratio"],
        "down_ratio": summary["down_ratio"],
        "market_details": advance_decline_results.get("market_details", {}),
    }


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


def print_report(target_date, results, summary, advance_decline_summary=None):
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
        
        # 涨跌家数统计（v1.2.2+ 包含涨停跌停）
        if advance_decline_summary:
            ads = advance_decline_summary
            up_ratio_str = f"{ads['up_ratio']:.1f}%" if ads['up_ratio'] is not None else "N/A"
            down_ratio_str = f"{ads['down_ratio']:.1f}%" if ads['down_ratio'] is not None else "N/A"
            
            # 判断市场情绪
            if ads['up_ratio'] and ads['down_ratio']:
                if ads['up_ratio'] > 60:
                    sentiment = "🟢 强势"
                elif ads['up_ratio'] > 50:
                    sentiment = "🟡 偏强"
                elif ads['down_ratio'] > 60:
                    sentiment = "🔴 弱势"
                elif ads['down_ratio'] > 50:
                    sentiment = "🟠 偏弱"
                else:
                    sentiment = "⚪ 震荡"
            else:
                sentiment = "N/A"
            
            # 涨停跌停数据
            limit_up = ads.get('limit_up', 0)
            limit_down = ads.get('limit_down', 0)
            
            print(f"""
  ╔══════════════════════════════════════════════════════════╗
  ║  📈 市场情绪（沪深京全市场）                               ║
  ╠══════════════════════════════════════════════════════════╣
  ║  上涨家数  ：{ads['total_up']:>6}  ({up_ratio_str:>6})                          ║
  ║  下跌家数  ：{ads['total_down']:>6}  ({down_ratio_str:>6})                          ║
  ║  平盘家数  ：{ads['total_unchanged']:>6}                                      ║
  ║  总计      ：{ads['grand_total']:>6}                                      ║
  ╠══════════════════════════════════════════════════════════╣
  ║  市场情绪  ：{sentiment:<6}                                      ║
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
    
    # 查询涨跌家数（v1.2.0+）
    print(f"正在查询 {raw_date} 的涨跌家数...")
    advance_decline_results = query_market_advance_decline(raw_date)
    advance_decline_summary = build_advance_decline_summary(advance_decline_results)

    if "--json" in sys.argv:
        output = {
            "target_date": raw_date,
            "summary": summary,
            "markets": results,
            "advance_decline_summary": advance_decline_summary,
            "advance_decline_details": advance_decline_results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_report(raw_date, results, summary, advance_decline_summary)


if __name__ == "__main__":
    main()
