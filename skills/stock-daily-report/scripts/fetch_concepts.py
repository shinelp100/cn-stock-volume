#!/usr/bin/env python3
"""
fetch_concepts.py - 题材方向（动态发现 + 实时价格）
数据来源：
  - 板块涨幅：东方财富 概念板块 clist API
  - 个股实时价格/涨跌幅：腾讯财经 qt.gtimg.cn（极快，无需批量限制）
"""

import sys
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime

HEADERS_EM = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.eastmoney.com/",
}
HEADERS_QT = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.eastmoney.com/",
}
EM_URL   = "https://push2.eastmoney.com/api/qt/clist/get"
QT_URL   = "https://qt.gtimg.cn/q="


def _safe_float(v, default=0.0):
    if v is None or v == "" or v == "-":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def parse_date(raw):
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 腾讯财经：批量查个股实时行情（极快）
# ══════════════════════════════════════════════════════════════════════════════

def fetch_stocks_realtime(codes):
    """
    codes: ["sh600726", "sz000601", ...] 或 ["600726", "sz000601", ...]
    自动补全前缀。
    返回 {"600726": {"price": float, "change_pct": float}, ...}
    """
    if not codes:
        return {}

    # 补全前缀
    prefixed = []
    for c in codes:
        c = str(c).strip()
        if c.startswith(("sh", "sz", "bj", "SH", "SZ")):
            prefixed.append(c)
        elif c.startswith(("6", "9")):
            prefixed.append(f"sh{c}")
        else:
            prefixed.append(f"sz{c}")

    url = QT_URL + ",".join(prefixed)
    result = {}
    try:
        req = urllib.request.Request(url, headers=HEADERS_QT)
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("gb2312", errors="ignore")
        for line in content.split(";"):
            m = re.search(r'v_(\w+)="([^"]+)"', line)
            if not m:
                continue
            raw_code, data = m.group(1), m.group(2)
            fields = data.split("~")
            if len(fields) < 33:
                continue
            # 去掉 sh/sz 前缀得到纯代码
            code = re.sub(r"^(sh|sz|bj)", "", raw_code, flags=re.IGNORECASE)
            result[code] = {
                "price":      _safe_float(fields[3]),
                "change":     _safe_float(fields[31]),
                "change_pct": _safe_float(fields[32]),
            }
    except Exception as e:
        print(f"⚠️ 腾讯实时行情失败: {e}")
    return result


# ══════════════════════════════════════════════════════════════════════════════
# 东方财富：概念板块涨幅榜
# ══════════════════════════════════════════════════════════════════════════════

def get_concept_boards():
    """获取概念板块涨幅榜（按今日涨幅降序），返回原始板块列表"""
    try:
        params = {
            "cb": "",
            "pn": 1,
            "pz": 60,
            "po": 1,
            "np": 1,
            "fltt": 2,
            "invt": 2,
            "wbp2u": "",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "ft": "hs.bk",
            "fs": "m:0+t:9,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f12,f14,f2,f3,f62,f100,f152,f162",
        }
        url = EM_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=HEADERS_EM)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        items = data.get("data", {}).get("diff", []) or []
        boards = []
        for item in items:
            name = item.get("f14", "")
            if not name:
                continue
            amount_raw = item.get("f62", 0)
            boards.append({
                "board_code": str(item.get("f12", "")),
                "board_name": name,
                "change_pct": _safe_float(item.get("f3")),
                "amount_yi":  round(_safe_float(amount_raw) / 1e8, 2),
                "up_count":   int(_safe_float(item.get("f152"))),
                "down_count": int(_safe_float(item.get("f162"))),
            })
        return boards
    except Exception as e:
        print(f"⚠️ 概念板块获取失败: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# 题材匹配
# ══════════════════════════════════════════════════════════════════════════════

# 题材模板：关键词 + 逻辑 + 代表股代码（腾讯前缀格式）
TOPIC_TEMPLATES = {
    "新能源/储能": {
        "keywords": ["新能源", "储能", "光伏", "风能", "充电桩", "氢能", "电池", "智能电网"],
        "logic": "全球能源转型加速，储能装机量持续增长，政策支持力度加大",
        "default_stocks": [
            ("sh300763", "锦浪科技"),
            ("sh300438", "鹏辉能源"),
            ("sh688348", "昱能科技"),
            ("sh301658", "首航新能"),
        ],
    },
    "电力": {
        "keywords": ["电力", "火电", "水电", "核电", "电网", "虚拟电厂", "绿色电力", "电力改革"],
        "logic": "电力改革深化，火电转型新能源，电价市场化推进",
        "default_stocks": [
            ("sh600726", "华电能源"),
            ("sh600396", "华电辽能"),
            ("sz000601", "韶能股份"),
            ("sz000539", "粤电力A"),
        ],
    },
    "科技/半导体": {
        "keywords": ["半导体", "芯片", "AI算力", "集成电路", "存储", "光刻机", "国产替代", "算力", "AI芯片"],
        "logic": "国产替代加速，AI算力需求爆发，存储芯片周期见底回升",
        "default_stocks": [
            ("sh688498", "源杰科技"),
            ("sh300048", "长光华芯"),
            ("sz300672", "国科微"),
            ("sh688519", "南亚新材"),
        ],
    },
    "新材料": {
        "keywords": ["碳纤维", "新材料", "复合材料", "稀土", "石墨", "先进材料"],
        "logic": "新材料国产替代加速，高端碳纤维需求爆发",
        "default_stocks": [
            ("sh688295", "中复神鹰"),
            ("sz300285", "国瓷材料"),
        ],
    },
    "消费电子": {
        "keywords": ["消费电子", "AI终端", "智能穿戴", "折叠屏", "OLED"],
        "logic": "AI终端创新周期开启，折叠屏与智能穿戴持续渗透",
        "default_stocks": [
            ("sz000020", "深华发A"),
            ("sh600183", "生益科技"),
        ],
    },
    "机器人": {
        "keywords": ["机器人", "人工智能", "人形机器人", "工业机器人", "智能装备"],
        "logic": "人形机器人产业化加速，工业机器人需求复苏",
        "default_stocks": [
            ("sz300720", "海川智能"),
            ("sh688256", "寒武纪"),
        ],
    },
    "房地产": {
        "keywords": ["房地产", "地产", "物业管理", "基建", "城中村"],
        "logic": "政策持续宽松，城中村改造与保障房建设加速",
        "default_stocks": [
            ("sh600683", "京投发展"),
            ("sz000402", "金融街"),
        ],
    },
}


def match_topics(boards):
    """
    从东方财富板块涨幅榜中匹配题材，返回带实时股价的题材列表。
    boards: get_concept_boards() 返回
    """
    matched      = []
    used_boards  = set()

    for topic, info in TOPIC_TEMPLATES.items():
        keywords   = info["keywords"]
        candidates = []
        for board in boards:
            bname = board["board_name"]
            if bname in used_boards:
                continue
            for kw in keywords:
                if kw in bname:
                    candidates.append(board)
                    used_boards.add(bname)
                    break

        if not candidates:
            continue

        # 取涨幅最高的板块为代表
        best = max(candidates, key=lambda x: x["change_pct"])

        # 收集代表股代码并批量查询实时价格
        stock_codes_raw = [code for code, _ in info["default_stocks"]]
        prices = fetch_stocks_realtime(stock_codes_raw)

        top_stocks = []
        for prefix_code, name in info["default_stocks"]:
            # 去掉前缀得到纯数字代码
            code = re.sub(r"^(sh|sz|bj)", "", prefix_code, flags=re.IGNORECASE)
            pdata = prices.get(code, {})
            top_stocks.append({
                "code":        code,
                "name":        name,
                "price":       pdata.get("price", 0) or 0,
                "change_pct":  pdata.get("change_pct", 0) or 0,
            })

        matched.append({
            "topic":       topic,
            "logic":       info["logic"],
            "board_names": [b["board_name"] for b in candidates],
            "lead_board":  best["board_name"],
            "change_pct":  best["change_pct"],
            "amount_yi":   best["amount_yi"],
            "top_stocks":  top_stocks[:3],   # 只取前3只
        })

    return matched


def _auto_discover_topics(boards):
    """
    无关键词匹配时，取涨幅前3板块（涨幅>2%且成交额>30亿）自动发现题材
    """
    hot = [b for b in boards
           if b["change_pct"] > 2 and b["amount_yi"] > 30]
    hot.sort(key=lambda x: x["change_pct"], reverse=True)
    topics = []
    for b in hot[:3]:
        topics.append({
            "topic":      b["board_name"],
            "logic":     f"{b['board_name']}板块涨幅 {b['change_pct']:+.2f}%，板块效应明显",
            "board_names": [b["board_name"]],
            "lead_board": b["board_name"],
            "change_pct": b["change_pct"],
            "amount_yi":  b["amount_yi"],
            "top_stocks": [],
        })
    return topics


# ══════════════════════════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════════════════════════

def get_topics_data():
    boards = get_concept_boards()
    if not boards:
        return _default_topics()
    topics = match_topics(boards)
    if not topics:
        return _auto_discover_topics(boards)
    return topics


def _default_topics():
    return [
        {
            "topic": "新能源/储能",
            "logic": "全球能源转型加速，储能装机量持续增长，政策支持力度加大",
            "board_names": ["新能源", "储能"],
            "top_stocks": [
                {"code": "300763", "name": "锦浪科技", "price": 0, "change_pct": 0},
                {"code": "300438", "name": "鹏辉能源", "price": 0, "change_pct": 0},
                {"code": "688348", "name": "昱能科技", "price": 0, "change_pct": 0},
            ],
        },
        {
            "topic": "电力",
            "logic": "电力改革深化，火电转型新能源，电价市场化推进",
            "board_names": ["电力", "绿色电力"],
            "top_stocks": [
                {"code": "600726", "name": "华电能源", "price": 0, "change_pct": 0},
                {"code": "600396", "name": "华电辽能", "price": 0, "change_pct": 0},
                {"code": "000601", "name": "韶能股份", "price": 0, "change_pct": 0},
            ],
        },
        {
            "topic": "科技/半导体",
            "logic": "国产替代加速，AI算力需求爆发，存储芯片周期见底回升",
            "board_names": ["半导体", "芯片"],
            "top_stocks": [
                {"code": "688498", "name": "源杰科技", "price": 0, "change_pct": 0},
                {"code": "300048", "name": "长光华芯", "price": 0, "change_pct": 0},
                {"code": "300672", "name": "国科微", "price": 0, "change_pct": 0},
            ],
        },
    ]


if __name__ == "__main__":
    result = get_topics_data()
    print(json.dumps(result, ensure_ascii=False, indent=2))
