# A 股股票分析 Skill 集合

这是一个 OpenClaw Skill 集合仓库，包含多个 A 股股票分析相关的技能。

## 📦 包含的 Skills

| Skill 名称 | 描述 | ClawHub Slug |
|-----------|------|-------------|
| **cn-stock-volume** | 获取 A 股四市（沪市/深市/创业板/北交所）成交金额、增缩量及比例 | `cn-stock-volume` |
| **stock-theme-events** | 股票题材事件分析 | `stock-theme-events` |
| **stock-top-gainers** | 获取 A 股近 10 日涨幅排名前 20 股票 | `stock-top-gainers` |
| **ths-stock-themes** | 获取同花顺个股题材/概念板块和人气排名 | `ths-stock-themes` |

## 🚀 快速安装

```bash
# 安装单个 skill
npx clawhub@latest install cn-stock-volume
npx clawhub@latest install stock-theme-events
npx clawhub@latest install stock-top-gainers
npx clawhub@latest install ths-stock-themes
```

## 📁 目录结构

```
cn-stock-volume/           # 仓库根目录
├── COLLECTION.md          # 本文件（集合说明）
├── cn-stock-volume/       # 成交金额分析 skill
│   ├── SKILL.md
│   ├── scripts/
│   └── ...
├── stock-theme-events/    # 题材事件分析 skill
│   ├── SKILL.md
│   ├── scripts/
│   └── ...
├── stock-top-gainers/     # 涨幅排名 skill
│   ├── SKILL.md
│   └── ...
└── ths-stock-themes/      # 同花顺题材 skill
    ├── SKILL.md
    ├── scripts/
    └── ...
```

## 🛠️ 发布更新

使用 `skill-publish-tool` 发布单个 skill 的更新：

```bash
# 安装发布工具
npx clawhub@latest install skill-publish-tool

# 发布 skill 更新
python3 ~/.jvs/.openclaw/workspace/skills/skill-publish-tool/scripts/publish_skill.py \
  ~/.jvs/.openclaw/workspace/skills/cn-stock-volume/cn-stock-volume \
  --slug cn-stock-volume \
  --changelog "修复 XX 问题" \
  --bump patch
```

## 📊 使用示例

### 1. 查询昨日成交数据

```bash
python3 scripts/fetch_volume.py 2026-03-20
```

### 2. 获取近 10 日涨幅排名

```bash
python3 stock-top-gainers/scripts/fetch_gainers.py
```

### 3. 查询个股题材

```bash
python3 ths-stock-themes/scripts/fetch_themes.py --stock 000001
```

### 4. 分析题材事件

```bash
python3 stock-theme-events/scripts/analyze_events.py
```

## 📝 更新日志

### 2026-03-21
- 创建 skill 集合仓库
- 整合 4 个股票分析 skill

## 🔗 相关链接

- **GitHub**: https://github.com/shinelp100/cn-stock-volume
- **ClawHub**: https://clawhub.ai

## 📄 许可证

MIT License
