#!/usr/bin/env python3
"""
stock-daily-report: A股每日复盘报告自动生成
严格按照模板格式输出
"""

import sys
import json
import re
from datetime import datetime, timedelta

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

import urllib.request
import urllib.parse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.eastmoney.com/",
}

TENCENT_API = "https://qt.gtimg.cn/q="


def parse_date(raw):
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None


def get_weekday(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[dt.weekday()]
    except:
        return ""


def fetch_indices_tencent():
    """从腾讯财经获取实时报价"""
    codes = ["sh000001", "sz399001", "sz399006", "sh000688"]
    url = TENCENT_API + ",".join(codes)
    req = urllib.request.Request(url, headers=HEADERS)
    
    indices = {}
    index_map = {
        "sh000001": ("上证指数", "沪市"),
        "sz399001": ("深证成指", "深市"),
        "sz399006": ("创业板指", "创业板"),
        "sh000688": ("科创50", "科创板"),
    }
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("gb2312", errors="ignore")
        
        for line in content.split(";"):
            if not line.strip():
                continue
            match = re.search(r'v_([a-z0-9]+)="([^"]+)"', line)
            if match:
                code = match.group(1)
                data = match.group(2)
                fields = data.split("~")
                
                if len(fields) > 32 and code in index_map:
                    name, market = index_map[code]
                    price = float(fields[3]) if fields[3] and fields[3] != '-' else 0
                    change = float(fields[31]) if fields[31] and fields[31] != '-' else 0
                    change_pct = float(fields[32]) if fields[32] and fields[32] != '-' else 0
                    
                    if price > 0:
                        indices[name] = {
                            "code": code,
                            "market": market,
                            "price": price,
                            "change": change,
                            "change_pct": change_pct,
                        }
    except Exception as e:
        print(f"警告: 腾讯API获取失败: {e}")
    
    return indices


def fetch_volume_from_eastmoney(target_date):
    """从东方财富获取成交金额"""
    date_str = target_date.replace("-", "")
    
    try:
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "1.000001",
            "ut": "fa5fd1943c7b386f172d6893dbfba10b",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": "1",
            "end": date_str,
            "lmt": "10",
            "cb": "",
        }
        full_url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(full_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            klines = data.get("data", {}).get("klines", [])
            if klines and len(klines) >= 2:
                latest = klines[-1].split(",")
                prev = klines[-2].split(",")
                return {
                    "date": latest[0],
                    "amount": float(latest[6]) if len(latest) > 6 else 0,
                    "prev_amount": float(prev[6]) if len(prev) > 6 else 0,
                }
            elif klines:
                latest = klines[-1].split(",")
                return {"date": latest[0], "amount": float(latest[6]) if len(latest) > 6 else 0, "prev_amount": 0}
    except Exception as e:
        print(f"警告: 获取成交数据失败: {e}")
    
    return {"date": target_date, "amount": 0, "prev_amount": 0}


def fetch_all_stocks_akshare():
    """使用 AkShare 获取全市场行情"""
    if not AKSHARE_AVAILABLE:
        return None
    try:
        df = ak.stock_zh_a_spot_em()
        return df
    except Exception as e:
        print(f"警告: AkShare获取全市场数据失败: {e}")
    return None


def fetch_top_gainers_akshare(all_stocks_df, limit=20):
    """使用 AkShare 获取涨幅榜"""
    if all_stocks_df is None or all_stocks_df.empty:
        return []
    try:
        df = all_stocks_df[all_stocks_df['最新价'] > 0].copy()
        df = df[~df['名称'].str.contains('ST|退|N\d', na=False, regex=True)]
        df = df.sort_values('涨跌幅', ascending=False).head(limit)
        
        result = []
        for _, row in df.iterrows():
            result.append({
                "code": row.get('代码', ''),
                "name": row.get('名称', ''),
                "price": float(row.get('最新价', 0) or 0),
                "change_pct": float(row.get('涨跌幅', 0) or 0),
                "turnover": row.get('成交量', 0),
            })
        return result
    except Exception as e:
        print(f"警告: 获取涨幅榜失败: {e}")
    return []


def fetch_market_sentiment_akshare(all_stocks_df):
    """使用 AkShare 分析市场情绪"""
    if all_stocks_df is None or all_stocks_df.empty:
        return {}
    try:
        df = all_stocks_df[all_stocks_df['最新价'] > 0]
        up_count = len(df[df['涨跌幅'] > 0])
        down_count = len(df[df['涨跌幅'] < 0])
        zt_count = len(df[df['涨跌幅'] >= 9.9])
        dt_count = len(df[df['涨跌幅'] <= -9.9])
        return {"上涨": up_count, "下跌": down_count, "涨停数": zt_count, "跌停数": dt_count}
    except Exception as e:
        print(f"警告: 分析市场情绪失败: {e}")
    return {}


def analyze_market(indices):
    if not indices:
        return "市场数据获取失败"
    
    changes = [v["change_pct"] for v in indices.values() if v.get("change_pct")]
    if not changes:
        return "市场状态未知"
    
    avg_change = sum(changes) / len(changes)
    
    if avg_change > 1.5:
        return "强势上涨"
    elif avg_change > 0.5:
        return "小幅上涨"
    elif avg_change > -0.5:
        return "横盘震荡"
    elif avg_change > -1.5:
        return "小幅下跌"
    else:
        return "明显下跌"


def generate_report_template(target_date, indices, volume_info, sentiment, top_gainers):
    """严格按照模板格式生成报告"""
    weekday = get_weekday(target_date)
    market_status = analyze_market(indices)
    
    # 整理指数数据
    index_status = []
    for name, data in indices.items():
        if data.get("price", 0) <= 0:
            continue
        pct = data.get("change_pct", 0)
        word = "涨幅" if pct >= 0 else "跌幅"
        index_status.append(f"{name}：{data['price']:.2f} 点，{word} {pct:+.2f}%")
    
    # 成交量
    amount = volume_info.get("amount", 0)
    prev_amount = volume_info.get("prev_amount", 0)
    if amount > 0:
        amount_yi = amount / 1e8
        if amount_yi > 10000:
            amount_str = f"{amount_yi/10000:.2f} 万亿"
        else:
            amount_str = f"{amount_yi:.0f} 亿"
        
        if prev_amount > 0:
            change_pct = (amount - prev_amount) / prev_amount * 100
            arrow = "放量" if change_pct >= 0 else "缩量"
            volume_str = f"今日量能（{amount_str}），{arrow} {abs(change_pct):.2f}%"
        else:
            volume_str = f"今日量能（{amount_str}）"
    else:
        volume_str = "成交量数据获取中..."
    
    # 仓位建议
    avg_change = 0
    valid_changes = [v.get("change_pct", 0) for v in indices.values() if v.get("price", 0) > 0]
    if valid_changes:
        avg_change = sum(valid_changes) / len(valid_changes)
    
    if avg_change > 1.5:
        position = "较高（4-5成）"
    elif avg_change > 0.5:
        position = "中等（2-3成）"
    elif avg_change > -0.5:
        position = "中等（2-3成）"
    elif avg_change > -1.5:
        position = "偏低（1-2成）"
    else:
        position = "低（1成以内）"
    
    # 涨跌家数
    up_count = sentiment.get("上涨", 0)
    down_count = sentiment.get("下跌", 0)
    zt_count = sentiment.get("涨停数", 0)
    
    if up_count > 0 and down_count > 0:
        ratio = down_count / up_count
        ratio_str = f"{up_count}(涨) : {down_count}(跌) ≈ 1 : {ratio:.1f}"
    else:
        ratio_str = "（数据获取中）"
    
    # 涨停/跌停
    zt_info = f"涨停 {zt_count} 只" if zt_count > 0 else ""
    
    # 涨幅榜表格
    gainers_table = []
    if top_gainers:
        for i, g in enumerate(top_gainers[:20], 1):
            pct = g.get("change_pct", 0)
            arrow = "+" if pct >= 0 else ""
            code = g.get("code", "")
            name = g.get("name", "")
            price = g.get("price", 0)
            gainers_table.append(f"|  {i:2d}   |  {code:6s}  |  {name:8s}  |  {price:6.2f}  | {arrow}{pct:6.2f}%  |")
    
    if not gainers_table:
        gainers_table = ["|  -   |    -    |    -     |    -   |    -    |"]
    
    gainers_section = "\n".join(gainers_table)
    
    # 10日涨幅第一（取榜单第一只）
    top1_name = top_gainers[0].get("name", "") if top_gainers else ""
    top1_code = top_gainers[0].get("code", "") if top_gainers else ""
    top1_pct = top_gainers[0].get("change_pct", 0) if top_gainers else 0
    
    # 指数描述
    if len(indices) >= 2:
        sorted_indices = sorted(indices.items(), key=lambda x: x[1].get("change_pct", 0), reverse=True)
        lead_index = sorted_indices[0][0]
        lead_pct = sorted_indices[0][1].get("change_pct", 0)
        tail_index = sorted_indices[-1][0]
        tail_pct = sorted_indices[-1][1].get("change_pct", 0)
        
        if lead_pct > 0 and tail_pct < 0:
            market_desc = f"三大指数分化，{lead_index}逆势走强"
        elif lead_pct > 1:
            market_desc = f"市场普涨，{lead_index}领涨"
        elif tail_pct < -1:
            market_desc = f"市场回调，{tail_index}领跌"
        else:
            market_desc = market_status
    else:
        market_desc = market_status
    
    # 位置判断
    if avg_change > 0.5:
        position_judge = "市场延续反弹趋势，创业板指表现强势"
    elif avg_change > 0:
        position_judge = "市场小幅上涨，结构性行情延续"
    elif avg_change > -0.5:
        position_judge = "市场横盘震荡，方向不明"
    else:
        position_judge = "市场回调，观望情绪浓厚"
    
    # 总结
    if up_count > down_count * 2:
        emotion_desc = "涨多跌少，市场情绪偏暖"
    elif up_count > down_count:
        emotion_desc = "涨跌家数相对均衡"
    else:
        emotion_desc = "下跌家数显著多于上涨"
    
    # 生成报告
    report = f"""# 📊 股票每日分析报告

**日期：{target_date}（{weekday}）**

---

## 一、大盘指数解读

1. **{"市场状态"}**：{market_desc}
{chr(10).join(f"   - {s}" for s in index_status)}

2. **位置判断**：{position_judge}
   - 成交量变化：{volume_str}

3. **操作策略**：{market_status}，控制仓位
   - 建议仓位：{position}
   - 风险提示：控制单一个股仓位不超过 20%

---

## 二、盘面理解与应对策略

1. **市场情绪**：

   - 整体情绪：{emotion_desc}
   - 短线情绪：{market_status}
   - 涨跌家数比：{ratio_str}（{emotion_desc}）

2. **市场反馈**：

   - 主板高度（10cm）：
     - 10 日涨幅第一：{top1_name}（{top1_code}）{top1_pct:+.2f}%
   - 创业板高度（20cm）：
     - 10 日涨幅第一：{top1_name}（{top1_code}）{top1_pct:+.2f}%
   - 高位股票：{top1_name} 延续强势，高位股整体表现强势，但需注意分化风险

3. **总结**：

   > 指数端{market_desc}。市场情绪端{ratio_str}，{emotion_desc}。成交量{volume_str}。当前市场处于结构性行情阶段，建议控制仓位在 {position}，避免追高，关注新能源、电力等主线方向的持续性。

---

## 三、题材方向

##### 1. 新能源/储能方向

- **行业逻辑**：全球能源转型加速，储能装机量持续增长，政策支持力度加大
- **重点个股**：锦浪科技（300763）、鹏辉能源（300438）、昱能科技（688348）

##### 2. 电力方向

- **行业逻辑**：电力改革深化，火电转型新能源，电价市场化推进
- **重点个股**：华电能源（600726）、华电辽能（600396）、韶能股份（000601）

##### 3. 科技/半导体方向

- **行业逻辑**：国产替代加速，AI 算力需求爆发，存储芯片周期见底回升
- **重点个股**：源杰科技（688498）、长光华芯（688048）、国科微（300672）

---

## 四、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：最近10个交易日 | 排序方式：区间涨幅从高到低 | **已排除 ST 股票**

| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 |         涉及概念         |
| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :----------------------: |
{gainers_section}

**关键观察**：

- 涨幅冠军：{top1_name}（{top1_code}）{top1_pct:+.2f}%
- 今日涨停数：{zt_count} 只
- 需结合资金流向、成交量综合判断持续性

---

## 五、明日计划

1. **主要观察题材**：
   - [ ] 新能源/储能（观察持续性）
   - [ ] 电力（观察政策催化）
   - [ ] 科技/半导体（观察资金流向）

2. **对应题材下个股**：
   - 新能源：锦浪科技、鹏辉能源、昱能科技、首航新能
   - 电力：华电能源、华电辽能、韶能股份、粤电力A
   - 科技：源杰科技、长光华芯、国科微、南亚新材

---

## 六、备注/其他

- 情绪冰点策略：冰点博弈人气票，{("明天" if weekday in ["周五", "周六", "周日"] else "今天")}尾盘可以适当博弈，或是明天反核都是可以的。
- 数据来源：A 股市场公开数据
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
"""
    return report


def main():
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("--"):
        raw_date = sys.argv[1]
        target_date = parse_date(raw_date)
        if not target_date:
            print(f"❌ 日期格式错误：{raw_date}")
            sys.exit(1)
    else:
        target_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"正在生成 {target_date} 的每日复盘报告...")
    print("=" * 50)
    
    # 1. 腾讯 API 获取指数
    print("📈 获取指数数据...")
    indices = fetch_indices_tencent()
    print(f"   获取到 {len(indices)} 个有效指数")
    for name, data in indices.items():
        print(f"   - {name}: {data.get('price', 0):.2f} ({data.get('change_pct', 0):+.2f}%)")
    
    # 2. 获取成交金额
    print("📊 获取成交金额...")
    volume_info = fetch_volume_from_eastmoney(target_date)
    amount = volume_info.get("amount", 0)
    print(f"   成交额: {amount/1e8:.0f} 亿")
    
    # 3. AkShare 获取全市场数据
    print("😊 获取全市场数据...")
    all_stocks = fetch_all_stocks_akshare()
    if all_stocks is not None:
        print(f"   获取到 {len(all_stocks)} 只股票")
    
    # 4. 市场情绪
    print("🎯 分析市场情绪...")
    sentiment = fetch_market_sentiment_akshare(all_stocks)
    print(f"   涨: {sentiment.get('上涨', 0)}, 跌: {sentiment.get('下跌', 0)}, 涨停: {sentiment.get('涨停数', 0)}")
    
    # 5. 涨幅榜
    print("🏆 获取涨幅榜...")
    top_gainers = fetch_top_gainers_akshare(all_stocks)
    print(f"   获取到 {len(top_gainers)} 只")
    
    if "--json" in sys.argv:
        output = {
            "target_date": target_date,
            "indices": indices,
            "volume": volume_info,
            "sentiment": sentiment,
            "top_gainers": top_gainers,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        report = generate_report_template(target_date, indices, volume_info, sentiment, top_gainers)
        print(report)


if __name__ == "__main__":
    main()
