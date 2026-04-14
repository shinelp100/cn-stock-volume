# stock-daily-report 实时数据优化

## 问题描述

**原问题**：生成的股票报告使用的是缓存数据（2026-03-21），不是最新的实时数据。

**根本原因**：
1. `fetch_gainers.py` 默认使用 `--source sample`（示例数据/缓存）
2. `clawhub_integration.py` 调用本地脚本时也是用 `sample` 数据源
3. 没有通过 browser 工具实时获取同花顺问财数据

## 优化方案

### 核心改进

✅ **优先实时获取**：默认通过 browser 工具访问同花顺问财获取最新数据  
✅ **自动 fallback**：browser 失败时自动降级到缓存数据  
✅ **数据验证**：添加数据日期验证，确保数据时效性  
✅ **ST 过滤**：实时排除 ST 股票（*ST、ST 等）

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `scripts/clawhub_integration.py` | 新增 `fetch_top_gainers_realtime()` 函数，优先 browser 获取 |
| `stock-top-gainers/scripts/fetch_gainers.py` | 改为默认 `--source auto`（自动选择） |
| `scripts/generate_report.py` | 优化日志输出，显示数据来源（实时/缓存） |
| `scripts/test_realtime.py` | 新增测试脚本，验证实时获取功能 |

### 数据获取流程

```
┌─────────────────────────────────────┐
│  step2_fetch_top_gainers()         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  clawhub.fetch_top_gainers()       │
│  (优先 browser 实时获取)             │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│ browser 成功 │  │ browser 失败 │
│ ✅ 实时数据  │  │ ❌          │
└──────┬──────┘  └──────┬──────┘
       │                │
       │                ▼
       │         ┌─────────────┐
       │         │ 缓存 fallback│
       │         │ 📦 缓存数据  │
       │         └──────┬──────┘
       │                │
       ▼                ▼
┌─────────────────────────────────────┐
│  数据验证（日期、ST 过滤）           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  返回股票列表（20 只）               │
└─────────────────────────────────────┘
```

## 使用方式

### 生成报告（自动实时获取）

```bash
# 生成今日报告（默认自动实时获取）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py

# 生成指定日期报告
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py 2026-03-23

# 测试模式（不保存文件）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py --test

# 详细日志（显示数据来源）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py --verbose
```

### 单独获取涨幅排名

```bash
# 自动模式（优先实时，失败则缓存）
python3 ~/.jvs/.openclaw/workspace/skills/stock-data-monorepo/stock-top-gainers/scripts/fetch_gainers.py

# 强制实时获取
python3 ~/.jvs/.openclaw/workspace/skills/stock-data-monorepo/stock-top-gainers/scripts/fetch_gainers.py --source browser

# 强制使用缓存
python3 ~/.jvs/.openclaw/workspace/skills/stock-data-monorepo/stock-top-gainers/scripts/fetch_gainers.py --source cache
```

### 测试实时获取功能

```bash
# 运行测试脚本
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/test_realtime.py
```

## 数据源优先级

| 数据类型 | 首选 | 降级 | 备用 |
|----------|------|------|------|
| 大盘指数 | sessions-spawn | cn-stock-volume | 待补充 |
| **涨幅排名** | **browser(同花顺问财)** | **本地缓存** | - |
| 题材概念 | ths-stock-themes | 内置映射表 | - |
| 行业逻辑 | stock-theme-events | 内置模板 | - |

## 验证方法

### 1. 检查日志输出

优化后，生成报告时会显示数据来源：

```
📈 获取近 10 日涨幅排名...
  🔄 调用 clawhub_integration 获取数据（browser 实时优先）...
  🌐 访问同花顺问财：https://www.iwencai.com/...
  📸 获取页面 snapshot...
  ✅ 成功获取 20 只股票（实时数据）
```

或使用缓存时：

```
📈 获取近 10 日涨幅排名...
  🔄 调用 clawhub_integration 获取数据（browser 实时优先）...
  📦 实时获取失败，使用缓存数据
  ℹ️  使用缓存数据：20 只股票
  ⚠️ 成功获取 20 只股票（缓存数据）
```

### 2. 检查数据时效性

实时数据包含"今日涨跌"字段，缓存数据可能缺失：

```python
# 实时数据示例
{
  "股票代码": "600396",
  "股票简称": "华电辽能",
  "收盘价": 6.89,
  "10 日涨幅": 89.81,
  "今日涨跌": 10.06  # ✅ 有今日涨跌数据
}

# 缓存数据示例（可能缺失今日涨跌）
{
  "股票代码": "688295",
  "股票简称": "中复神鹰",
  "收盘价": 60.59,
  "10 日涨幅": 99.97
  # ❌ 可能没有今日涨跌字段
}
```

### 3. 验证 ST 过滤

实时数据会自动排除 ST 股票：

```bash
# 获取 50 只股票，检查是否有 ST
python3 fetch_gainers.py --limit 50 | grep ST
# 应该无输出（已过滤）
```

## 性能对比

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 数据时效 | 缓存（1-2 天前） | 实时（当日） |
| 获取方式 | 本地脚本 | browser 实时 + fallback |
| 网络依赖 | 无 | 是（可 fallback） |
| 获取耗时 | ~1 秒 | ~5-10 秒（browser） |
| 可靠性 | 高 | 高（有 fallback） |

## 注意事项

1. **网络要求**：实时获取需要访问同花顺问财网站
2. **browser 依赖**：需要 OpenClaw browser 工具可用
3. **fallback 机制**：browser 失败时自动使用缓存，不会中断报告生成
4. **数据验证**：添加了数据日期验证，异常数据会触发 fallback

## 故障排查

### Q: browser 获取失败

**检查**：
```bash
# 测试 browser 是否可用
openclaw browser status

# 手动访问同花顺问财
openclaw browser open --url "https://www.iwencai.com/unifiedwap/result?w=近 10 日涨幅排名"
```

**解决**：
- 检查网络连接
- 检查 browser 配置
- 自动 fallback 到缓存数据（不影响报告生成）

### Q: 数据不是最新的

**检查**：
```bash
# 查看详细日志
python3 generate_report.py --verbose

# 检查数据来源
# 日志中应显示 "browser(realtime)" 或 "cache(fallback)"
```

**解决**：
- 确保 browser 可用
- 清除浏览器缓存
- 检查同花顺问财网站是否正常

### Q: ST 股票未被过滤

**检查**：
```bash
# 手动测试 ST 过滤
python3 fetch_gainers.py --limit 50 --exclude-st | grep -i st
```

**解决**：
- 检查 `exclude_st` 参数是否启用
- 验证过滤逻辑（大小写 insensitive）

## 更新日志

### 2026-03-23 - 实时数据优化 ⭐

- ✅ 新增 `fetch_top_gainers_realtime()` 函数
- ✅ 修改 `fetch_gainers.py` 默认使用 `--source auto`
- ✅ 添加数据日期验证逻辑
- ✅ 优化日志输出（显示数据来源）
- ✅ 新增测试脚本 `test_realtime.py`
- ✅ 完善 ST 股票过滤

### 2026-03-21 - 重构为可执行脚本

- 创建 `generate_report.py` 主入口
- 模块化：config/、scripts/ 分离
- 添加数据验证模块

---

**维护者**：shinelp100  
**最后更新**：2026-03-23
