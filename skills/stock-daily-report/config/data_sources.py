# -*- coding: utf-8 -*-
"""
数据源优先级配置
定义各类数据的首选、降级、备用数据源
"""

DATA_SOURCE_PRIORITY = {
    # === 近 10 日涨幅排名 ===
    "top_gainers": {
        "primary": "clawhub:astock-top-gainers",
        "fallback": "browser:iwencai",
        "backup": None,
        "description": "近 10 日涨幅排名前 20 股票（排除 ST）"
    },
    
    # === 大盘指数数据（四市）===
    "index_data": {
        "primary": "local:cn-stock-volume",
        "fallback": "browser:eastmoney",
        "backup": "akshare",
        "description": "沪市/深市/创业板/北交所指数及成交数据"
    },
    
    # === 股票题材概念 ===
    "themes": {
        "primary": "clawhub:ths-stock-themes",
        "fallback": "browser:iwencai",
        "backup": None,
        "description": "个股题材概念及同花顺人气排名"
    },
    
    # === 市场情绪（涨跌家数）===
    "market_sentiment": {
        "primary": "browser:eastmoney",
        "fallback": "akshare",
        "backup": None,
        "description": "上涨/下跌/涨停/跌停家数"
    },
    
    # === 板块资金流向 ===
    "sector_flow": {
        "primary": "browser:eastmoney",
        "fallback": "akshare",
        "backup": None,
        "description": "行业/概念板块资金流向"
    },
}

# 数据验证阈值
VALIDATION_THRESHOLDS = {
    "max_index_change_pct": 10.0,  # 指数涨跌幅最大合理值（%）
    "max_stock_gain_pct": 200.0,   # 个股涨幅最大合理值（%）
    "min_volume": 0,               # 最小成交额（亿）
    "st_check_enabled": True,      # 是否启用 ST 股票检查
}
