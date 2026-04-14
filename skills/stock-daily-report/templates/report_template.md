# 📊 股票每日分析报告

**日期：{date}**

---

## 一、大盘指数解读

1. **市场状态**：三大指数分化，成交量放大
   - 上证指数：{index.shanghai.close} 点，涨跌幅 {index.shanghai.change_pct}%
   - 深证成指：{index.shenzhen.close} 点，涨跌幅 {index.shenzhen.change_pct}%
   - 创业板指：{index.chinext.close} 点，涨跌幅 {index.chinext.change_pct}%

2. **位置判断**：市场震荡整理
   - 成交量变化：今日量能（{index.summary.total_fmt}），{index.summary.change_fmt}（{index.summary.change_pct}%）

3. **操作策略**：控制仓位，跟随主线
   - 建议仓位：中等（2-3 成）
   - 风险提示：控制单一个股仓位不超过 20%

---

## 二、盘面理解与应对策略

1. **市场情绪**：

   - 整体情绪：分歧加大
   - 短线情绪：指数分化，个股跌多涨少
   - 涨跌家数比：{market_sentiment.ratio}

2. **市场反馈**：

   - 主板高度（10cm）：
     - 10 日涨幅第一：{gainers.main_board_top.name}（{gainers.main_board_top.code}）
   - 创业板高度（20cm）：
     - 10 日涨幅第一：{gainers.chinext_top.name}（{gainers.chinext_top.code}）

3. **总结**：

   > 指数端三大指数分化，成交量放大显示资金活跃度提升。市场情绪端{market_sentiment.summary}。当前市场处于震荡整理阶段，建议控制仓位在 2-3 成，跟随强势板块轮动，避免追高。

---

## 三、题材方向

{theme_section}

---

## 四、明日计划

1. **主要观察题材**：
   - [ ] {watch_themes.0}（观察持续性）
   - [ ] {watch_themes.1}（观察轮动）
   - [ ] {watch_themes.2}（观察资金流向）

2. **对应题材下个股**：
   - {watch_themes.0}：{theme_stocks.0}
   - {watch_themes.1}：{theme_stocks.1}
   - {watch_themes.2}：{theme_stocks.2}

---

## 五、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：{date_range} | **已排除 ST 股票**

{gainers_table}

**关键观察**：
- 涨幅冠军：{gainers.top1.name}（{gainers.top1.code}）{gainers.top1.change}%
- 前 20 平均涨幅：{gainers.avg_change}%

---

## 六、备注/其他

- 情绪冰点策略：等待市场企稳
- 数据来源：A 股市场公开数据
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
