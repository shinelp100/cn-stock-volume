# stock-daily-report v2.1

> 📊 生成 A 股每日复盘报告，包括大盘指数、市场情绪、题材方向、近 10 日涨幅前 20 股票等。

---

## ✨ 特性

- 📅 **指定日期生成** - 支持生成历史日期的复盘报告
- 🔄 **非交易日自动处理** - 周末/节假日自动往前推到最近交易日
- 📈 **多数据源 fallback** - cn-stock-volume → akshare，确保数据可用性
- 🎯 **结构化输出** - 标准化 Markdown 报告，保存到 ~/Desktop/A 股每日复盘/

---

## 🚀 快速开始

### 生成今日报告

```bash
python3 scripts/generate_report.py
```

### 生成指定日期

```bash
python3 scripts/generate_report.py --date 2026-03-25
```

### 周末/节假日自动处理

```bash
# 周日运行，自动使用最近交易日（周五）
python3 scripts/generate_report.py --date 2026-03-29
# 输出：ℹ 2026-03-29 为非交易日，使用最近交易日：2026-03-27
```

### 测试模式

```bash
python3 scripts/generate_report.py --date 2026-03-25 --test
```

---

## 📦 依赖

### Python 包

```bash
pip3 install akshare
```

### 本地 Skills

所有依赖的 skills 已包含在 `stock-data-monorepo` 目录中：

- `cn-stock-volume` - 大盘指数数据
- `ths-stock-themes` - 个股题材概念
- `stock-top-gainers` - 涨幅排名

---

## 📁 目录结构

```
stock-daily-report/
├── scripts/
│   ├── generate_report.py       # 主脚本 ⭐
│   ├── browser_popularity.py    # 人气热度获取
│   ├── fetch_realtime_gainers.py # 实时涨幅获取
│   ├── filter_concepts.py       # 概念过滤
│   ├── validate_data.py         # 数据验证
│   └── clawhub_integration.py   # ClawHub 集成
├── config/
│   ├── data_sources.py          # 数据源配置
│   ├── concept_blacklist.py     # 概念黑名单
│   └── theme_priority.py        # 题材优先级
├── templates/
│   └── report_template.md       # 报告模板
├── SKILL.md                     # 详细文档
├── README.md                    # 本文件
└── backup/                      # 备份文件
```

---

## 📊 数据源

| 数据类型 | 首选 | Fallback |
|----------|------|----------|
| 大盘指数 | cn-stock-volume/fetch_data.py | akshare |
| 涨幅排名 | browser/iwencai | fetch_realtime_gainers |
| 题材概念 | ths-stock-themes | 人工整理 |
| 人气热度 | browser/iwencai | 缓存数据 |

---

## 📝 输出示例

报告保存到：`~/Desktop/A 股每日复盘/stock-report-YYYY-MM-DD.md`

包含章节：
1. 大盘指数解读
2. 盘面理解与应对策略
3. 题材方向
4. 明日计划
5. 近 10 日涨幅前 20 股票
6. 备注/其他

---

## 🔧 配置

### 数据源优先级

编辑 `config/data_sources.py` 调整数据源优先级。

### 概念黑名单

编辑 `config/concept_blacklist.py` 添加/删除过滤概念。

### 题材优先级

编辑 `config/theme_priority.py` 调整题材评分。

---

## ⚠️ 注意事项

1. **浏览器依赖**：部分数据需要 OpenClaw browser 工具可用
2. **成交量数据**：需手动补充（使用 cn-stock-volume 的补数据.py）
3. **非交易日**：自动往前推，最多 7 天
4. **数据延迟**：行情数据可能有 15 分钟延迟

---

## 🐛 问题排查

### Q: 指数数据获取失败

**解决**：
1. 检查 cn-stock-volume/fetch_data.py 是否存在
2. 检查 browser 工具是否可用
3. 自动降级到 akshare

### Q: 涨幅排名获取失败

**解决**：
1. 检查 browser 工具连接
2. 使用占位符生成报告

### Q: 指定日期无效

**解决**：
1. 确保日期格式为 YYYY-MM-DD
2. 检查是否在 7 天范围内

---

## 📖 文档

- **详细文档**：[SKILL.md](SKILL.md)
- **更新日志**：[UPDATE_SUMMARY_v2.1.md](UPDATE_SUMMARY_v2.1.md)
- **完成报告**：[COMPLETION_REPORT.md](COMPLETION_REPORT.md)

---

## 📄 许可证

本 Skill 仅供学习交流使用，不构成投资建议。

---

**版本**：v2.1  
**更新日期**：2026-03-28  
**维护者**：shinelp100
