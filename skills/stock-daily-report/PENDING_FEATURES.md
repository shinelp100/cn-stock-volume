# stock-daily-report v2.1 待完善功能

**更新时间**：2026-03-28 09:43

---

## 📋 待完善功能清单

| 优先级 | 功能 | 状态 | 问题描述 | 影响范围 |
|--------|------|------|----------|----------|
| 🔴 P0 | 模板变量替换 | ⚠️ 部分完成 | 模板变量未被正确替换 | 报告内容 |
| 🔴 P0 | 人气热度获取 | ⚠️ 部分完成 | browser 模块导入失败 | 涨幅排名表格 |
| 🟡 P1 | 题材概念获取 | ⚠️ 部分完成 | 需要 browser 工具 | 题材方向章节 |
| 🟡 P1 | stock-theme-events 集成 | ❌ 未开始 | 真实行业逻辑缺失 | 行业逻辑准确性 |
| 🟢 P2 | 数据缓存机制 | ❌ 未开始 | 重复获取相同数据 | 性能 |

---

## 🔍 问题检测

### 问题 1：模板变量替换失败

**现象**：
```markdown
**日期：{date}**
- 上证指数：{index.shanghai.close} 点
```

**原因分析**：
- `_generate_report_content()` 使用了错误的模板格式
- 模板变量格式与数据填充方式不匹配

**检测方法**：
```bash
python3 scripts/generate_report.py --date 2026-03-28 --test 2>&1 | grep "{date}"
```

---

### 问题 2：人气热度获取失败

**错误信息**：
```
⚠️  fetch_popularity_ranking 失败：No module named 'browser'
⚠️  fetch_realtime_gainers 失败：Expecting value: line 1 column 1 (char 0)
```

**原因分析**：
- `browser_popularity.py` 依赖 `browser` 模块，但该模块只在 OpenClaw 会话中可用
- `fetch_realtime_gainers.py` 输出格式不正确

**检测方法**：
```bash
python3 -c "from scripts.browser_popularity import fetch_popularity_ranking; print(fetch_popularity_ranking())"
```

---

### 问题 3：题材概念获取不完整

**现象**：
- 题材方向章节使用默认模板
- 没有基于真实股票数据生成

**原因分析**：
- `ths-stock-themes/fetch_themes.py` 需要 browser 工具
- 数据格式与报告生成器不匹配

---

## 💡 解决方案设计

### 方案 1：模板变量替换修复

**目标**：使用正确的模板引擎替换变量

**选项**：
1. **Python str.format()** - 简单直接，无需额外依赖
2. **Jinja2 模板** - 功能强大，需要安装
3. **f-string + dict** - 灵活但代码复杂

**推荐**：选项 1（str.format()）
- 无需额外依赖
- 与现有代码兼容
- 性能良好

**实现**：
```python
def _generate_report_content(self) -> str:
    """生成报告内容（修复版）"""
    template = self._load_template()
    
    # 准备数据字典
    data = {
        'date': self.date,
        'index': self.index_data,
        'gainers': self._prepare_gainers_data(),
        'themes': self._prepare_themes_data(),
        ...
    }
    
    # 使用 str.format() 替换
    content = template.format(**data)
    return content
```

---

### 方案 2：人气热度获取优化

**目标**：不依赖 browser 模块，直接获取人气数据

**选项**：
1. **web_fetch + 解析** - 使用 web_fetch 工具获取网页内容
2. **akshare 接口** - 使用 akshare 的人气排名接口
3. **缓存数据** - 使用缓存的人气排名数据

**推荐**：选项 1 + 选项 3（组合方案）
- web_fetch 获取实时数据
- 缓存作为 fallback

**实现**：
```python
def fetch_popularity_ranking(limit: int = 20) -> List[Dict]:
    """获取人气排名（优化版）"""
    # 尝试 web_fetch
    try:
        url = "https://www.iwencai.com/unifiedwap/result?w=个股人气排名"
        result = subprocess.run(
            ["openclaw", "web-fetch", url, "--extract-mode", "text"],
            capture_output=True, text=True, timeout=15
        )
        stocks = parse_popularity_snapshot(result.stdout, limit=limit)
        if stocks:
            return stocks
    except Exception as e:
        log(f"web_fetch 失败：{e}", "warning")
    
    # Fallback：使用缓存数据
    return load_cached_popularity(limit=limit)
```

---

### 方案 3：题材概念获取优化

**目标**：获取真实的题材概念数据

**选项**：
1. **web_fetch + 解析** - 获取同花顺个股页面
2. **akshare 接口** - 使用 akshare 的题材接口
3. **人工整理** - 基于股票名称推断

**推荐**：选项 3（短期）+ 选项 1（长期）
- 短期：基于股票名称/代码推断题材
- 长期：集成 web_fetch 获取真实数据

**实现**：
```python
def fetch_themes_simple(stock_codes: List[str]) -> Dict:
    """获取题材概念（简化版）"""
    themes = {}
    for code in stock_codes:
        # 基于行业/名称推断
        if '600' in code or '601' in code:
            themes[code] = ['主板', '传统行业']
        elif '300' in code or '301' in code:
            themes[code] = ['创业板', '成长股']
        elif '688' in code:
            themes[code] = ['科创板', '硬科技']
    return themes
```

---

## 📝 实施计划

### 第一阶段：修复模板变量（P0，1 小时）

1. 修改 `_generate_report_content()` 方法
2. 准备完整的数据字典
3. 测试所有变量替换

### 第二阶段：优化人气热度（P0，2 小时）

1. 修改 `browser_popularity.py`
2. 添加 web_fetch 支持
3. 添加缓存 fallback

### 第三阶段：优化题材概念（P1，2 小时）

1. 实现简化版题材获取
2. 基于股票信息推断题材
3. 测试题材分类准确性

### 第四阶段：集成 stock-theme-events（P1，3 小时）

1. 调用 stock-theme-events 获取行业逻辑
2. 集成到报告生成流程
3. 测试行业逻辑准确性

---

## ✅ 验收标准

### 模板变量替换

- [ ] 所有 `{date}` 变量被正确替换
- [ ] 所有 `{index.*}` 变量被正确替换
- [ ] 所有 `{gainers.*}` 变量被正确替换
- [ ] 报告内容完整可读

### 人气热度获取

- [ ] 不依赖 browser 模块
- [ ] 能获取实时人气数据
- [ ] fallback 机制正常
- [ ] 涨幅排名表格完整

### 题材概念获取

- [ ] 题材方向章节有真实数据
- [ ] 行业逻辑准确
- [ ] 重点个股正确

---

**下一步**：开始第一阶段实施（模板变量修复）
