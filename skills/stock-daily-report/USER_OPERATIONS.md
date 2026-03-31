# 用户操作指南总结

## 🎯 目标

获取"二、盘面理解与应对策略"下的数据：
- ✅ 涨跌家数比
- ✅ 主板高度（10cm）冠军
- ✅ 创业板高度（20cm）冠军
- ✅ 高位股票

## 📋 用户需要做什么

### 方案 A：手动填充（推荐 - 5分钟）

**步骤 1：生成报告框架**
```bash
python3 scripts/generate_report.py 2026-03-27 --no-browser --output=~/Desktop/report.md
```

**步骤 2：打开同花顺问财**
- 涨幅榜：https://www.iwencai.com/unifiedwap/result?w=近10日涨幅排名&querytype=stock
- 涨跌家数：https://www.iwencai.com/unifiedwap/result?w=涨跌家数&querytype=stock

**步骤 3：记录数据**
| 数据项 | 来源 | 格式 |
|-------|------|------|
| 主板冠军 | 涨幅榜中第一个600/601/603 | 名称（代码）+涨幅% |
| 创业板冠军 | 涨幅榜中第一个300 | 名称（代码）+涨幅% |
| 高位股票1 | 涨幅榜中涨幅最高 | 名称 +涨幅% |
| 高位股票2 | 涨幅榜中涨幅第二高 | 名称 +涨幅% |
| 涨家数 | 涨跌家数查询 | 数字 |
| 跌家数 | 涨跌家数查询 | 数字 |

**步骤 4：编辑报告**
打开 `~/Desktop/report.md`，找到占位符并替换：

```markdown
# 查找这些占位符：
   - 涨跌家数比：（数据获取中）
  - 主板高度（10cm）：—（—）+0%，数据获取中
  - 创业板高度（20cm）：—（—）+0%，数据获取中
 - 高位股票：高位股数据获取中

# 替换为实际数据：
   - 涨跌家数比：1500(涨) : 2500(跌) ≈ 1 : 1.7（下跌家数显著多于上涨）
  - 主板高度（10cm）：华电辽能（600396）+131.70%，高位震荡继续新高，...
  - 创业板高度（20cm）：海科新源（301292）+49.33%，锂电池板块加强
 - 高位股票：普昂医疗 10 日涨幅超 136% 领涨，华电辽能 +131.70% 紧随其后，...
```

**步骤 5：保存**
✅ 完成！

---

### 方案 B：完全自动化（需要开发）

需要在 `generate_report.py` 中实现浏览器集成：

1. **启动浏览器**
   ```python
   browser action=start
   ```

2. **导航到同花顺问财**
   ```python
   browser action=act kind=evaluate fn="() => { window.location.href = 'https://www.iwencai.com/unifiedwap/result?w=近10日涨幅排名&querytype=stock'; }"
   ```

3. **获取快照**
   ```python
   browser action=snapshot
   ```

4. **解析数据**
   ```python
   from fetch_browser_data import parse_iwencai_snapshot, get_market_feedback_from_gainers
   stocks = parse_iwencai_snapshot(snapshot_html)
   feedback = get_market_feedback_from_gainers(stocks)
   ```

5. **填充报告**
   自动替换占位符

---

## 📁 相关文件

| 文件 | 用途 |
|------|------|
| `QUICK_REFERENCE.md` | 快速参考卡片（推荐用户查看） |
| `BROWSER_AUTOMATION_GUIDE.md` | 详细的浏览器自动化指南 |
| `fetch_browser_data.py` | 浏览器数据解析脚本 |
| `generate_report.py` | 主报告生成脚本 |

---

## ⏱️ 时间成本

| 方案 | 耗时 | 自动化程度 |
|------|------|----------|
| 方案 A（手动填充） | 5 分钟 | 70% |
| 方案 B（完全自动化） | 开发 2-4 小时 | 100% |

---

## 🚀 立即开始

### 快速命令

```bash
# 1. 进入目录
cd ~/.qclaw/workspace/skills/stock-daily-report

# 2. 生成报告
python3 scripts/generate_report.py 2026-03-27 --no-browser --output=~/Desktop/report.md

# 3. 打开报告
open ~/Desktop/report.md

# 4. 打开同花顺问财获取数据
open "https://www.iwencai.com/unifiedwap/result?w=近10日涨幅排名&querytype=stock"

# 5. 编辑报告，填充数据
# （使用任何文本编辑器）
```

---

## 📞 需要帮助？

- 查看 `QUICK_REFERENCE.md` 了解数据填充模板
- 查看 `BROWSER_AUTOMATION_GUIDE.md` 了解自动化方案
- 查看 `SKILL.md` 了解完整功能说明

---

## ✅ 验收标准

报告生成后，检查以下项目：

- [ ] 涨跌家数比已填充（格式：`XXXX(涨) : XXXX(跌) ≈ 1 : X.X`）
- [ ] 主板高度已填充（格式：`名称（代码）+X.XX%，...`）
- [ ] 创业板高度已填充（格式：`名称（代码）+X.XX%，...`）
- [ ] 高位股票已填充（格式：`名称1 10日涨幅超 X% 领涨，...`）
- [ ] 所有占位符已替换
- [ ] 报告可正常打开和阅读

✅ 全部完成 = 报告就绪！

