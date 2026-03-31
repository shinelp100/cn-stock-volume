# stock-daily-report v3.2

A股每日复盘报告自动生成工具（完整数据集成版）。

## 🎯 功能

自动生成包含以下内容的每日复盘报告：

1. **大盘指数解读** - 四大指数、支撑/压力位、成交量、仓位建议
2. **盘面理解与应对** - 市场情绪、主板/创业板冠军、高位股票、总结
3. **题材方向** - 动态发现的热门题材、逻辑、个股
4. **近10日涨幅前20** - 完整表格（排名/代码/名称/收盘价/涨幅/人气/概念）
5. **明日计划** - 观察题材及对应个股
6. **备注/免责声明**

## 📋 快速开始

### 方案 A：快速模式（推荐）

```bash
# 1. 生成报告框架（15秒）
python3 scripts/generate_report.py 2026-03-27 --no-browser --output=~/Desktop/report.md

# 2. 打开同花顺问财获取数据（2分钟）
# https://www.iwencai.com/unifiedwap/result?w=近10日涨幅排名&querytype=stock

# 3. 编辑报告，填充数据（2分钟）
open ~/Desktop/report.md

# 总耗时：~5分钟
```

**需要填充的数据**：
- 涨跌家数比：`XXXX(涨) : XXXX(跌) ≈ 1 : X.X`
- 主板冠军：`名称（代码）+涨幅%`
- 创业板冠军：`名称（代码）+涨幅%`
- 高位股票：`名称1 10日涨幅超 X% 领涨，名称2 +X.XX% 紧随其后`

详见 `QUICK_REFERENCE.md`

### 方案 B：完全自动化（需要开发）

需要在 `generate_report.py` 中集成浏览器工具调用。

详见 `BROWSER_AUTOMATION_GUIDE.md`

## 📁 文件结构

```
stock-daily-report/
├── README.md                          # 本文件
├── SKILL.md                           # 技能说明
├── QUICK_REFERENCE.md                 # 快速参考卡片（用户必读）
├── USER_OPERATIONS.md                 # 用户操作指南
├── BROWSER_AUTOMATION_GUIDE.md        # 浏览器自动化详细指南
└── scripts/
    ├── generate_report.py             # 主脚本：数据聚合 + 模板渲染
    ├── fetch_volume.py                # 三市成交量
    ├── fetch_concepts.py              # 题材方向 + 实时股价
    ├── fetch_sentiment.py             # 市场情绪（AkShare）
    ├── fetch_top10.py                 # 涨幅榜解析
    └── fetch_browser_data.py          # 浏览器数据解析
```

## 🚀 使用方式

### 生成今日报告

```bash
python3 scripts/generate_report.py
```

### 生成指定日期报告

```bash
python3 scripts/generate_report.py 2026-03-27
```

### 快速模式（跳过AkShare）

```bash
python3 scripts/generate_report.py 2026-03-27 --no-browser
```

### 输出到文件

```bash
python3 scripts/generate_report.py 2026-03-27 --output=~/Desktop/report.md
```

## 📊 数据源

| 字段 | 数据源 | 获取方式 |
|------|--------|---------|
| 四大指数 | 东方财富 K线 | 直接 API |
| 三市成交量 | 东方财富 K线 | 直接 API |
| 市场情绪 | 同花顺问财 | 浏览器快照 |
| 主板/创业板冠军 | 同花顺问财 | 浏览器快照 |
| 高位股票 | 同花顺问财 | 浏览器快照 |
| 涨幅榜前20 | 同花顺问财 | 浏览器快照 |
| 题材方向 | 东方财富 | 直接 API |

## ⏱️ 性能

| 模式 | 耗时 | 数据完整度 |
|------|------|----------|
| 快速模式（--no-browser） | 15 秒 | 70%（需手动填充） |
| 完整模式 | 1-2 分钟 | 100%（自动化） |

## 📖 文档

- **QUICK_REFERENCE.md** - 快速参考卡片（用户必读）
- **USER_OPERATIONS.md** - 用户操作指南
- **BROWSER_AUTOMATION_GUIDE.md** - 浏览器自动化详细指南
- **SKILL.md** - 完整技能说明

## 🔗 相关 Skills

- `astock-top-gainers` - A股涨幅排行
- `cn-stock-concept` - 个股题材查询
- `cn-stock-volume` - 三市成交量

## ⚠️ 注意事项

- 周末/非交易日数据可能不完整
- 快速模式下市场反馈显示占位符，需手动填充
- 报告生成后建议人工复核关键信息
- 本报告仅供参考，不构成投资建议

## 📞 支持

- 快速问题：查看 `QUICK_REFERENCE.md`
- 详细问题：查看 `BROWSER_AUTOMATION_GUIDE.md`
- 功能说明：查看 `SKILL.md`

---

**版本**：v3.2.0  
**最后更新**：2026-03-28  
**状态**：✅ 可用（快速模式）| ⏳ 开发中（完全自动化）
