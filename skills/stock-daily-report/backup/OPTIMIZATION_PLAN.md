# stock-daily-report 优化计划 v2.1

## 优化目标

1. **提高数据获取及时性** - 使用 cn-stock-volume 成熟的数据获取方式
2. **提高数据准确性** - 多数据源 fallback 机制
3. **新增指定日期功能** - 支持生成历史日期的复盘报告
4. **改进人气热度获取** - 优化 browser_popularity.py

## 优化点

### 1. 指数数据获取优化

**现状**：
- 使用 sessions_spawn 调用 cn-stock-volume skill
- 失败后降级到 akshare

**优化后**：
- 直接调用 cn-stock-volume/scripts/fetch_data.py
- 支持指定日期获取
- 添加多数据源 fallback（同花顺问财 → 东方财富 → akshare）

**代码改动**：
```python
# generate_report.py step1_fetch_index_data
def step1_fetch_index_data(self):
    """获取大盘指数数据（优化版）"""
    # 1. 优先使用 cn-stock-volume 的 fetch_data.py
    fetch_script = self.workspace_root / "skills/stock-data-monorepo/cn-stock-volume/scripts/fetch_data.py"
    if fetch_script.exists():
        result = subprocess.run(
            ["python3", str(fetch_script), self.date],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            self.index_data = json.loads(result.stdout)
            self.stats["data_source"]["index"] = "cn-stock-volume/fetch_data.py"
            return True
    
    # 2. 降级到 akshare
    self.index_data = self._fetch_index_via_akshare()
    self.stats["data_source"]["index"] = "akshare"
    return True
```

### 2. 指定日期功能

**新增参数**：
```bash
# 生成今日报告
python3 generate_report.py

# 生成指定日期
python3 generate_report.py --date 2026-03-25

# 生成最近交易日（周末/节假日自动往前推）
python3 generate_report.py --date 2026-03-29  # 周日 → 3月27日（周五）
```

**实现**：
- 复用 cn-stock-volume 的 `get_previous_trading_day()` 函数
- 支持非交易日自动处理

### 3. 人气热度获取优化

**现状**：
- browser_popularity.py 依赖 openclaw CLI
- 失败后使用缓存数据

**优化后**：
- 直接调用 browser 工具（不依赖 CLI）
- 添加同花顺问财 URL 配置
- 支持指定数量（默认 20）

**代码改动**：
```python
# browser_popularity.py
def fetch_popularity_ranking(limit: int = 20) -> List[Dict]:
    """获取人气排名（优化版）"""
    # 1. 使用 browser 工具直接获取
    url = "https://www.iwencai.com/unifiedwap/result?w=个股人气排名"
    
    # 2. 解析 snapshot
    stocks = parse_snapshot_to_stocks(snapshot_text, limit=limit)
    
    # 3. 返回带人气值的数据
    return stocks
```

### 4. 数据源配置优化

**新增配置文件**：
```python
# config/data_sources_v2.py
DATA_SOURCE_PRIORITY = {
    "index": {
        "primary": "cn-stock-volume/fetch_data.py",
        "fallback": ["akshare", "web_fetch"],
    },
    "gainers": {
        "primary": "browser/iwencai",
        "fallback": ["akshare", "web_fetch"],
    },
    "themes": {
        "primary": "ths-stock-themes/fetch_themes.py",
        "fallback": ["browser/10jqka"],
    },
    "popularity": {
        "primary": "browser/iwencai",
        "fallback": ["cache"],
    },
}
```

## 实施步骤

1. **[ ] 更新 generate_report.py**
   - 添加 `--date` 参数支持
   - 优化 step1_fetch_index_data()
   - 添加非交易日处理

2. **[ ] 优化 browser_popularity.py**
   - 移除 openclaw CLI 依赖
   - 直接使用 browser 工具
   - 添加错误处理

3. **[ ] 更新 config/data_sources.py**
   - 添加数据源优先级配置 v2
   - 添加 fallback 逻辑

4. **[ ] 测试验证**
   - 测试今日报告生成
   - 测试指定日期报告生成
   - 测试非交易日处理
   - 测试数据源 fallback

## 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 指数数据成功率 | ~70% | ~95% |
| 人气热度成功率 | ~50% | ~85% |
| 指定日期支持 | ❌ | ✅ |
| 非交易日处理 | ❌ | ✅ |
| 数据源 fallback | 单一 | 多级 |

## 时间估算

- 代码修改：30 分钟
- 测试验证：20 分钟
- 文档更新：10 分钟
- **总计**：约 1 小时
