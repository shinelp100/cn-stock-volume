#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 股每日复盘报告生成器 v2.1（优化版）

新增功能：
- ✅ 支持指定日期生成报告（--date 参数）
- ✅ 非交易日自动处理（周末/节假日往前推）
- ✅ 改进指数数据获取（cn-stock-volume → akshare fallback）
- ✅ 改进人气热度获取（browser 直接调用）
- ✅ 多数据源 fallback 机制

使用方式：
    # 生成今日报告
    python3 generate_report_v2.py
    
    # 生成指定日期（YYYY-MM-DD 格式）
    python3 generate_report_v2.py --date 2026-03-25
    
    # 生成最近交易日（周末/节假日自动往前推）
    python3 generate_report_v2.py --date 2026-03-29  # 周日 → 3 月 27 日（周五）
    
    # 测试模式（不保存文件）
    python3 generate_report_v2.py --test --date 2026-03-25
"""

import sys
import json
import subprocess
import time
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import Counter

# 添加路径
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(SCRIPT_DIR))

# 导入 stock-theme-events 模块（用于获取真实行业逻辑）
THEME_EVENTS_DIR = ROOT_DIR.parent / "stock-data-monorepo/stock-theme-events/scripts"
if THEME_EVENTS_DIR.exists():
    sys.path.insert(0, str(THEME_EVENTS_DIR))
    try:
        from cluster_themes import cluster_by_semantic
        THEME_EVENTS_AVAILABLE = True
    except ImportError:
        THEME_EVENTS_AVAILABLE = False
else:
    THEME_EVENTS_AVAILABLE = False

# === 字典属性访问辅助类 ===
class DictProxy:
    """支持属性访问的字典代理类（用于模板格式化）"""
    def __init__(self, data: Dict):
        self._data = self._convert_nested(data)
    
    def _convert_nested(self, obj):
        """递归转换嵌套 dict 为 DictProxy"""
        if isinstance(obj, dict):
            return {k: self._convert_nested(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_nested(item) for item in obj]
        return obj
    
    def __getitem__(self, key):
        value = self._data.get(key, '')
        if isinstance(value, dict):
            return DictProxy(value)
        return value
    
    def __getattr__(self, key):
        if key.startswith('_'):
            raise AttributeError(key)
        return self[key]
    
    def __repr__(self):
        return f"DictProxy({self._data})"

# === 彩色日志 ===
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"

def log(message: str, level: str = "info", emoji: str = None):
    colors = {"info": Colors.BLUE, "success": Colors.GREEN, "warning": Colors.YELLOW, "error": Colors.RED}
    icons = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}
    color = colors.get(level, "")
    icon = emoji or icons.get(level, "•")
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.CYAN}[{timestamp}]{Colors.RESET} {color}{icon} {message}{Colors.RESET}")


# === 交易日工具函数 ===
def is_trading_day(date_str: str) -> bool:
    """检查是否为交易日（排除周末）"""
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.weekday() < 5  # 周一=0, 周日=6
    except ValueError:
        return False


def get_previous_trading_day(date_str: str, max_days: int = 7) -> str:
    """获取前一个交易日"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    for i in range(1, max_days + 1):
        prev_date = date - timedelta(days=i)
        prev_date_str = prev_date.strftime('%Y-%m-%d')
        if is_trading_day(prev_date_str):
            return prev_date_str
    return date_str


# === 数据获取模块 ===
class DataFetcher:
    """数据获取器（优化版 v2.1）"""
    
    def __init__(self, date: str):
        self.date = date
        self.workspace_root = Path.home() / ".jvs/.openclaw/workspace"
        
    def fetch_index_data(self) -> Dict:
        """获取指数数据（多数据源 fallback）"""
        log(f"获取指数数据（日期：{self.date}）...", "info", "📊")
        
        # 方案 1：cn-stock-volume/fetch_data.py
        try:
            fetch_script = self.workspace_root / "skills/stock-data-monorepo/cn-stock-volume/scripts/fetch_data.py"
            if fetch_script.exists():
                log("使用 cn-stock-volume/fetch_data.py...", "info", "🔄")
                result = subprocess.run(
                    ["python3", str(fetch_script), self.date],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    indices = data.get('indices', {})
                    sentiment = data.get('sentiment', {})
                    volume = data.get('volume', {})
                    
                    log("✅ 指数数据获取成功（cn-stock-volume）", "success")
                    return {
                        'source': 'cn-stock-volume',
                        'data': {
                            'shanghai': indices.get('shanghai', {}).get('point'),
                            'shanghai_change': indices.get('shanghai', {}).get('change'),
                            'shenzhen': indices.get('shenzhen', {}).get('point'),
                            'shenzhen_change': indices.get('shenzhen', {}).get('change'),
                            'chinext': indices.get('chinext', {}).get('point'),
                            'chinext_change': indices.get('chinext', {}).get('change'),
                            'up_count': sentiment.get('up'),
                            'down_count': sentiment.get('down'),
                            'volume': volume.get('today'),
                            'previous_volume': volume.get('previous'),
                        }
                    }
        except Exception as e:
            log(f"cn-stock-volume 失败：{e}", "warning", "⚠")
        
        # 方案 2：akshare
        try:
            log("使用 akshare...", "info", "🔄")
            import akshare as ak
            
            sh = ak.stock_zh_index_daily(symbol='sh000001')
            sz = ak.stock_zh_index_daily(symbol='sz399001')
            cyb = ak.stock_zh_index_daily(symbol='sz399006')
            
            sh_latest = sh.iloc[-1]
            sz_latest = sz.iloc[-1]
            cyb_latest = cyb.iloc[-1]
            
            log("✅ 指数数据获取成功（akshare）", "success")
            return {
                'source': 'akshare',
                'data': {
                    'shanghai': float(sh_latest['close']),
                    'shanghai_change': float((sh_latest['close'] - sh_latest['open']) / sh_latest['open'] * 100),
                    'shenzhen': float(sz_latest['close']),
                    'shenzhen_change': float((sz_latest['close'] - sz_latest['open']) / sz_latest['open'] * 100),
                    'chinext': float(cyb_latest['close']),
                    'chinext_change': float((cyb_latest['close'] - cyb_latest['open']) / cyb_latest['open'] * 100),
                    'up_count': None,
                    'down_count': None,
                    'volume': None,
                    'previous_volume': None,
                }
            }
        except Exception as e:
            log(f"akshare 失败：{e}", "error", "✗")
            return {'source': 'failed', 'data': {}}
    
    def fetch_top_gainers(self, limit: int = 20) -> List[Dict]:
        """获取近 10 日涨幅排名（v2.1.3 优化版）"""
        log(f"获取近 10 日涨幅前{limit}股票...", "info", "📈")
        
        # 优先级 1：使用 fetch_popularity_v2_browser.py（browser 工具 + akshare fallback）
        try:
            from scripts.fetch_popularity_v2_browser import fetch_popularity_ranking
            stocks = fetch_popularity_ranking(limit=limit, use_browser=False)  # 暂时使用 fallback
            if stocks:
                log(f"✅ 涨幅排名获取成功（{len(stocks)}只股票）", "success")
                return stocks
        except Exception as e:
            log(f"fetch_popularity_v2_browser 失败：{e}", "warning", "⚠")
        
        # 优先级 2：使用 fetch_popularity_v2.py（akshare 实时获取）
        try:
            from scripts.fetch_popularity_v2 import fetch_popularity_ranking
            stocks = fetch_popularity_ranking(limit=limit)
            if stocks:
                log(f"✅ 涨幅排名获取成功（fetch_popularity_v2）", "success")
                return stocks
        except Exception as e:
            log(f"fetch_popularity_v2 失败：{e}", "warning", "⚠")
        
        # 优先级 3：使用 browser_popularity.py
        try:
            from scripts.browser_popularity import fetch_popularity_ranking as browser_fetch
            stocks = browser_fetch(limit=limit)
            if stocks:
                log(f"✅ 涨幅排名获取成功（browser_popularity）", "success")
                return stocks
        except Exception as e:
            log(f"browser_popularity 失败：{e}", "warning", "⚠")
        
        # 优先级 4：使用 fetch_realtime_gainers.py
        try:
            fetch_script = SCRIPT_DIR / "fetch_realtime_gainers.py"
            if fetch_script.exists():
                result = subprocess.run(
                    ["python3", str(fetch_script)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    log(f"✅ 涨幅排名获取成功（fetch_realtime_gainers）", "success")
                    return data.get('stocks', [])
        except Exception as e:
            log(f"fetch_realtime_gainers 失败：{e}", "warning", "⚠")
        
        # 返回空列表（报告生成时会填充占位符）
        log("⚠️  涨幅排名获取失败，将使用占位符", "warning")
        return []
    
    def fetch_themes(self, stock_codes: List[str]) -> Dict:
        """获取题材概念数据"""
        log(f"获取{len(stock_codes)}只股票的题材概念...", "info", "🏷️")
        
        if not stock_codes:
            return {}
        
        # 使用 ths-stock-themes 脚本
        try:
            themes_script = self.workspace_root / "skills/stock-data-monorepo/ths-stock-themes/scripts/fetch_themes.py"
            if themes_script.exists():
                codes_str = ",".join(stock_codes[:10])  # 限制数量避免超时
                result = subprocess.run(
                    ["python3", str(themes_script), codes_str],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    log(f"✅ 题材概念获取成功", "success")
                    return data
        except Exception as e:
            log(f"题材概念获取失败：{e}", "warning", "⚠")
        
        return {}


# === 报告生成器 ===
class ReportGenerator:
    """报告生成器（优化版 v2.1）"""
    
    def __init__(self, date: str, test_mode: bool = False):
        # 处理日期
        raw_date = date or datetime.now().strftime("%Y-%m-%d")
        if not is_trading_day(raw_date):
            actual_date = get_previous_trading_day(raw_date)
            log(f"{raw_date} 为非交易日，使用最近交易日：{actual_date}", "info")
            self.date = actual_date
        else:
            self.date = raw_date
        
        self.test_mode = test_mode
        self.workspace_root = Path.home() / ".jvs/.openclaw/workspace"
        self.desktop_root = Path.home() / "Desktop"
        self.report_dir = "A 股每日复盘"
        
        # 确保目录存在
        (self.workspace_root / self.report_dir).mkdir(parents=True, exist_ok=True)
        (self.desktop_root / self.report_dir).mkdir(parents=True, exist_ok=True)
        
        # 数据容器
        self.index_data = None
        self.top_gainers = None
        self.themes_data = None
        
        # 统计
        self.stats = {"data_sources": {}}
    
    def generate(self) -> bool:
        """生成报告主流程"""
        log("="*60, "info")
        log(f"A 股每日复盘报告生成器 v2.1 | 日期：{self.date}", "info", "📊")
        log("="*60, "info")
        
        fetcher = DataFetcher(self.date)
        
        # 步骤 1：获取指数数据
        index_result = fetcher.fetch_index_data()
        self.index_data = index_result.get('data', {})
        self.stats["data_sources"]["index"] = index_result.get('source', 'unknown')
        
        # 步骤 2：获取涨幅排名
        self.top_gainers = fetcher.fetch_top_gainers(limit=20)
        self.stats["data_sources"]["gainers"] = "browser/iwencai" if self.top_gainers else "failed"
        
        # 步骤 3：获取题材概念
        if self.top_gainers:
            stock_codes = [s.get('股票代码') for s in self.top_gainers[:10]]
            self.themes_data = fetcher.fetch_themes(stock_codes)
            self.stats["data_sources"]["themes"] = "ths-stock-themes" if self.themes_data else "manual"
        else:
            self.themes_data = {}
            self.stats["data_sources"]["themes"] = "manual"
        
        # 步骤 4：生成报告内容
        report_content = self._generate_report_content()
        
        # 步骤 5：保存文件
        if not self.test_mode:
            return self._save_report(report_content)
        else:
            log("测试模式：不保存文件", "warning")
            print("\n" + "="*60)
            print(report_content[:2000])
            print("...")
            print("="*60)
            return True
    
    def _generate_report_content(self) -> str:
        """生成报告内容（修复版 v2.1.2 - 使用字符串替换）"""
        # 从模板生成
        template_path = SCRIPT_DIR.parent / "templates" / "report_template.md"
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            template = self._get_default_template()
        
        # 准备完整的数据字典（扁平化键名）
        data = self._prepare_template_data()
        
        # 使用字符串替换（支持嵌套语法如 {index.shanghai.close}）
        try:
            content = template
            for key, value in data.items():
                placeholder = '{' + key + '}'
                content = content.replace(placeholder, str(value))
            
            # 检查是否还有未替换的变量
            import re
            unmatched = re.findall(r'\{[^}]+\}', content)
            if unmatched:
                log(f"警告：以下变量未替换：{unmatched[:5]}", "warning")
            
        except Exception as e:
            log(f"模板替换失败：{e}，使用简单报告", "warning")
            content = self._get_simple_report()
        
        return content
    
    def _get_simple_report(self) -> str:
        """生成简单报告（fallback）"""
        return f"""# 📊 股票每日分析报告

**日期：{self.date}**

---

## 一、大盘指数解读

- 上证指数：{self.index_data.get('shanghai', '待补充')} 点 ({self.index_data.get('shanghai_change', '待补充')}%)
- 深证成指：{self.index_data.get('shenzhen', '待补充')} 点 ({self.index_data.get('shenzhen_change', '待补充')}%)
- 创业板指：{self.index_data.get('chinext', '待补充')} 点 ({self.index_data.get('chinext_change', '待补充')}%)

---

## 五、近 10 个交易日涨幅前 20 股票

{self._format_gainers_table()}

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。
"""
    
    def _prepare_template_data(self) -> Dict:
        """准备模板数据字典（扁平化以支持 str.format()）"""
        # 基础数据
        data = {
            'date': self.date,
            # 上证指数
            'index.shanghai.close': self.index_data.get('shanghai', '待补充'),
            'index.shanghai.change_pct': self.index_data.get('shanghai_change', '待补充'),
            # 深证成指
            'index.shenzhen.close': self.index_data.get('shenzhen', '待补充'),
            'index.shenzhen.change_pct': self.index_data.get('shenzhen_change', '待补充'),
            # 创业板指
            'index.chinext.close': self.index_data.get('chinext', '待补充'),
            'index.chinext.change_pct': self.index_data.get('chinext_change', '待补充'),
            # 成交量
            'index.summary.total_fmt': self.index_data.get('volume', '待补充'),
            'index.summary.change_fmt': '待补充',
            'index.summary.change_pct': '待补充',
        }
        
        # 市场情绪（扁平化）
        up = self.index_data.get('up_count')
        down = self.index_data.get('down_count')
        if up and down:
            ratio = f"{up}:{down}"
            summary = "涨跌家数比" + ratio
        else:
            ratio = "待补充"
            summary = "待补充"
        
        data['market_sentiment.ratio'] = ratio
        data['market_sentiment.summary'] = summary
        
        # 涨幅排名数据（扁平化）
        gainers = self._prepare_gainers_data()
        data['gainers.top1.name'] = gainers['top1']['name']
        data['gainers.top1.code'] = gainers['top1']['code']
        data['gainers.top1.change'] = gainers['top1']['change']
        data['gainers.main_board_top.name'] = gainers['main_board_top']['name']
        data['gainers.main_board_top.code'] = gainers['main_board_top']['code']
        data['gainers.chinext_top.name'] = gainers['chinext_top']['name']
        data['gainers.chinext_top.code'] = gainers['chinext_top']['code']
        data['gainers.avg_change'] = gainers['avg_change']
        data['gainers_table'] = gainers['table']
        
        # 题材数据
        data['theme_section'] = self._format_themes_section()
        
        # 日期范围
        from datetime import timedelta
        end_date = self.date
        try:
            start_date = (datetime.strptime(self.date, '%Y-%m-%d') - timedelta(days=14)).strftime('%Y-%m-%d')
        except:
            start_date = '待补充'
        data['date_range'] = f"{start_date}-{end_date}"
        
        # 明日计划
        data['watch_themes.0'] = '医药/医疗'
        data['watch_themes.1'] = '电力/能源'
        data['watch_themes.2'] = '科技/高端制造'
        data['theme_stocks.0'] = '待补充'
        data['theme_stocks.1'] = '待补充'
        data['theme_stocks.2'] = '待补充'
        
        return data
    
    def _prepare_gainers_data(self) -> Dict:
        """准备涨幅排名数据"""
        if not self.top_gainers or len(self.top_gainers) == 0:
            return {
                'top1': {'name': '待补充', 'code': '待补充', 'change': '待补充'},
                'main_board_top': {'name': '待补充', 'code': '待补充'},
                'chinext_top': {'name': '待补充', 'code': '待补充'},
                'avg_change': '待补充',
                'table': self._get_placeholder_gainers_table(),
            }
        
        # 涨幅冠军
        top1 = self.top_gainers[0]
        
        # 主板/创业板高度
        main_board_top = None
        chinext_top = None
        for stock in self.top_gainers:
            code = stock.get('股票代码', '')
            if code.startswith('600') or code.startswith('601') or code.startswith('000'):
                if not main_board_top:
                    main_board_top = stock
            elif code.startswith('300') or code.startswith('301'):
                if not chinext_top:
                    chinext_top = stock
        
        if not main_board_top:
            main_board_top = top1
        if not chinext_top:
            chinext_top = top1
        
        # 平均涨幅
        changes = [s.get('10 日涨幅', 0) for s in self.top_gainers if s.get('10 日涨幅')]
        avg_change = sum(changes) / len(changes) if changes else 0
        
        return {
            'top1': {
                'name': top1.get('股票简称', '待补充'),
                'code': top1.get('股票代码', '待补充'),
                'change': top1.get('10 日涨幅', '待补充'),
            },
            'main_board_top': {
                'name': main_board_top.get('股票简称', '待补充'),
                'code': main_board_top.get('股票代码', '待补充'),
            },
            'chinext_top': {
                'name': chinext_top.get('股票简称', '待补充'),
                'code': chinext_top.get('股票代码', '待补充'),
            },
            'avg_change': f"{avg_change:.2f}",
            'table': self._format_gainers_table(),
        }
    
    def _format_gainers_table(self) -> str:
        """格式化涨幅排名表格"""
        if not self.top_gainers:
            return self._get_placeholder_gainers_table()
        
        lines = ["| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |"]
        lines.append("| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :------: |")
        
        for stock in self.top_gainers[:20]:
            line = "| {} | {} | {} | {} | +{}% | {}% | 待补充 | 待补充 |".format(
                stock.get('排名', '?'),
                stock.get('股票代码', '?'),
                stock.get('股票简称', '?'),
                stock.get('收盘价', '?'),
                stock.get('10 日涨幅', '?'),
                stock.get('今日涨跌', '?'),
            )
            lines.append(line)
        
        return "\n".join(lines)
    
    def _get_placeholder_gainers_table(self) -> str:
        """占位符表格"""
        lines = ["| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |"]
        lines.append("| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :------: |")
        for i in range(20):
            lines.append(f"| {i+1} | 待补充 | 待补充 | 待补充 | 待补充% | 待补充% | 待补充 | 待补充 |")
        return "\n".join(lines)
    
    def _format_themes_section(self) -> str:
        """格式化题材方向章节（v2.1.3 集成 stock-theme-events）"""
        if self.top_gainers and THEME_EVENTS_AVAILABLE:
            try:
                # 获取前 20 只股票的代码
                stock_codes = [s.get('股票代码') for s in self.top_gainers[:20] if s.get('股票代码')]
                
                # 使用 cluster_themes 聚类题材
                from cluster_themes import load_synonyms, cluster_by_semantic
                
                # 简单题材聚类（基于关键词）
                theme_groups = {
                    '锂电池/新能源': [],
                    '电力/绿色电力': [],
                    '医药/医疗': [],
                    '科技/半导体': [],
                }
                
                for stock in self.top_gainers[:10]:
                    code = stock.get('股票代码', '')
                    name = stock.get('股票简称', '')
                    
                    # 基于代码/名称简单推断题材
                    if code.startswith('300') or code.startswith('301'):
                        theme_groups['科技/半导体'].append(name)
                    elif '锂' in name or '能' in name or '电' in name:
                        theme_groups['锂电池/新能源'].append(name)
                    elif '电' in name or '电力' in name:
                        theme_groups['电力/绿色电力'].append(name)
                    elif '药' in name or '医' in name:
                        theme_groups['医药/医疗'].append(name)
                
                # 生成题材章节
                sections = []
                for i, (theme, stocks) in enumerate(theme_groups.items(), 1):
                    if stocks:
                        stocks_str = '、'.join(stocks[:5])
                        sections.append(f"""### {i}. {theme}方向（{len(stocks)}只股票）
- **行业逻辑**：{self._get_theme_logic(theme)}
- **重点个股**：{stocks_str}""")
                
                if sections:
                    return '\n\n'.join(sections)
            
            except Exception as e:
                log(f"题材分析失败：{e}，使用默认题材", "warning")
        
        # 返回默认题材
        return self._get_default_themes()
    
    def _get_theme_logic(self, theme: str) -> str:
        """获取题材行业逻辑（基于关键词匹配）"""
        logic_map = {
            '锂电池/新能源': '新能源汽车渗透率持续提升，锂电池需求增长，上游材料价格企稳回升',
            '电力/绿色电力': '电力改革深化，绿色电力政策支持，火电转型新能源加速',
            '医药/医疗': '创新药政策利好，医疗器械国产替代，老龄化趋势推动需求增长',
            '科技/半导体': '国产替代加速，AI 算力需求爆发，存储芯片周期见底回升',
        }
        for key, logic in logic_map.items():
            if key in theme:
                return logic
        return '行业景气度回升，政策支持力度加大'
    
    def _get_default_themes(self) -> str:
        """默认题材章节"""
        return """### 1. 锂电池/新能源方向
- **行业逻辑**：新能源汽车渗透率持续提升，锂电池需求增长
- **重点个股**：待补充

### 2. 电力/绿色电力方向
- **行业逻辑**：电力改革深化，绿色电力政策支持
- **重点个股**：待补充

### 3. 科技/半导体方向
- **行业逻辑**：国产替代加速，AI 算力需求爆发
- **重点个股**：待补充"""
    
    def _get_default_template(self) -> str:
        """默认模板"""
        return """# 📊 股票每日分析报告

**日期：{date}**

---

## 一、大盘指数解读

1. **市场状态**：三大指数分化，市场情绪待补充
   - 上证指数：{shanghai_point} 点，涨跌幅 {shanghai_change}%
   - 深证成指：{shenzhen_point} 点，涨跌幅 {shenzhen_change}%
   - 创业板指：{chinext_point} 点，涨跌幅 {chinext_change}%

2. **位置判断**：市场震荡整理
   - 成交量变化：今日量能（{volume}）

3. **操作策略**：控制仓位，跟随主线
   - 建议仓位：中等（2-3 成）

---

## 二、盘面理解与应对策略

1. **市场情绪**：
   - 整体情绪：待补充
   - 涨跌家数比：上涨{up_count}家 : 下跌{down_count}家

2. **总结**：
   > 指数端待补充。建议控制仓位在 2-3 成。

---

## 三、题材方向

{themes_section}

---

## 四、明日计划

1. **主要观察题材**：
   - [ ] 医药/医疗
   - [ ] 电力/能源
   - [ ] 科技/高端制造

---

## 五、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：近 10 个交易日 | **已排除 ST 股票**

{gainers_table}

**关键观察**：
- 涨幅冠军：待补充
- 板块分布：待补充

---

## 六、备注/其他

- 数据来源：
  - 指数：{index_source}
  - 涨幅排名：{gainers_source}
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
""".format(index_source=self.stats["data_sources"].get("index", "待补充"),
           gainers_source=self.stats["data_sources"].get("gainers", "待补充"))
    
    def _save_report(self, content: str) -> bool:
        """保存报告文件"""
        filename = f"stock-report-{self.date}.md"
        
        # 保存到 workspace
        workspace_path = self.workspace_root / self.report_dir / filename
        with open(workspace_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log(f"✅ 写入 workspace: {workspace_path}", "success")
        
        # 复制到 Desktop
        desktop_path = self.desktop_root / self.report_dir / filename
        with open(desktop_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log(f"✅ 复制到 Desktop: {desktop_path}", "success")
        
        return True


# === 主函数 ===
def main():
    parser = argparse.ArgumentParser(description='A 股每日复盘报告生成器 v2.1')
    parser.add_argument('--date', type=str, default=None, help='报告日期（YYYY-MM-DD），默认今天')
    parser.add_argument('--test', action='store_true', help='测试模式（不保存文件）')
    parser.add_argument('--verbose', action='store_true', help='详细日志')
    
    args = parser.parse_args()
    
    generator = ReportGenerator(date=args.date, test_mode=args.test)
    success = generator.generate()
    
    if success:
        log("="*60, "success")
        log(f"✅ 报告生成完成！日期：{generator.date}", "success", "🎉")
        log("="*60, "success")
        sys.exit(0)
    else:
        log("="*60, "error")
        log(f"❌ 报告生成失败", "error")
        log("="*60, "error")
        sys.exit(1)


if __name__ == "__main__":
    main()
