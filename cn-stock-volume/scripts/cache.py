#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据缓存模块

功能：
- 缓存 Browser 获取的数据，避免重复调用
- 支持按日期存储和读取
- 自动清理过期缓存
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 24):
        """
        初始化缓存
        
        参数：
            cache_dir: 缓存目录（默认：~/.jvs/.openclaw/workspace/.cache）
            ttl_hours: 缓存有效期（小时），默认 24 小时
        """
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.home() / ".jvs/.openclaw/workspace/.cache"
        
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用 key 的哈希值作为文件名，避免特殊字符
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Dict]:
        """
        从缓存读取数据
        
        参数：
            key: 缓存键（如："browser:2026-03-21"）
        
        返回：
            缓存数据，如果过期或不存在则返回 None
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查是否过期
            cached_at = datetime.fromisoformat(data['_cached_at'])
            age = datetime.now() - cached_at
            
            if age > timedelta(hours=self.ttl_hours):
                # 过期，删除缓存
                cache_path.unlink()
                return None
            
            return data
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # 缓存文件损坏，删除
            try:
                cache_path.unlink()
            except:
                pass
            return None
    
    def set(self, key: str, data: Dict, metadata: Optional[Dict] = None):
        """
        写入缓存
        
        参数：
            key: 缓存键
            data: 要缓存的数据
            metadata: 可选元数据（如数据源、耗时等）
        """
        cache_path = self._get_cache_path(key)
        
        cache_data = {
            '_cached_at': datetime.now().isoformat(),
            '_key': key,
            'data': data,
        }
        
        if metadata:
            cache_data['_metadata'] = metadata
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        参数：
            key: 缓存键
        
        返回：
            是否成功删除
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except:
                return False
        
        return False
    
    def clear(self, older_than_hours: Optional[int] = None):
        """
        清理缓存
        
        参数：
            older_than_hours: 清理超过此时长的缓存（None=清理全部）
        """
        if not self.cache_dir.exists():
            return
        
        cutoff = datetime.now() - timedelta(hours=older_than_hours) if older_than_hours else None
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                cached_at = datetime.fromisoformat(data.get('_cached_at', ''))
                
                if cutoff is None or cached_at < cutoff:
                    cache_file.unlink()
            
            except:
                # 文件损坏，直接删除
                try:
                    cache_file.unlink()
                except:
                    pass
    
    def get_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        返回：
            {
                "total_files": int,
                "total_size_bytes": int,
                "oldest_cache": str,
                "newest_cache": str,
            }
        """
        if not self.cache_dir.exists():
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "oldest_cache": None,
                "newest_cache": None,
            }
        
        files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in files)
        
        times = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    times.append(datetime.fromisoformat(data['_cached_at']))
            except:
                pass
        
        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "oldest_cache": min(times).isoformat() if times else None,
            "newest_cache": max(times).isoformat() if times else None,
        }


# 全局缓存实例（默认 24 小时 TTL）
_default_cache = None

def get_cache(ttl_hours: int = 24) -> DataCache:
    """获取全局缓存实例"""
    global _default_cache
    if _default_cache is None or _default_cache.ttl_hours != ttl_hours:
        _default_cache = DataCache(ttl_hours=ttl_hours)
    return _default_cache


# 缓存键生成函数
def make_browser_key(date: str) -> str:
    """生成 Browser 数据缓存键"""
    return f"browser:{date}"

def make_api_key(source: str, date: str) -> str:
    """生成 API 数据缓存键"""
    return f"api:{source}:{date}"


if __name__ == "__main__":
    # 测试缓存功能
    cache = DataCache(ttl_hours=1)
    
    # 写入缓存
    cache.set("test:key", {"data": "test_value"}, {"source": "test"})
    
    # 读取缓存
    result = cache.get("test:key")
    print(f"读取缓存：{result}")
    
    # 统计信息
    stats = cache.get_stats()
    print(f"缓存统计：{stats}")
    
    # 清理缓存
    cache.delete("test:key")
    print("已删除测试缓存")
