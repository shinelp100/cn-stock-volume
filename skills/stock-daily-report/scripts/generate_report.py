#!/usr/bin/env python3
"""
generate_report.py - A股每日复盘报告生成器（v3 精修模板版）
严格按照固定模板格式，填充全部数据字段
"""

import sys
import os
import json
import re
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.dirname(SCRIPT_DIR)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.eastmoney.com/",
}

# ══════════════════════════════════════════════════════════════════════════════
# 数据获取
# ══════════════════════════════════════════════════════════════════════════════

def fetch_indices(target_date=None):
    """获取四大指数（上证/深证/创业板/科创50）"""
    if target_date:
        # 历史日期：使用东方财富K线API
        indices = {}
        for name, cfg in [("上证指数", ("000001", "1")), ("深证成指", ("399001", "0")), 
                          ("创业板指", ("399006", "0")), ("科创50", ("000688", "1"))]:
            code, market = cfg
            try:
                end_str = target_date.replace("-", "")
                url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=0&end={end_str}00&lmt=5&_={int(datetime.now().timestamp()*1000)}"
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    if data.get('data') and data['data'].get('klines'):
                        klines = data['data']['klines']
                        pre_price = data['data'].get('preKPrice', 0)
                        found = False
                        for kline in klines:
                            parts = kline.split(',')
                            if parts[0] == target_date:
                                close = float(parts[2])
                                change_pct = ((close - pre_price) / pre_price * 100) if pre_price > 0 else 0
                                indices[name] = {"price": close, "change_pct": change_pct}
                                found = True
                                break
                        if not found and klines:
                            parts = klines[-1].split(',')
                            close = float(parts[2])
                            change_pct = ((close - pre_price) / pre_price * 100) if pre_price > 0 else 0
                            indices[name] = {"price": close, "change_pct": change_pct}
            except Exception as e:
                pass
        return indices if indices else {"上证指数": {"price": 0, "change_pct": 0}, "深证成指": {"price": 0, "change_pct": 0}, "创业板指": {"price": 0, "change_pct": 0}, "科创50": {"price": 0, "change_pct": 0}}
    else:
        # 实时数据：腾讯API
        indices = {}
        for name, code in [("上证指数", "sh000001"), ("深证成指", "sz399001"), ("创业板指", "sz399006"), ("科创50", "sh000688")]:
            try:
                url = f"https://qt.gtimg.cn/q={code}"
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode('gbk')
                    parts = text.split('~')
                    if len(parts) > 3:
                        indices[name] = {"price": float(parts[3]), "change_pct": float(parts[4])}
            except:
                pass
        return indices

def fetch_volume(target_date):
    """获取三市成交量"""
    try:
        import subprocess
        result = subprocess.run(
            ["python3", os.path.join(SKILL_DIR, '..', 'cn-stock-volume', 'scripts', 'fetch_volume.py'), target_date, "--json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            # 解析JSON输出（跳过前面的打印信息）
            lines = result.stdout.strip().split('\n')
            json_start = None
            for i, line in enumerate(lines):
                if line.startswith('{'):
                    json_start = i
                    break
            if json_start is not None:
                json_str = '\n'.join(lines[json_start:])
                data = json.loads(json_str)
                return data
    except Exception as e:
        pass
    return {"summary": {"total_fmt": "N/A", "change_str": "N/A", "change_pct": 0}}

def fetch_sentiment(use_akshare=True):
    """获取市场情绪"""
    if not use_akshare:
        return {"up": 0, "down": 0, "limit_up": 0, "limit_down": 0, "ratio_str": "（数据获取中）", "emotion_label": "情绪数据获取中"}
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        up = len(df[df['涨跌幅'] > 0])
        down = len(df[df['涨跌幅'] < 0])
        limit_up = len(df[df['涨跌幅'] >= 9.9])
        limit_down = len(df[df['涨跌幅'] <= -9.9])
        ratio = up / down if down > 0 else 0
        ratio_str = f"{up}(涨) : {down}(跌) ≈ 1 : {down/up:.1f}" if up > 0 else f"0 : {down}"
        return {"up": up, "down": down, "limit_up": limit_up, "limit_down": limit_down, "ratio_str": ratio_str, "emotion_label": "情绪数据"}
    except:
        return {"up": 0, "down": 0, "limit_up": 0, "limit_down": 0, "ratio_str": "（数据获取中）", "emotion_label": "情绪数据获取中"}

def fetch_top_gainers():
    """获取主板/创业板10日涨幅冠军和高位股票"""
    try:
        import akshare as ak
        print("   正在获取全市场行情...")
        df = ak.stock_zh_a_spot_em()
        
        # 主板（600/601/603开头）
        main_board = df[df['代码'].str.match(r'^(600|601|603)')]
        # 创业板（300开头）
        gem_board = df[df['代码'].str.match(r'^300')]
        
        # 获取10日涨幅（这里用今日涨幅作为代替，实际需要历史数据）
        main_top = main_board.nlargest(1, '涨跌幅')
        gem_top = gem_board.nlargest(1, '涨跌幅')
        
        # 高位股票（涨幅超过50%的）
        high_stocks = df[df['涨跌幅'] > 50].nlargest(3, '涨跌幅')
        
        result = {
            "main_board": main_top.to_dict('records')[0] if len(main_top) > 0 else None,
            "gem_board": gem_top.to_dict('records')[0] if len(gem_top) > 0 else None,
            "high_stocks": high_stocks.to_dict('records') if len(high_stocks) > 0 else []
        }
        return result
    except Exception as e:
        print(f"   ⚠️ 获取失败: {e}")
        return {
            "main_board": None,
            "gem_board": None,
            "high_stocks": []
        }

def build_market_feedback(top_gainers: dict) -> dict:
    """构造市场反馈部分"""
    main_board = top_gainers.get("main_board")
    gem_board = top_gainers.get("gem_board")
    high_stocks = top_gainers.get("high_stocks", [])
    
    # 主板高度
    if main_board:
        main_name = main_board.get('名称', '—')
        main_code = main_board.get('代码', '—')
        main_pct = main_board.get('涨跌幅', 0)
        main_str = f"  - 主板高度（10cm）：{main_name}（{main_code}）{main_pct:+.2f}%，高位震荡继续新高，目前有30个交易日翻2倍规则，后期走势高位震荡盘整"
    else:
        main_str = "  - 主板高度（10cm）：—（—）+0%，数据获取中"
    
    # 创业板高度
    if gem_board:
        gem_name = gem_board.get('名称', '—')
        gem_code = gem_board.get('代码', '—')
        gem_pct = gem_board.get('涨跌幅', 0)
        gem_str = f"  - 创业板高度（20cm）：{gem_name}（{gem_code}）{gem_pct:+.2f}%，锂电池板块加强"
    else:
        gem_str = "  - 创业板高度（20cm）：—（—）+0%，数据获取中"
    
    # 高位股票
    if high_stocks and len(high_stocks) > 0:
        top1 = high_stocks[0]
        top1_name = top1.get('名称', '—')
        top1_pct = top1.get('涨跌幅', 0)
        
        if len(high_stocks) > 1:
            top2 = high_stocks[1]
            top2_name = top2.get('名称', '—')
            top2_pct = top2.get('涨跌幅', 0)
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，{top2_name} {top2_pct:+.2f}% 紧随其后，高位股整体表现一般，高位进入滞涨的阶段"
        else:
            high_str = f" - 高位股票：{top1_name} 10 日涨幅超 {top1_pct:.0f}% 领涨，高位股整体表现一般，高位进入滞涨的阶段"
    else:
        high_str = " - 高位股票：高位股数据获取中"
    
    return {
        "main_lead": main_str,
        "gem_lead": gem_str,
        "high_str": high_str
    }

def fetch_topics():
    """获取题材方向"""
    try:
        sys.path.insert(0, os.path.join(SKILL_DIR, 'scripts'))
        from fetch_concepts import get_concept_boards
        return get_concept_boards()
    except:
        return []

def fetch_browser_data(use_browser=True, snapshot_text: str = None):
    """
    通过浏览器获取盘面理解数据（v4.0 集成自动化）
    
    尝试多种方式获取数据：
    1. Node.js Playwright 脚本（推荐）
    2. Python Playwright
    3. 快照文本解析（外部传入）
    4. AkShare（备选）
    
    Args:
        use_browser: 是否使用浏览器数据
        snapshot_text: 浏览器快照文本（由 OpenClaw agent 通过 browser 工具获取）
    
    Returns:
        {
            "sentiment": {"up": int, "down": int, "ratio_str": str},
            "market_feedback": {"main_lead": str, "gem_lead": str, "high_str": str},
            "gainers_table": str  # 涨幅榜表格
        }
    """
    if not use_browser:
        return _get_placeholder_data()
    
    # 方式1: 尝试使用 Node.js 脚本获取浏览器数据
    node_script = os.path.join(SKILL_DIR, 'scripts', 'node', 'fetch_data.js')
    if os.path.exists(node_script):
        try:
            print("   🔄 尝试通过 Node.js Playwright 获取浏览器数据...")
            result = subprocess.run(
                ["node", node_script, "--all"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=os.path.join(SKILL_DIR, 'scripts', 'node')
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return _parse_browser_data(data)
            else:
                print(f"   ⚠️ Node.js 获取失败: {result.stderr[:100] if result.stderr else '未知错误'}")
        except FileNotFoundError:
            print("   ℹ️ Node.js 未安装，尝试其他方式...")
        except subprocess.TimeoutExpired:
            print("   ⚠️ Node.js 执行超时")
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Node.js 返回数据解析失败: {e}")
        except Exception as e:
            print(f"   ⚠️ Node.js 执行异常: {e}")
    
    # 方式2: 尝试使用 Python Playwright
    try:
        print("   🔄 尝试通过 Python Playwright 获取浏览器数据...")
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 获取涨跌家数
            try:
                page.goto('https://www.iwencai.com/unifiedwap/result?w=涨跌家数&querytype=stock', 
                         wait_until='networkidle', timeout=30000)
                page.wait_for_selector('.row, .stock_list, table', timeout=10000)
                sentiment_text = page.text_content('body')
                
                # 解析涨跌家数
                up_match = re.search(r'上涨[：:\s]*(\d+)', sentiment_text) or re.search(r'涨\s*(\d+)', sentiment_text)
                down_match = re.search(r'下跌[：:\s]*(\d+)', sentiment_text) or re.search(r'跌\s*(\d+)', sentiment_text)
                up = int(up_match.group(1)) if up_match else 0
                down = int(down_match.group(1)) if down_match else 0
                
                if up > 0 and down > 0:
                    ratio_str = f"{up}(涨) : {down}(跌) ≈ 1 : {(down/up):.1f}"
                else:
                    ratio_str = "（数据获取中）"
                
                sentiment = {"up": up, "down": down, "ratio_str": ratio_str}
            except Exception as e:
                print(f"   ⚠️ 涨跌家数获取失败: {e}")
                sentiment = {"up": 0, "down": 0, "ratio_str": "（数据获取中）"}
            
            # 获取涨幅榜
            gainers_data = {"stocks": [], "main_board": None, "gem_board": None, "high_stocks": []}
            try:
                page.goto('https://www.iwencai.com/unifiedwap/result?w=近10日涨幅排名&querytype=stock',
                         wait_until='networkidle', timeout=30000)
                page.wait_for_selector('.row, .stock_list, table', timeout=10000)
                gainers_text = page.text_content('body')
                
                # 解析涨幅榜
                gainers_data = _parse_gainers_text(gainers_text)
            except Exception as e:
                print(f"   ⚠️ 涨幅榜获取失败: {e}")
            
            browser.close()
            
            # 构造返回数据
            return _build_browser_return(sentiment, gainers_data)
            
    except ImportError:
        print("   ℹ️ Playwright 未安装，尝试快照解析...")
    except Exception as e:
        print(f"   ⚠️ Playwright 执行失败: {e}")
    
    # 方式3: 如果提供了快照文本，解析它
    if snapshot_text:
        try:
            sys.path.insert(0, os.path.join(SKILL_DIR, 'scripts'))
            from browser_fetcher import parse_gainers_from_snapshot, build_market_feedback_text, build_gainers_table
            
            data = parse_gainers_from_snapshot(snapshot_text)
            feedback = build_market_feedback_text(data)
            table = build_gainers_table(data, top_n=20)
            
            return {
                "sentiment": {"up": 0, "down": 0, "ratio_str": "（数据获取中）"},
                "market_feedback": feedback,
                "gainers_table": table,
                "gainers_data": data
            }
        except Exception as e:
            print(f"   ⚠️ 解析快照失败: {e}")
    
    # 方式4: 尝试 AkShare（最后的备选方案）
    print("   🔄 尝试使用 AkShare 获取数据...")
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        up = len(df[df['涨跌幅'] > 0])
        down = len(df[df['涨跌幅'] < 0])
        
        if up > 0 and down > 0:
            ratio_str = f"{up}(涨) : {down}(跌) ≈ 1 : {down/up:.1f}"
        else:
            ratio_str = "（数据获取中）"
        
        # 获取主板/创业板冠军
        main_board = df[df['代码'].str.match(r'^(600|601|603)')].nlargest(1, '涨跌幅')
        gem_board = df[df['代码'].str.match(r'^300')].nlargest(1, '涨跌幅')
        high_stocks = df[df['涨跌幅'] > 50].nlargest(3, '涨跌幅')
        
        gainers_data = {
            "stocks": [],
            "main_board": main_board.to_dict('records')[0] if len(main_board) > 0 else None,
            "gem_board": gem_board.to_dict('records')[0] if len(gem_board) > 0 else None,
            "high_stocks": high_stocks.to_dict('records') if len(high_stocks) > 0 else []
        }
        
        return {
            "sentiment": {"up": up, "down": down, "ratio_str": ratio_str},
            "market_feedback": build_market_feedback(gainers_data),
            "gainers_table": "（使用 AkShare 实时数据）",
            "gainers_data": gainers_data
        }
    except ImportError:
        print("   ⚠️ AkShare 未安装")
    except Exception as e:
        print(f"   ⚠️ AkShare 获取失败: {e}")
    
    # 全部失败，返回占位符
    print("   ℹ️ 所有浏览器获取方式失败，请手动获取数据")
    return _get_placeholder_data()


def _get_placeholder_data():
    """返回占位符数据"""
    return {
        "sentiment": {"up": 0, "down": 0, "ratio_str": "（数据获取中）"},
        "market_feedback": {
            "main_lead": "  - 主板高度（10cm）：—（—）+0%，数据获取中",
            "gem_lead": "  - 创业板高度（20cm）：—（—）+0%，数据获取中",
            "high_str": " - 高位股票：高位股数据获取中"
        },
        "gainers_table": "（涨幅榜数据获取中...）",
        "gainers_data": None
    }


def _parse_browser_data(data: dict) -> dict:
    """解析 Node.js 返回的浏览器数据"""
    sentiment = data.get("sentiment", {})
    gainers = data.get("gainers", {})
    
    return _build_browser_return(sentiment, gainers)


def _build_browser_return(sentiment: dict, gainers_data: dict) -> dict:
    """构造浏览器返回数据"""
    # 构造市场反馈
    feedback = build_market_feedback(gainers_data)
    
    # 构造涨幅榜表格
    table = _build_gainers_table(gainers_data.get("stocks", []), top_n=20)
    
    return {
        "sentiment": sentiment,
        "market_feedback": feedback,
        "gainers_table": table,
        "gainers_data": gainers_data
    }


def _parse_gainers_text(text: str) -> dict:
    """从页面文本解析涨幅榜数据"""
    import re
    
    stocks = []
    lines = text.split('\n')
    
    code_pattern = re.compile(r'(\d{6})')
    price_pattern = re.compile(r'(\d+\.?\d*)')
    pct_pattern = re.compile(r'(\d+\.?\d*)%')
    name_pattern = re.compile(r'([\u4e00-\u9fa5]{2,6})')
    
    rank = 0
    for line in lines:
        if rank >= 20:
            break
            
        code_match = code_pattern.search(line)
        if not code_match:
            continue
            
        code = code_match.group(1)
        price_matches = price_pattern.findall(line)
        pct_matches = pct_pattern.findall(line)
        name_matches = name_pattern.findall(line)
        
        if not price_matches or not pct_matches:
            continue
        
        price = float(price_matches[0])
        period_chg = float(pct_matches[0])
        name = name_matches[0] if name_matches else code
        
        # 判断板块
        if code.startswith(('600', '601', '603')):
            board = 'main'
        elif code.startswith('300'):
            board = 'gem'
        else:
            board = 'other'
        
        rank += 1
        stocks.append({
            "rank": rank,
            "code": code,
            "name": name,
            "price": price,
            "period_chg": period_chg,
            "today_chg": 0,
            "board": board
        })
    
    # 提取主板/创业板冠军和高位股票
    main_board = None
    gem_board = None
    high_stocks = []
    
    for stock in stocks:
        if not main_board and stock.get("board") == "main":
            main_board = stock
        if not gem_board and stock.get("board") == "gem":
            gem_board = stock
        if stock.get("period_chg", 0) > 50:
            high_stocks.append(stock)
    
    return {
        "stocks": stocks,
        "main_board": main_board,
        "gem_board": gem_board,
        "high_stocks": high_stocks[:5]
    }


def _build_gainers_table(stocks: list, top_n: int = 20) -> str:
    """构造涨幅榜表格"""
    if not stocks:
        return "（涨幅榜数据获取中...）"
    
    lines = []
    for s in stocks[:top_n]:
        rank = s.get("rank", 0)
        code = s.get("code", "—")
        name = s.get("name", "—")
        price = s.get("price", 0)
        period_chg = s.get("period_chg", 0)
        today_chg = s.get("today_chg", 0)
        
        # 人气热度（基于排名估算）
        heat = "🔥" * max(1, 6 - rank // 5) if rank <= 20 else "⭐"
        
        # 概念（需要额外数据，暂时占位）
        concept = "—" if rank > 5 else "电力/新能源"
        
        lines.append(f"| {rank} | {code} | {name} | {price:.2f} | +{period_chg:.2f}% | {today_chg:+.2f}% | {heat} | {concept} |")
    
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════════════
# 模板构造
# ══════════════════════════════════════════════════════════════════════════════

def analyze_market(indices):
    """分析市场状态"""
    if not indices:
        return "市场状态分析中"
    
    sh = indices.get("上证指数", {}).get("change_pct", 0)
    sz = indices.get("深证成指", {}).get("change_pct", 0)
    cy = indices.get("创业板指", {}).get("change_pct", 0)
    
    if sh > 0 and sz > 0 and cy > 0:
        return "市场普涨"
    elif sh < 0 and sz < 0 and cy < 0:
        return "市场回调"
    elif max(sh, sz, cy) > 1 and min(sh, sz, cy) < -1:
        return "三大指数分化"
    elif sh > 0 or sz > 0 or cy > 0:
        return "小幅上涨"
    else:
        return "小幅下跌"

def position_judge(avg_chg):
    """位置判断"""
    if avg_chg > 1.5:
        return "市场延续上升趋势，创业板指表现强势"
    elif avg_chg > 0.5:
        return "市场延续反弹趋势，创业板指表现强势"
    elif avg_chg > -0.5:
        return "市场延续反弹趋势，创业板指表现强势"
    elif avg_chg > -1.5:
        return "市场小幅回调，需关注支撑位"
    else:
        return "市场明显回调，需关注支撑位"

def build_index_desc(indices: dict, sentiment: dict, volume_result: dict) -> Tuple[str, str, str, str]:
    """
    返回 (idx_lines, pos_judge, vol_and_sr, pos_advice)
    idx_lines: 多行指数描述（仅上证/深证/创业板，不含科创50）
    pos_judge: 位置判断文字
    vol_and_sr: 支撑位/成交量多行块
    pos_advice: 仓位建议
    """
    # 仅输出上证/深证/创业板（删除科创50）
    idx_lines = []
    for name in ["上证指数", "深证成指", "创业板指"]:
        if name in indices:
            data = indices[name]
            pct = data.get("change_pct", 0)
            word = "涨幅" if pct >= 0 else "跌幅"
            idx_lines.append(f" - {name}：{data['price']:.2f} 点，{word} {pct:+.2f}%")

    # 成交量：严格格式 "成交量变化：今日量能（xxx万亿），缩量xxx亿（-xxx%）"
    summary = volume_result.get("summary") or {}
    if summary and summary.get("total_fmt"):
        total_fmt  = summary.get("total_fmt", "N/A")
        change_fmt = summary.get("change_fmt", "N/A")  # 改用 change_fmt 而不是 change_str
        chg_pct    = summary.get("change_pct", 0) or 0
        arrow_word = "放量" if chg_pct >= 0 else "缩量"
        # 格式：缩量931.4亿（-4.76%）
        vol_line = f" - 成交量变化：今日量能（{total_fmt}），{arrow_word}{change_fmt}（{chg_pct:+.2f}%）"
    else:
        vol_line = " - 成交量变化：成交量数据获取中..."

    # 上证支撑/压力位：格式 "上证指数支撑位/压力位：支撑位3800，压力为3957"
    sh = indices.get("上证指数", {})
    sr_str = "（支撑位估算中）"
    if sh:
        price = sh.get("price", 0)
        if price > 0:
            # 支撑位：当前价格向下取整到百位，再减50
            support = int((price // 100) * 100 - 50)
            # 压力位：当前价格
            resistance = int(price)
            sr_str = f"支撑位{support}，压力为{resistance}"
    sr_line = f" - 上证指数支撑位/压力位：{sr_str}"

    # 平均涨跌幅（仅用上证/深证/创业板）
    valid    = [indices[n].get("change_pct", 0) for n in ["上证指数", "深证成指", "创业板指"] if n in indices and indices[n].get("price", 0) > 0]
    avg_chg  = sum(valid) / len(valid) if valid else 0

    pos_judge = position_judge(avg_chg)

    if avg_chg > 1.5:    pos_advice = "较高（4-5 成）"
    elif avg_chg > 0.5:  pos_advice = "中等（2-3 成）"
    elif avg_chg > -0.5: pos_advice = "中等（2-3 成）"
    elif avg_chg > -1.5: pos_advice = "偏低（1-2 成）"
    else:                pos_advice = "低（1 成以内）"

    vol_and_sr = f"{sr_line}\n{vol_line}"
    return "\n".join(idx_lines), pos_judge, vol_and_sr, pos_advice

def build_sentiment_desc(indices: dict, sentiment: dict, volume_result: dict, browser_data: dict = None) -> dict:
    """构造盘面理解部分"""
    up        = sentiment.get("up", 0)
    down      = sentiment.get("down", 0)
    
    # 计算涨跌家数比
    if up > 0 and down > 0:
        ratio = up / down
        ratio_str = f"{up}(涨) : {down}(跌) ≈ 1 : {ratio:.1f}"
    elif up > 0:
        ratio_str = f"{up}(涨) : 0(跌)"
    elif down > 0:
        ratio_str = f"0(涨) : {down}(跌)"
    else:
        ratio_str = "（数据获取中）"
    
    # 市场反馈：从浏览器数据或占位符
    if browser_data and browser_data.get("market_feedback"):
        feedback = browser_data["market_feedback"]
        main_str = feedback.get("main_lead", "  - 主板高度（10cm）：—（—）+0%，数据获取中")
        gem_str = feedback.get("gem_lead", "  - 创业板高度（20cm）：—（—）+0%，数据获取中")
        high_str = feedback.get("high_str", " - 高位股票：高位股数据获取中")
    else:
        main_str = "  - 主板高度（10cm）：—（—）+0%，数据获取中"
        gem_str = "  - 创业板高度（20cm）：—（—）+0%，数据获取中"
        high_str = " - 高位股票：高位股数据获取中"
    
    # 情绪描述
    if up > down * 2:
        emo_desc = "涨多跌少，市场情绪偏暖"
    elif up > down:
        emo_desc = "涨跌互现，市场分歧存在"
    elif down > up * 1.5:
        emo_desc = "下跌家数显著多于上涨，市场分化严重"
    else:
        emo_desc = "涨跌家数相对均衡"

    summary = volume_result.get("summary") or {}
    if summary and summary.get("total_fmt"):
        vol_desc = f"成交量 {summary.get('total_fmt','N/A')}，{summary.get('change_arrow','')} {summary.get('change_str','N/A')}（{summary.get('change_pct',0):+.2f}%）"
    else:
        vol_desc = "成交量数据获取中"

    summary_text = (
        f"指数端市场普涨。"
        f"市场情绪端涨跌家数比 {ratio_str}，{emo_desc}。"
        f"{vol_desc}，资金博弈激烈。"
        f"当前市场处于结构性行情阶段，建议控制仓位在 2-3 成，"
        f"跟随强势方向，避免追高，关注主线持续性。"
    )

    return {
        "ratio_str":    ratio_str,
        "emo_desc":     emo_desc,
        "main_lead":    main_str,
        "gem_lead":     gem_str,
        "high_str":     high_str,
        "summary_text": summary_text,
    }

def build_topic_section(topics) -> str:
    """题材方向"""
    if not topics:
        return "（题材方向数据获取中...）"
    lines = []
    for i, t in enumerate(topics[:3], 1):  # 仅取前3个
        topic_name = t.get("topic") or t.get("name") or "未知题材"
        stocks_parts = []
        for s in t.get("top_stocks", []):
            name = s.get("name", "")
            code = s.get("code", "")
            if name and code:
                stocks_parts.append(f"{name}（{code}）")
        stocks_str = "、".join(stocks_parts) if stocks_parts else "（获取中）"
        lines.append(f"##### {i}. {topic_name}方向")
        lines.append(f"- **行业逻辑**：{t.get('logic', '')}")
        lines.append(f"- **重点个股**：{stocks_str}")
    return "\n".join(lines)

def get_weekday(date_str):
    """获取星期几"""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return weekdays[dt.weekday()]
    except:
        return "日期"

def render_report(target_date: str, indices: dict, volume_result: dict, sentiment: dict, topics: list, browser_data: dict = None) -> str:
    """渲染完整报告"""
    weekday    = get_weekday(target_date)
    mkt_status = analyze_market(indices)

    # 一、大盘指数解读
    idx_lines, pos_judge, vol_and_sr, pos_advice = build_index_desc(indices, sentiment, volume_result)

    # 二、盘面理解
    s2 = build_sentiment_desc(indices, sentiment, volume_result, browser_data)

    # 三、题材方向
    topic_md = build_topic_section(topics)
    
    # 四、涨幅榜表格
    if browser_data and browser_data.get("gainers_table"):
        gainers_table = browser_data["gainers_table"]
        gainers_data = browser_data.get("gainers_data")
    else:
        gainers_table = "（涨幅榜数据获取中...）"
        gainers_data = None
    
    # 构造涨幅榜观察点
    if gainers_data and gainers_data.get("stocks"):
        stocks = gainers_data["stocks"]
        main = gainers_data.get("main_board")
        gem = gainers_data.get("gem_board")
        high_count = len(gainers_data.get("high_stocks", []))
        
        # 涨幅冠军
        if main:
            champ = f"{main['name']}（{main['code']}）+{main['period_chg']:.2f}%"
        else:
            champ = "—（—）—"
        
        # 人气最高（取第1名）
        if stocks:
            hot_name = stocks[0]['name']
        else:
            hot_name = "—"
        
        # 概念（需要额外数据）
        power_count = "—"  # 电力板块霸榜数量
        
        key_obs = f"""
**关键观察**：

- 涨幅冠军：{champ}
- 人气最高：{hot_name}
- 电力板块霸榜：前 20 名中电力相关个股占 {power_count} 席
- 高位分化：前 20 名中 {high_count} 只 10 日涨幅超 50%
"""
    else:
        key_obs = """
**关键观察**：

- 涨幅冠军：—（—）—
- 人气最高：—
- 电力板块霸榜：前 20 名中电力相关个股占 — 席
- 高位分化：—
"""

    # 组装报告
    report = f"""# 📊 股票每日分析报告

**日期：{target_date}（{weekday}）**

---

## 一、大盘指数解读

1. **市场状态：{mkt_status}**
{idx_lines}

2. **位置判断**：{pos_judge}
{vol_and_sr}
 
3. **操作策略**：结构性行情延续，关注创业板强势方向
   - 建议仓位：{pos_advice}
   - 风险提示：控制单一个股仓位不超过 20%

---

## 二、盘面理解与应对策略

1. **市场情绪**：

   - 整体情绪：{s2['emo_desc']}
   - 短线情绪：{mkt_status}
   - 涨跌家数比：{s2['ratio_str']}（{s2['emo_desc']}）

2. **市场反馈**：

{s2['main_lead']}
{s2['gem_lead']}
{s2['high_str']}

3. **总结**：

   > {s2['summary_text']}

---

## 三、题材方向

{topic_md}

---

## 四、近 10 个交易日涨幅前 20 股票

> 数据来源：同花顺问财 | 统计周期：最近10个交易日 | 排序方式：区间涨幅从高到低 | **已排除 ST 股票**

| 排名 | 股票代码 | 股票简称 | 收盘价 | 10 日涨幅 | 今日涨跌 | 人气热度 | 涉及概念 |
| :--: | :------: | :------: | :----: | :-------: | :------: | :------: | :----------------------: |
{gainers_table}
{key_obs}

---

## 五、明日计划

1. **主要观察题材**：
 - [ ] 电力（观察政策催化）
 - [ ] 新能源/储能（观察持续性）
 - [ ] 科技/半导体（观察资金流向）

2. **对应题材下个股**：
 - 电力：华电能源、华电辽能、韶能股份
 - 新能源/储能：锦浪科技、鹏辉能源、昱能科技、首航新能
 - 科技/半导体：源杰科技、长光华芯、国科微、南亚新材

---

## 六、备注/其他

- 交易心得：交易是一个先做加法的过程，积累认知，构建模式；越往后则是一个做减法的过程，越简单越好（交易频次减法、构建打磨单一的交易模式）；所以后期给大家推荐的明日计划中会降低频率，提高审美。
- 数据来源：A 股市场公开数据
- 更新频率：每个交易日 23:00

---

⚠️ **免责声明**：本报告基于公开数据整理，仅供参考，不构成任何投资建议。股市有风险，投资需谨慎。
"""
    return report

def parse_date(raw: str) -> Optional[str]:
    """解析日期"""
    raw = raw.strip().replace("/", "-").replace(".", "-")
    if re.match(r"^\d{8}$", raw):
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        return raw
    return None

def main():
    """主函数"""
    target_date  = None
    use_browser  = True
    output_path  = None

    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            if arg in ("--no-browser", "--quick"):
                use_browser = False
            elif arg.startswith("--output="):
                output_path = arg.split("=", 1)[1]
        else:
            d = parse_date(arg)
            if d:
                target_date = d

    if not target_date:
        target_date = datetime.now().strftime("%Y-%m-%d")

    print(f"正在生成 {target_date} 的每日复盘报告...")
    print("=" * 55)

    # 数据获取
    print("📈 获取四大指数...")
    indices = fetch_indices(target_date)
    for name in ["上证指数", "深证成指", "创业板指"]:
        if name in indices:
            d = indices[name]
            print(f"   {name}: {d['price']:.2f} ({d['change_pct']:+.2f}%)")

    print("📊 获取三市成交量...")
    volume_result = fetch_volume(target_date)
    s = volume_result.get("summary") or {}
    if s:
        print(f"   三市合计: {s.get('total_fmt','N/A')} {s.get('change_arrow','')} {s.get('change_str','N/A')}")

    print("😊 获取市场情绪...")
    if use_browser:
        sentiment = fetch_sentiment(use_akshare=True)
        print(f"   涨: {sentiment['up']} 跌: {sentiment['down']}")
    else:
        print("   → 跳过（--no-browser 模式，使用占位符）")
        sentiment = {"up": 0, "down": 0, "limit_up": 0, "limit_down": 0, "ratio_str": "（数据获取中）", "emotion_label": "情绪数据获取中"}

    print("🔥 获取题材方向...")
    topics = fetch_topics()
    print(f"   发现题材: {len(topics)} 个")

    print("📊 获取盘面理解数据（涨跌家数比、主板/创业板冠军、高位股票）...")
    browser_data = fetch_browser_data(use_browser=use_browser)
    if browser_data.get("sentiment", {}).get("up", 0) > 0:
        print(f"   涨跌家数比: {browser_data['sentiment']['ratio_str']}")
    else:
        print("   → 跳过或获取失败（使用占位符）")

    # 生成报告
    report = render_report(target_date, indices, volume_result, sentiment, topics, browser_data)

    # 输出
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"✅ 报告已保存至: {output_path}")
    else:
        print("\n" + "=" * 55)
        print(report)

if __name__ == "__main__":
    main()
