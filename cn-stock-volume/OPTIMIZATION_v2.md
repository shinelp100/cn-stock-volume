# cn-stock-volume v2.0 优化说明

**更新时间**: 2026-03-22  
**版本**: v2.0.0

---

## 🎯 优化目标

本次优化针对 `cn-stock-volume` skill 进行了全面升级，实现：

1. **自动化集成** - 自动调用 Browser 工具，无需手动操作
2. **智能缓存** - 避免重复调用 Browser，提升效率
3. **鲁棒性解析** - 支持页面结构变化，增强稳定性

---

## 🚀 新增功能

### 1. 自动化报告脚本 `generate_report.py`

**位置**: `scripts/generate_report.py`

**功能**:
- 自动调用 Browser 工具导航到东方财富网
- 自动获取 snapshot 并解析数据
- 自动降级到 API 方案（如果 Browser 失败）
- 自动生成完整报告

**用法**:
```bash
# 查询今日（自动选择最优方案）
python3 scripts/generate_report.py

# 查询指定日期
python3 scripts/generate_report.py 2026-03-21

# 强制使用 Browser（忽略缓存）
python3 scripts/generate_report.py --force-browser

# 不使用缓存，重新获取
python3 scripts/generate_report.py --no-cache

# JSON 输出（用于程序处理）
python3 scripts/generate_report.py --json
```

---

### 2. 智能缓存机制

**模块**: `scripts/cache.py`

**特性**:
- **缓存位置**: `~/.jvs/.openclaw/workspace/.cache/`
- **TTL**: 24 小时（可配置）
- **缓存键**: `browser:YYYY-MM-DD`
- **自动清理**: 过期缓存自动删除

**缓存策略**:
```
1. 检查缓存（如果启用）
   ↓ 命中
   返回缓存数据

2. 缓存未命中
   ↓
   调用 Browser 工具
   ↓
   解析数据
   ↓
   写入缓存
   ↓
   返回数据
```

**优势**:
- 避免重复调用 Browser（节省时间）
- 支持离线查询（缓存有效期内）
- 自动清理过期数据（不占用空间）

---

### 3. 鲁棒性解析（4 层策略）

**模块**: `scripts/generate_report.py` - `parse_snapshot_robust()`

**解析策略**:

| 优先级 | 策略 | 说明 | 成功率 |
|--------|------|------|--------|
| 1️⃣ | **标准解析** | 正则表达式匹配标准格式 | ⭐⭐⭐⭐ |
| 2️⃣ | **宽松解析** | 关键词 + 数字提取 | ⭐⭐⭐ |
| 3️⃣ | **表格解析** | 表格行解析（支持 \| 和制表符） | ⭐⭐ |
| 4️⃣ | **OCR 解析** | OCR 文本解析 | ⭐ |

**标准格式示例**:
```
1 000001 上证指数 3957.05 -49.50 -1.24% 6.67 亿 9648.63 亿 4006.55 4004.57 4022.70 3955.71
```

**宽松格式示例**:
```
上证指数 3957.05 (-1.24%) 成交额 9648.63 亿
```

**表格格式示例**:
```
| 上证指数 | 3957.05 | -1.24% | 9648.63 亿 |
```

**优势**:
- 支持东方财富网页面结构变化
- 即使格式改变也能成功解析
- 降低维护成本（不需要频繁更新正则）

---

### 4. 数据验证与降级

**验证项**:
1. **数据完整性** - 至少获取 3/4 个市场
2. **数值合理性** - 成交额 > 0，指数点位在 100-50000 之间
3. **API 对比** - 与 API 数据偏差不超过 50%

**降级策略**:
```
Browser 工具
    ↓ 失败
东方财富 API
    ↓ 失败
新浪财经 API
    ↓ 失败
腾讯财经 API
```

**优势**:
- 确保数据可靠性
- 即使所有方案失败也优雅降级
- 输出有意义的错误信息

---

## 📊 数据源优先级（v2.0）

| 优先级 | 数据源 | 类型 | 状态 |
|--------|--------|------|------|
| **1️⃣ 首选** | Browser 工具（东方财富网网页版） | 浏览器自动化 | ✅ |
| **2️⃣ 备用 1** | 东方财富网 K 线 API | API | ✅ |
| **3️⃣ 备用 2** | 新浪财经 API | API | ✅ |
| **4️⃣ 备用 3** | 腾讯财经 API | API | ✅ |

---

## 🔧 技术实现

### BrowserClient 类

封装 Browser 工具调用：

```python
class BrowserClient:
    def navigate_and_snapshot(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """导航到 URL 并获取 snapshot"""
    
    def is_available(self) -> bool:
        """检查 Browser 工具是否可用"""
```

### 缓存类

```python
class DataCache:
    def get(self, key: str) -> Optional[Dict]:
        """读取缓存"""
    
    def set(self, key: str, data: Dict, metadata: Optional[Dict] = None):
        """写入缓存"""
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
    
    def clear(self, older_than_hours: Optional[int] = None):
        """清理缓存"""
```

---

## 📝 使用示例

### 示例 1: 查询今日数据（自动模式）

```bash
python3 scripts/generate_report.py
```

**输出**:
```
======================================================================
  📊 cn-stock-volume 自动生成报告（优化版 v2.0）
  目标日期：2026-03-22
  选项：force_browser=False, no_cache=False, json=False
======================================================================

步骤 1: 查询成交数据...
  🌐 尝试 Browser 方案...
  ✅ Browser 成功（standard 解析）：获取到 4/4 个市场

步骤 2: 查询涨跌家数...
  📊 查询涨跌家数...

步骤 3: 生成报告...

======================================================================
  📊 中国股市成交报告（自动化版 v2.0）
  日期：2026-03-22
  数据源：browser（实时）
======================================================================

  ╔══════════════════════════════════════════════════════════╗
  ║  📋 三市合计总结（不含重复计算）                           ║
  ╠══════════════════════════════════════════════════════════╣
  ║  合计成交金额：    23030.9 亿                            ║
  ║  增缩比例    ：📈   +8.25%                            ║
  ╚══════════════════════════════════════════════════════════╝
```

### 示例 2: 查询指定日期（使用缓存）

```bash
python3 scripts/generate_report.py 2026-03-21
```

**第一次运行**:
```
步骤 1: 查询成交数据...
  🌐 尝试 Browser 方案...
  ✅ Browser 成功：获取到 4/4 个市场
```

**第二次运行（缓存命中）**:
```
步骤 1: 查询成交数据...
  💾 命中缓存（2026-03-21）
```

### 示例 3: 强制使用 Browser

```bash
python3 scripts/generate_report.py --force-browser
```

**输出**:
```
步骤 1: 查询成交数据...
  🌐 使用 Browser 方案（强制模式）...
  ✅ Browser 成功：获取到 4/4 个市场
```

### 示例 4: JSON 输出

```bash
python3 scripts/generate_report.py --json
```

**输出**:
```json
{
  "target_date": "2026-03-22",
  "volume_data": {
    "status": "ok",
    "data": {
      "沪市": {"amount": 964863000000, "close": 3957.05, ...},
      "深市": {"amount": 13200000000000, "close": 13866.20, ...},
      ...
    },
    "source": "browser",
    "cache_hit": false
  },
  "advance_decline": {...},
  "generated_at": "2026-03-22T10:45:00"
}
```

---

## ⚠️ 注意事项

1. **Browser 工具依赖**: `generate_report.py` 需要 `browser` 工具可用
2. **缓存位置**: `~/.jvs/.openclaw/workspace/.cache/`，定期清理
3. **网络要求**: 需要访问东方财富网（`https://quote.eastmoney.com/center/hszs.html`）
4. **超时设置**: Browser 操作超时 30 秒（可配置）

---

## 🔄 版本历史

### v2.0.0 (2026-03-22)
- 🤖 新增 `generate_report.py` 自动化脚本
- 💾 智能缓存机制（TTL=24 小时）
- 🔧 4 层鲁棒性解析（标准→宽松→表格→OCR）
- 📊 数据源优先级调整：Browser 首选 → API 降级
- ✅ 数据验证：完整性、合理性、API 对比

### v1.2.2 (2026-03-21)
- 修复非交易日数据处理逻辑

---

## 📞 问题反馈

- GitHub: https://github.com/shinelp100/cn-stock-volume/issues
- ClawHub: https://clawhub.ai/k97ekrd0xh6t7z33p4523psahd83czv7/cn-stock-volume
