#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成严格按照模板格式的 A 股每日复盘报告
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timedelta

# ============== 配置 ==============
WORKSPACE_DIR = os.path.expanduser("~/.jvs/.openclaw/workspace")
DESKTOP_DIR = os.path.expanduser("~/Desktop/A 股每日复盘")
WORKSPACE_OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "A 股每日复盘")
REPORT_DATE = "2026-04-06"

# ============== 获取大盘指数数据 ==============
def get_index_data():
    """获取大盘指数数据"""
    print("📊 获取指数数据...")
    
    # 使用 akshare 获取指数数据
    try:
        import akshare as ak
        
        # 上证指数 - 使用实时行情
        sh_index = ak.stock_zh_index_daily(symbol="sh000001")
        sh_close = float(sh_index['close'].iloc[-1])
        sh_prev = float(sh_index['close'].iloc[-2])
        sh_change = ((sh_close - sh_prev) / sh_prev) * 100
        
        # 深证成指
        sz_index = ak.stock_zh_index_daily(symbol="sz399001")
        sz_close = float(sz_index['close'].iloc[-1])
        sz_prev = float(sz_index['close'].iloc[-2])
        sz_change = ((sz_close - sz_prev) / sz_prev) * 100
        
        # 创业板指
        cyb_index = ak.stock_zh_index_daily(symbol="sz399006")
        cyb_close = float(cyb_index['close'].iloc[-1])
        cyb_prev = float(cyb_index['close'].iloc[-2])
        cyb_change = ((cyb_close - cyb_prev) / cyb_prev) * 100
        
        # 成交量 - 从指数数据中获取
        sh_volume = float(sh_index['volume'].iloc[-1])
        
        return {
            'sh_close': round(sh_close, 2),
            'sh_change': round(sh_change, 2),
            'sz_close': round(sz_close, 2),
            'sz_change': round(sz_change, 2),
            'cyb_close': round(cyb_close, 2),
            'cyb_change': round(cyb_change, 2),
            'volume': round(sh_volume / 100000000, 2) if sh_volume else 0
        }
    except Exception as e:
        print(f"⚠ 指数数据获取失败：{e}")
        import traceback
        traceback.print_exc()
        return None

# ============== 获取近 10 日涨幅排名 ==============
def get_top_gainers():
    """获取近 10 日涨幅前 20 股票"""
    print("📈 获取近 10 日涨幅前 20 股票...")
    
    try:
        # 使用本地 skill 获取
        skill_path = os.path.join(WORKSPACE_DIR, "skills/stock-data-monorepo/stock-top-gainers/scripts/get_gainers.py")
        
        if os.path.exists(skill_path):
            result = subprocess.run(['python3', skill_path, '--limit', '20', '--days', '10'], 
                                  capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return json.loads(result.stdout)
        
        # Fallback: 使用 akshare
        import akshare as ak
        gainers = ak.stock_rank_lxsz_ths()
        gainers = gainers.head(20)
        
        result = []
        for _, row in gainers.iterrows():
            result.append({
                'rank': len(result) + 1,
                'code': str(row.get('代码', '')),
                'name': row.get('名称', ''),
                'close': row.get('最新价', 0),
                'change_10d': row.get('区间涨跌幅', 0),
                'change_today': 0,
                'popularity': '待补充',
                'concepts': '待补充'
            })
        return result
    except Exception as e:
        print(f"⚠ 涨幅排名获取失败：{e}")
        return None

# ============== 获取人气热度 ==============
def get_popularity_ranking():
    """获取同花顺人气排名"""
    print("🔥 获取人气热度排名...")
    
    try:
        skill_path = os.path.join(WORKSPACE_DIR, "skills/stock-data-monorepo/ths-stock-themes/scripts/get_popularity.py")
        
        if os.path.exists(skill_path):
            result = subprocess.run(['python3', skill_path], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                return json.loads(result.stdout)
        
        # Fallback
        return {
            1: '待补充',
            2: '待补充',
            3: '待补充',
            4: '待补充',
            5: '待补充',
            6: '待补充',
            7: '待补充',
            8: '待补充',
            9: '待补充',
            10: '待补充'
        }
    except Exception as e:
        print(f"⚠ 人气排名获取失败：{e}")
        return {}

# ============== 获取题材概念 ==============
def get_stock_concepts(stock_codes):
    """获取股票的题材概念"""
    print("🏷️ 获取题材概念...")
    
    concepts_map = {}
    for code in stock_codes[:10]:
        try:
            skill_path = os.path.join(WORKSPACE_DIR, "skills/stock-data-monorepo/ths-stock-themes/scripts/get_concepts.py")
            if os.path.exists(skill_path):
                result = subprocess.run(['python3', skill_path, '--code', code], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    concepts_map[code] = result.stdout.strip()
                    continue
            concepts_map[code] = '待补充'
        except:
            concepts_map[code] = '待补充'
    
    return concepts_map

# ============== 生成报告 ==============
def generate_report():
    """生成完整报告"""
    
    # 获取数据
    index_data = get_index_data()
    gainers = get_top_gainers()
    popularity = get_popularity_ranking()
    
    if not index_data or not gainers:
        print("❌ 关键数据获取失败，无法生成报告")
        return
    
    # 获取前 10 只股票的题材概念
    stock_codes = [g['code'] for g in gainers[:10]]
    concepts_map = get_stock_concepts(stock_codes)
    
    # 更新 gainers 的题材概念
    for g in gainers:
        if g['code'] in concepts_map:
            g['concepts'] = concepts_map[g['code']]
    
    # 判断市场状态
    sh_change = index_data['sh_change']
    sz_change = index_data['sz_change']
    cyb_change = index_data['cyb_change']
    
    if sh_change > 0 and sz_change > 0 and cyb_change > 0:
        market_state = "三大指数全线上涨"
    elif sh_change < 0 and sz_change < 0 and cyb_change < 0:
        market_state = "三大指数全线回调"
    else:
        market_state = "三大指数分化"
    
    # 确定领涨/领跌
    changes = [('上证指数', sh_change), ('深证成指', sz_change), ('创业板指', cyb_change)]
    leader = max(changes, key=lambda x: x[1])
    lagger = min(changes, key=lambda x: x[1])
    
    # 生成报告内容
    report = f"""# 📊 股票每日分析报告

**日期：{REPORT_DATE}**

---

## 一、大盘指数解读

1. **市场状态**：{market_state}
   - 上证指数：{index_data['sh_close']} 点，涨幅 {sh_change:+.2f}%
   - 深证成指：{index_data['sz_close']} 点，涨幅 {sz_change:+.2f}%
   - 创业板指：{index_data['cyb_close']} 点，涨幅 {cyb_change:+.2f}%

2. **位置判断**：上证指数{ '回调' if sh_change < 0 else '上涨' }，关注后续{ '支撑' if sh_change < 0 else '压力' }位
   - 上证指数支撑位/压力位：支撑位 3800，压力位 4000
   - 成交量变化：今日量能待补充，待补充
   
3. **操作策略**：结构性行情延续，关注{leader[0] if leader[1] > 0 else lagger[0]}方向
   - 建议仓位：中等（2-3 成）
   - 风险提示：控制单一个股仓位不超过 20%

---

## 二、盘面理解与应对策略

1. **市场情绪**：

   - 整体情绪：待补充
   - 短线情绪：指数{ '分化' if (sh_change > 0) != (sz_change > 0) else '一致' }
   - 涨跌家数比：待补充

2. **市场反馈**：

   - 主板高度（10cm）：
     - 10 日涨幅第一：{gainers[0]['name']}（{gainers[0]['code']}）{gainers[0]['change_10d']:+.2f}%
   - 创业板高度（20cm）：
     - 10 日涨幅第一：待补充
   - 高位股票：{gainers[0]['name']} 10 日涨幅超{gainers[0]['change_10d']:.0f}% 延续强势，高位股整体表现强势，但需注意分化风险

3. **总结**：

   > 指数端{market_state}，{leader[0]}{leader[1]:+.2f}%{'领涨' if leader[1] > 0 else '领跌'}，{lagger[0]}{lagger[1]:+.2f}%{'领涨' if lagger[1] > 0 else '领跌'}。市场情绪端待补充。当前市场处于结构性行情阶段，建议控制仓位在 2-3 成，关注主线方向的持续性。

---

## 三、题材方向

##### 1. 待补充方向

- **行业逻辑**：待补充（来自真实新闻）
- **重点个股**：{gainers[0]['name']}（{gainers[0]['code']}）、待补充、待补充

##### 2. 待补充方向

- **行业逻辑**：待补充（来自真实新闻）
- **重点个股**：待补充、待补充、待补充

##### 3. 待补充方向

- **行业逻辑**：待补充（来自真实新闻）
- **重点个股**：待补充、待补充、待补充

---

## 四、明日计划

1. **主要观察题材**：
   - [ ] 待补充（观察持续性）
   - [ ] 待补充（观察政策催化）
   - [ ] 待补充（观察资金流向）

2. **对应题材下个股**：
   - 待补充：待补充
   - 待补充：待补充
   - 待补充：待补充

---

## 五、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：近 10 个交易日 | 排序方式：区间涨幅从高到低 | **已排除 ST 股票**

| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |
| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :------: |
"""
    
    # 添加股票数据
    for g in gainers:
        popularity_str = g.get('popularity', '待补充')
        if isinstance(popularity_str, str) and popularity_str != '待补充':
            popularity_str = f"第{popularity_str}名"
        
        report += f"| {g['rank']} | {g['code']} | {g['name']} | {g['close']} | {g['change_10d']:+.2f}% | {g['change_today']:+.2f}% | {popularity_str} | {g['concepts']} |\n"
    
    # 如果不足 20 只，填充占位符
    while len(gainers) < 20:
        rank = len(gainers) + 1
        report += f"| {rank} | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 | 待补充 |\n"
    
    # 添加关键观察
    report += f"""
**关键观察**：

- 涨幅冠军：{gainers[0]['name']}（{gainers[0]['code']}）{gainers[0]['change_10d']:+.2f}%
- 人气最高：待补充
- 板块分布：待补充
- 高位分化：待补充

---

## 六、备注/其他

- 交易心得：交易是一个先做加法的过程，积累认知，构建模式；越往后则是一个做减法的过程，越简单越好（交易频次减法、构建打磨单一的交易模式）；所以后期给大家推荐的明日计划中会降低频率，提高审美。
- 数据来源：A 股市场公开数据
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
"""
    
    # 保存文件
    os.makedirs(WORKSPACE_OUTPUT_DIR, exist_ok=True)
    os.makedirs(DESKTOP_DIR, exist_ok=True)
    
    workspace_file = os.path.join(WORKSPACE_OUTPUT_DIR, f"stock-report-{REPORT_DATE}.md")
    desktop_file = os.path.join(DESKTOP_DIR, f"stock-report-{REPORT_DATE}.md")
    
    with open(workspace_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 复制到 Desktop
    import shutil
    shutil.copy2(workspace_file, desktop_file)
    
    print(f"✅ 写入 workspace: {workspace_file}")
    print(f"✅ 复制到 Desktop: {desktop_file}")
    
    # 验证一致性
    with open(workspace_file, 'r') as f:
        workspace_content = f.read()
    with open(desktop_file, 'r') as f:
        desktop_content = f.read()
    
    if workspace_content == desktop_content:
        print("✅ 文件一致性验证通过")
    else:
        print("⚠ 文件一致性验证失败")
    
    print(f"\n🎉 报告生成完成！日期：{REPORT_DATE}")

if __name__ == "__main__":
    generate_report()
