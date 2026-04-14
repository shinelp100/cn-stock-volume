# stock-daily-report 实时数据优化总结

## 问题

生成的股票报告使用缓存数据（2026-03-21），不是最新的实时数据。

## 根本原因

在 Python 子进程中无法调用 `openclaw` CLI 命令（PATH 环境变量问题），导致 browser 工具无法在子进程中使用。

## 解决方案

### 方案 A：在主进程中直接调用 browser（推荐）⭐

修改 `generate_report.py`，让它在主进程中直接调用 browser 工具，而不是通过子进程。

**优点**：
- 可以访问 browser 工具
- 获取真正的实时数据
- 有 fallback 机制

**实现**：需要在 `generate_report.py` 的 `step2_fetch_top_gainers()` 中直接调用 browser 工具。

### 方案 B：手动获取数据后运行脚本

用户手动通过 browser 获取数据，然后运行生成脚本。

**步骤**：
1. 手动执行：`openclaw browser open --url "https://www.iwencai.com/unifiedwap/result?w=近 10 日涨幅排名"`
2. 获取 snapshot：`openclaw browser snapshot --refs aria`
3. 运行脚本：`python3 generate_report.py`

**缺点**：需要手动操作，不够自动化。

### 方案 C：使用缓存数据（当前 fallback）

当 browser 不可用时，使用本地缓存数据作为 fallback。

**优点**：
- 不依赖网络
- 始终可以运行

**缺点**：
- 数据不是最新的

## 当前状态

✅ 已完成的优化：
1. `clawhub_integration.py` - 添加了实时获取接口
2. `fetch_gainers.py` - 改为默认 `--source auto`（自动选择）
3. `generate_report.py` - 优化日志输出，显示数据来源
4. 添加了 fallback 机制（browser 失败时使用缓存）

⚠️ 待完成：
- 在 `generate_report.py` 中直接集成 browser 调用（方案 A）
- 或在主会话中通过其他方式获取实时数据

## 临时解决方案

由于子进程无法调用 openclaw CLI，当前采用以下策略：

1. **优先尝试实时获取**（需要主进程支持）
2. **失败则 fallback 到缓存**（当前默认行为）
3. **用户可手动指定数据源**

### 使用缓存数据生成报告（当前可用）

```bash
# 生成报告（使用缓存数据）
python3 ~/.jvs/.openclaw/workspace/skills/stock-daily-report/scripts/generate_report.py

# 强制使用缓存
python3 ~/.jvs/.openclaw/workspace/skills/stock-data-monorepo/stock-top-gainers/scripts/fetch_gainers.py --source cache
```

### 获取实时数据（需要手动）

在主 OpenClaw 会话中执行：

```python
# 1. 打开同花顺问财
browser open --url "https://www.iwencai.com/unifiedwap/result?w=近 10 日涨幅排名"

# 2. 等待加载
sleep 3

# 3. 获取 snapshot
browser snapshot --refs aria

# 4. 解析数据（使用提供的解析函数）
# 将 snapshot 输出传递给 parse_snapshot 函数
```

## 后续优化计划

### Phase 1: 在主进程中集成 browser 调用

修改 `generate_report.py`，在 `step2_fetch_top_gainers()` 中直接调用 browser：

```python
def step2_fetch_top_gainers(self):
    # 直接在主进程中调用 browser
    from browser import open, snapshot
    
    # 打开页面
    open(url="https://www.iwencai.com/...")
    
    # 获取 snapshot
    snap = snapshot(refs="aria")
    
    # 解析数据
    self.top_gainers = parse_iwencai_snapshot(snap)
```

### Phase 2: 添加数据验证

- 验证数据日期（检查"今日涨跌"字段）
- 验证数据合理性（涨幅范围）
- 异常数据自动 fallback

### Phase 3: 优化缓存更新

- 定期更新缓存数据
- 缓存过期自动刷新
- 多数据源对比验证

## 文件修改清单

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `scripts/clawhub_integration.py` | 添加实时获取接口 | ✅ 完成 |
| `stock-top-gainers/scripts/fetch_gainers.py` | 默认 auto 模式 | ✅ 完成 |
| `scripts/generate_report.py` | 优化日志输出 | ✅ 完成 |
| `scripts/test_realtime.py` | 新增测试脚本 | ✅ 完成 |
| `scripts/fetch_realtime_gainers.py` | 独立获取脚本 | ✅ 完成 |
| `REALTIME_UPDATE.md` | 优化说明文档 | ✅ 完成 |

## 验证方法

### 检查日志

运行生成脚本时，查看数据来源：

```bash
python3 generate_report.py --verbose
```

**实时数据**：
```
📈 获取近 10 日涨幅排名...
  ✅ 成功获取 20 只股票（实时数据）
  数据源：browser(realtime)
```

**缓存数据**：
```
📈 获取近 10 日涨幅排名...
  ℹ️  使用缓存数据：20 只股票
  数据源：cache(fallback)
```

### 检查数据时效

实时数据包含"今日涨跌"字段：

```json
{
  "股票代码": "600396",
  "股票简称": "华电辽能",
  "10 日涨幅": 89.81,
  "今日涨跌": 10.06  // ✅ 有这个字段说明是实时数据
}
```

## 总结

**当前状态**：优化已完成 70%，fallback 机制工作正常，但实时获取需要在主进程中直接调用 browser。

**建议**：
1. 短期：使用缓存数据生成报告（fallback 机制保证可用性）
2. 中期：在主会话中手动获取实时数据后运行脚本
3. 长期：在 generate_report.py 中直接集成 browser 调用

---

**更新时间**：2026-03-23 22:35  
**维护者**：shinelp100
