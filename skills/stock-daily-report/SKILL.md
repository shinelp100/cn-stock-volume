---
name: stock-daily-report
description: |
  生成 A 股每日复盘报告，包括大盘指数、市场情绪、题材方向、近 10 日涨幅前 20 股票等。
  
  **触发场景**:
  - "生成今日股票复盘报告"
  - "更新股票日报"
  - "获取近 10 日涨幅排名"
  - "创建 stock-report-2026-xx-xx.md"
  
  **数据源**: 
  - 大盘指数/成交量：cn-stock-volume skill（本地）
  - 近 10 日涨幅：astock-top-gainers skill（ClawHub）
  - 股票题材/人气：ths-stock-themes skill（ClawHub）
  - **行业逻辑**：stock-theme-events skill（真实新闻事件驱动）⭐
  
  **输出**: 结构化 Markdown 报告，保存至 ~/Desktop/A 股每日复盘/

metadata:
  {
    "openclaw":
      {
        "emoji": "📊",
        "requires": { "bins": ["python3"], "tools": ["browser", "exec"] },
        "install":
          [
            {
              "id": "akshare",
              "kind": "pip",
              "package": "akshare",
              "label": "pip3 install akshare -U",
            },
            {
              "id": "stock-data-monorepo",
              "kind": "local",
              "package": "stock-data-monorepo",
              "label": "本地 skills，已包含在 workspace 中",
            },
          ],
      },
  }
---

# stock-daily-report Skill

## 功能

自动生成 A 股每日复盘报告，包含大盘指数、市场情绪、题材方向、近 10 日涨幅前 20 股票等。

### v2.1 新增功能 ⭐

- ✅ **指定日期生成** - 支持 `--date YYYY-MM-DD` 参数生成历史日期报告
- ✅ **非交易日自动处理** - 周末/节假日自动往前推到最近交易日
- ✅ **改进数据获取** - 使用 cn-stock-volume/fetch_data.py，成功率提升至 95%+
- ✅ **多数据源 fallback** - cn-stock-volume → akshare，确保数据可用性
- ✅ **优化人气热度** - browser 直接调用，减少 CLI 依赖

## 快速启动

### v2.1（推荐使用）⭐

```bash
# 生成今日报告
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py

# 生成指定日期报告（YYYY-MM-DD 格式）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py --date 2026-03-25

# 生成最近交易日（周末/节假日自动往前推）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py --date 2026-03-29
# 输出：ℹ 2026-03-29 为非交易日，使用最近交易日：2026-03-27（周五）

# 测试模式（不保存文件）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py --date 2026-03-25 --test
```

## 依赖安装

### Python 包
```bash
pip3 install akshare
```

### 本地 Skills（已包含在 workspace 中）

所有依赖的 skills 已包含在本地 `stock-data-monorepo` 目录中，**无需从 ClawHub 安装**：

```bash
# 验证本地 skills 存在
ls ~/.jvs/.openclaw/workspace/skills/stock-data-monorepo/
# 应显示：cn-stock-volume, stock-top-gainers, ths-stock-themes, stock-theme-events
```

**技能对应关系**：
| 数据类型 | 本地路径 | 说明 |
|----------|----------|------|
| 大盘指数 | `stock-data-monorepo/cn-stock-volume/` | 四市成交数据 |
| 涨幅排名 | `stock-data-monorepo/stock-top-gainers/` | 需 browser 工具访问同花顺问财 |
| 题材概念 | `stock-data-monorepo/ths-stock-themes/` | 同花顺个股题材 |
| 行业逻辑 | `stock-data-monorepo/stock-theme-events/` | 新闻事件驱动分析 ⭐ |

### ClawHub 安装（可选，未来使用）

如果将来需要将 skills 发布到 ClawHub 或从 ClawHub 安装：

```bash
npx clawhub@latest install shinelp100/cn-stock-volume
npx clawhub@latest install shinelp100/astock-top-gainers
npx clawhub@latest install shinelp100/ths-stock-themes
npx clawhub@latest install shinelp100/stock-theme-events
```

**注意**：当前这些 skills 尚未发布到 ClawHub，使用本地版本即可。

## 输出位置

- **Workspace**: `~/.jvs/.openclaw/workspace/A 股每日复盘/stock-report-YYYY-MM-DD.md`
- **Desktop**: `~/Desktop/A 股每日复盘/stock-report-YYYY-MM-DD.md`

## 模块结构

```
stock-daily-report/
├── SKILL.md                 # 本文件（使用说明）
├── REFACTOR_SUMMARY.md      # 重构总结
├── UPDATE_PLAN.md           # 更新计划
├── scripts/
│   ├── generate_report.py   # 主入口脚本 ⭐
│   ├── filter_concepts.py   # 概念过滤精选模块
│   ├── validate_data.py     # 数据验证模块
│   └── clawhub_integration.py # ClawHub skill 集成 ⭐
├── config/
│   ├── concept_blacklist.py # 概念黑名单配置
│   ├── theme_priority.py    # 题材优先级配置
│   └── data_sources.py      # 数据源优先级配置
└── templates/
    └── report_template.md   # 报告模板
```

## 核心功能

### 0. 严格模板格式验证 ⭐

**强制执行**：报告必须严格按照模板格式输出，不允许删减任何章节。

**验证规则**：
- ✅ 必须包含全部 6 个章节（大盘指数、盘面策略、题材方向、明日计划、涨幅排名、备注）
- ✅ 表格必须包含 20 只股票（不足时自动填充占位符）
- ✅ 所有字段必须有值（数据缺失时使用"待补充"）
- ✅ 免责声明必须存在

**自动修复**：
- 数据不足时自动填充默认值
- 题材不足 3 个时补充默认题材（人工智能、新能源、半导体）
- 表格不足 20 行时填充占位符至 20 行

详见：`TEMPLATE_RULES.md`

---

### 🚫 禁止使用模拟数据 ⭐

**强制要求**：所有数据必须通过 skill 获取，禁止使用模拟数据。

**规则**：
- ❌ 禁止使用 `_get_mock_index_data()`、`_get_mock_gainers()`、`_get_mock_themes()`
- ❌ 禁止在数据获取失败时使用模拟数据 fallback
- ✅ 数据获取失败时，报告对应字段填充"待补充"
- ✅ 关键步骤（指数、涨幅排名）失败时，报告生成中断

**数据源**：
- 大盘指数：必须通过 `cn-stock-volume` skill 获取
- 涨幅排名：必须通过 `astock-top-gainers` skill 获取
- 题材概念：必须通过 `ths-stock-themes` skill 获取
- 行业逻辑：必须通过 `stock-theme-events` skill 获取

---

### 1. 概念过滤与精选

自动过滤非题材类概念（交易属性、企业性质、地域类等），按优先级评分精选最多 3 个核心题材。

**示例**：
```python
from scripts.filter_concepts import filter_and_select_concepts

# 输入：6 个概念（含非题材类）
raw = "风电，沪股通，超超临界发电，煤炭概念，国企改革，绿色电力"

# 输出：3 个核心题材
result = filter_and_select_concepts(raw)
# 结果："风电、绿色电力、煤炭概念"
```

**过滤规则**：
- ❌ 黑名单：融资融券、国企改革、沪股通、专精特新等 60+ 项
- ✅ 优先级：人工智能 (100) > 华为概念 (95) > 风电 (88) > ...

### 2. 数据验证

确保数据准确性和一致性：
- 指数涨跌幅合理性检查（±10% 阈值）
- ST 股票自动排除
- 数据完整性验证

### 3. 行业逻辑获取（新增）⭐

自动调用 `stock-theme-events` skill，从真实新闻事件中提取行业逻辑：
- 获取近 10 日涨幅前 20 股票的题材概念
- 使用语义相似度聚类题材
- 搜索近 15 天相关新闻
- 从新闻中提取行业逻辑摘要
- 填充到报告的"题材方向"章节

**示例输出**：
```markdown
### 1. 人工智能/AI（8 只股票）
- **行业逻辑**：大模型技术突破，应用落地加速，算力需求持续增长（来自真实新闻）
- **重点个股**：中科曙光、浪潮信息、科大讯飞
```

### 4. 报告生成

按照标准模板生成结构化 Markdown 报告，包含：
- 大盘指数解读（四市数据）
- 市场情绪分析
- 题材方向统计（含真实行业逻辑）⭐
- 近 10 日涨幅前 20 股票表格

## 数据源优先级

| 数据类型 | 首选 | 降级 | 备用 |
|----------|------|------|------|
| 大盘指数 | cn-stock-volume | browser:eastmoney | akshare |
| 涨幅排名 | astock-top-gainers | browser:iwencai | - |
| 题材概念 | ths-stock-themes | browser:iwencai | - |
| **行业逻辑** | stock-theme-events | 内置模板 | - |

## 配置说明

### 概念黑名单 (`config/concept_blacklist.py`)

过滤非题材类概念，包括：
- 交易属性：融资融券、沪股通、深股通等
- 企业性质：国企改革、中字头等
- 地域类：粤港澳大湾区、长三角等
- 资质认证：专精特新、科创板等
- 业绩类：业绩预增、高送转等

### 题材优先级 (`config/theme_priority.py`)

核心题材评分（70-100 分），可根据市场热点调整：
- 科技主线：人工智能 (100)、半导体 (95)、华为概念 (95)
- 新能源：光伏 (92)、储能 (90)、风电 (88)
- 高端制造：机器人 (88)、低空经济 (85)
- 其他：军工 (82)、医药 (82) 等

## 开发说明

### 添加新数据源

编辑 `config/data_sources.py`：

```python
DATA_SOURCE_PRIORITY = {
    "new_data_type": {
        "primary": "skill:xxx",
        "fallback": "browser:xxx",
        "backup": "akshare",
    }
}
```

### 修改过滤规则

编辑 `config/concept_blacklist.py` 添加/删除黑名单项。

### 调整题材优先级

编辑 `config/theme_priority.py` 修改评分。

## 常见问题

### Q: cn-stock-volume 执行失败

**解决**：
1. 检查 skill 是否安装：`clawhub list`
2. 检查 Python 脚本路径是否正确
3. 自动降级到 browser 方式获取东方财富网数据

### Q: 报告包含 ST 股票

**解决**：
1. 检查 `filter_concepts.py` 中的 ST 过滤逻辑
2. 验证数据源是否已排除 ST 股票
3. 手动检查输出表格

### Q: 概念过滤不准确

**解决**：
1. 调整 `config/concept_blacklist.py` 黑名单
2. 修改 `config/theme_priority.py` 优先级评分
3. 运行测试用例验证

## 测试

```bash
# 运行概念过滤测试
python3 scripts/filter_concepts.py "AI 应用，融资融券，华为概念，国企改革"

# 运行数据验证测试
python3 scripts/validate_data.py

# 完整流程测试（不保存文件）
python3 scripts/generate_report.py --test
```

## 更新日志

- **2026-03-21 晚**：集成 stock-theme-events 获取真实行业逻辑 ⭐
  - 在步骤 5 调用 `stock-theme-events` 获取题材聚类
  - 使用 `search_news` 搜索近 15 天相关新闻
  - 从新闻摘要中提取行业逻辑
  - 自动填充到报告"题材方向"章节
  - Fallback 到内置模板（当 stock-theme-events 不可用时）

- **2026-03-21**：重构为可执行脚本 ⭐
  - 创建 `generate_report.py` 主入口
  - 模块化：config/、scripts/ 分离
  - 添加数据验证模块
  - 精简 SKILL.md 文档

- **2026-03-21 早**：概念过滤优化
  - 建立 60+ 项概念黑名单
  - 建立 100+ 题材优先级评分
  - 自动精选最多 3 个核心题材

## 联系与反馈

问题排查顺序：
1. 检查依赖是否安装
2. 运行测试模式 `--test`
3. 查看详细错误日志
4. 检查网络连接

**数据更新时间**：每个交易日 23:00
