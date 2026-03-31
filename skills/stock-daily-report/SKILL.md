---
name: stock-daily-report
version: 4.0.0
description: A股每日复盘报告自动生成（v4.0 浏览器自动化集成版）。严格按照固定模板输出，含大盘指数、情绪分析、题材方向、近10日涨幅榜、明日计划等。触发：用户询问"每日复盘"、"今日盘面"、"A股总结"、"昨日股市怎么样"等。
---

# stock-daily-report v4.0

A股每日复盘报告自动生成工具（浏览器自动化集成版）。

## 模板结构（6段固定格式）

```
一、大盘指数解读
  1. 市场状态：xxx（动态生成：市场普涨/市场回调/三大指数分化等）
     - 上证指数：xxxx.xx 点，涨幅 +x.xx%
     - 深证成指：xxxx.xx 点，涨幅 +x.xx%
     - 创业板指：xxxx.xx 点，涨幅 +x.xx%
  2. 位置判断：xxx
     - 上证指数支撑位/压力位：支撑位xxxx，压力为xxxx
     - 成交量变化：今日量能（xxxx亿），缩量xxx亿（-x.xx%）
  3. 操作策略：结构性行情延续，关注创业板强势方向
     - 建议仓位：x成
     - 风险提示：控制单一个股仓位不超过 20%

二、盘面理解与应对策略
  1. 市场情绪
     - 整体情绪：xxx
     - 短线情绪：xxx
     - 涨跌家数比：xxx(涨) : xxx(跌) ≈ 1 : x.x（xxx）
  2. 市场反馈
     - 主板高度（10cm）：xxx（xxx）+x.xx%，高位震荡继续新高
     - 创业板高度（20cm）：xxx（xxx）+x.xx%，xxx板块加强
     - 高位股票：xxx 10 日涨幅超 x% 领涨，xxx +x.xx% 紧随其后
  3. 总结：> xxx

三、题材方向
  ##### 1. xxx方向
  - 行业逻辑：xxx
  - 重点个股：xxx（xxx）、xxx（xxx）

四、近 10 个交易日涨幅前 20 股票
  | 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |

五、明日计划
  1. 主要观察题材
  2. 对应题材下个股

六、备注/其他
```

## v4.0 关键改进

| 项目 | v3.x | v4.0 |
|------|------|------|
| 浏览器自动化 | 无真正集成 | **自动调用 Playwright** |
| 数据获取方式 | 仅 AkShare | **多级降级：Node.js → Python Playwright → AkShare** |
| 涨跌家数比 | AkShare 或占位符 | **实时浏览器获取** |
| 涨幅榜数据 | AkShare | **浏览器实时获取** |

## 目录结构

```
stock-daily-report/
├── SKILL.md
└── scripts/
    ├── generate_report.py    # 主脚本（v4.0 集成浏览器）
    ├── browser_fetcher.py    # 浏览器数据解析
    ├── fetch_volume.py       # 三市成交量
    ├── fetch_concepts.py     # 题材方向
    └── node/
        ├── package.json      # Node.js 依赖
        ├── browser_client.js # Playwright 客户端
        └── fetch_data.js     # 数据获取入口
```

## 使用方式

### 方式一：OpenClaw Skill 触发（推荐）

当用户说以下内容时，OpenClaw agent 自动执行：
- "每日复盘"
- "今日盘面"
- "A股总结"
- "昨日股市怎么样"
- "生成今日股票报告"

Agent 会自动：
1. 调用 `generate_report.py` 生成报告
2. 尝试使用 Playwright 浏览器获取数据
3. 数据获取失败时自动降级到 AkShare

### 方式二：命令行运行

```bash
# 进入 skill 目录
cd ~/.qclaw/workspace/skills/stock-daily-report/scripts

# 生成今日报告（完整模式）
python3 generate_report.py

# 生成指定日期报告
python3 generate_report.py 2026-03-27

# 快速模式（跳过浏览器）
python3 generate_report.py 2026-03-27 --no-browser

# 输出到文件
python3 generate_report.py --output=~/Desktop/report.md
```

### 方式三：Node.js 独立运行

```bash
cd ~/.qclaw/workspace/skills/stock-daily-report/scripts/node

# 安装依赖
npm install
npx playwright install chromium  # 首次运行需要

# 获取全部数据
node fetch_data.js

# 仅获取涨跌家数
node fetch_data.js --sentiment

# 仅获取涨幅榜
node fetch_data.js --gainers
```

## 数据获取流程（自动降级）

```
1. Node.js Playwright
   ↓ 失败
2. Python Playwright
   ↓ 失败
3. AkShare（备选）
   ↓ 失败
4. 返回占位符
```

## 数据源说明

| 字段 | 首选数据源 | 备选数据源 |
|------|-----------|-----------|
| 四大指数 | 腾讯/东方财富 API | 东方财富 K线 |
| 三市成交量 | cn-stock-volume skill | 东方财富 |
| 涨跌家数 | Playwright 同花顺 | AkShare |
| 涨幅榜 | Playwright 同花顺 | AkShare |
| 题材方向 | 东方财富 API | 本地缓存 |

## 浏览器自动化说明

### 自动获取（推荐）

脚本会自动尝试使用 Playwright 浏览器获取数据：
- 涨跌家数比：访问同花顺问财"涨跌家数"
- 涨幅榜：访问同花顺问财"近10日涨幅排名"

### 手动获取（备选）

如果自动获取失败，可以手动通过 OpenClaw browser 工具获取：

1. 使用 browser 工具访问同花顺问财
2. 截图或获取页面快照
3. 脚本会尝试解析快照数据

### 依赖安装

```bash
# Node.js 方式（推荐）
cd scripts/node
npm install
npx playwright install chromium

# 或 Python 方式
pip install playwright
playwright install chromium
```

## 输出示例

```bash
$ python3 generate_report.py

正在生成 2026-03-29 的每日复盘报告...
=======================================================
📈 获取四大指数...
   上证指数: 3425.67 (+0.89%)
   深证成指: 11234.56 (+1.23%)
   创业板指: 2345.78 (+1.56%)
📊 获取三市成交量...
   三市合计: 1.23万亿 放量 456.7亿（+3.89%）
😊 获取市场情绪...
   涨: 3245 跌: 1789
🔍 获取题材方向...
   发现题材: 5 个
📊 获取盘面理解数据...
   🔄 尝试通过 Node.js Playwright 获取浏览器数据...
   ℹ️ Playwright 未安装，尝试快照解析...
   → 跳过或获取失败（使用占位符）
✅ 报告已保存至: ~/Desktop/report.md
```

## 性能说明

| 模式 | 耗时 | 数据完整度 |
|------|------|----------|
| 完整模式（自动浏览器） | 1-2 分钟 | ~90% |
| 快速模式（--no-browser） | 15 秒 | ~70% |

## 常见问题

### Q: Playwright 浏览器下载失败
A: 使用 `npx playwright install chromium` 重新安装，或使用 `--no-browser` 跳过

### Q: 同花顺问财需要登录
A: 自动降级到 AkShare 获取基础数据，或手动获取快照

### Q: 数据获取超时
A: 检查网络连接，或使用 `--no-browser` 快速模式

## 风险提示

⚠️ 本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
