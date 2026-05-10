# 第一部分后端：账号、匿名权限与隐私安全模块

本目录只实现课程设计后端五部分中的第 1 部分，对应前端页面 2「登录注册 & 匿名隐私选择页」以及页面 10 中的隐私设置能力。前端文件未修改。

## 技术选型

- Python 标准库 HTTP 服务，无需安装第三方依赖
- SQLite 本地数据库，默认位置：`backend/data/auth.sqlite3`
- 密码安全：PBKDF2-SHA256 加盐哈希，数据库不保存明文密码
- 会话安全：Bearer Token 只返回给客户端一次，数据库只保存 Token 哈希
- 隐私策略：匿名模式默认不保存长期历史，且禁止开启长期历史保存权限

## 启动

在项目根目录运行：

```powershell
python backend/app.py --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

## 接口清单

统一返回结构：

```json
{
  "success": true,
  "data": {}
}
```

错误返回：

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "..."
  }
}
```

### 1. 获取隐私政策

`GET /api/privacy/policy`

用于登录页隐私政策弹窗，返回当前政策版本、摘要和条款内容。

### 2. 用户注册

`POST /api/auth/register`

请求体：

```json
{
  "username": "student01",
  "password": "secret123",
  "displayName": "学生01",
  "privacyConsentVersion": "2026.05"
}
```

返回 Token、用户信息、隐私设置和权限。

### 3. 用户登录

`POST /api/auth/login`

请求体：

```json
{
  "username": "student01",
  "password": "secret123",
  "privacyConsentVersion": "2026.05"
}
```

### 4. 一键匿名进入

`POST /api/auth/anonymous`

请求体可为空：

```json
{
  "privacyConsentVersion": "2026.05"
}
```

匿名用户返回短期 Token，默认：

- `allowHistorySave = false`
- `canSaveLongTermHistory = false`
- `dataRetentionDays = 7`

### 5. 获取当前登录状态

`GET /api/auth/me`

请求头：

```http
Authorization: Bearer <token>
```

### 6. 更新隐私设置

`PATCH /api/user/privacy`

请求头：

```http
Authorization: Bearer <token>
```

请求体：

```json
{
  "allowHistorySave": true,
  "allowAiMemory": false,
  "allowAnonymizedResearch": false,
  "dataRetentionDays": 180
}
```

匿名模式下，后端会拒绝 `allowHistorySave = true`，以符合“匿名用户默认不保存”的产品规则。

### 7. 记录隐私协议同意


请求头：

```http
Authorization: Bearer <token>
```

请求体：

```json
{
  "version": "2026.05"
}
```

### 8. 退出登录

`POST /api/auth/logout`

请求头：

```http
Authorization: Bearer <token>
```

### 9. 删除当前账号/匿名数据

`DELETE /api/user/me`

请求头：

```http
Authorization: Bearer <token>
```

注册用户会被软删除并撤销全部会话；匿名用户会直接删除临时身份与会话。

## 前端对接位置

- `login.html` 的 `login()` 调 `POST /api/auth/login`
- `login.html` 的 `anonymousLogin()` 调 `POST /api/auth/anonymous`
- `login.html` 的隐私弹窗可调 `GET /api/privacy/policy`
- `profile.html` 可调 `GET /api/auth/me` 展示账号/匿名状态
- `profile.html` 的隐私开关可调 `PATCH /api/user/privacy`
- `profile.html` 的退出登录可调 `POST /api/auth/logout`

## 给其他后端模块的对接约定

后续 2-5 部分接口如果涉及用户状态、评估记录、历史保存或 AI 记忆，都应先读取请求头：

```http
Authorization: Bearer <token>
```

同一`POST /api/privacy/consent`
个 Python 后端内可复用：

```python
from auth_backend.security import hash_token
from auth_backend.store import Database

user = db.get_session_user(hash_token(token))
```

拿到的 `user` 中需要重点使用：

- `id`：后续场景、评估、结果、历史、AI 对话表的 `user_id`
- `is_anonymous`：是否匿名模式
- `allow_history_save`：是否允许保存长期历史
- `allow_ai_memory`：是否允许写入 AI 长期记忆
- `allow_anonymized_research`：是否允许脱敏研究统计
- `data_retention_days`：数据保留天数

关键规则：

- 场景生成与微评估可以允许匿名用户使用。
- 历史记录和长期记忆写入前必须检查 `allow_history_save` 与 `is_anonymous`。
- 匿名用户即使有临时 `user_id`，也不能默认写入长期历史库。
- AI 对话可以读取本次评估上下文，但写入长期记忆前必须检查 `allow_ai_memory`。
- 任意受保护接口收到无效、过期或已退出的 Token，应返回 `401`，前端再跳回登录/匿名入口。

## 自测

```powershell
python -m unittest discover -s backend/tests
```
