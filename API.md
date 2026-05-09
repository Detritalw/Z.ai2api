# Z.ai 2 API - 系统设置 API 文档

## 概述

系统设置 API 提供了完整的运行时配置管理功能，允许您在不重启服务的情况下动态修改系统设置。

**基础路径**: `/api/settings`

**认证**: 部分敏感操作需要 API 密钥（如果已配置）

---

## 目录

- [设置分类](#设置分类)
- [API 端点](#api-端点)
  - [获取所有设置](#获取所有设置)
  - [获取指定类别设置](#获取指定类别设置)
  - [更新设置](#更新设置)
  - [更新指定类别设置](#更新指定类别设置)
  - [重置设置](#重置设置)
  - [重新加载设置](#重新加载设置)
  - [获取 Schema](#获取-schema)
  - [获取变更历史](#获取变更历史)
  - [验证设置](#验证设置)
  - [导出设置](#导出设置)
  - [导入设置](#导入设置)
- [设置项说明](#设置项说明)
- [使用示例](#使用示例)

---

## 设置分类

| 分类 | 说明 |
|------|------|
| `source` | 上游服务器配置 |
| `api` | API 服务配置 |
| `model` | 模型配置 |
| `security` | 安全配置 |
| `logging` | 日志配置 |

---

## API 端点

### 获取所有设置

```
GET /api/settings
GET /api/settings/
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mask` | string | `true` | 是否隐藏敏感信息（如 token、api_key） |

**响应示例**:

```json
{
  "success": true,
  "settings": {
    "source": {
      "protocol": "https:",
      "host": "chat.z.ai",
      "token": "***abc1234"
    },
    "api": {
      "port": 8080,
      "debug": false,
      "debug_msg": false,
      "think": "reasoning",
      "anon": true
    },
    "model": {
      "default": "glm-4.6",
      "mapping": {},
      "whitelist": [],
      "blacklist": []
    },
    "security": {
      "rate_limit": 0,
      "allowed_origins": ["*"],
      "api_key": "***xyz9876",
      "max_tokens": 0,
      "max_messages": 0
    },
    "logging": {
      "level": "INFO",
      "format": "%(asctime)s - %(levelname)s - %(message)s",
      "max_size": 10
    }
  },
  "schema": {
    "source": {
      "protocol": {
        "value": "https:",
        "type": "string",
        "description": "上游服务器协议",
        "enum": ["https:", "http:"]
      }
    }
  }
}
```

---

### 获取指定类别设置

```
GET /api/settings/<category>
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `category` | 设置类别（`source`、`api`、`model`、`security`、`logging`） |

**查询参数**: 同 [获取所有设置](#获取所有设置)

**响应示例**:

```json
{
  "success": true,
  "category": "api",
  "settings": {
    "port": 8080,
    "debug": false,
    "debug_msg": false,
    "think": "reasoning",
    "anon": true
  },
  "schema": {
    "port": {
      "value": 8080,
      "type": "integer",
      "description": "API 服务端口",
      "min": 1,
      "max": 65535
    }
  }
}
```

---

### 更新设置

```
PUT /api/settings
PUT /api/settings/
```

**请求体**: JSON 对象，包含要更新的设置

**请求示例**:

```json
{
  "api": {
    "debug": true,
    "debug_msg": true
  },
  "model": {
    "default": "glm-5"
  }
}
```

**响应示例** (成功):

```json
{
  "success": true,
  "settings": {
    "source": { "..." : "..." },
    "api": {
      "port": 8080,
      "debug": true,
      "debug_msg": true,
      "think": "reasoning",
      "anon": true
    },
    "model": {
      "default": "glm-5",
      "mapping": {},
      "whitelist": [],
      "blacklist": []
    },
    "security": { "..." : "..." },
    "logging": { "..." : "..." }
  }
}
```

**响应示例** (验证失败):

```json
{
  "success": false,
  "errors": [
    "api.port 应为整数类型",
    "api.think 的值 'invalid' 不在允许范围内: [\"reasoning\", \"think\", \"strip\", \"details\", \"none\"]"
  ]
}
```

---

### 更新指定类别设置

```
PUT /api/settings/<category>
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `category` | 设置类别 |

**请求体**: JSON 对象

**请求示例**:

```json
{
  "port": 9090,
  "debug": true
}
```

**响应**: 同 [更新设置](#更新设置)

---

### 重置设置

```
POST /api/settings/reset
POST /api/settings/reset/
```

将所有设置恢复为默认值。

**响应示例**:

```json
{
  "success": true,
  "settings": {
    "source": {
      "protocol": "https:",
      "host": "chat.z.ai",
      "token": ""
    },
    "api": {
      "port": 8080,
      "debug": false,
      "debug_msg": false,
      "think": "reasoning",
      "anon": true
    },
    "model": {
      "default": "glm-4.6",
      "mapping": {},
      "whitelist": [],
      "blacklist": []
    },
    "security": {
      "rate_limit": 0,
      "allowed_origins": ["*"],
      "api_key": "",
      "max_tokens": 0,
      "max_messages": 0
    },
    "logging": {
      "level": "INFO",
      "format": "%(asctime)s - %(levelname)s - %(message)s",
      "max_size": 10
    }
  }
}
```

---

### 重新加载设置

```
POST /api/settings/reload
POST /api/settings/reload/
```

从环境变量重新加载设置（覆盖当前运行时设置）。

**响应**: 同 [重置设置](#重置设置)

---

### 获取 Schema

```
GET /api/settings/schema
GET /api/settings/schema/
```

返回所有设置项的 schema，包含类型、描述、验证规则等。

**响应示例**:

```json
{
  "success": true,
  "schema": {
    "source": {
      "protocol": {
        "value": "https:",
        "type": "string",
        "description": "上游服务器协议",
        "enum": ["https:", "http:"],
        "required": true
      },
      "host": {
        "value": "chat.z.ai",
        "type": "string",
        "description": "上游服务器域名",
        "required": true
      },
      "token": {
        "value": "",
        "type": "string",
        "description": "上游服务器认证令牌",
        "required": false,
        "sensitive": true
      }
    },
    "api": {
      "port": {
        "value": 8080,
        "type": "integer",
        "description": "API 服务端口",
        "min": 1,
        "max": 65535,
        "required": true
      }
    }
  }
}
```

---

### 获取变更历史

```
GET /api/settings/history
GET /api/settings/history/
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | integer | `50` | 返回的历史记录数量 |

**响应示例**:

```json
{
  "success": true,
  "history": [
    {
      "timestamp": 1695000000000,
      "action": "update",
      "changes": {
        "api": {
          "debug": true
        }
      }
    },
    {
      "timestamp": 1694999000000,
      "action": "reset",
      "changes": {}
    }
  ],
  "total": 2
}
```

**action 类型**:

| 值 | 说明 |
|------|------|
| `update` | 更新设置 |
| `reset` | 重置为默认值 |
| `reload` | 从环境变量重新加载 |

---

### 验证设置

```
POST /api/settings/validate
POST /api/settings/validate/
```

验证设置是否有效（不实际应用）。

**请求体**: JSON 对象（与更新设置格式相同）

**响应示例** (验证通过):

```json
{
  "success": true,
  "errors": []
}
```

**响应示例** (验证失败):

```json
{
  "success": false,
  "errors": [
    "未知的设置类别: invalid_category",
    "api.port 应为整数类型",
    "api.think 的值 'invalid' 不在允许范围内: [\"reasoning\", \"think\", \"strip\", \"details\", \"none\"]"
  ]
}
```

---

### 导出设置

```
GET /api/settings/export
GET /api/settings/export/
```

导出完整设置（包含敏感信息，需要 API 密钥认证）。

**响应示例**:

```json
{
  "success": true,
  "settings": {
    "source": {
      "protocol": "https:",
      "host": "chat.z.ai",
      "token": "your-full-token-here"
    },
    "api": { "..." : "..." },
    "model": { "..." : "..." },
    "security": {
      "rate_limit": 0,
      "allowed_origins": ["*"],
      "api_key": "your-full-api-key-here",
      "max_tokens": 0,
      "max_messages": 0
    },
    "logging": { "..." : "..." }
  },
  "exported_at": 1695000000000
}
```

---

### 导入设置

```
POST /api/settings/import
POST /api/settings/import/
```

**请求体**:

```json
{
  "settings": {
    "api": {
      "debug": true
    },
    "model": {
      "default": "glm-5"
    }
  }
}
```

**响应**: 同 [更新设置](#更新设置)

---

## 设置项说明

### source - 上游服务器配置

| 设置项 | 类型 | 默认值 | 说明 | 可选值 |
|--------|------|--------|------|--------|
| `protocol` | string | `https:` | 上游服务器协议 | `https:`, `http:` |
| `host` | string | `chat.z.ai` | 上游服务器域名 | - |
| `token` | string | `""` | 上游服务器认证令牌 | - |

### api - API 服务配置

| 设置项 | 类型 | 默认值 | 说明 | 可选值 |
|--------|------|--------|------|--------|
| `port` | integer | `8080` | API 服务端口 | 1-65535 |
| `debug` | boolean | `false` | 调试模式（显示详细错误信息） | - |
| `debug_msg` | boolean | `false` | 调试日志（显示详细请求/响应日志） | - |
| `think` | string | `reasoning` | 思考链处理模式 | `reasoning`, `think`, `strip`, `details`, `none` |
| `anon` | boolean | `true` | 访客模式（无需登录即可使用） | - |

### model - 模型配置

| 设置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `default` | string | `glm-4.6` | 默认模型（当请求未指定模型时使用） |
| `mapping` | object | `{}` | 模型映射表（将外部模型名映射到内部模型 ID） |
| `whitelist` | array | `[]` | 模型白名单（为空则允许所有模型） |
| `blacklist` | array | `[]` | 模型黑名单（优先级高于白名单） |

**映射表示例**:

```json
{
  "mapping": {
    "gpt-4": "glm-4",
    "gpt-3.5-turbo": "glm-4-flash",
    "claude-3-opus": "glm-5"
  }
}
```

### security - 安全配置

| 设置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `rate_limit` | integer | `0` | 请求频率限制（每分钟请求数，0 表示不限制） |
| `allowed_origins` | array | `["*"]` | 允许的 CORS 来源 |
| `api_key` | string | `""` | API 访问密钥（为空则不需要认证） |
| `max_tokens` | integer | `0` | 最大输出 token 数限制（0 表示不限制） |
| `max_messages` | integer | `0` | 最大消息数限制（0 表示不限制） |

### logging - 日志配置

| 设置项 | 类型 | 默认值 | 说明 | 可选值 |
|--------|------|--------|------|--------|
| `level` | string | `INFO` | 日志级别 | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `format` | string | `%(asctime)s - %(levelname)s - %(message)s` | 日志格式 | - |
| `max_size` | integer | `10` | 日志文件最大大小（MB） | 1-1000 |

---

## 使用示例

### 1. 查看当前所有设置

```bash
curl http://localhost:8080/api/settings
```

### 2. 启用调试模式

```bash
curl -X PUT http://localhost:8080/api/settings/api \
  -H "Content-Type: application/json" \
  -d '{"debug": true, "debug_msg": true}'
```

### 3. 修改默认模型

```bash
curl -X PUT http://localhost:8080/api/settings/model \
  -H "Content-Type: application/json" \
  -d '{"default": "glm-5"}'
```

### 4. 设置 API 密钥

```bash
curl -X PUT http://localhost:8080/api/settings/security \
  -H "Content-Type: application/json" \
  -d '{"api_key": "my-secret-key"}'
```

### 5. 重置所有设置

```bash
curl -X POST http://localhost:8080/api/settings/reset
```

### 6. 从环境变量重新加载

```bash
curl -X POST http://localhost:8080/api/settings/reload
```

### 7. 验证设置

```bash
curl -X POST http://localhost:8080/api/settings/validate \
  -H "Content-Type: application/json" \
  -d '{"api": {"port": 9090}}'
```

### 8. 导出完整配置

```bash
curl http://localhost:8080/api/settings/export
```

### 9. 导入配置

```bash
curl -X POST http://localhost:8080/api/settings/import \
  -H "Content-Type: application/json" \
  -d '{"settings": {"api": {"debug": true}, "model": {"default": "glm-5"}}}'
```

### 10. 查看变更历史

```bash
curl http://localhost:8080/api/settings/history?limit=10
```

---

## 运行时生效说明

| 设置项 | 运行时生效 | 说明 |
|--------|-----------|------|
| `source.protocol` | 是 | 立即更新请求头 |
| `source.host` | 是 | 立即更新请求头 |
| `source.token` | 是 | 下次请求生效 |
| `api.port` | 否 | 需要重启服务 |
| `api.debug` | 是 | 立即生效 |
| `api.debug_msg` | 是 | 立即调整日志级别 |
| `api.think` | 是 | 下次请求生效 |
| `api.anon` | 是 | 下次请求生效 |
| `model.default` | 是 | 下次请求生效 |
| `model.mapping` | 是 | 下次请求生效 |
| `model.whitelist` | 是 | 下次请求生效 |
| `model.blacklist` | 是 | 下次请求生效 |
| `security.*` | 是 | 立即生效 |
| `logging.*` | 是 | 立即生效 |

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权（API 密钥无效） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

## 注意事项

1. **敏感信息**: 获取设置时，默认会隐藏敏感信息（如 `token`、`api_key`），设置值会被替换为 `***` + 后4位字符。如需获取完整值，请使用 `mask=false` 参数或导出接口。

2. **端口修改**: 修改 `api.port` 后需要重启服务才能生效。

3. **环境变量优先级**: 使用 `POST /api/settings/reload` 会从环境变量重新加载，覆盖当前运行时设置。

4. **并发安全**: 设置更新操作是原子的，但在高并发场景下建议使用适当的锁机制。

5. **持久化**: 运行时修改的设置不会自动保存到 `.env` 文件。如需持久化，请手动更新 `.env` 文件。
