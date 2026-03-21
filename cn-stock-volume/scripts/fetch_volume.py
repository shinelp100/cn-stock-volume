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

# 新浪财经股票代码映射
SINA_CODES = {
    "沪市": "sh000001",
    "深市": "sz399001",
    "创业板": "sz399006",
    "北交所": "sh899050",
}

# 腾讯财经股票代码映射
TENCENT_CODES = {
    "沪市": "sh000001",
    "深市": "sz399001",
    "创业板": "sz399006",
    "北交所": "sh899050",
}


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


def fetch_sina_volume(market_name):
    """
    新浪财经 API 获取成交金额（备用方案 1）
    返回：{ amount: float(元), volume: int(手), close: float, date: str }
    
    数据源：https://hq.sinajs.cn/list=[股票代码]
    注意：返回 GBK 编码，需解码
    """
    if market_name not in SINA_CODES:
        return None
    
    sina_code = SINA_CODES[market_name]
    url = f"https://hq.sinajs.cn/list={sina_code}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("gbk")  # 新浪返回 GBK 编码
        
        # 解析：var hq_str_sh000001="上证指数，3041.23,3050.12,..."
        match = re.search(r'="([^"]+)"', data)
        if not match:
            return None
        
        fields = match.group(1).split(",")
        if len(fields) < 8:
            return None
        
        # 字段 7 = 成交额（元），字段 6 = 成交量（手），字段 3 = 当前点位
        amount = float(fields[7]) if fields[7] else 0
        volume = float(fields[6]) if fields[6] else 0
        close = float(fields[3]) if fields[3] else 0
        
        # 获取日期（从系统时间，新浪实时数据不提供日期）
        today = datetime.now().strftime("%Y-%m-%d")
        
        return {
            "amount": amount,
            "volume": int(volume),
            "close": close,
            "date": today,
            "source": "sina",
        }
    except Exception as e:
        print(f"  ⚠️  新浪财经 API 失败：{e}")
        return None


def fetch_sina_with_retry(market_name, retries=2):
    """新浪财经 API 带重试"""
    for i in range(retries):
        result = fetch_sina_volume(market_name)
        if result and result['amount'] > 0:
            return result
        if i < retries - 1:
            import time
            time.sleep(1)
    return None


def fetch_tencent_volume(market_name):
    """
    腾讯财经 API 获取成交金额（备用方案 2）
    返回：{ amount: float(元), close: float, date: str }
    
    数据源：https://web.ifzq.gtimg.cn/appstock/app/fqkline/get
    """
    if market_name not in TENCENT_CODES:
        return None
    
    tencent_code = TENCENT_CODES[market_name]
    # 转换代码格式：sh000001 → sh000001
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},,,,60"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://stockapp.finance.qq.com/",
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode('utf-8')
        
        json_data = json.loads(data)
        kline_data = json_data.get("data", {}).get(tencent_code, {})
        data_list = kline_data.get("data", [])
        
        if not data_list:
            return None
        
        # 最新数据（最后一条）
        latest = data_list[-1]
        if len(latest) >= 6:
            # 字段：[日期，收盘，开盘，最高，最低，成交额，...]
            return {
                "date": latest[0],
                "close": float(latest[1]) if latest[1] else 0,
                "amount": float(latest[5]) if len(latest) > 5 and latest[5] else 0,
                "source": "tencent",
            }
        return None
    except Exception as e:
        print(f"  ⚠️  腾讯财经 API 失败：{e}")
        return None


def fetch_tencent_with_retry(market_name, retries=2):
    """腾讯财经 API 带重试"""
    for i in range(retries):
        result = fetch_tencent_volume(market_name)
        if result and result.get('amount', 0) > 0:
            return result
        if i < retries - 1:
            import time
            time.sleep(1)
    return None


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
    查询四市指定日期的成交金额数据（支持多层降级）
    返回：{ market_name: { status, index_name, date, amount, change... } }
    
    降级策略：
    1️⃣ 首选：东方财富网 K 线 API
    2️⃣ 备用：新浪财经 API（实时数据）
    
    注意：如果目标日期是非交易日，自动使用最近交易日数据
    """
    end_date = target_date.replace("-", "")
    all_results = {}
    actual_date = None  # 记录实际使用的交易日
    sina_fallback_used = False  # 标记是否使用了新浪财经备用方案

    for market_name, info in MARKETS.items():
        result = None
        
        # 1️⃣ 首选：东方财富网 K 线 API
        try:
            klines = fetch_kline(info["code"], info["market"], end_date, count=5)

            if klines:
                today_rec  = klines[-1]
                prev_rec   = klines[-2] if len(klines) >= 2 else None

                # 如果目标日期不是交易日，自动使用最近交易日数据
                if today_rec["date"] != target_date:
                    if actual_date is None:
                        actual_date = today_rec["date"]
                    
                    result = {
                        "status":       "ok",
                        "index_name":   info["name"],
                        "date":         today_rec["date"],
                        "prev_date":    prev_rec["date"] if prev_rec else None,
                        "note":         f"目标日期 {target_date} 为非交易日，使用最近交易日 {today_rec['date']} 数据",
                        "amount":       today_rec["amount"],
                        "amount_fmt":   fmt_amount(today_rec["amount"]),
                        "amount_prev":  prev_rec["amount"]  if prev_rec else None,
                        "prev_fmt":     fmt_amount(prev_rec["amount"]) if prev_rec and prev_rec["amount"] else "N/A",
                        "change":       None,
                        "change_fmt":   "N/A",
                        "change_pct":   None,
                        "close":        today_rec["close"],
                        "close_prev":   prev_rec["close"] if prev_rec else None,
                        "source":       "eastmoney",
                    }
                else:
                    amt_today  = today_rec["amount"]
                    amt_prev   = prev_rec["amount"]  if prev_rec else None
                    amt_chg, amt_pct = calc_change(amt_today, amt_prev)

                    result = {
                        "status":       "ok",
                        "index_name":   info["name"],
                        "date":         target_date,
                        "prev_date":    prev_rec["date"] if prev_rec else None,
                        "amount":       amt_today,
                        "amount_fmt":   fmt_amount(amt_today),
                        "amount_prev":  amt_prev,
                        "prev_fmt":     fmt_amount(amt_prev) if amt_prev else "N/A",
                        "change":       amt_chg,
                        "change_fmt":   (("+" if amt_chg >= 0 else "") + fmt_amount(abs(amt_chg))) if amt_chg is not None else "N/A",
                        "change_pct":   amt_pct,
                        "close":        today_rec["close"],
                        "close_prev":   prev_rec["close"] if prev_rec else None,
                        "source":       "eastmoney",
                    }
        except Exception as e:
            print(f"  ⚠️  东方财富 API 失败（{market_name}）：{e}")
        
        # 2️⃣ 备用：新浪财经 API（如果东方财富失败）
        if result is None or result.get("status") != "ok":
            print(f"  🔄 尝试新浪财经 API（备用 1）：{market_name}...")
            sina_result = fetch_sina_with_retry(market_name)
            
            if sina_result and sina_result['amount'] > 0:
                sina_fallback_used = True
                result = {
                    "status":       "ok",
                    "index_name":   info["name"],
                    "date":         sina_result["date"],
                    "prev_date":    None,
                    "note":         "使用新浪财经 API（备用 1）",
                    "amount":       sina_result["amount"],
                    "amount_fmt":   fmt_amount(sina_result["amount"]),
                    "amount_prev":  None,
                    "prev_fmt":     "N/A",
                    "change":       None,
                    "change_fmt":   "N/A",
                    "change_pct":   None,
                    "close":        sina_result["close"],
                    "close_prev":   None,
                    "source":       "sina",
                }
                print(f"  ✅ 新浪财经 API 成功：{market_name} = {result['amount_fmt']}")
        
        # 3️⃣ 备用：腾讯财经 API（如果新浪财经也失败）
        if result is None or result.get("status") != "ok":
            print(f"  🔄 尝试腾讯财经 API（备用 2）：{market_name}...")
            tencent_result = fetch_tencent_with_retry(market_name)
            
            if tencent_result and tencent_result.get('amount', 0) > 0:
                sina_fallback_used = True
                result = {
                    "status":       "ok",
                    "index_name":   info["name"],
                    "date":         tencent_result["date"],
                    "prev_date":    None,
                    "note":         "使用腾讯财经 API（备用 2）",
                    "amount":       tencent_result["amount"],
                    "amount_fmt":   fmt_amount(tencent_result["amount"]),
                    "amount_prev":  None,
                    "prev_fmt":     "N/A",
                    "change":       None,
                    "change_fmt":   "N/A",
                    "change_pct":   None,
                    "close":        tencent_result["close"],
                    "close_prev":   None,
                    "source":       "tencent",
                }
                print(f"  ✅ 腾讯财经 API 成功：{market_name} = {result['amount_fmt']}")
        
        # 全部失败
        if result is None or result.get("status") != "ok":
            result = {
                "status": "error",
                "index_name": info["name"],
                "message": "所有 API 均失败（东方财富、新浪、腾讯）",
                "source": "none",
            }
        
        all_results[market_name] = result

    if sina_fallback_used:
        print(f"  📌 已启用新浪财经备用方案")
    
    return all_results


def build_summary(results):
    """
    汇总市场数据，计算合计成交金额及环比变化
    
    注意：创业板是深交所的子板块，深市成交金额已包含创业板数据。
         合计计算时只统计：沪市 + 深市 + 北交所，避免重复计算。
    
    如果所有市场都失败，返回一个包含错误信息的 summary（而不是 None）
    """
    ok_markets = {k: v for k, v in results.items() if v["status"] == "ok"}

    # 如果没有成功获取的市场，返回一个空的 summary（而不是 None）
    if not ok_markets:
        return {
            "total_amount": 0,
            "total_fmt": "0 亿",
            "total_prev": 0,
            "total_prev_fmt": "0 亿",
            "change": 0,
            "change_fmt": "0 亿",
            "change_pct": 0,
            "contributions": {},
            "largest_market": "N/A",
            "smallest_market": "N/A",
            "market_count": 0,
            "error": "所有市场数据获取失败",
        }

    # 用于合计的市场（排除创业板，避免重复计算）
    summary_markets = {k: v for k, v in ok_markets.items() if k in SUMMARY_MARKETS}

    if not summary_markets:
        return {
            "total_amount": 0,
            "total_fmt": "0 亿",
            "total_prev": 0,
            "total_prev_fmt": "0 亿",
            "change": 0,
            "change_fmt": "0 亿",
            "change_pct": 0,
            "contributions": {},
            "largest_market": "N/A",
            "smallest_market": "N/A",
            "market_count": 0,
            "error": "可用于合计的市场数据为空",
        }

    total_amount     = sum(v["amount"]      for v in summary_markets.values())
    total_prev      = sum(v["amount_prev"] for v in summary_markets.values() if v["amount_prev"])
    
    # 只有在所有市场都有 prev 数据时才计算环比
    has_all_prev = all(v.get("amount_prev") is not None for v in summary_markets.values())
    if has_all_prev:
        total_chg, total_pct = calc_change(total_amount, total_prev)
    else:
        total_chg, total_pct = None, None

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
        
        # 处理 N/A 情况（所有市场数据获取失败时）
        if s['largest_market'] == "N/A" or not s['contributions']:
            print(f"""  ╠══════════════════════════════════════════════════════════╣
  ║  成交最大  ：数据不足                                              ║
  ║  成交最小  ：数据不足                                              ║
  ╠══════════════════════════════════════════════════════════╣
  ║  注：创业板已包含在深市中，合计不重复计算                  ║
  ╚══════════════════════════════════════════════════════════╝""")
        else:
            largest_pct = s['contributions'].get(s['largest_market'], 0)
            smallest_pct = s['contributions'].get(s['smallest_market'], 0)
            print(f"""  ╠══════════════════════════════════════════════════════════╣
  ║  成交最大  ：{s['largest_market']:<6}（{largest_pct:.2f}%）                         ║
  ║  成交最小  ：{s['smallest_market']:<6}（{smallest_pct:.2f}%）                         ║
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
            if "--json" not in sys.argv:
                print(f"❌ 日期格式错误：{sys.argv[1]}，支持 YYYY-MM-DD 或 YYYYMMDD")
            sys.exit(1)
    else:
        raw_date = datetime.now().strftime("%Y-%m-%d")

    # --json 模式下不打印日志，避免污染 JSON 输出
    quiet_mode = "--json" in sys.argv
    
    if not quiet_mode:
        print(f"正在查询 {raw_date} 的成交数据...")
    results = query_market_volume(raw_date)
    summary = build_summary(results)
    
    # 查询涨跌家数（v1.2.0+）
    if not quiet_mode:
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
