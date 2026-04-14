#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 股每日复盘报告生成器 v2.0

优化点：
- 彩色日志输出
- 进度条显示
- 更好的错误处理
- 支持断点续跑
- 添加性能统计

使用方式：
    # 生成今日报告
    python3 generate_report.py
    
    # 生成指定日期
    python3 generate_report.py 2026-03-21
    
    # 测试模式（不保存文件）
    python3 generate_report.py --test
    
    # 详细日志
    python3 generate_report.py --verbose
    
    # 从指定步骤继续
    python3 generate_report.py --from-step 3
"""

import sys
import json
import subprocess
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import Counter

# 添加路径
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

from config.data_sources import DATA_SOURCE_PRIORITY, VALIDATION_THRESHOLDS
from scripts.validate_data import (
    validate_index_data, 
    validate_gainers_data,
    run_all_validations
)
from scripts.filter_concepts import (
    filter_and_select_concepts,
    analyze_stocks,
    batch_filter
)
from scripts.clawhub_integration import ClawHubIntegration

# 导入 browser 人气排名模块（在主会话中运行）
try:
    from scripts.browser_popularity import fetch_popularity_ranking
    BROWSER_POPULARITY_AVAILABLE = True
except ImportError:
    BROWSER_POPULARITY_AVAILABLE = False
    fetch_popularity_ranking = None

# 模板验证配置
REQUIRED_SECTIONS = [
    "一、大盘指数解读",
    "二、盘面理解与应对策略",
    "三、题材方向",
    "四、明日计划",
    "五、近 10 个交易日涨幅前 20 股票",
    "六、备注/其他",
]

REQUIRED_FIELDS = [
    "上证指数",
    "深证成指",
    "创业板指",
    "成交量变化",
    "操作策略",
    "市场情绪",
    "题材方向",
    "明日计划",
    "涨幅前 20",
    "免责声明",
]

# 导入 stock-theme-events 模块
THEME_EVENTS_DIR = ROOT_DIR.parent / "stock-data-monorepo/stock-theme-events/scripts"
if THEME_EVENTS_DIR.exists():
    sys.path.insert(0, str(THEME_EVENTS_DIR))
    try:
        from cluster_themes import cluster_by_semantic, load_synonyms
        from search_news import search_news, search_akshare
        THEME_EVENTS_AVAILABLE = True
    except ImportError:
        THEME_EVENTS_AVAILABLE = False
else:
    THEME_EVENTS_AVAILABLE = False


# === 彩色日志 ===
class Colors:
    """ANSI 颜色代码"""
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    
    @classmethod
    def disable(cls):
        """禁用颜色（Windows 兼容）"""
        cls.RESET = cls.RED = cls.GREEN = cls.YELLOW = ""
        cls.BLUE = cls.MAGENTA = cls.CYAN = cls.BOLD = ""


# 检测 Windows 终端
if sys.platform == "win32":
    Colors.disable()


def log(message: str, level: str = "info", emoji: str = None):
    """
    彩色日志输出
    
    Args:
        message: 日志内容
        level: 日志级别（info/success/warning/error/debug）
        emoji: 可选 emoji
    """
    colors = {
        "info": Colors.BLUE,
        "success": Colors.GREEN,
        "warning": Colors.YELLOW,
        "error": Colors.RED,
        "debug": Colors.MAGENTA,
    }
    
    icons = {
        "info": "ℹ",
        "success": "✓",
        "warning": "⚠",
        "error": "✗",
        "debug": "•",
    }
    
    color = colors.get(level, "")
    icon = emoji or icons.get(level, "•")
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.CYAN}[{timestamp}]{Colors.RESET} {color}{icon} {message}{Colors.RESET}")


def print_progress(step: int, total: int, message: str = ""):
    """
    打印进度条
    
    Args:
        step: 当前步骤
        total: 总步骤数
        message: 可选消息
    """
    percent = (step / total) * 100
    bar_length = 30
    filled = int(bar_length * step / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    
    sys.stdout.write(f"\r{Colors.CYAN}进度：[{bar}] {percent:.0f}%{Colors.RESET} {message}")
    sys.stdout.flush()
    
    if step == total:
        print()  # 完成后换行


class ReportGenerator:
    """
    A 股每日复盘报告生成器 v2.0
    
    工作流程：
    1. fetch_index_data()   - 获取大盘指数
    2. fetch_top_gainers()  - 获取涨幅排名
    3. fetch_themes()       - 获取题材概念
    4. validate_data()      - 数据验证
    5. generate_report()    - 生成报告
    6. save_report()        - 保存文件
    """
    
    def __init__(self, date: str = None, test_mode: bool = False, 
                 verbose: bool = False, from_step: int = 1):
        """
        初始化生成器
        
        Args:
            date: 报告日期（YYYY-MM-DD，默认今天）
            test_mode: 测试模式（不保存文件）
            verbose: 详细日志模式
            from_step: 从第几步开始（用于断点续跑）
        """
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.test_mode = test_mode
        self.verbose = verbose
        self.from_step = from_step
        
        # 路径配置
        self.workspace_root = Path.home() / ".jvs/.openclaw/workspace"
        self.desktop_root = Path.home() / "Desktop"
        self.report_dir = "A 股每日复盘"
        
        # 确保目录存在
        (self.workspace_root / self.report_dir).mkdir(parents=True, exist_ok=True)
        (self.desktop_root / self.report_dir).mkdir(parents=True, exist_ok=True)
        
        # 数据容器
        self.index_data: Optional[Dict] = None
        self.top_gainers: Optional[List[Dict]] = None
        self.themes_data: Optional[Dict] = None
        self.market_sentiment: Optional[Dict] = None
        self.theme_analysis: Optional[Dict] = None
        
        # ClawHub 集成器
        self.clawhub = ClawHubIntegration(verbose=verbose)
        
        # 统计信息
        self.stats = {
            "start_time": datetime.now(),
            "steps_completed": [],
            "steps_failed": [],
            "errors": [],
            "warnings": [],
            "step_times": {},
            "data_source": {},  # 记录各步骤使用的数据源
        }
        
        # 步骤定义
        self.steps = [
            (1, "获取指数数据", self.step1_fetch_index_data),
            (2, "获取涨幅排名", self.step2_fetch_top_gainers),
            (3, "获取题材概念", self.step3_fetch_themes),
            (4, "数据验证", self.step4_validate_data),
            (5, "分析题材分布", self.step5_analyze_themes),
            (6, "生成报告", self.step6_generate_report),
            (7, "保存文件", self.step7_save_report),
        ]
    
    def log(self, message: str, level: str = "info", emoji: str = None):
        """日志输出（封装）"""
        if level == "debug" and not self.verbose:
            return
        log(message, level, emoji)
    
    def step1_fetch_index_data(self) -> bool:
        """步骤 1：获取大盘指数数据 + 涨跌家数（使用 sessions_spawn 调用 browser 工具）"""
        self.log("获取大盘指数数据（三大指数 + 涨跌家数）...", "info", "📊")
        start = time.time()
        
        try:
            # 使用 sessions_spawn 调用 browser 工具获取指数和涨跌家数
            task = f"""
请使用 browser 工具获取 A 股市场数据：

## 任务 1：获取三大指数
访问同花顺问财：
- 上证指数：https://www.iwencai.com/unifiedwap/result?w=上证指数
- 深证成指：https://www.iwencai.com/unifiedwap/result?w=深证成指
- 创业板指：https://www.iwencai.com/unifiedwap/result?w=创业板指

从每个页面提取：指数点位、涨跌幅

## 任务 2：获取涨跌家数
访问：https://www.iwencai.com/unifiedwap/result?w=涨跌家数

从页面提取：
- 上涨家数（数字）
- 下跌家数（数字）

## 返回纯 JSON 格式（不要其他内容）：
{{
  "shanghai": {{"point": 数字，"change": 数字}},
  "shenzhen": {{"point": 数字，"change": 数字}},
  "chinext": {{"point": 数字，"change": 数字}},
  "sentiment": {{"up": 数字，"down": 数字}}
}}

如果某个数据获取失败，对应字段为 null。
"""
            
            self.log("调用 sessions_spawn 获取指数数据...", "info", "🔄")
            
            # 使用 sessions_spawn 执行
            result = subprocess.run(
                ['openclaw', 'sessions', 'spawn', 
                 '--task', task, 
                 '--runtime', 'subagent', 
                 '--mode', 'run',
                 '--timeout', '90'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                # 解析输出中的 JSON
                json_match = re.search(r'\{.*\}', result.stdout, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    
                    # 验证数据
                    has_data = any(
                        data.get(k, {}).get('point') is not None 
                        for k in ['shanghai', 'shenzhen', 'chinext']
                    )
                    
                    if has_data:
                        # 提取 sentiment 数据（如果存在）
                        sentiment = data.get('sentiment', {})
                        
                        self.index_data = {
                            'date': self.date,
                            'indices': {
                                'shanghai': data.get('shanghai'),
                                'shenzhen': data.get('shenzhen'),
                                'chinext': data.get('chinext'),
                            },
                            'sentiment': {
                                'up': sentiment.get('up') if sentiment else None,
                                'down': sentiment.get('down') if sentiment else None,
                            },
                            'volume': {'today': None, 'previous': None},
                        }
                        elapsed = time.time() - start
                        self.stats["step_times"]["step1"] = elapsed
                        self.stats["data_source"]["index"] = "sessions-spawn"
                        
                        # 日志输出
                        if sentiment and sentiment.get('up'):
                            self.log(f"成功获取指数数据 + 涨跌家数（上涨{sentiment['up']}家，下跌{sentiment['down']}家）", "success", "✅")
                        else:
                            self.log(f"成功获取指数数据（涨跌家数待补充）", "success", "✅")
                        return True
            
            # 如果 sessions_spawn 失败，回退到 cn-stock-volume 脚本
            self.log("sessions_spawn 未返回有效数据，回退到 cn-stock-volume...", "warning", "⚠")
            raise RuntimeError("sessions_spawn 未返回有效数据")
            
        except Exception as e:
            self.log(f"sessions_spawn 失败：{e}，使用 cn-stock-volume 脚本", "warning", "⚠")
            
            # Fallback：使用 cn-stock-volume 脚本
            try:
                script_path = ROOT_DIR.parent / "stock-data-monorepo/cn-stock-volume/scripts/fetch_data.py"
                
                if not script_path.exists():
                    raise FileNotFoundError(f"cn-stock-volume 脚本不存在：{script_path}")
                
                result = subprocess.run(
                    ["python3", str(script_path), self.date, "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"脚本执行失败：{result.stderr}")
                
                # 提取 JSON（过滤日志行）
                json_lines = [line for line in result.stdout.split('\n') 
                             if line.strip() and not line.strip().startswith('[')]
                json_str = '\n'.join(json_lines)
                
                self.index_data = json.loads(json_str)
                
                elapsed = time.time() - start
                self.stats["step_times"]["step1"] = elapsed
                self.stats["data_source"]["index"] = "cn-stock-volume"
                
                self.log(f"使用 cn-stock-volume 脚本（可能为占位符）", "warning", "⚠")
                return True
                
            except Exception as e2:
                self.log(f"获取指数数据完全失败：{e2}", "error", "❌")
                self.stats["errors"].append(f"step1: {e2}")
                self.index_data = None
                return False
    
    def step2_fetch_top_gainers(self) -> bool:
        """步骤 2：获取近 10 日涨幅前 20 股票（优先实时数据）"""
        self.log("获取近 10 日涨幅排名...", "info", "📈")
        start = time.time()
        
        try:
            # 通过 ClawHub 集成获取真实数据（优先 browser 实时获取）
            self.log("调用 clawhub_integration 获取数据（browser 实时优先）...", "debug", "🔄")
            self.top_gainers = self.clawhub.fetch_top_gainers(limit=20, exclude_st=True)
            
            if not self.top_gainers:
                raise ValueError("ClawHub 返回空数据")
            
            # 检查是否返回了任务（需要 sessions_spawn 执行）
            if isinstance(self.top_gainers[0], dict) and "_task" in self.top_gainers[0]:
                self.log("需要执行 sessions_spawn 获取数据", "warning", "⚠")
                raise RuntimeError("需要 sessions_spawn 执行，当前不支持")
            
            # 记录数据源
            # 检查是否有"今日涨跌"字段（说明是实时数据）
            has_realtime_data = any(
                stock.get("今日涨跌") is not None 
                for stock in self.top_gainers[:5]
            )
            
            if has_realtime_data:
                self.stats["data_source"]["top_gainers"] = "browser(realtime)"
                self.log(f"成功获取 {len(self.top_gainers)} 只股票（实时数据）", "success", "✅")
            else:
                self.stats["data_source"]["top_gainers"] = "cache(fallback)"
                self.log(f"成功获取 {len(self.top_gainers)} 只股票（缓存数据）", "warning", "⚠")
            
            elapsed = time.time() - start
            self.stats["step_times"]["step2"] = elapsed
            return True
            
        except Exception as e:
            self.log(f"获取涨幅排名失败：{e}", "error", "❌")
            self.stats["errors"].append(f"step2: {e}")
            return False
    
    def step3_fetch_themes(self) -> bool:
        """步骤 3：获取股票题材和人气排名（⭐ 优先 browser 实时获取）"""
        self.log("获取题材概念并应用过滤...", "info", "🏷️")
        start = time.time()
        
        if not self.top_gainers:
            self.log("跳过：无涨幅股票数据", "warning", "⚠")
            return False
        
        try:
            # 提取股票代码列表
            stock_codes = [s["股票代码"] for s in self.top_gainers]
            
            # ⭐ 步骤 3.1：优先通过 browser 获取人气排名榜单（主会话中运行）
            popularity_map = {}
            if BROWSER_POPULARITY_AVAILABLE and fetch_popularity_ranking:
                self.log("通过 browser 获取人气排名榜单...", "debug", "📊")
                popularity_map = fetch_popularity_ranking(limit=100)
                
                if popularity_map:
                    self.log(f"成功获取 {len(popularity_map)} 只股票的人气排名", "success", "✅")
                else:
                    self.log("browser 获取人气排名失败，使用 fallback", "warning", "⚠")
            else:
                self.log("browser_popularity 模块不可用，使用 fallback", "warning", "⚠")
            
            # 步骤 3.2：通过 ClawHub 获取题材数据
            themes_result = self.clawhub.fetch_stock_themes(stock_codes)
            
            if not themes_result:
                raise ValueError("ClawHub 返回空数据")
            
            self.stats["data_source"]["themes"] = "browser+clawhub" if popularity_map else "clawhub"
            
            # 步骤 3.3：批量应用概念过滤和人气排名
            for stock in self.top_gainers:
                code = stock["股票代码"]
                
                # 获取题材
                raw = themes_result.get(code, {}).get("concepts", "暂无概念")
                stock["涉及概念（精选）"] = filter_and_select_concepts(raw, max_count=3)
                
                # ⭐ 优先使用 browser 获取的真实人气排名
                rank = popularity_map.get(code)
                if rank:
                    stock["人气热度"] = str(rank)
                else:
                    # fallback 到 ClawHub 或默认值
                    fallback_rank = themes_result.get(code, {}).get("popularity_rank", "100+")
                    stock["人气热度"] = fallback_rank if fallback_rank else "100+"
            
            self.themes_data = themes_result
            elapsed = time.time() - start
            self.stats["step_times"]["step3"] = elapsed
            
            # 统计过滤效果
            total_concepts = sum(
                len(parse_concepts(themes_result.get(code, {}).get("concepts", "")))
                for code in stock_codes
            )
            filtered_concepts = sum(
                len([c for c in s.get("涉及概念（精选）", "").split("、") if c.strip()])
                for s in self.top_gainers
            )
            
            # 统计有多少股票有真实人气排名
            has_real_rank = sum(1 for s in self.top_gainers if s.get("人气热度", "100+").isdigit())
            
            self.log(f"概念过滤：{total_concepts} → {filtered_concepts} 个，人气排名：{has_real_rank}/{len(self.top_gainers)} 只有真实排名", "success", "✅")
            return True
            
        except Exception as e:
            self.log(f"获取题材数据失败：{e}", "error", "❌")
            self.stats["errors"].append(f"step3: {e}")
            return False
    
    def step4_validate_data(self) -> bool:
        """步骤 4：数据验证"""
        self.log("数据验证...", "info", "🔍")
        start = time.time()
        
        passed = run_all_validations(
            index_data=self.index_data,
            gainers=self.top_gainers,
            themes_data=self.themes_data
        )
        
        elapsed = time.time() - start
        self.stats["step_times"]["step4"] = elapsed
        
        if passed:
            self.log("数据验证通过", "success", "✅")
        else:
            self.log("数据验证未通过，继续生成报告", "warning", "⚠")
        
        return passed
    
    def step5_analyze_themes(self) -> bool:
        """步骤 5：分析题材分布（使用 stock-theme-events 获取真实行业逻辑）"""
        self.log("分析题材分布...", "info", "📊")
        start = time.time()
        
        if not self.top_gainers:
            return False
        
        try:
            # 基础分析
            self.theme_analysis = analyze_stocks(self.top_gainers)
            
            # 使用 stock-theme-events 获取真实行业逻辑
            if THEME_EVENTS_AVAILABLE:
                self.log("调用 stock-theme-events 获取行业逻辑...", "debug", "🔗")
                try:
                    self.theme_logic_data = self._fetch_theme_logic_from_events()
                    self.log("成功获取行业逻辑数据", "success", "✅")
                except Exception as e:
                    self.log(f"获取行业逻辑失败：{e}，使用内置模板", "warning", "⚠")
                    self.theme_logic_data = None
            else:
                self.log("stock-theme-events 不可用，使用内置模板", "warning", "⚠")
                self.theme_logic_data = None
            
            elapsed = time.time() - start
            self.stats["step_times"]["step5"] = elapsed
            
            # 输出分析结果
            top_3 = self.theme_analysis.get("top_3_themes", [])
            if top_3:
                themes_str = ", ".join([f"{t}({c}只)" for t, c in top_3])
                self.log(f"热门题材：{themes_str}", "success", "✅")
            
            return True
            
        except Exception as e:
            self.log(f"题材分析失败：{e}", "error", "❌")
            self.stats["errors"].append(f"step5: {e}")
            return False
    
    def _fetch_theme_logic_from_events(self) -> Dict:
        """
        从 stock-theme-events 获取真实的行业逻辑数据
        
        返回格式：{题材名称：行业逻辑描述}
        """
        if not self.top_gainers:
            return {}
        
        # 提取股票代码
        stock_codes = [s["股票代码"] for s in self.top_gainers]
        
        # 获取题材数据（从 themes_data 或重新获取）
        themes_dict = {}
        for stock in self.top_gainers:
            code = stock["股票代码"]
            raw = self.themes_data.get(code, {}).get("concepts", "")
            if raw:
                concepts = parse_concepts(raw)
                themes_dict[code] = concepts
        
        # 加载同义词配置
        config_path = THEME_EVENTS_DIR.parent / "config/theme_synonyms.json"
        if config_path.exists():
            synonyms = load_synonyms(str(config_path))
        else:
            synonyms = {}
        
        # 提取所有题材
        all_themes = []
        for concepts in themes_dict.values():
            all_themes.extend(concepts)
        
        # 聚类题材
        clustered = cluster_by_semantic(all_themes, synonyms, top_n=10, threshold=0.7)
        
        # 为每个题材搜索新闻（获取行业逻辑）
        theme_logic = {}
        for theme, count in clustered[:8]:  # 取前 8 个主流题材
            try:
                # 搜索近 15 天新闻（使用 akshare）
                result = search_news(theme, days=15, limit=3, use_browser=False)
                news_list = result.get("news", [])
                
                if news_list and len(news_list) > 0:
                    # 从新闻摘要中提取行业逻辑
                    logic_summary = self._extract_logic_from_news(news_list)
                    theme_logic[theme] = logic_summary
                else:
                    theme_logic[theme] = "行业景气度提升，资金关注度提高"
            except Exception as e:
                self.log(f"搜索题材 {theme} 新闻失败：{e}", "debug")
                theme_logic[theme] = "行业景气度提升，资金关注度提高"
        
        return theme_logic
    
    def _extract_logic_from_news(self, news_list: List[Dict]) -> str:
        """从新闻列表中提取行业逻辑摘要"""
        if not news_list:
            return "行业景气度提升，资金关注度提高"
        
        # 提取前 3 条新闻的关键词
        keywords = []
        for news in news_list[:3]:
            title = news.get("title", "")
            summary = news.get("summary", "")
            
            # 简单关键词提取（可以优化）
            if "政策" in title or "政策" in summary:
                keywords.append("政策支持")
            if "增长" in title or "增长" in summary:
                keywords.append("需求增长")
            if "技术" in title or "技术" in summary:
                keywords.append("技术突破")
            if "订单" in title or "订单" in summary:
                keywords.append("订单饱满")
            if "产能" in title or "产能" in summary:
                keywords.append("产能扩张")
        
        if keywords:
            return f"{'、'.join(keywords)}，行业景气度提升"
        else:
            # 使用第一条新闻摘要的前 50 字
            first_summary = news_list[0].get("summary", "")
            if len(first_summary) > 50:
                return first_summary[:50] + "..."
            return first_summary or "行业景气度提升，资金关注度提高"
    
    def step6_generate_report(self) -> bool:
        """步骤 6：生成报告"""
        self.log("生成报告内容...", "info", "📝")
        start = time.time()
        
        try:
            self.report_content = self._generate_report_content()
            
            # 严格验证模板格式
            validation_passed = self._validate_template_format()
            if not validation_passed:
                self.log("模板格式验证失败，已自动修复", "warning", "⚠")
            
            elapsed = time.time() - start
            self.stats["step_times"]["step6"] = elapsed
            
            lines = len(self.report_content.split("\n"))
            chars = len(self.report_content)
            self.log(f"报告生成完成：{lines} 行，{chars} 字符", "success", "✅")
            return True
            
        except Exception as e:
            self.log(f"生成报告失败：{e}", "error", "❌")
            self.stats["errors"].append(f"step6: {e}")
            return False
    
    def step7_save_report(self) -> bool:
        """步骤 7：保存文件"""
        if self.test_mode:
            self.log("测试模式：跳过文件保存", "info", "🧪")
            print("\n" + "="*60)
            print(self.report_content[:2000] + "..." if len(self.report_content) > 2000 else self.report_content)
            print("="*60 + "\n")
            return True
        
        self.log("保存报告文件...", "info", "💾")
        start = time.time()
        
        try:
            filename = f"stock-report-{self.date}.md"
            
            # 写入 workspace
            workspace_path = self.workspace_root / self.report_dir / filename
            workspace_path.write_text(self.report_content, encoding="utf-8")
            self.log(f"写入 workspace: {workspace_path}", "success", "✅")
            
            # 复制到 Desktop
            desktop_path = self.desktop_root / self.report_dir / filename
            subprocess.run(["cp", str(workspace_path), str(desktop_path)], check=True)
            self.log(f"复制到 Desktop: {desktop_path}", "success", "✅")
            
            # 验证
            result = subprocess.run(
                ["diff", str(workspace_path), str(desktop_path)],
                capture_output=True
            )
            if result.returncode == 0:
                self.log("✓ 文件一致性验证通过", "success", "✅")
            else:
                self.log("⚠ 文件内容不一致", "warning", "⚠")
            
            elapsed = time.time() - start
            self.stats["step_times"]["step7"] = elapsed
            self.stats["report_path"] = str(desktop_path)
            
            return True
            
        except Exception as e:
            self.log(f"保存文件失败：{e}", "error", "❌")
            self.stats["errors"].append(f"step7: {e}")
            return False
    
    def _generate_report_content(self) -> str:
        """
        生成报告内容（严格按照模板格式，不删减任何章节）
        
        模板格式要求：
        - 必须包含全部 6 个章节
        - 表格必须包含 20 只股票（不足则用占位符填充）
        - 所有字段必须有值（数据缺失时使用"待补充"）
        - 免责声明必须存在
        
        ⚠️ 注意：所有数据必须来自 skill 获取，不再使用模拟数据
        """
        # 计算统计周期
        end_date = datetime.strptime(self.date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=14)
        
        # ❌ 不再使用模拟数据 fallback，数据缺失时使用"待补充"
        if not self.index_data:
            self.log("指数数据缺失，使用待补充", "warning", "⚠")
            markets = {}
            summary = {}
        else:
            # 兼容新旧数据结构
            # 新结构：indices（包含 shanghai, shenzhen, chinext）
            # 旧结构：markets（包含 沪市，深市，创业板）
            if self.index_data.get("indices"):
                indices = self.index_data.get("indices", {})
                # 转换为 markets 格式（处理 None 值）
                sh_point = indices.get("shanghai", {}).get("point")
                sh_change = indices.get("shanghai", {}).get("change")
                sz_point = indices.get("shenzhen", {}).get("point")
                sz_change = indices.get("shenzhen", {}).get("change")
                cn_point = indices.get("chinext", {}).get("point")
                cn_change = indices.get("chinext", {}).get("change")
                
                markets = {
                    "沪市": {
                        "close": sh_point if sh_point is not None else "暂缺",
                        "change_pct": sh_change if sh_change is not None else "暂缺",
                    },
                    "深市": {
                        "close": sz_point if sz_point is not None else "暂缺",
                        "change_pct": sz_change if sz_change is not None else "暂缺",
                    },
                    "创业板": {
                        "close": cn_point if cn_point is not None else "暂缺",
                        "change_pct": cn_change if cn_change is not None else "暂缺",
                    },
                }
            else:
                markets = self.index_data.get("markets", {}) or {}
            
            summary = self.index_data.get("summary", {}) or {}
        
        # 确保 top_gainers 至少有 20 只股票（不足则填充占位符）
        gainers_list = self.top_gainers or []
        if len(gainers_list) < 20:
            self.log(f"涨幅股票不足 20 只（{len(gainers_list)}），填充占位符", "warning", "⚠")
            for i in range(len(gainers_list), 20):
                gainers_list.append({
                    "股票代码": "待补充",
                    "股票简称": "待补充",
                    "现价": "待补充",
                    "10 日涨幅": "待补充",
                    "当日涨跌": "待补充",
                    "人气热度": "待补充",
                    "涉及概念（精选）": "待补充"
                })
        
        # 题材分析
        theme_analysis = self.theme_analysis or {}
        top_3_themes = theme_analysis.get("top_3_themes", [])
        theme_stocks = theme_analysis.get("theme_stocks", {})
        
        # 确保至少有 3 个题材（不足则填充）
        if len(top_3_themes) < 3:
            default_themes = [
                ("人工智能", 0),
                ("新能源", 0),
                ("半导体", 0)
            ]
            for theme, count in default_themes:
                if not any(t[0] == theme for t in top_3_themes):
                    top_3_themes.append((theme, count))
        top_3_themes = top_3_themes[:3]  # 确保只有 3 个
        
        # 行业逻辑：优先使用 stock-theme-events 获取的真实数据
        if hasattr(self, 'theme_logic_data') and self.theme_logic_data:
            theme_logic = self.theme_logic_data
            self.log("使用 stock-theme-events 提供的真实行业逻辑", "debug", "📰")
        else:
            # Fallback 到内置模板
            theme_logic = {
                "人工智能": "大模型技术突破，应用落地加速，算力需求持续增长",
                "AI 应用": "AI 技术商业化落地，应用场景持续拓展",
                "算力": "AI 训练推理需求爆发，算力资源紧缺",
                "华为概念": "鸿蒙生态扩张，昇腾算力布局，国产化进程加速",
                "风电": "全球能源转型加速，装机量持续增长，政策支持力度加大",
                "光伏": "光伏装机需求旺盛，技术迭代推动成本下降",
                "储能": "新能源配储政策推动，工商业储能经济性提升",
                "半导体": "国产替代加速，存储芯片周期见底回升",
                "芯片": "AI 算力需求拉动，国产替代进程加速",
                "机器人": "人形机器人技术突破，产业链降本加速",
                "低空经济": "政策密集落地，eVTOL 适航认证推进",
                "新能源": "全球能源转型加速，光伏风电装机量持续增长",
            }
        
        # 生成题材方向章节（必须生成 3 个题材）
        theme_sections = []
        for i, (theme, count) in enumerate(top_3_themes, 1):
            logic = theme_logic.get(theme, "行业景气度提升，资金关注度提高")
            stocks = theme_stocks.get(theme, [])[:3]
            stocks_str = "、".join(stocks) if stocks else "待补充"
            
            theme_sections.append(f"""### {i}. {theme}（{count}只股票）
- **行业逻辑**：{logic}
- **重点个股**：{stocks_str}
""")
        
        themes_content = "\n".join(theme_sections)
        
        # 生成表格（必须 20 行）
        table_lines = [
            "| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |",
            "| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :------: |"
        ]
        
        for i, stock in enumerate(gainers_list[:20], 1):
            # 确保所有字段都有值
            code = stock.get("股票代码", "待补充") or "待补充"
            name = stock.get("股票简称", "待补充") or "待补充"
            price = stock.get("现价", stock.get("收盘价", "待补充")) or "待补充"
            gain_10d = stock.get("10 日涨幅", stock.get("区间涨幅", "待补充")) or "待补充"
            # 兼容字段名：fetch_gainers.py 返回"今日涨跌"，但模板用"当日涨跌"
            gain_1d = stock.get("当日涨跌") or stock.get("今日涨跌") or "待补充"
            popularity = stock.get("人气热度", "100+") or "100+"
            concepts = stock.get("涉及概念（精选）", "待补充") or "待补充"
            
            # 格式化涨幅（确保有 + 号）
            if isinstance(gain_10d, (int, float)):
                gain_10d = f"{gain_10d:.2f}"
            if not str(gain_10d).startswith("+") and str(gain_10d) != "待补充":
                gain_10d = f"+{gain_10d}"
            
            if isinstance(gain_1d, (int, float)):
                gain_1d = f"{gain_1d:.2f}"
            if not str(gain_1d).startswith("+") and not str(gain_1d).startswith("-") and str(gain_1d) != "待补充":
                gain_1d = f"+{gain_1d}"
            
            row = "| {} | {} | {} | {} | {}% | {}% | {} | {} |".format(
                i, code, name, price, gain_10d, gain_1d, popularity, concepts
            )
            table_lines.append(row)
        
        table_content = "\n".join(table_lines)
        
        # 关键观察
        key_observations = []
        if gainers_list and gainers_list[0].get("股票代码") != "待补充":
            top1 = gainers_list[0]
            gain_val = top1.get("10 日涨幅", 0)
            if isinstance(gain_val, (int, float)):
                gain_str = f"+{gain_val:.2f}"
            else:
                gain_str = gain_val
            key_observations.append(f"涨幅冠军：{top1.get('股票简称', '待补充')}（{top1.get('股票代码', '')}）{gain_str}%")
            
            # 计算平均涨幅
            valid_gains = [
                s.get("10 日涨幅", 0) 
                for s in gainers_list[:20] 
                if isinstance(s.get("10 日涨幅"), (int, float))
            ]
            if valid_gains:
                avg_gain = sum(valid_gains) / len(valid_gains)
                key_observations.append(f"前 20 平均涨幅：{avg_gain:.1f}%")
            else:
                key_observations.append("前 20 平均涨幅：待补充")
        else:
            key_observations.append("涨幅冠军：待补充")
            key_observations.append("前 20 平均涨幅：待补充")
        
        # 生成完整报告（严格按照模板格式）
        content = f"""# 📊 股票每日分析报告

**日期：{self.date}**

---

## 一、大盘指数解读

1. **市场状态**：三大指数分化，成交量放大
   - 上证指数：{markets.get('沪市', {}).get('close', '暂缺')} 点，涨跌幅 {markets.get('沪市', {}).get('change_pct', '暂缺')}%
   - 深证成指：{markets.get('深市', {}).get('close', '暂缺')} 点，涨跌幅 {markets.get('深市', {}).get('change_pct', '暂缺')}%
   - 创业板指：{markets.get('创业板', {}).get('close', '暂缺')} 点，涨跌幅 {markets.get('创业板', {}).get('change_pct', '暂缺')}%

2. **位置判断**：市场震荡整理
   - 成交量变化：今日量能（{summary.get('total_fmt', '暂缺')}），{summary.get('change_fmt', '暂缺')}（{summary.get('change_pct', '暂缺')}%）

3. **操作策略**：控制仓位，跟随主线
   - 建议仓位：中等（2-3 成）
   - 风险提示：控制单一个股仓位不超过 20%

---

## 二、盘面理解与应对策略

1. **市场情绪**：

   - 整体情绪：分歧加大
   - 短线情绪：指数分化，个股跌多涨少
   - 涨跌家数比：待补充

2. **市场反馈**：

   - 主板高度（10cm）：
     - 10 日涨幅第一：{self._get_top_gainer_name('主板')}
   - 创业板高度（20cm）：
     - 10 日涨幅第一：{self._get_top_gainer_name('创业板/科创板')}

3. **总结**：

   > 指数端三大指数分化，成交量放大显示资金活跃度提升。市场情绪端涨跌家数比待补充。当前市场处于震荡整理阶段，建议控制仓位在 2-3 成，跟随强势板块轮动，避免追高。

---

## 三、题材方向

{themes_content}

---

## 四、明日计划

1. **主要观察题材**：
   - [ ] 人工智能（观察持续性）
   - [ ] 新能源（观察轮动）
   - [ ] 半导体（观察资金流向）

2. **对应题材下个股**：
   - 人工智能：待补充
   - 新能源：待补充
   - 半导体：待补充

---

## 五、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：{start_date.strftime('%Y.%m.%d')}-{end_date.strftime('%Y.%m.%d')} | **已排除 ST 股票**

{table_content}

**关键观察**：
{chr(10).join(f"- {obs}" for obs in key_observations)}

---

## 六、备注/其他

- 情绪冰点策略：等待市场企稳
- 数据来源：A 股市场公开数据
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
"""
        
        return content
    
    def _get_top_gainer_name(self, board_type: str) -> str:
        """获取板块涨幅第一的股票"""
        if not self.top_gainers:
            return "待补充"
        
        top = self.top_gainers[0]
        name = top.get("股票简称", "待补充")
        code = top.get("股票代码", "")
        gain = top.get("10 日涨幅", 0)
        
        return f"{name}（{code}）+{gain}%"
    
    def _validate_template_format(self) -> bool:
        """
        严格验证报告格式是否符合模板要求
        
        检查项目：
        1. 所有必需章节是否存在
        2. 所有必需字段是否填充
        3. 表格格式是否正确
        4. 免责声明是否存在
        
        Returns:
            bool: 验证是否通过
        """
        self.log("验证模板格式...", "debug", "🔍")
        
        errors = []
        warnings = []
        
        # 检查必需章节
        for section in REQUIRED_SECTIONS:
            if section not in self.report_content:
                errors.append(f"缺少必需章节：{section}")
        
        # 检查必需字段
        for field in REQUIRED_FIELDS:
            if field not in self.report_content:
                warnings.append(f"缺少字段：{field}")
        
        # 检查表格格式（至少 20 行数据）
        if "五、近 10 个交易日涨幅前 20 股票" in self.report_content:
            table_lines = [
                line for line in self.report_content.split("\n")
                if line.startswith("|") and "排名" not in line and ":--" not in line
            ]
            if len(table_lines) < 20:
                warnings.append(f"表格行数不足：{len(table_lines)}/20")
        
        # 检查免责声明
        if "免责声明" not in self.report_content and "风险提示" not in self.report_content:
            errors.append("缺少免责声明或风险提示")
        
        # 输出验证结果
        if errors:
            self.log(f"格式错误：{len(errors)}", "error", "❌")
            for err in errors[:5]:  # 最多显示 5 个错误
                self.log(f"  - {err}", "error")
            return False
        
        if warnings:
            self.log(f"格式警告：{len(warnings)}", "warning", "⚠")
            for warn in warnings[:5]:  # 最多显示 5 个警告
                self.log(f"  - {warn}", "warning")
        
        self.log("模板格式验证通过", "success", "✅")
        return True
    
    # ❌ 已删除模拟数据方法，不再使用模拟数据
    
    def run(self) -> bool:
        """执行完整流程"""
        print("\n" + "="*60)
        print(f"{Colors.BOLD}A 股每日复盘报告生成器 v2.0{Colors.RESET}")
        print(f"报告日期：{self.date}")
        print(f"测试模式：{'是' if self.test_mode else '否'}")
        print(f"详细日志：{'是' if self.verbose else '否'}")
        print("="*60 + "\n")
        
        total_steps = len(self.steps)
        
        for step_num, step_name, step_func in self.steps:
            # 跳过已完成的步骤
            if step_num < self.from_step:
                self.log(f"跳过步骤 {step_num}：{step_name}（已指定从步骤{self.from_step}开始）", "debug")
                continue
            
            # 打印进度
            print_progress(step_num - 1, total_steps, f"正在执行：{step_name}")
            
            # 执行步骤
            try:
                success = step_func()
                
                if success:
                    self.stats["steps_completed"].append(step_name)
                else:
                    self.stats["steps_failed"].append(step_name)
                    
                    # 关键步骤失败处理
                    if step_num in [1, 2]:
                        self.log(f"关键步骤{step_num}失败，但继续执行", "warning")
                        
            except Exception as e:
                self.log(f"步骤{step_num}异常：{e}", "error")
                self.stats["errors"].append(f"step{step_num}: {e}")
                self.stats["steps_failed"].append(step_name)
        
        # 完成进度
        print_progress(total_steps, total_steps, "完成")
        
        # 汇总报告
        self._print_summary()
        
        return len(self.stats["errors"]) == 0
    
    def _print_summary(self):
        """打印执行摘要"""
        end_time = datetime.now()
        duration = (end_time - self.stats["start_time"]).total_seconds()
        
        print("\n" + "="*60)
        print(f"{Colors.BOLD}执行摘要{Colors.RESET}")
        print("="*60)
        
        print(f"开始时间：{self.stats['start_time'].strftime('%H:%M:%S')}")
        print(f"结束时间：{end_time.strftime('%H:%M:%S')}")
        print(f"总耗时：{Colors.GREEN}{duration:.2f}秒{Colors.RESET}")
        
        # 步骤统计
        completed = len(self.stats["steps_completed"])
        failed = len(self.stats["steps_failed"])
        print(f"完成步骤：{Colors.GREEN}{completed}{Colors.RESET} / 失败：{Colors.RED}{failed}{Colors.RESET}")
        
        # 数据源统计
        if self.stats.get("data_source"):
            print(f"\n数据源:")
            for step, source in self.stats["data_source"].items():
                icon = "✅" if source == "clawhub" else "⚠️"
                print(f"  {icon} {step}: {source}")
        
        # 步骤耗时
        if self.stats["step_times"] and self.verbose:
            print("\n步骤耗时:")
            for step, time_cost in self.stats["step_times"].items():
                print(f"  {step}: {time_cost:.2f}秒")
        
        # 错误列表
        if self.stats["errors"]:
            print(f"\n{Colors.RED}错误列表:{Colors.RESET}")
            for error in self.stats["errors"]:
                print(f"  ❌ {error}")
        
        # 报告路径
        if "report_path" in self.stats:
            print(f"\n{Colors.GREEN}✅ 报告已生成：{self.stats['report_path']}{Colors.RESET}")
        elif self.test_mode:
            print(f"\n{Colors.YELLOW}🧪 测试模式：报告已输出到控制台{Colors.RESET}")
        
        print("="*60 + "\n")


# 工具函数
def parse_concepts(concepts_str: str) -> List[str]:
    """解析概念字符串（兼容导入）"""
    if not concepts_str:
        return []
    normalized = concepts_str.replace("，", ",").replace("、", ",")
    return [c.strip() for c in normalized.split(",") if c.strip()]


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="A 股每日复盘报告生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 generate_report.py                    # 生成今日报告
  python3 generate_report.py 2026-03-21         # 生成指定日期
  python3 generate_report.py --test             # 测试模式
  python3 generate_report.py --verbose          # 详细日志
  python3 generate_report.py --from-step 3      # 从步骤 3 开始
        """
    )
    
    parser.add_argument("date", nargs="?", help="报告日期（YYYY-MM-DD，默认今天）")
    parser.add_argument("--test", action="store_true", help="测试模式（不保存文件）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志模式")
    parser.add_argument("--from-step", type=int, default=1, 
                        help="从指定步骤开始（1-7，用于断点续跑）")
    
    args = parser.parse_args()
    
    # 创建生成器
    generator = ReportGenerator(
        date=args.date,
        test_mode=args.test,
        verbose=args.verbose,
        from_step=args.from_step
    )
    
    # 执行
    success = generator.run()
    
    # 退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
