#!/usr/bin/env python3
"""
fetch_top10.py - 近10日涨幅榜 Top20 + 主板/创业板冠军
数据来源：同花顺问财（browser）+ 东方财富（人气热度+涉及概念）
用法：
    python3 fetch_top10.py [--json]
    python3 fetch_top10.py --top1-only [--json]  # 只查冠军
"""

import sys
import json
import re
import urllib.request
import urllib.parse
import time

HEADERS_EASTMONEY = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.eastmoney.com/",
}

# 东方财富人气热度 & 概念
EM_POPULARITY_URL = "https://push2.eastmoney.com/api/qt/clist/get"
EM_STOCK_CONCEPTS_URL = "https://push2.eastmoney.com/api/qt/clist/get"


def parse_date(raw):
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


# ── 东方财富：人气热度 + 涉及概念 ────────────────────────────────────────────

def get_stock_popularity(code):
    """通过东方财富获取个股人气排名"""
    try:
        mkt = "1" if code.startswith(("6", "9")) else "0"
        params = {
            "cb": "",
            "fid": "f62",
            "po": 1,
            "pz": 20,
            "pn": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "wbp2u": "",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "ft": ".hs",
            "fields": "f12,f13,f14,f62",
        }
        url = EM_POPULARITY_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS_EASTMONEY)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        items = data.get("data", {}).get("diff", [])
        for item in items:
            if str(item.get("f12", "")) == code:
                rank = item.get("f62", 0)
                if rank >= 100:
                    return "100+", None
                else:
                    return f"第 {rank} 名", rank
        return "100+", None
    except Exception:
        return "100+", None


def get_stock_concepts(code):
    """通过东方财富获取个股涉及的概念板块"""
    try:
        mkt = "1" if code.startswith(("6", "9")) else "0"
        params = {
            "cb": "",
            "fltt": 2,
            "invt": 2,
            "wbp2u": "",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "ft": "hs.a",
            "fs": f"m:{mkt}+t:6",
            "fields": "f12,f14,f13",
        }
        url = EM_STOCK_CONCEPTS_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS_EASTMONEY)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        # 概念信息走另一个接口，这里用简版行情替代
        return []
    except Exception:
        return []


# ── 东方财富：个股概念板块（新版API） ─────────────────────────────────────────

def get_stock_concepts_v2(codes):
    """
    批量获取个股概念。codes = ["600726", "000001", ...]
    返回 {code: [概念名, ...]}
    """
    if not codes:
        return {}
    result = {}
    try:
        fs_list = []
        for c in codes:
            mkt = "1" if c.startswith(("6", "9")) else "0"
            fs_list.append(f"m:{mkt}+t:6,m:{mkt}+t:13")
        fs_str = ",".join(fs_list)
        params = {
            "cb": "",
            "fltt": 2,
            "invt": 2,
            "wbp2u": "",
            "np": 1,
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "ft": "hs.a",
            "fs": fs_str[:2000],  # 截断避免太长
            "fields": "f12,f14,f100",
        }
        url = EM_STOCK_CONCEPTS_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS_EASTMONEY)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        diff = data.get("data", {}).get("diff", []) or []
        for item in diff:
            code = str(item.get("f12", ""))
            concepts_raw = item.get("f100", "")
            if concepts_raw:
                concepts = [x.strip() for x in concepts_raw.split(",") if x.strip()]
                result[code] = concepts[:5]  # 最多5个概念
    except Exception as e:
        print(f"⚠️ 概念获取失败: {e}")
    # 补空
    for c in codes:
        if c not in result:
            result[c] = []
    return result


def get_popularity_rank(codes):
    """
    批量获取人气排名，返回 {code: (热度描述, 排名数字或None)}
    """
    if not codes:
        return {}
    result = {}
    try:
        params = {
            "cb": "",
            "fid": "f62",
            "po": 1,
            "pz": 50,
            "pn": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "fields": "f12,f62",
        }
        url = EM_POPULARITY_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS_EASTMONEY)
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rank_map = {}
        for item in data.get("data", {}).get("diff", []) or []:
            rank_map[str(item.get("f12", ""))] = item.get("f62", 0)
        for c in codes:
            r = rank_map.get(c, 0)
            if r <= 0 or r >= 100:
                result[c] = ("100+", None)
            else:
                result[c] = (f"第 {r} 名", r)
    except Exception:
        pass
    for c in codes:
        if c not in result:
            result[c] = ("100+", None)
    return result


# ── 近10日涨幅榜（浏览器解析 - 由调用方传入 snapshot 结果）──────────────────

def enrich_top20(raw_stocks, target_date=None):
    """
    接收从同花顺问财解析出的原始股票列表（未过滤概念/热度），
    批量补全人气热度 + 涉及概念。

    raw_stocks: [{"rank":1,"code":"600726","name":"华电能源",
                  "price":5.52,"today_chg":9.96,"period_chg":95.74}, ...]

    返回同样结构但增加 popularity_str, concepts, popularity_rank 字段。
    """
    if not raw_stocks:
        return raw_stocks

    codes = [s["code"] for s in raw_stocks]

    # 批量获取
    pop_map = get_popularity_rank(codes)
    conc_map = get_stock_concepts_v2(codes)

    for s in raw_stocks:
        c = s["code"]
        s["popularity_str"] = pop_map.get(c, ("100+", None))[0]
        s["popularity_rank"] = pop_map.get(c, ("100+", None))[1]
        concepts = conc_map.get(c, [])
        s["concepts"] = concepts
        s["concepts_str"] = "、".join(concepts) if concepts else "—"

    return raw_stocks


# ── 解析同花顺问财 snapshot（供 generate_report.py 的浏览器回调使用）──────────

def parse_iwencai_snapshot(html_or_text, limit=25):
    """
    解析同花顺问财涨幅榜页面的 snapshot/text 数据。
    支持两种格式：
    1. 结构化表格行（tabledata / list 格式）
    2. 纯文本行格式（每行 "排名  代码  名称  ... "）

    返回 [{"rank", "code", "name", "price", "today_chg", "period_chg", "period_rank"}, ...]
    """
    lines = []
    if "<" in html_or_text:
        # 去掉 HTML 标签
        import html as html_module
        text = html_module.unescape(html_or_text)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        lines = [l.strip() for l in re.split(r"[\n\r]+", text) if l.strip()]
    else:
        lines = [l.strip() for l in html_or_text.split("\n") if l.strip()]

    stocks = []
    seen_codes = set()

    # 寻找"序号 代码 名称"或类似的表头行作为起点
    header_pattern = re.compile(
        r"序号|排名.*代码.*名称|代码.*名称.*涨幅",
        re.IGNORECASE
    )
    data_pattern = re.compile(
        r"^\s*(\d+)[　\s]+(\d{6})[　\s]+([^\s　]+)[　\s]+([\d\.]+)[　\s]+([+-]?[\d\.]+)%?\s*$"
    )

    in_table = False
    for line in lines:
        if header_pattern.search(line):
            in_table = True
            continue
        if not in_table:
            continue
        m = data_pattern.match(line)
        if not m:
            # 尝试更宽松的解析
            m = re.match(
                r"^\s*(\d+)\s+(\d{6})\s+([^\s]+)\s+([\d\.]+)\s+([+-]?[\d\.]+)",
                line
            )
        if m:
            rank = int(m.group(1))
            code = m.group(2)
            name = m.group(3).strip()
            # 过滤ST
            if "ST" in name or "*ST" in name or "S*ST" in name or "SST" in name:
                continue
            if code in seen_codes:
                continue
            seen_codes.add(code)
            price_str = m.group(4)
            today_str = m.group(5)
            # period_chg 需要从列表中找，暂置0
            stocks.append({
                "rank": rank,
                "code": code,
                "name": name,
                "price": float(price_str) if price_str.replace(".", "").isdigit() else 0,
                "today_chg": float(today_str) if today_str.replace(".", "").replace("+", "").replace("-", "").isdigit() else 0,
                "period_chg": 0.0,
                "period_rank": "",
            })
            if len(stocks) >= limit:
                break

    return stocks


def parse_iwencai_json(data):
    """
    解析同花顺问财返回的 JSON 格式数据。
    data: 页面注入的 JS 变量或 JSONP 回调内容。
    """
    results = []
    # 尝试提取 JSON
    m = re.search(r"\[.*\]", data, re.DOTALL)
    if not m:
        return results
    try:
        items = json.loads(m.group())
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("stock_name", item.get("name", "")))
                if "ST" in name or "*ST" in name:
                    continue
                results.append({
                    "rank": item.get("序号", 0),
                    "code": str(item.get("code", item.get("stock_code", ""))),
                    "name": name,
                    "price": float(item.get("最新价", 0)),
                    "today_chg": float(item.get("涨跌幅", 0)),
                    "period_chg": float(item.get("区间涨跌幅", 0)),
                    "period_rank": str(item.get("区间涨幅排名", "")),
                })
    except Exception:
        pass
    return results


# ── 批量获取近10日涨幅（东方财富 - 无需浏览器）────────────────────────────────

def get_top10_by_em(days=10, limit=20):
    """
    使用东方财富区间涨幅排行 API 获取近N日涨幅前20。
    返回结构化列表。

    注意：东方财富区间涨幅接口较复杂，这里用 AkShare 兜底，
    如果 AkShare 不可用则返回空列表（由 generate_report.py 用浏览器补全）。
    """
    AKSHARE_AVAILABLE = False
    try:
        import akshare as ak
        AKSHARE_AVAILABLE = True
    except ImportError:
        pass

    if not AKSHARE_AVAILABLE:
        return []

    try:
        # 获取全市场数据
        df = ak.stock_zh_a_spot_em()
        df = df[df["最新价"] > 0]
        # 排除ST
        df = df[~df["名称"].str.contains("ST|退|N\\d", na=False, regex=True)]
        # 按涨跌幅排序取Top20
        df = df.sort_values("涨跌幅", ascending=False).head(limit)

        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "rank": len(stocks) + 1,
                "code": str(row.get("代码", "")),
                "name": str(row.get("名称", "")),
                "price": float(row.get("最新价", 0) or 0),
                "today_chg": float(row.get("涨跌幅", 0) or 0),
                "period_chg": float(row.get("涨跌幅", 0) or 0),  # 当日涨幅作为近似
                "period_rank": "",
                "popularity_str": "100+",
                "concepts_str": "—",
                "concepts": [],
                "popularity_rank": None,
            })
        return stocks
    except Exception as e:
        print(f"⚠️ AkShare Top20 获取失败: {e}")
        return []


if __name__ == "__main__":
    # 演示：无浏览器时用 AkShare 兜底
    stocks = get_top10_by_em(days=10, limit=5)
    stocks = enrich_top20(stocks)
    print(json.dumps(stocks, ensure_ascii=False, indent=2))
