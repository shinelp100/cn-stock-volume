#!/usr/bin/env python3
"""
fetch_volume.py - 三市成交金额
数据来源：东方财富网 K线 API
已排除ST股票
"""

import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.eastmoney.com/",
}

# 沪市、深市、北交所
MARKETS = {
    "沪市":   {"code": "000001", "market": "1", "name": "上证指数"},
    "深市":   {"code": "399001", "market": "0", "name": "深证成指"},
    "北交所": {"code": "899050", "market": "0", "name": "北证50"},
}

EMC_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def parse_date(raw):
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


def fetch_kline(code, market, end_date, count=5):
    params = {
        "secid": f"{market}.{code}",
        "ut": "fa5fd1943c7b386f172d6893dbfba10b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",
        "fqt": "1",
        "end": end_date,
        "lmt": str(count),
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
                "close":  float(parts[2]),
                "amount": float(parts[6]),
            })
    result.sort(key=lambda x: x["date"])
    return result


def fmt_yuan(yuan):
    亿 = yuan / 1e8
    if abs(亿) >= 10000:
        return f"{亿/10000:.2f}万亿", 亿
    elif abs(亿) >= 100:
        return f"{亿:.1f}亿", 亿
    else:
        return f"{亿:.2f}亿", 亿


def calc_change(curr, prev):
    if prev and prev != 0:
        chg = curr - prev
        pct = round(chg / prev * 100, 2)
        return chg, pct
    return None, None


def get_volume(target_date):
    """
    返回结构：
    {
        "status": "ok"|"error",
        "target_date": str,
        "markets": {
            "沪市": { "status": "ok"|..., "amount": float, "amount_fmt": str,
                      "change": float, "change_pct": float, "close": float, ... },
            ...
        },
        "summary": {
            "total_amount": float, "total_fmt": str,
            "change": float, "change_pct": float,
            "change_arrow": "📈"|"📉", "change_str": str,
            "contributions": {"沪市": float, ...},
            "largest": str, "smallest": str
        }
    }
    """
    end_date = target_date.replace("-", "")
    results = {}

    for m_name, info in MARKETS.items():
        try:
            klines = fetch_kline(info["code"], info["market"], end_date, count=5)
            if not klines:
                results[m_name] = {"status": "no_data", "message": "API返回空"}
                continue
            today_rec = klines[-1]
            prev_rec  = klines[-2] if len(klines) >= 2 else None

            if today_rec["date"] != target_date:
                results[m_name] = {
                    "status": "not_today",
                    "nearest_date": today_rec["date"],
                    "message": f"非交易日，最近 {today_rec['date']}"
                }
                continue

            amt_today = today_rec["amount"]
            amt_prev = prev_rec["amount"] if prev_rec else None
            amt_chg, amt_pct = calc_change(amt_today, amt_prev)
            amt_fmt, _ = fmt_yuan(amt_today)
            prev_fmt, _ = fmt_yuan(amt_prev) if amt_prev else ("N/A", 0)

            results[m_name] = {
                "status": "ok",
                "date": target_date,
                "prev_date": prev_rec["date"] if prev_rec else None,
                "amount": amt_today,
                "amount_fmt": amt_fmt,
                "amount_prev": amt_prev,
                "prev_fmt": prev_fmt,
                "change": amt_chg,
                "change_fmt": (("+" if amt_chg >= 0 else "") + fmt_yuan(abs(amt_chg))[0]) if amt_chg is not None else "N/A",
                "change_pct": amt_pct,
                "close": today_rec["close"],
                "close_prev": prev_rec["close"] if prev_rec else None,
            }
        except Exception as e:
            results[m_name] = {"status": "error", "message": str(e)}

    # 汇总
    ok = {k: v for k, v in results.items() if v.get("status") == "ok"}
    if ok:
        total_amt = sum(v["amount"] for v in ok.values())
        total_prev = sum(v["amount_prev"] for v in ok.values() if v.get("amount_prev"))
        tot_chg, tot_pct = calc_change(total_amt, total_prev)
        tot_fmt, _ = fmt_yuan(total_amt)
        tot_prev_fmt, _ = fmt_yuan(total_prev) if total_prev else ("N/A", 0)
        contributions = {}
        for k, v in ok.items():
            contributions[k] = round(v["amount"] / total_amt * 100, 2) if total_amt else 0
        sorted_m = sorted(ok.items(), key=lambda x: x[1]["amount"], reverse=True)
        summary = {
            "total_amount": total_amt,
            "total_fmt": tot_fmt,
            "total_prev": total_prev,
            "total_prev_fmt": tot_prev_fmt,
            "change": tot_chg,
            "change_pct": tot_pct,
            "change_arrow": "📈" if (tot_pct or 0) >= 0 else "📉",
            "change_str": (("+" if tot_chg >= 0 else "") + fmt_yuan(abs(tot_chg))[0]) if tot_chg is not None else "N/A",
            "contributions": contributions,
            "largest": sorted_m[0][0],
            "smallest": sorted_m[-1][0],
        }
    else:
        summary = None

    return {"status": "ok" if summary else "error", "target_date": target_date, "markets": results, "summary": summary}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) >= 2 and not sys.argv[1].startswith("--") else datetime.now().strftime("%Y-%m-%d")
    target = parse_date(target) or datetime.now().strftime("%Y-%m-%d")
    result = get_volume(target)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        s = result["summary"]
        if s:
            print(f"三市成交：{s['total_fmt']} {s['change_arrow']} {s['change_str']} ({s['change_pct']:+.2f}%)")
        for m, v in result["markets"].items():
            if v.get("status") == "ok":
                print(f"  {m}: {v['amount_fmt']} {v['change_pct']:+.2f}%")
