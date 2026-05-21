# Z.ai 2 API - 账号管理 API 文档

## 概述

账号管理 API 提供了完整的多账号管理功能，支持账号 CRUD、批量导入、健康检查、负载均衡等。

**基础路径**: `/api/accounts`

**数据存储**: `accounts.json`

---

## 目录

- [功能特性](#功能特性)
- [API 端点](#api-端点)
  - [获取所有账号](#获取所有账号)
  - [获取指定账号](#获取指定账号)
  - [添加账号](#添加账号)
  - [批量添加账号](#批量添加账号)
  - [更新账号](#更新账号)
  - [删除账号](#删除账号)
  - [批量删除账号](#批量删除账号)
  - [切换账号状态](#切换账号状态)
  - [获取下一个可用账号](#获取下一个可用账号)
  - [健康检查](#健康检查)
  - [获取配置](#获取配置)
  - [更新配置](#更新配置)
  - [获取统计信息](#获取统计信息)
  - [重置统计信息](#重置统计信息)
  - [验证 Cookie](#验证-cookie)
  - [搜索和过滤账号](#搜索和过滤账号)
  - [导出账号数据](#导出账号数据)
  - [导入账号数据](#导入账号数据)
  - [更新账号优先级](#更新账号优先级)
  - [批量启用/禁用账号](#批量启用禁用账号)
  - [设置账号有效期](#设置账号有效期)
  - [重置单个账号统计](#重置单个账号统计)
  - [获取账号详细使用情况](#获取账号详细使用情况)
  - [获取所有标签](#获取所有标签)
  - [根据条件批量删除账号](#根据条件批量删除账号)
- [配置说明](#配置说明)
- [轮询策略](#轮询策略)
- [使用示例](#使用示例)

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 账号 CRUD | 增删改查完整支持 |
| 批量导入 | 支持批量添加/删除 |
| Cookie 验证 | 自动验证 Cookie 有效性 |
| 健康检查 | 定期检查账号状态 |
| 负载均衡 | 多种轮询策略 |
| 自动禁用 | 连续失败自动禁用 |
| 冷却机制 | 失败后冷却避免频繁请求 |
| 统计信息 | 请求次数、成功率等 |
| 敏感信息保护 | API 返回时自动隐藏 |
| 搜索过滤 | 按状态、标签、用户名等筛选 |
| 导入导出 | 支持 JSON 格式导入导出 |
| 优先级设置 | 设置账号使用优先级 |
| 有效期管理 | 设置账号过期时间 |
| 批量操作 | 批量启用/禁用/删除 |
| 详细统计 | 单个账号详细使用情况 |
| 标签管理 | 获取所有标签列表 |

---

## API 端点

### 获取所有账号

```
GET /api/accounts
GET /api/accounts/
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `mask` | string | `true` | 是否隐藏敏感信息 |

**响应示例**:

```json
{
  "success": true,
  "accounts": [
    {
      "id": "a1b2c3d4e5f6",
      "cookie": "***abc12345",
      "token": "***xyz98765",
      "user_id": "user_123",
      "user_name": "张三",
      "label": "主账号",
      "is_active": true,
      "status": "healthy",
      "added_at": "2024-01-01T00:00:00",
      "last_used": "2024-01-15T12:00:00",
      "last_error": null,
      "error_count": 0,
      "success_count": 150,
      "total_requests": 150,
      "avg_response_time": 0.5,
      "cooldown_until": 0
    }
  ],
  "stats": {
    "total_accounts": 1,
    "active_accounts": 1,
    "healthy_accounts": 1,
    "total_requests": 150,
    "total_errors": 0,
    "error_rate": 0,
    "last_reset": 1705276800000
  }
}
```

---

### 获取指定账号

```
GET /api/accounts/<account_id>
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `account_id` | 账号 ID |

**查询参数**: 同 [获取所有账号](#获取所有账号)

**响应示例**:

```json
{
  "success": true,
  "account": {
    "id": "a1b2c3d4e5f6",
    "cookie": "***abc12345",
    "token": "***xyz98765",
    "user_id": "user_123",
    "user_name": "张三",
    "label": "主账号",
    "is_active": true,
    "status": "healthy",
    "added_at": "2024-01-01T00:00:00",
    "last_used": "2024-01-15T12:00:00",
    "last_error": null,
    "error_count": 0,
    "success_count": 150,
    "total_requests": 150,
    "avg_response_time": 0.5,
    "cooldown_until": 0
  }
}
```

---

### 添加账号

```
POST /api/accounts
POST /api/accounts/
```

**请求体**:

```json
{
  "cookie": "acw_tc=abc123...",
  "label": "主账号",
  "auto_enable": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `cookie` | string | 是 | Z.ai Cookie |
| `label` | string | 否 | 账号标签 |
| `auto_enable` | boolean | 否 | 是否自动启用（默认 true） |

**响应示例** (成功):

```json
{
  "success": true,
  "account": {
    "id": "a1b2c3d4e5f6",
    "cookie": "***abc12345",
    "token": "***xyz98765",
    "user_id": "user_123",
    "user_name": "张三",
    "label": "主账号",
    "is_active": true,
    "status": "healthy",
    "added_at": "2024-01-15T12:00:00"
  }
}
```

**响应示例** (失败):

```json
{
  "success": false,
  "error": "Cookie 无效或网络错误"
}
```

---

### 批量添加账号

```
POST /api/accounts/batch
```

**请求体**:

```json
{
  "cookies": [
    "acw_tc=abc123...",
    "acw_tc=def456...",
    "acw_tc=ghi789..."
  ],
  "label": "批量导入"
}
```

**响应示例**:

```json
{
  "success": true,
  "results": {
    "total": 3,
    "success": 2,
    "failed": 1,
    "skipped": 0,
    "details": [
      {"index": 1, "status": "success", "account": {"id": "...", "user_name": "张三"}},
      {"index": 2, "status": "success", "account": {"id": "...", "user_name": "李四"}},
      {"index": 3, "status": "failed", "reason": "Cookie 无效或网络错误"}
    ]
  }
}
```

---

### 更新账号

```
PUT /api/accounts/<account_id>
```

**请求体**:

```json
{
  "label": "新标签",
  "is_active": false,
  "cookie": "new_cookie_value"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `label` | string | 账号标签 |
| `is_active` | boolean | 是否启用 |
| `cookie` | string | 新的 Cookie（会重新验证） |

**响应示例**:

```json
{
  "success": true,
  "account": {
    "id": "a1b2c3d4e5f6",
    "label": "新标签",
    "is_active": false
  }
}
```

---

### 删除账号

```
DELETE /api/accounts/<account_id>
```

**响应示例**:

```json
{
  "success": true
}
```

---

### 批量删除账号

```
DELETE /api/accounts/batch
```

**请求体**:

```json
{
  "ids": ["a1b2c3d4e5f6", "g7h8i9j0k1l2"]
}
```

**响应示例**:

```json
{
  "success": true,
  "deleted": 2
}
```

---

### 切换账号状态

```
POST /api/accounts/<account_id>/toggle
```

**响应示例**:

```json
{
  "success": true,
  "is_active": false
}
```

---

### 获取下一个可用账号

```
GET /api/accounts/next
```

根据当前轮询策略返回下一个可用账号。

**响应示例**:

```json
{
  "success": true,
  "account": {
    "id": "a1b2c3d4e5f6",
    "cookie": "***abc12345",
    "token": "***xyz98765",
    "user_id": "user_123",
    "user_name": "张三"
  }
}
```

**响应示例** (无可用账号):

```json
{
  "success": false,
  "error": "没有可用的账号"
}
```

---

### 健康检查

```
POST /api/accounts/health
```

**请求体** (可选):

```json
{
  "account_id": "a1b2c3d4e5f6"
}
```

不传 `account_id` 则检查所有账号。

**响应示例**:

```json
{
  "success": true,
  "results": [
    {
      "id": "a1b2c3d4e5f6",
      "user_name": "张三",
      "status": "healthy"
    },
    {
      "id": "g7h8i9j0k1l2",
      "user_name": "李四",
      "status": "unhealthy"
    }
  ]
}
```

---

### 获取配置

```
GET /api/accounts/config
```

**响应示例**:

```json
{
  "success": true,
  "config": {
    "mode": "round-robin",
    "retry_failed": true,
    "max_retries": 3,
    "health_check_interval": 300,
    "auto_disable_threshold": 5,
    "cooldown_period": 60,
    "max_concurrent": 0,
    "token_refresh": true
  }
}
```

---

### 更新配置

```
PUT /api/accounts/config
```

**请求体**:

```json
{
  "mode": "least-used",
  "auto_disable_threshold": 10,
  "cooldown_period": 120
}
```

**响应示例**:

```json
{
  "success": true,
  "config": {
    "mode": "least-used",
    "retry_failed": true,
    "max_retries": 3,
    "health_check_interval": 300,
    "auto_disable_threshold": 10,
    "cooldown_period": 120,
    "max_concurrent": 0,
    "token_refresh": true
  }
}
```

---

### 获取统计信息

```
GET /api/accounts/stats
```

**响应示例**:

```json
{
  "success": true,
  "stats": {
    "total_accounts": 5,
    "active_accounts": 4,
    "healthy_accounts": 3,
    "total_requests": 1500,
    "total_errors": 25,
    "error_rate": 1.67,
    "last_reset": 1705276800000
  }
}
```

---

### 重置统计信息

```
POST /api/accounts/stats/reset
```

**响应示例**:

```json
{
  "success": true,
  "stats": {
    "total_accounts": 5,
    "active_accounts": 5,
    "healthy_accounts": 5,
    "total_requests": 0,
    "total_errors": 0,
    "error_rate": 0,
    "last_reset": 1705280400000
  }
}
```

---

### 验证 Cookie

```
POST /api/accounts/validate
```

**请求体**:

```json
{
  "cookie": "acw_tc=abc123..."
}
```

**响应示例** (有效):

```json
{
  "success": true,
  "valid": true,
  "user": {
    "user_id": "user_123",
    "user_name": "张三",
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**响应示例** (无效):

```json
{
  "success": true,
  "valid": false,
  "error": "Cookie 无效或网络错误"
}
```

---

### 搜索和过滤账号

```
GET /api/accounts/search
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `query` | string | `""` | 搜索关键词（用户名、标签、用户ID） |
| `status` | string | - | 状态过滤（healthy/unhealthy/disabled） |
| `label` | string | - | 标签过滤 |
| `is_active` | string | - | 启用状态过滤（true/false） |
| `sort_by` | string | `added_at` | 排序字段（added_at/last_used/total_requests/success_count/error_count/avg_response_time/priority/user_name） |
| `sort_order` | string | `desc` | 排序顺序（asc/desc） |
| `page` | integer | `1` | 页码 |
| `page_size` | integer | `20` | 每页数量 |

**响应示例**:

```json
{
  "success": true,
  "accounts": [
    {
      "id": "a1b2c3d4e5f6",
      "cookie": "***abc12345",
      "user_name": "张三",
      "label": "主账号",
      "is_active": true,
      "status": "healthy",
      "priority": 10,
      "total_requests": 150
    }
  ],
  "total": 25,
  "page": 1,
  "page_size": 20,
  "total_pages": 2
}
```

---

### 导出账号数据

```
GET /api/accounts/export
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ids` | string | - | 账号ID列表（逗号分隔），不传则导出所有 |
| `include_sensitive` | string | `false` | 是否包含敏感信息（true/false） |

**响应示例**:

```json
{
  "success": true,
  "accounts": [
    {
      "id": "a1b2c3d4e5f6",
      "cookie": "acw_tc=abc123...",
      "token": "eyJhbGciOiJIUzI1NiIs...",
      "user_id": "user_123",
      "user_name": "张三",
      "label": "主账号",
      "is_active": true,
      "status": "healthy",
      "priority": 10,
      "expires_at": null,
      "added_at": "2024-01-01T00:00:00"
    }
  ],
  "config": {
    "mode": "round-robin"
  },
  "exported_at": "2024-01-15T12:00:00",
  "count": 1
}
```

---

### 导入账号数据

```
POST /api/accounts/import
```

**请求体**:

```json
{
  "accounts": [
    {
      "cookie": "acw_tc=abc123...",
      "token": "eyJhbGciOiJIUzI1NiIs...",
      "user_id": "user_123",
      "user_name": "张三",
      "label": "主账号",
      "is_active": true,
      "status": "healthy",
      "priority": 10,
      "expires_at": "2024-12-31T23:59:59"
    }
  ],
  "overwrite": false
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `accounts` | array | 是 | 账号数据列表 |
| `overwrite` | boolean | 否 | 是否覆盖已存在的账号（默认 false） |

**响应示例**:

```json
{
  "success": true,
  "results": {
    "total": 3,
    "imported": 2,
    "skipped": 1,
    "failed": 0,
    "details": [
      {"index": 1, "status": "imported", "account_id": "a1b2c3d4e5f6"},
      {"index": 2, "status": "imported", "account_id": "g7h8i9j0k1l2"},
      {"index": 3, "status": "skipped", "reason": "账号已存在"}
    ]
  }
}
```

---

### 更新账号优先级

```
PUT /api/accounts/<account_id>/priority
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `account_id` | 账号 ID |

**请求体**:

```json
{
  "priority": 10
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `priority` | integer | 优先级值（越大优先级越高） |

**响应示例**:

```json
{
  "success": true,
  "priority": 10
}
```

---

### 批量启用/禁用账号

```
POST /api/accounts/batch/toggle
```

**请求体**:

```json
{
  "ids": ["a1b2c3d4e5f6", "g7h8i9j0k1l2"],
  "is_active": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `ids` | array | 是 | 账号 ID 列表 |
| `is_active` | boolean | 是 | 目标状态（true=启用，false=禁用） |

**响应示例**:

```json
{
  "success": true,
  "updated": 2
}
```

---

### 设置账号有效期

```
PUT /api/accounts/<account_id>/expiry
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `account_id` | 账号 ID |

**请求体**:

```json
{
  "expires_at": "2024-12-31T23:59:59"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `expires_at` | string | 过期时间（ISO 8601 格式），设为 null 则永不过期 |

**响应示例**:

```json
{
  "success": true,
  "expires_at": "2024-12-31T23:59:59"
}
```

---

### 重置单个账号统计

```
POST /api/accounts/<account_id>/stats/reset
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `account_id` | 账号 ID |

**响应示例**:

```json
{
  "success": true
}
```

---

### 获取账号详细使用情况

```
GET /api/accounts/<account_id>/details
```

**路径参数**:

| 参数 | 说明 |
|------|------|
| `account_id` | 账号 ID |

**响应示例**:

```json
{
  "success": true,
  "account": {
    "id": "a1b2c3d4e5f6",
    "cookie": "***abc12345",
    "token": "***xyz98765",
    "user_id": "user_123",
    "user_name": "张三",
    "label": "主账号",
    "is_active": true,
    "status": "healthy",
    "priority": 10,
    "expires_at": "2024-12-31T23:59:59",
    "added_at": "2024-01-01T00:00:00",
    "last_used": "2024-01-15T12:00:00",
    "total_requests": 150,
    "success_count": 145,
    "error_count": 5,
    "avg_response_time": 0.5,
    "success_rate": 96.67,
    "error_rate": 3.33,
    "is_expired": false,
    "days_since_added": 15,
    "days_since_used": 0
  }
}
```

---

### 获取所有标签

```
GET /api/accounts/labels
```

**响应示例**:

```json
{
  "success": true,
  "labels": ["主账号", "备用账号", "测试账号"]
}
```

---

### 根据条件批量删除账号

```
POST /api/accounts/batch/delete
```

**请求体**:

```json
{
  "status": "unhealthy",
  "label": "测试账号",
  "is_active": false,
  "older_than_days": 30
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | string | 按状态删除（healthy/unhealthy/disabled） |
| `label` | string | 按标签删除 |
| `is_active` | boolean | 按启用状态删除 |
| `older_than_days` | integer | 删除添加时间早于指定天数的账号 |

**响应示例**:

```json
{
  "success": true,
  "deleted": 5
}
```

---

## 配置说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `mode` | string | `round-robin` | 轮询模式 |
| `retry_failed` | boolean | `true` | 失败时自动重试其他账号 |
| `max_retries` | integer | `3` | 最大重试次数 |
| `health_check_interval` | integer | `300` | 健康检查间隔（秒） |
| `auto_disable_threshold` | integer | `5` | 连续失败次数达到此值自动禁用 |
| `cooldown_period` | integer | `60` | 失败后冷却时间（秒） |
| `max_concurrent` | integer | `0` | 最大并发数（0=不限制） |
| `token_refresh` | boolean | `true` | 自动刷新 token |

---

## 轮询策略

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `round-robin` | 轮流使用每个账号 | 通用场景 |
| `random` | 随机选择账号 | 均衡负载 |
| `least-used` | 优先使用请求次数最少的账号 | 均衡使用量 |
| `health-based` | 优先使用健康的账号 | 高可用场景 |

---

## 使用示例

### 1. 添加账号

```bash
curl -X POST http://localhost:8080/api/accounts \
  -H "Content-Type: application/json" \
  -d '{"cookie": "acw_tc=abc123...", "label": "主账号"}'
```

### 2. 批量导入

```bash
curl -X POST http://localhost:8080/api/accounts/batch \
  -H "Content-Type: application/json" \
  -d '{
    "cookies": [
      "acw_tc=cookie1...",
      "acw_tc=cookie2...",
      "acw_tc=cookie3..."
    ],
    "label": "批量导入"
  }'
```

### 3. 查看所有账号

```bash
curl http://localhost:8080/api/accounts
```

### 4. 禁用账号

```bash
curl -X POST http://localhost:8080/api/accounts/a1b2c3d4e5f6/toggle
```

### 5. 健康检查所有账号

```bash
curl -X POST http://localhost:8080/api/accounts/health
```

### 6. 修改轮询策略

```bash
curl -X PUT http://localhost:8080/api/accounts/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "least-used"}'
```

### 7. 查看统计信息

```bash
curl http://localhost:8080/api/accounts/stats
```

### 8. 重置统计

```bash
curl -X POST http://localhost:8080/api/accounts/stats/reset
```

### 9. 验证 Cookie 是否有效

```bash
curl -X POST http://localhost:8080/api/accounts/validate \
  -H "Content-Type: application/json" \
  -d '{"cookie": "acw_tc=abc123..."}'
```

### 10. 获取下一个可用账号

```bash
curl http://localhost:8080/api/accounts/next
```

### 11. 搜索账号

```bash
# 按关键词搜索
curl "http://localhost:8080/api/accounts/search?query=张三"

# 按状态过滤
curl "http://localhost:8080/api/accounts/search?status=healthy"

# 按标签过滤
curl "http://localhost:8080/api/accounts/search?label=主账号"

# 组合过滤并分页
curl "http://localhost:8080/api/accounts/search?status=healthy&label=主账号&page=1&page_size=10"
```

### 12. 导出账号

```bash
# 导出所有账号（隐藏敏感信息）
curl http://localhost:8080/api/accounts/export

# 导出指定账号（包含敏感信息）
curl "http://localhost:8080/api/accounts/export?ids=a1b2c3d4e5f6,g7h8i9j0k1l2&include_sensitive=true"
```

### 13. 导入账号

```bash
curl -X POST http://localhost:8080/api/accounts/import \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": [
      {
        "cookie": "acw_tc=abc123...",
        "user_name": "张三",
        "label": "主账号"
      }
    ],
    "overwrite": false
  }'
```

### 14. 设置账号优先级

```bash
curl -X PUT http://localhost:8080/api/accounts/a1b2c3d4e5f6/priority \
  -H "Content-Type: application/json" \
  -d '{"priority": 10}'
```

### 15. 批量启用/禁用账号

```bash
curl -X POST http://localhost:8080/api/accounts/batch/toggle \
  -H "Content-Type: application/json" \
  -d '{
    "ids": ["a1b2c3d4e5f6", "g7h8i9j0k1l2"],
    "is_active": false
  }'
```

### 16. 设置账号有效期

```bash
curl -X PUT http://localhost:8080/api/accounts/a1b2c3d4e5f6/expiry \
  -H "Content-Type: application/json" \
  -d '{"expires_at": "2024-12-31T23:59:59"}'
```

### 17. 重置单个账号统计

```bash
curl -X POST http://localhost:8080/api/accounts/a1b2c3d4e5f6/stats/reset
```

### 18. 获取账号详细使用情况

```bash
curl http://localhost:8080/api/accounts/a1b2c3d4e5f6/details
```

### 19. 获取所有标签

```bash
curl http://localhost:8080/api/accounts/labels
```

### 20. 根据条件批量删除账号

```bash
# 删除所有不健康的账号
curl -X POST http://localhost:8080/api/accounts/batch/delete \
  -H "Content-Type: application/json" \
  -d '{"status": "unhealthy"}'

# 删除30天前添加的测试账号
curl -X POST http://localhost:8080/api/accounts/batch/delete \
  -H "Content-Type: application/json" \
  -d '{"label": "测试账号", "older_than_days": 30}'
```

---

## 账号状态说明

| 状态 | 说明 |
|------|------|
| `healthy` | 健康可用 |
| `unhealthy` | 不健康（验证失败） |
| `disabled` | 已禁用（连续失败过多） |
| `no_cookie` | 无 Cookie |

---

## 注意事项

1. **Cookie 格式**: Cookie 应为完整的 Cookie 字符串，可从浏览器开发者工具获取。

2. **自动禁用**: 当连续失败次数达到 `auto_disable_threshold` 时，账号会被自动禁用。

3. **冷却机制**: 失败后账号会进入冷却期，冷却期内不会被选择使用。

4. **敏感信息**: API 返回时会自动隐藏 `cookie` 和 `token`，如需获取完整值请使用 `mask=false` 参数。

5. **并发安全**: 所有操作都是线程安全的。

6. **数据持久化**: 所有数据保存在 `accounts.json` 文件中。

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 账号不存在 |
| 500 | 服务器内部错误 |
