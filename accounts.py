#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Z.ai 2 API - 账号管理模块
提供完整的账号 CRUD API，支持多账号轮询、负载均衡、状态监控
"""

import os
import json
import time
import random
import hashlib
import logging
import threading
import requests
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, request, jsonify, make_response
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

# 创建蓝图
accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')

# 账号文件路径
ACCOUNTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.json")

# 默认配置
DEFAULT_CONFIG = {
    "mode": "round-robin",           # 轮询模式: round-robin, random, least-used, health-based
    "retry_failed": True,            # 失败时自动重试其他账号
    "max_retries": 3,                # 最大重试次数
    "health_check_interval": 300,    # 健康检查间隔（秒）
    "auto_disable_threshold": 5,     # 连续失败次数达到此值自动禁用
    "cooldown_period": 60,           # 失败后冷却时间（秒）
    "max_concurrent": 0,             # 最大并发数（0=不限制）
    "token_refresh": True,           # 自动刷新 token
}

# 全局状态
_accounts_lock = threading.Lock()
_accounts_data: Dict = {
    "accounts": [],
    "config": DEFAULT_CONFIG.copy(),
    "stats": {
        "total_requests": 0,
        "total_errors": 0,
        "last_reset": int(time.time() * 1000)
    }
}


class AccountManager:
    """账号管理器"""
    
    def __init__(self):
        self._load()
    
    def _load(self):
        """从文件加载账号数据"""
        global _accounts_data
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    _accounts_data["accounts"] = data.get("accounts", [])
                    _accounts_data["config"] = {**DEFAULT_CONFIG, **data.get("config", {})}
            except Exception as e:
                log.error("加载账号文件失败: %s", e)
    
    def _save(self):
        """保存账号数据到文件"""
        try:
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "accounts": _accounts_data["accounts"],
                    "config": _accounts_data["config"]
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.error("保存账号文件失败: %s", e)
    
    def _generate_id(self) -> str:
        """生成唯一 ID"""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]
    
    def validate_cookie(self, cookie_str: str) -> Optional[Dict]:
        """验证 cookie 是否有效"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": cookie_str,
                "Accept": "*/*",
                "X-FE-Version": "prod-fe-1.0.111",
            }
            r = requests.get("https://chat.z.ai/api/v1/auths/", headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if data.get("id") and data.get("name"):
                    return {
                        "user_id": data["id"],
                        "user_name": data["name"],
                        "token": data.get("token", ""),
                    }
        except Exception as e:
            log.debug("Cookie 验证失败: %s", e)
        return None
    
    def get_all(self, mask_sensitive: bool = True) -> List[Dict]:
        """获取所有账号"""
        with _accounts_lock:
            accounts = _accounts_data["accounts"].copy()
            if mask_sensitive:
                for acc in accounts:
                    if "cookie" in acc and acc["cookie"]:
                        acc["cookie"] = "***" + acc["cookie"][-8:] if len(acc["cookie"]) > 8 else "***"
                    if "token" in acc and acc["token"]:
                        acc["token"] = "***" + acc["token"][-8:] if len(acc["token"]) > 8 else "***"
            return accounts
    
    def get_active_accounts(self) -> List[Dict]:
        """获取所有启用的账号"""
        with _accounts_lock:
            return [acc for acc in _accounts_data["accounts"] if acc.get("is_active", True)]
    
    def get_account(self, account_id: str, mask_sensitive: bool = True) -> Optional[Dict]:
        """获取指定账号"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    if mask_sensitive:
                        acc = acc.copy()
                        if "cookie" in acc and acc["cookie"]:
                            acc["cookie"] = "***" + acc["cookie"][-8:] if len(acc["cookie"]) > 8 else "***"
                        if "token" in acc and acc["token"]:
                            acc["token"] = "***" + acc["token"][-8:] if len(acc["token"]) > 8 else "***"
                    return acc
        return None
    
    def add_account(self, cookie: str, label: str = "", auto_enable: bool = True) -> Dict:
        """添加账号"""
        with _accounts_lock:
            # 检查是否已存在
            for acc in _accounts_data["accounts"]:
                if acc.get("cookie") == cookie:
                    return {"success": False, "error": "该 Cookie 已存在"}
            
            # 验证 cookie
            user_info = self.validate_cookie(cookie)
            if not user_info:
                return {"success": False, "error": "Cookie 无效或网络错误"}
            
            account = {
                "id": self._generate_id(),
                "cookie": cookie,
                "token": user_info.get("token", ""),
                "user_id": user_info["user_id"],
                "user_name": user_info["user_name"],
                "label": label,
                "is_active": auto_enable,
                "status": "healthy",
                "added_at": datetime.now().isoformat(),
                "last_used": None,
                "last_error": None,
                "error_count": 0,
                "success_count": 0,
                "total_requests": 0,
                "avg_response_time": 0,
                "cooldown_until": 0,
            }
            _accounts_data["accounts"].append(account)
            self._save()
            
            log.info("账号已添加: %s (%s)", user_info["user_name"], user_info["user_id"])
            return {"success": True, "account": {**account, "cookie": "***" + cookie[-8:] if len(cookie) > 8 else "***"}}
    
    def add_account_batch(self, cookies: List[str], label: str = "") -> Dict:
        """批量添加账号"""
        results = {
            "total": len(cookies),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        for i, cookie in enumerate(cookies):
            cookie = cookie.strip()
            if not cookie:
                results["skipped"] += 1
                results["details"].append({"index": i + 1, "status": "skipped", "reason": "空 Cookie"})
                continue
            
            result = self.add_account(cookie, label)
            if result["success"]:
                results["success"] += 1
                results["details"].append({"index": i + 1, "status": "success", "account": result["account"]})
            else:
                results["failed"] += 1
                results["details"].append({"index": i + 1, "status": "failed", "reason": result["error"]})
        
        return {"success": True, "results": results}
    
    def update_account(self, account_id: str, updates: Dict) -> Dict:
        """更新账号"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    # 允许更新的字段
                    allowed_fields = ["label", "is_active"]
                    for field in allowed_fields:
                        if field in updates:
                            acc[field] = updates[field]
                    
                    # 如果 cookie 变更，重新验证
                    if "cookie" in updates and updates["cookie"] != acc.get("cookie"):
                        user_info = self.validate_cookie(updates["cookie"])
                        if not user_info:
                            return {"success": False, "error": "新 Cookie 无效或网络错误"}
                        acc["cookie"] = updates["cookie"]
                        acc["token"] = user_info.get("token", "")
                        acc["user_id"] = user_info["user_id"]
                        acc["user_name"] = user_info["user_name"]
                    
                    self._save()
                    return {"success": True, "account": self.get_account(account_id)}
            
            return {"success": False, "error": "账号不存在"}
    
    def delete_account(self, account_id: str) -> Dict:
        """删除账号"""
        with _accounts_lock:
            for i, acc in enumerate(_accounts_data["accounts"]):
                if acc.get("id") == account_id:
                    _accounts_data["accounts"].pop(i)
                    self._save()
                    log.info("账号已删除: %s", acc.get("user_name"))
                    return {"success": True}
            
            return {"success": False, "error": "账号不存在"}
    
    def delete_batch(self, account_ids: List[str]) -> Dict:
        """批量删除账号"""
        deleted = 0
        with _accounts_lock:
            _accounts_data["accounts"] = [
                acc for acc in _accounts_data["accounts"]
                if acc.get("id") not in account_ids
            ]
            deleted = len(account_ids)
            self._save()
        
        return {"success": True, "deleted": deleted}
    
    def toggle_account(self, account_id: str) -> Dict:
        """切换账号启用状态"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["is_active"] = not acc.get("is_active", True)
                    self._save()
                    return {"success": True, "is_active": acc["is_active"]}
            
            return {"success": False, "error": "账号不存在"}
    
    def get_next_account(self) -> Optional[Dict]:
        """获取下一个可用账号（根据轮询策略）"""
        with _accounts_lock:
            config = _accounts_data["config"]
            now = time.time() * 1000
            
            # 筛选可用账号
            available = []
            for acc in _accounts_data["accounts"]:
                if not acc.get("is_active", True):
                    continue
                # 检查冷却期
                if acc.get("cooldown_until", 0) > now:
                    continue
                available.append(acc)
            
            if not available:
                return None
            
            mode = config.get("mode", "round-robin")
            
            if mode == "random":
                return random.choice(available)
            
            elif mode == "least-used":
                # 选择使用次数最少的
                return min(available, key=lambda a: a.get("total_requests", 0))
            
            elif mode == "health-based":
                # 优先选择健康的账号
                healthy = [a for a in available if a.get("status") == "healthy"]
                if healthy:
                    # 在健康账号中轮询
                    return min(healthy, key=lambda a: a.get("last_used") or 0)
                return available[0]
            
            else:  # round-robin
                # 选择最久未使用的
                return min(available, key=lambda a: a.get("last_used") or 0)
    
    def record_success(self, account_id: str, response_time: float = 0):
        """记录账号请求成功"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["last_used"] = datetime.now().isoformat()
                    acc["success_count"] = acc.get("success_count", 0) + 1
                    acc["total_requests"] = acc.get("total_requests", 0) + 1
                    acc["error_count"] = 0  # 重置连续错误计数
                    acc["status"] = "healthy"
                    acc["cooldown_until"] = 0
                    
                    # 更新平均响应时间
                    old_avg = acc.get("avg_response_time", 0)
                    count = acc.get("success_count", 1)
                    acc["avg_response_time"] = (old_avg * (count - 1) + response_time) / count
                    
                    _accounts_data["stats"]["total_requests"] += 1
                    self._save()
                    return
    
    def record_failure(self, account_id: str, error: str = ""):
        """记录账号请求失败"""
        with _accounts_lock:
            config = _accounts_data["config"]
            now = time.time() * 1000
            
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["last_error"] = error
                    acc["error_count"] = acc.get("error_count", 0) + 1
                    acc["total_requests"] = acc.get("total_requests", 0) + 1
                    _accounts_data["stats"]["total_errors"] += 1
                    
                    # 检查是否需要自动禁用
                    if acc["error_count"] >= config.get("auto_disable_threshold", 5):
                        acc["is_active"] = False
                        acc["status"] = "disabled"
                        log.warning("账号已自动禁用: %s (连续失败 %d 次)", acc.get("user_name"), acc["error_count"])
                    
                    # 设置冷却期
                    cooldown = config.get("cooldown_period", 60) * 1000
                    acc["cooldown_until"] = now + cooldown
                    
                    self._save()
                    return
    
    def reset_stats(self):
        """重置统计信息"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                acc["error_count"] = 0
                acc["success_count"] = 0
                acc["total_requests"] = 0
                acc["avg_response_time"] = 0
                acc["status"] = "healthy"
                acc["cooldown_until"] = 0
                acc["last_error"] = None
            _accounts_data["stats"] = {
                "total_requests": 0,
                "total_errors": 0,
                "last_reset": int(time.time() * 1000)
            }
            self._save()
    
    def get_config(self) -> Dict:
        """获取配置"""
        return _accounts_data["config"].copy()
    
    def update_config(self, config: Dict) -> Dict:
        """更新配置"""
        with _accounts_lock:
            _accounts_data["config"].update(config)
            self._save()
            return {"success": True, "config": self.get_config()}
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with _accounts_lock:
            accounts = _accounts_data["accounts"]
            active = [a for a in accounts if a.get("is_active", True)]
            healthy = [a for a in accounts if a.get("status") == "healthy"]
            
            return {
                "total_accounts": len(accounts),
                "active_accounts": len(active),
                "healthy_accounts": len(healthy),
                "total_requests": _accounts_data["stats"]["total_requests"],
                "total_errors": _accounts_data["stats"]["total_errors"],
                "error_rate": (
                    _accounts_data["stats"]["total_errors"] / _accounts_data["stats"]["total_requests"] * 100
                    if _accounts_data["stats"]["total_requests"] > 0 else 0
                ),
                "last_reset": _accounts_data["stats"]["last_reset"]
            }
    
    def health_check(self, account_id: str = None) -> Dict:
        """健康检查"""
        accounts_to_check = []
        with _accounts_lock:
            if account_id:
                for acc in _accounts_data["accounts"]:
                    if acc.get("id") == account_id:
                        accounts_to_check.append(acc)
                        break
            else:
                accounts_to_check = _accounts_data["accounts"].copy()
        
        results = []
        for acc in accounts_to_check:
            cookie = acc.get("cookie", "")
            if not cookie:
                results.append({
                    "id": acc.get("id"),
                    "user_name": acc.get("user_name"),
                    "status": "no_cookie"
                })
                continue
            
            user_info = self.validate_cookie(cookie)
            if user_info:
                with _accounts_lock:
                    acc["status"] = "healthy"
                    acc["token"] = user_info.get("token", "")
                results.append({
                    "id": acc.get("id"),
                    "user_name": acc.get("user_name"),
                    "status": "healthy"
                })
            else:
                with _accounts_lock:
                    acc["status"] = "unhealthy"
                results.append({
                    "id": acc.get("id"),
                    "user_name": acc.get("user_name"),
                    "status": "unhealthy"
                })
        
        self._save()
        return {"success": True, "results": results}
    
    def search_accounts(self, query: str = "", status: str = None, label: str = None, 
                       is_active: bool = None, sort_by: str = "added_at", 
                       sort_order: str = "desc", page: int = 1, 
                       page_size: int = 20) -> Dict:
        """搜索和过滤账号"""
        with _accounts_lock:
            accounts = _accounts_data["accounts"].copy()
        
        # 应用过滤条件
        filtered = []
        for acc in accounts:
            # 文本搜索（用户名、标签、用户ID）
            if query:
                query_lower = query.lower()
                match = False
                if query_lower in (acc.get("user_name") or "").lower():
                    match = True
                if query_lower in (acc.get("label") or "").lower():
                    match = True
                if query_lower in (acc.get("user_id") or "").lower():
                    match = True
                if not match:
                    continue
            
            # 状态过滤
            if status and acc.get("status") != status:
                continue
            
            # 标签过滤
            if label and acc.get("label") != label:
                continue
            
            # 启用状态过滤
            if is_active is not None and acc.get("is_active") != is_active:
                continue
            
            filtered.append(acc)
        
        # 排序
        reverse = sort_order.lower() == "desc"
        if sort_by == "added_at":
            filtered.sort(key=lambda x: x.get("added_at", ""), reverse=reverse)
        elif sort_by == "last_used":
            filtered.sort(key=lambda x: x.get("last_used") or "", reverse=reverse)
        elif sort_by == "total_requests":
            filtered.sort(key=lambda x: x.get("total_requests", 0), reverse=reverse)
        elif sort_by == "success_count":
            filtered.sort(key=lambda x: x.get("success_count", 0), reverse=reverse)
        elif sort_by == "error_count":
            filtered.sort(key=lambda x: x.get("error_count", 0), reverse=reverse)
        elif sort_by == "avg_response_time":
            filtered.sort(key=lambda x: x.get("avg_response_time", 0), reverse=reverse)
        elif sort_by == "priority":
            filtered.sort(key=lambda x: x.get("priority", 0), reverse=reverse)
        elif sort_by == "user_name":
            filtered.sort(key=lambda x: x.get("user_name", ""), reverse=reverse)
        
        # 分页
        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]
        
        # 隐藏敏感信息
        for acc in paged:
            if "cookie" in acc and acc["cookie"]:
                acc["cookie"] = "***" + acc["cookie"][-8:] if len(acc["cookie"]) > 8 else "***"
            if "token" in acc and acc["token"]:
                acc["token"] = "***" + acc["token"][-8:] if len(acc["token"]) > 8 else "***"
        
        return {
            "accounts": paged,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    def export_accounts(self, account_ids: List[str] = None, include_sensitive: bool = False) -> Dict:
        """导出账号数据"""
        with _accounts_lock:
            if account_ids:
                accounts = [acc for acc in _accounts_data["accounts"] if acc.get("id") in account_ids]
            else:
                accounts = _accounts_data["accounts"].copy()
        
        # 处理敏感信息
        if not include_sensitive:
            for acc in accounts:
                if "cookie" in acc and acc["cookie"]:
                    acc["cookie"] = "***" + acc["cookie"][-8:] if len(acc["cookie"]) > 8 else "***"
                if "token" in acc and acc["token"]:
                    acc["token"] = "***" + acc["token"][-8:] if len(acc["token"]) > 8 else "***"
        
        return {
            "accounts": accounts,
            "config": _accounts_data["config"].copy(),
            "exported_at": datetime.now().isoformat(),
            "count": len(accounts)
        }
    
    def import_accounts(self, accounts_data: List[Dict], overwrite: bool = False) -> Dict:
        """导入账号数据"""
        results = {
            "total": len(accounts_data),
            "imported": 0,
            "skipped": 0,
            "failed": 0,
            "details": []
        }
        
        with _accounts_lock:
            for i, acc_data in enumerate(accounts_data):
                try:
                    # 检查必填字段
                    cookie = acc_data.get("cookie")
                    if not cookie:
                        results["failed"] += 1
                        results["details"].append({"index": i + 1, "status": "failed", "reason": "缺少 cookie 字段"})
                        continue
                    
                    # 检查是否已存在
                    existing = False
                    for acc in _accounts_data["accounts"]:
                        if acc.get("cookie") == cookie:
                            existing = True
                            if overwrite:
                                # 更新现有账号
                                acc.update({k: v for k, v in acc_data.items() if k not in ["id", "added_at"]})
                                results["imported"] += 1
                                results["details"].append({"index": i + 1, "status": "updated", "account_id": acc.get("id")})
                            else:
                                results["skipped"] += 1
                                results["details"].append({"index": i + 1, "status": "skipped", "reason": "账号已存在"})
                            break
                    
                    if not existing:
                        # 添加新账号
                        account = {
                            "id": self._generate_id(),
                            "cookie": cookie,
                            "token": acc_data.get("token", ""),
                            "user_id": acc_data.get("user_id", ""),
                            "user_name": acc_data.get("user_name", ""),
                            "label": acc_data.get("label", ""),
                            "is_active": acc_data.get("is_active", True),
                            "status": acc_data.get("status", "healthy"),
                            "priority": acc_data.get("priority", 0),
                            "expires_at": acc_data.get("expires_at"),
                            "added_at": acc_data.get("added_at", datetime.now().isoformat()),
                            "last_used": acc_data.get("last_used"),
                            "last_error": acc_data.get("last_error"),
                            "error_count": acc_data.get("error_count", 0),
                            "success_count": acc_data.get("success_count", 0),
                            "total_requests": acc_data.get("total_requests", 0),
                            "avg_response_time": acc_data.get("avg_response_time", 0),
                            "cooldown_until": acc_data.get("cooldown_until", 0),
                        }
                        _accounts_data["accounts"].append(account)
                        results["imported"] += 1
                        results["details"].append({"index": i + 1, "status": "imported", "account_id": account["id"]})
                
                except Exception as e:
                    results["failed"] += 1
                    results["details"].append({"index": i + 1, "status": "failed", "reason": str(e)})
            
            self._save()
        
        return {"success": True, "results": results}
    
    def update_priority(self, account_id: str, priority: int) -> Dict:
        """更新账号优先级"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["priority"] = priority
                    self._save()
                    return {"success": True, "priority": priority}
            return {"success": False, "error": "账号不存在"}
    
    def batch_toggle(self, account_ids: List[str], is_active: bool) -> Dict:
        """批量启用/禁用账号"""
        updated = 0
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") in account_ids:
                    acc["is_active"] = is_active
                    updated += 1
            self._save()
        return {"success": True, "updated": updated}
    
    def set_expiry(self, account_id: str, expires_at: str = None) -> Dict:
        """设置账号有效期"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["expires_at"] = expires_at
                    self._save()
                    return {"success": True, "expires_at": expires_at}
            return {"success": False, "error": "账号不存在"}
    
    def reset_account_stats(self, account_id: str) -> Dict:
        """重置单个账号统计"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    acc["error_count"] = 0
                    acc["success_count"] = 0
                    acc["total_requests"] = 0
                    acc["avg_response_time"] = 0
                    acc["status"] = "healthy"
                    acc["cooldown_until"] = 0
                    acc["last_error"] = None
                    self._save()
                    return {"success": True}
            return {"success": False, "error": "账号不存在"}
    
    def get_account_details(self, account_id: str) -> Dict:
        """获取账号详细使用情况"""
        with _accounts_lock:
            for acc in _accounts_data["accounts"]:
                if acc.get("id") == account_id:
                    # 计算额外统计信息
                    total = acc.get("total_requests", 0)
                    success = acc.get("success_count", 0)
                    error = acc.get("error_count", 0)
                    
                    details = {
                        **acc,
                        "success_rate": (success / total * 100) if total > 0 else 0,
                        "error_rate": (error / total * 100) if total > 0 else 0,
                        "is_expired": False,
                        "days_since_added": 0,
                        "days_since_used": None
                    }
                    
                    # 检查是否过期
                    if acc.get("expires_at"):
                        try:
                            expires = datetime.fromisoformat(acc["expires_at"].replace('Z', '+00:00'))
                            details["is_expired"] = datetime.now(expires.tzinfo) > expires
                        except:
                            pass
                    
                    # 计算添加天数
                    if acc.get("added_at"):
                        try:
                            added = datetime.fromisoformat(acc["added_at"].replace('Z', '+00:00'))
                            details["days_since_added"] = (datetime.now(added.tzinfo) - added).days
                        except:
                            pass
                    
                    # 计算上次使用天数
                    if acc.get("last_used"):
                        try:
                            last_used = datetime.fromisoformat(acc["last_used"].replace('Z', '+00:00'))
                            details["days_since_used"] = (datetime.now(last_used.tzinfo) - last_used).days
                        except:
                            pass
                    
                    # 隐藏敏感信息
                    if "cookie" in details and details["cookie"]:
                        details["cookie"] = "***" + details["cookie"][-8:] if len(details["cookie"]) > 8 else "***"
                    if "token" in details and details["token"]:
                        details["token"] = "***" + details["token"][-8:] if len(details["token"]) > 8 else "***"
                    
                    return {"success": True, "account": details}
            
            return {"success": False, "error": "账号不存在"}
    
    def get_all_labels(self) -> List[str]:
        """获取所有标签"""
        with _accounts_lock:
            labels = set()
            for acc in _accounts_data["accounts"]:
                label = acc.get("label")
                if label:
                    labels.add(label)
            return sorted(list(labels))
    
    def batch_delete_by_filter(self, status: str = None, label: str = None, 
                               is_active: bool = None, older_than_days: int = None) -> Dict:
        """根据条件批量删除账号"""
        deleted = 0
        with _accounts_lock:
            accounts_to_keep = []
            for acc in _accounts_data["accounts"]:
                should_delete = True
                
                # 状态过滤
                if status and acc.get("status") != status:
                    should_delete = False
                
                # 标签过滤
                if label and acc.get("label") != label:
                    should_delete = False
                
                # 启用状态过滤
                if is_active is not None and acc.get("is_active") != is_active:
                    should_delete = False
                
                # 时间过滤
                if older_than_days is not None and acc.get("added_at"):
                    try:
                        added = datetime.fromisoformat(acc["added_at"].replace('Z', '+00:00'))
                        if (datetime.now(added.tzinfo) - added).days <= older_than_days:
                            should_delete = False
                    except:
                        should_delete = False
                
                if should_delete:
                    deleted += 1
                else:
                    accounts_to_keep.append(acc)
            
            _accounts_data["accounts"] = accounts_to_keep
            self._save()
        
        return {"success": True, "deleted": deleted}


# 全局实例
_manager: Optional[AccountManager] = None


def init_accounts():
    """初始化账号管理器"""
    global _manager
    _manager = AccountManager()
    return _manager


def get_manager() -> AccountManager:
    """获取账号管理器实例"""
    if _manager is None:
        raise RuntimeError("Account manager not initialized")
    return _manager


def get_next_account() -> Optional[Dict]:
    """获取下一个可用账号（供 app.py 使用）"""
    return get_manager().get_next_account()


def record_success(account_id: str, response_time: float = 0):
    """记录请求成功"""
    get_manager().record_success(account_id, response_time)


def record_failure(account_id: str, error: str = ""):
    """记录请求失败"""
    get_manager().record_failure(account_id, error)


# ============ API 路由 ============

@accounts_bp.route('', methods=['GET', 'OPTIONS'])
@accounts_bp.route('/', methods=['GET', 'OPTIONS'])
def list_accounts():
    """获取所有账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        mask_sensitive = request.args.get('mask', 'true').lower() == 'true'
        accounts = manager.get_all(mask_sensitive=mask_sensitive)
        stats = manager.get_stats()
        return jsonify({
            "success": True,
            "accounts": accounts,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>', methods=['GET', 'OPTIONS'])
def get_account(account_id):
    """获取指定账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        mask_sensitive = request.args.get('mask', 'true').lower() == 'true'
        account = manager.get_account(account_id, mask_sensitive=mask_sensitive)
        if account is None:
            return jsonify({"error": 404, "message": "账号不存在"}), 404
        return jsonify({
            "success": True,
            "account": account
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('', methods=['POST', 'OPTIONS'])
@accounts_bp.route('/', methods=['POST', 'OPTIONS'])
def add_account():
    """添加账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        
        cookie = data.get("cookie", "")
        if not cookie:
            return jsonify({"error": 400, "message": "cookie 不能为空"}), 400
        
        label = data.get("label", "")
        auto_enable = data.get("auto_enable", True)
        
        result = manager.add_account(cookie, label, auto_enable)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/batch', methods=['POST', 'OPTIONS'])
def add_accounts_batch():
    """批量添加账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        
        cookies = data.get("cookies", [])
        if not cookies:
            return jsonify({"error": 400, "message": "cookies 列表不能为空"}), 400
        
        label = data.get("label", "")
        result = manager.add_account_batch(cookies, label)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>', methods=['PUT', 'OPTIONS'])
def update_account(account_id):
    """更新账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        
        result = manager.update_account(account_id, data)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>', methods=['DELETE', 'OPTIONS'])
def delete_account(account_id):
    """删除账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.delete_account(account_id)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/batch', methods=['DELETE', 'OPTIONS'])
def delete_accounts_batch():
    """批量删除账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or "ids" not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 ids 字段"}), 400
        
        result = manager.delete_batch(data["ids"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>/toggle', methods=['POST', 'OPTIONS'])
def toggle_account(account_id):
    """切换账号启用状态"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.toggle_account(account_id)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/next', methods=['GET', 'OPTIONS'])
def get_next():
    """获取下一个可用账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        account = manager.get_next_account()
        if account:
            # 隐藏敏感信息
            safe_account = {**account}
            if "cookie" in safe_account:
                safe_account["cookie"] = "***" + safe_account["cookie"][-8:] if len(safe_account["cookie"]) > 8 else "***"
            if "token" in safe_account:
                safe_account["token"] = "***" + safe_account["token"][-8:] if len(safe_account["token"]) > 8 else "***"
            return jsonify({
                "success": True,
                "account": safe_account
            })
        else:
            return jsonify({
                "success": False,
                "error": "没有可用的账号"
            }), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/health', methods=['POST', 'OPTIONS'])
def health_check():
    """健康检查"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True) or {}
        account_id = data.get("account_id")
        result = manager.health_check(account_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/config', methods=['GET', 'OPTIONS'])
def get_config():
    """获取账号管理配置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        config = manager.get_config()
        return jsonify({
            "success": True,
            "config": config
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/config', methods=['PUT', 'OPTIONS'])
def update_config():
    """更新账号管理配置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        
        result = manager.update_config(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/stats', methods=['GET', 'OPTIONS'])
def get_stats():
    """获取统计信息"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        stats = manager.get_stats()
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/stats/reset', methods=['POST', 'OPTIONS'])
def reset_stats():
    """重置统计信息"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        manager.reset_stats()
        return jsonify({
            "success": True,
            "stats": manager.get_stats()
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/validate', methods=['POST', 'OPTIONS'])
def validate_cookie():
    """验证 Cookie"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or "cookie" not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 cookie 字段"}), 400
        
        user_info = manager.validate_cookie(data["cookie"])
        if user_info:
            return jsonify({
                "success": True,
                "valid": True,
                "user": user_info
            })
        else:
            return jsonify({
                "success": True,
                "valid": False,
                "error": "Cookie 无效或网络错误"
            })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/search', methods=['GET', 'OPTIONS'])
def search_accounts():
    """搜索和过滤账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        query = request.args.get('query', '')
        status = request.args.get('status')
        label = request.args.get('label')
        is_active_str = request.args.get('is_active')
        sort_by = request.args.get('sort_by', 'added_at')
        sort_order = request.args.get('sort_order', 'desc')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        is_active = None
        if is_active_str is not None:
            is_active = is_active_str.lower() == 'true'
        
        result = manager.search_accounts(
            query=query,
            status=status,
            label=label,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
        
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/export', methods=['GET', 'OPTIONS'])
def export_accounts():
    """导出账号数据"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        account_ids_str = request.args.get('ids', '')
        include_sensitive = request.args.get('include_sensitive', 'false').lower() == 'true'
        
        account_ids = None
        if account_ids_str:
            account_ids = [id.strip() for id in account_ids_str.split(',') if id.strip()]
        
        result = manager.export_accounts(account_ids=account_ids, include_sensitive=include_sensitive)
        return jsonify({
            "success": True,
            **result
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/import', methods=['POST', 'OPTIONS'])
def import_accounts():
    """导入账号数据"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or "accounts" not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 accounts 字段"}), 400
        
        overwrite = data.get("overwrite", False)
        result = manager.import_accounts(data["accounts"], overwrite=overwrite)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>/priority', methods=['PUT', 'OPTIONS'])
def update_priority(account_id):
    """更新账号优先级"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or "priority" not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 priority 字段"}), 400
        
        result = manager.update_priority(account_id, data["priority"])
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/batch/toggle', methods=['POST', 'OPTIONS'])
def batch_toggle():
    """批量启用/禁用账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or "ids" not in data or "is_active" not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 ids 和 is_active 字段"}), 400
        
        result = manager.batch_toggle(data["ids"], data["is_active"])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>/expiry', methods=['PUT', 'OPTIONS'])
def set_expiry(account_id):
    """设置账号有效期"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        
        expires_at = data.get("expires_at")
        result = manager.set_expiry(account_id, expires_at)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>/stats/reset', methods=['POST', 'OPTIONS'])
def reset_account_stats(account_id):
    """重置单个账号统计"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.reset_account_stats(account_id)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/<account_id>/details', methods=['GET', 'OPTIONS'])
def get_account_details(account_id):
    """获取账号详细使用情况"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.get_account_details(account_id)
        if result["success"]:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/labels', methods=['GET', 'OPTIONS'])
def get_labels():
    """获取所有标签"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        labels = manager.get_all_labels()
        return jsonify({
            "success": True,
            "labels": labels
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@accounts_bp.route('/batch/delete', methods=['POST', 'OPTIONS'])
def batch_delete_by_filter():
    """根据条件批量删除账号"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True) or {}
        
        status = data.get("status")
        label = data.get("label")
        is_active_str = data.get("is_active")
        older_than_days = data.get("older_than_days")
        
        is_active = None
        if is_active_str is not None:
            is_active = is_active_str.lower() == 'true' if isinstance(is_active_str, str) else bool(is_active_str)
        
        result = manager.batch_delete_by_filter(
            status=status,
            label=label,
            is_active=is_active,
            older_than_days=older_than_days
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500
