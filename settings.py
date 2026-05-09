#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
Z.ai 2 API - 系统设置管理模块
提供完整的设置 API，支持运行时动态配置
"""

import os
import json
import copy
import time
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, make_response
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger(__name__)

# 创建蓝图
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')

# 设置历史记录
_settings_history: List[Dict] = []
MAX_HISTORY_SIZE = 100

# 默认设置
DEFAULT_SETTINGS = {
    "source": {
        "protocol": {
            "value": "https:",
            "type": "string",
            "description": "上游服务器协议",
            "enum": ["https:", "http:"],
            "required": True
        },
        "host": {
            "value": "chat.z.ai",
            "type": "string",
            "description": "上游服务器域名",
            "required": True
        },
        "token": {
            "value": "",
            "type": "string",
            "description": "上游服务器认证令牌",
            "required": False,
            "sensitive": True
        }
    },
    "api": {
        "port": {
            "value": 8080,
            "type": "integer",
            "description": "API 服务端口",
            "min": 1,
            "max": 65535,
            "required": True
        },
        "debug": {
            "value": False,
            "type": "boolean",
            "description": "调试模式（开启后显示详细错误信息）",
            "required": True
        },
        "debug_msg": {
            "value": False,
            "type": "boolean",
            "description": "调试日志（开启后显示详细请求/响应日志）",
            "required": True
        },
        "think": {
            "value": "reasoning",
            "type": "string",
            "description": "思考链处理模式",
            "enum": ["reasoning", "think", "strip", "details", "none"],
            "required": True
        },
        "anon": {
            "value": True,
            "type": "boolean",
            "description": "访客模式（无需登录即可使用）",
            "required": True
        }
    },
    "model": {
        "default": {
            "value": "glm-4.6",
            "type": "string",
            "description": "默认模型（当请求未指定模型时使用）",
            "required": True
        },
        "mapping": {
            "value": {},
            "type": "object",
            "description": "模型映射表（将外部模型名映射到内部模型 ID）",
            "required": False
        },
        "whitelist": {
            "value": [],
            "type": "array",
            "description": "模型白名单（为空则允许所有模型）",
            "required": False
        },
        "blacklist": {
            "value": [],
            "type": "array",
            "description": "模型黑名单（优先级高于白名单）",
            "required": False
        }
    },
    "security": {
        "rate_limit": {
            "value": 0,
            "type": "integer",
            "description": "请求频率限制（每分钟请求数，0 表示不限制）",
            "min": 0,
            "max": 10000,
            "required": True
        },
        "allowed_origins": {
            "value": ["*"],
            "type": "array",
            "description": "允许的 CORS 来源",
            "required": True
        },
        "api_key": {
            "value": "",
            "type": "string",
            "description": "API 访问密钥（为空则不需要认证）",
            "required": False,
            "sensitive": True
        },
        "max_tokens": {
            "value": 0,
            "type": "integer",
            "description": "最大输出 token 数限制（0 表示不限制）",
            "min": 0,
            "max": 1000000,
            "required": True
        },
        "max_messages": {
            "value": 0,
            "type": "integer",
            "description": "最大消息数限制（0 表示不限制）",
            "min": 0,
            "max": 1000,
            "required": True
        }
    },
    "logging": {
        "level": {
            "value": "INFO",
            "type": "string",
            "description": "日志级别",
            "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "required": True
        },
        "format": {
            "value": "%(asctime)s - %(levelname)s - %(message)s",
            "type": "string",
            "description": "日志格式",
            "required": True
        },
        "max_size": {
            "value": 10,
            "type": "integer",
            "description": "日志文件最大大小（MB）",
            "min": 1,
            "max": 1000,
            "required": True
        }
    }
}


class SettingsManager:
    """设置管理器"""
    
    def __init__(self, cfg):
        self.cfg = cfg
        self._current = self._load_from_config()
        self._schema = copy.deepcopy(DEFAULT_SETTINGS)
    
    def _load_from_config(self) -> Dict:
        """从配置对象加载当前设置"""
        return {
            "source": {
                "protocol": getattr(self.cfg.source, 'protocol', 'https:'),
                "host": getattr(self.cfg.source, 'host', 'chat.z.ai'),
                "token": getattr(self.cfg.source, 'token', '')
            },
            "api": {
                "port": getattr(self.cfg.api, 'port', 8080),
                "debug": getattr(self.cfg.api, 'debug', False),
                "debug_msg": getattr(self.cfg.api, 'debug_msg', False),
                "think": getattr(self.cfg.api, 'think', 'reasoning'),
                "anon": getattr(self.cfg.api, 'anon', True)
            },
            "model": {
                "default": getattr(self.cfg.model, 'default', 'glm-4.6'),
                "mapping": getattr(self.cfg.model, 'mapping', {}),
                "whitelist": getattr(self.cfg.model, 'whitelist', []),
                "blacklist": getattr(self.cfg.model, 'blacklist', [])
            },
            "security": {
                "rate_limit": getattr(self.cfg, '_rate_limit', 0),
                "allowed_origins": getattr(self.cfg, '_allowed_origins', ['*']),
                "api_key": getattr(self.cfg, '_api_key', ''),
                "max_tokens": getattr(self.cfg, '_max_tokens', 0),
                "max_messages": getattr(self.cfg, '_max_messages', 0)
            },
            "logging": {
                "level": getattr(self.cfg, '_log_level', 'INFO'),
                "format": getattr(self.cfg, '_log_format', '%(asctime)s - %(levelname)s - %(message)s'),
                "max_size": getattr(self.cfg, '_log_max_size', 10)
            }
        }
    
    def _apply_to_config(self, settings: Dict):
        """将设置应用到配置对象"""
        # Source
        if 'source' in settings:
            src = settings['source']
            if 'protocol' in src:
                self.cfg.source.protocol = src['protocol']
                self.cfg.headers["Origin"] = f"{self.cfg.source.protocol}//{self.cfg.source.host}"
                self.cfg.headers["Referer"] = f"{self.cfg.source.protocol}//{self.cfg.source.host}/"
            if 'host' in src:
                self.cfg.source.host = src['host']
                self.cfg.headers["Origin"] = f"{self.cfg.source.protocol}//{self.cfg.source.host}"
                self.cfg.headers["Referer"] = f"{self.cfg.source.protocol}//{self.cfg.source.host}/"
            if 'token' in src:
                self.cfg.source.token = src['token']
        
        # API
        if 'api' in settings:
            api = settings['api']
            if 'debug' in api:
                self.cfg.api.debug = api['debug']
            if 'debug_msg' in api:
                self.cfg.api.debug_msg = api['debug_msg']
                # 动态调整日志级别
                new_level = logging.DEBUG if api['debug_msg'] else logging.INFO
                logging.getLogger().setLevel(new_level)
            if 'think' in api:
                self.cfg.api.think = api['think']
            if 'anon' in api:
                self.cfg.api.anon = api['anon']
        
        # Model
        if 'model' in settings:
            model = settings['model']
            if 'default' in model:
                self.cfg.model.default = model['default']
            if 'mapping' in model:
                self.cfg.model.mapping = model['mapping']
            if 'whitelist' in model:
                self.cfg.model.whitelist = model['whitelist']
            if 'blacklist' in model:
                self.cfg.model.blacklist = model['blacklist']
        
        # Security
        if 'security' in settings:
            sec = settings['security']
            for key in ['rate_limit', 'allowed_origins', 'api_key', 'max_tokens', 'max_messages']:
                if key in sec:
                    setattr(self.cfg, f'_{key}', sec[key])
        
        # Logging
        if 'logging' in settings:
            log_settings = settings['logging']
            if 'level' in log_settings:
                self.cfg._log_level = log_settings['level']
                log_level = getattr(logging, log_settings['level'].upper(), logging.INFO)
                logging.getLogger().setLevel(log_level)
            if 'format' in log_settings:
                self.cfg._log_format = log_settings['format']
                # 重新配置日志格式
                formatter = logging.Formatter(log_settings['format'])
                for handler in logging.getLogger().handlers:
                    handler.setFormatter(formatter)
            if 'max_size' in log_settings:
                self.cfg._log_max_size = log_settings['max_size']
    
    def get_all(self, mask_sensitive: bool = True) -> Dict:
        """获取所有设置"""
        settings = copy.deepcopy(self._current)
        if mask_sensitive:
            for category in settings:
                for key in settings[category]:
                    if self._schema.get(category, {}).get(key, {}).get('sensitive'):
                        if settings[category][key]:
                            settings[category][key] = '***' + str(settings[category][key])[-4:]
        return settings
    
    def get_category(self, category: str, mask_sensitive: bool = True) -> Optional[Dict]:
        """获取指定类别的设置"""
        settings = self.get_all(mask_sensitive)
        return settings.get(category)
    
    def get_schema(self) -> Dict:
        """获取设置 schema"""
        return copy.deepcopy(self._schema)
    
    def update(self, new_settings: Dict) -> Dict:
        """更新设置"""
        # 验证
        errors = self.validate(new_settings)
        if errors:
            return {"success": False, "errors": errors}
        
        # 记录历史
        old_settings = copy.deepcopy(self._current)
        
        # 合并设置
        for category in new_settings:
            if category not in self._current:
                self._current[category] = {}
            self._current[category].update(new_settings[category])
        
        # 应用到配置对象
        try:
            self._apply_to_config(new_settings)
        except Exception as e:
            # 回滚
            self._current = old_settings
            return {"success": False, "errors": [f"应用设置失败: {str(e)}"]}
        
        # 记录历史
        self._add_history("update", old_settings, new_settings)
        
        log.info("设置已更新: %s", json.dumps(new_settings, ensure_ascii=False, default=str))
        return {"success": True, "settings": self.get_all()}
    
    def update_category(self, category: str, new_settings: Dict) -> Dict:
        """更新指定类别的设置"""
        return self.update({category: new_settings})
    
    def reset(self) -> Dict:
        """重置为默认值"""
        old_settings = copy.deepcopy(self._current)
        self._current = self._load_from_config()
        self._apply_to_config(self._current)
        self._add_history("reset", old_settings, self._current)
        log.info("设置已重置为默认值")
        return {"success": True, "settings": self.get_all()}
    
    def reload(self) -> Dict:
        """从环境变量重新加载"""
        old_settings = copy.deepcopy(self._current)
        # 重新加载环境变量
        from dotenv import load_dotenv
        load_dotenv(override=True)
        self._current = self._load_from_config()
        self._apply_to_config(self._current)
        self._add_history("reload", old_settings, self._current)
        log.info("设置已从环境变量重新加载")
        return {"success": True, "settings": self.get_all()}
    
    def validate(self, settings: Dict) -> List[str]:
        """验证设置"""
        errors = []
        for category in settings:
            if category not in self._schema:
                errors.append(f"未知的设置类别: {category}")
                continue
            for key, value in settings[category].items():
                if key not in self._schema[category]:
                    errors.append(f"未知的设置项: {category}.{key}")
                    continue
                schema = self._schema[category][key]
                # 类型检查
                if schema['type'] == 'integer' and not isinstance(value, int):
                    errors.append(f"{category}.{key} 应为整数类型")
                elif schema['type'] == 'boolean' and not isinstance(value, bool):
                    errors.append(f"{category}.{key} 应为布尔类型")
                elif schema['type'] == 'string' and not isinstance(value, str):
                    errors.append(f"{category}.{key} 应为字符串类型")
                elif schema['type'] == 'array' and not isinstance(value, list):
                    errors.append(f"{category}.{key} 应为数组类型")
                elif schema['type'] == 'object' and not isinstance(value, dict):
                    errors.append(f"{category}.{key} 应为对象类型")
                # 枚举检查
                if 'enum' in schema and value not in schema['enum']:
                    errors.append(f"{category}.{key} 的值 '{value}' 不在允许范围内: {schema['enum']}")
                # 范围检查
                if schema['type'] == 'integer' and isinstance(value, int):
                    if 'min' in schema and value < schema['min']:
                        errors.append(f"{category}.{key} 的值 {value} 小于最小值 {schema['min']}")
                    if 'max' in schema and value > schema['max']:
                        errors.append(f"{category}.{key} 的值 {value} 大于最大值 {schema['max']}")
        return errors
    
    def _add_history(self, action: str, old_settings: Dict, new_settings: Dict):
        """添加历史记录"""
        global _settings_history
        _settings_history.append({
            "timestamp": int(time.time() * 1000),
            "action": action,
            "changes": new_settings
        })
        # 限制历史记录大小
        if len(_settings_history) > MAX_HISTORY_SIZE:
            _settings_history = _settings_history[-MAX_HISTORY_SIZE:]
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取设置历史"""
        return _settings_history[-limit:]


# 全局设置管理器实例
_manager: Optional[SettingsManager] = None


def init_settings(cfg):
    """初始化设置管理器"""
    global _manager
    _manager = SettingsManager(cfg)
    return _manager


def get_manager() -> SettingsManager:
    """获取设置管理器实例"""
    if _manager is None:
        raise RuntimeError("Settings manager not initialized")
    return _manager


def require_api_key(f):
    """API 密钥验证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        manager = get_manager()
        api_key = getattr(manager.cfg, '_api_key', '')
        if api_key:
            provided_key = request.headers.get('X-API-Key') or request.args.get('api_key')
            if provided_key != api_key:
                return jsonify({"error": 401, "message": "Unauthorized: Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ============ API 路由 ============

@settings_bp.route('', methods=['GET', 'OPTIONS'])
@settings_bp.route('/', methods=['GET', 'OPTIONS'])
def get_settings():
    """获取所有设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        mask_sensitive = request.args.get('mask', 'true').lower() == 'true'
        settings = manager.get_all(mask_sensitive=mask_sensitive)
        return jsonify({
            "success": True,
            "settings": settings,
            "schema": manager.get_schema()
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/<category>', methods=['GET', 'OPTIONS'])
def get_category_settings(category):
    """获取指定类别的设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        mask_sensitive = request.args.get('mask', 'true').lower() == 'true'
        settings = manager.get_category(category, mask_sensitive=mask_sensitive)
        if settings is None:
            return jsonify({"error": 404, "message": f"未找到设置类别: {category}"}), 404
        return jsonify({
            "success": True,
            "category": category,
            "settings": settings,
            "schema": manager.get_schema().get(category, {})
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('', methods=['PUT', 'OPTIONS'])
@settings_bp.route('/', methods=['PUT', 'OPTIONS'])
def update_settings():
    """更新设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        new_settings = request.get_json(force=True, silent=True)
        if not new_settings:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        result = manager.update(new_settings)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/<category>', methods=['PUT', 'OPTIONS'])
def update_category_settings(category):
    """更新指定类别的设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        new_settings = request.get_json(force=True, silent=True)
        if not new_settings:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        result = manager.update_category(category, new_settings)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/reset', methods=['POST', 'OPTIONS'])
def reset_settings():
    """重置设置为默认值"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.reset()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/reload', methods=['POST', 'OPTIONS'])
def reload_settings():
    """从环境变量重新加载设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        result = manager.reload()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/schema', methods=['GET', 'OPTIONS'])
def get_schema():
    """获取设置 schema"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        return jsonify({
            "success": True,
            "schema": manager.get_schema()
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/history', methods=['GET', 'OPTIONS'])
def get_history():
    """获取设置变更历史"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        limit = request.args.get('limit', 50, type=int)
        history = manager.get_history(limit=limit)
        return jsonify({
            "success": True,
            "history": history,
            "total": len(_settings_history)
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/validate', methods=['POST', 'OPTIONS'])
def validate_settings():
    """验证设置（不实际应用）"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        settings = request.get_json(force=True, silent=True)
        if not settings:
            return jsonify({"error": 400, "message": "请求体不能为空"}), 400
        errors = manager.validate(settings)
        return jsonify({
            "success": len(errors) == 0,
            "errors": errors
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/export', methods=['GET', 'OPTIONS'])
def export_settings():
    """导出设置（包含敏感信息，需要 API 密钥）"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        settings = manager.get_all(mask_sensitive=False)
        return jsonify({
            "success": True,
            "settings": settings,
            "exported_at": int(time.time() * 1000)
        })
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500


@settings_bp.route('/import', methods=['POST', 'OPTIONS'])
def import_settings():
    """导入设置"""
    if request.method == 'OPTIONS':
        return make_response()
    try:
        manager = get_manager()
        data = request.get_json(force=True, silent=True)
        if not data or 'settings' not in data:
            return jsonify({"error": 400, "message": "请求体必须包含 settings 字段"}), 400
        result = manager.update(data['settings'])
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({"error": 500, "message": str(e)}), 500
