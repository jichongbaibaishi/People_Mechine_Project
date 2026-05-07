# 第一部分后端实现文档：用户账号、匿名权限与隐私安全模块

## 1. 模块定位

本模块对应项目后端五部分中的第一部分：

> 用户账号、匿名权限、隐私安全模块

它主要服务于前端页面 2「登录注册 & 匿名隐私选择页」和页面 10「个人中心 & 隐私设置页」，同时为后续场景生成、微评估、结果保存、历史记录和 AI 对话模块提供统一的用户身份与权限基础。

本模块只负责身份、会话、匿名模式和隐私授权，不实现情景生成、评估评分、历史记录、结果可视化或 AI 对话逻辑。

## 2. 实现目标

本模块围绕以下目标实现：

- 支持普通用户注册和登录。
- 支持一键匿名进入，无需用户名和密码。
- 为登录用户和匿名用户签发统一的访问 Token。
- 通过 Token 为后续模块提供用户身份识别能力。
- 保存用户隐私协议同意记录。
- 提供隐私设置管理能力。
- 对匿名用户进行权限限制，防止匿名数据默认写入长期历史库。
- 提供账号删除和匿名临时数据清理能力。

## 3. 技术选型

当前实现采用轻量级后端方案：

- 开发语言：Python
- HTTP 服务：Python 标准库 `http.server`
- 数据库：SQLite
- 密码安全：PBKDF2-SHA256 加盐哈希
- 会话机制：Bearer Token
- 依赖管理：无第三方依赖

选择该方案的原因：

- 项目当前前端为静态 HTML 原型，后端只需要先支撑核心接口。
- 第一部分功能边界清晰，不需要复杂框架。
- 无需安装依赖，便于课程演示、拷贝运行和组内交接。
- 后续如果项目扩展为 Flask、FastAPI、Node.js 等框架，本模块的数据结构和接口语义仍可复用。

## 4. 目录结构

```text
backend/
  app.py
  README.md
  auth_backend/
    __init__.py
    api.py
    security.py
    store.py
  data/
    .gitkeep
  tests/
    test_auth_backend.py
docs/
  backend-part1-auth-privacy.md
```

主要文件说明：

- `backend/app.py`：后端服务启动入口。
- `backend/auth_backend/api.py`：HTTP 接口层，处理请求、响应、鉴权和错误返回。
- `backend/auth_backend/store.py`：SQLite 数据库访问层。
- `backend/auth_backend/security.py`：密码哈希、密码校验、Token 生成和 Token 哈希。
- `backend/tests/test_auth_backend.py`：第一部分接口自测。
- `backend/README.md`：运行说明和接口清单。

## 5. 核心业务流程

### 5.1 普通登录流程

1. 用户在登录页输入用户名和密码。
2. 前端调用 `POST /api/auth/login`。
3. 后端校验用户名格式和密码格式。
4. 后端根据用户名查询用户。
5. 后端使用 PBKDF2 校验密码，不比较明文密码。
6. 校验成功后生成 Bearer Token。
7. 后端只保存 Token 的 SHA-256 哈希，不保存 Token 明文。
8. 前端保存 Token，后续请求放入 `Authorization` 请求头。

### 5.2 注册流程

1. 前端调用 `POST /api/auth/register`。
2. 后端校验用户名和密码。
3. 密码经 PBKDF2-SHA256 加盐哈希后入库。
4. 创建默认隐私设置。
5. 记录隐私政策同意版本。
6. 签发 Token 并返回用户状态。

### 5.3 匿名进入流程

1. 用户点击「一键匿名开始测试」。
2. 前端调用 `POST /api/auth/anonymous`。
3. 后端创建匿名用户记录，不需要用户名和密码。
4. 匿名用户默认隐私设置为：

```json
{
  "allowHistorySave": false,
  "allowAiMemory": false,
  "allowAnonymizedResearch": false,
  "dataRetentionDays": 7
}
```

5. 后端签发短期 Token。
6. 后续场景体验和微评估可以继续使用该匿名 Token。
7. 历史记录或长期记忆保存前，其他模块必须检查匿名权限。

### 5.4 隐私设置流程

1. 前端进入个人中心或隐私设置页。
2. 前端调用 `GET /api/auth/me` 获取当前用户状态。
3. 前端调用 `PATCH /api/user/privacy` 更新隐私设置。
4. 后端根据用户是否匿名进行权限限制。
5. 如果匿名用户尝试开启长期历史保存，后端返回 `403`。

### 5.5 退出和删除流程

退出登录：

- 前端调用 `POST /api/auth/logout`。
- 后端撤销当前 Token。
- 被撤销 Token 再访问受保护接口会返回 `401`。

删除账号：

- 前端调用 `DELETE /api/user/me`。
- 注册用户执行软删除，清空敏感字段并撤销全部会话。
- 匿名用户执行硬删除，直接删除临时身份与会话。

## 6. 数据库设计

### 6.1 users 表

用于保存用户主体信息。

| 字段 | 说明 |
| :--- | :--- |
| `id` | 用户唯一 ID，UUID |
| `username` | 用户名，匿名用户为空 |
| `display_name` | 展示名称 |
| `password_hash` | 密码哈希，匿名用户为空 |
| `is_anonymous` | 是否匿名用户 |
| `status` | 用户状态，`active` 或 `deleted` |
| `privacy_consent_version` | 已同意的隐私政策版本 |
| `privacy_consented_at` | 隐私政策同意时间 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |
| `deleted_at` | 删除时间 |

### 6.2 privacy_settings 表

用于保存用户隐私设置。

| 字段 | 说明 |
| :--- | :--- |
| `user_id` | 关联用户 ID |
| `allow_history_save` | 是否允许保存长期历史记录 |
| `allow_ai_memory` | 是否允许写入 AI 长期记忆 |
| `allow_anonymized_research` | 是否允许脱敏研究统计 |
| `data_retention_days` | 数据保留天数 |
| `updated_at` | 更新时间 |

### 6.3 sessions 表

用于保存登录会话。

| 字段 | 说明 |
| :--- | :--- |
| `id` | 会话 ID |
| `user_id` | 关联用户 ID |
| `token_hash` | Token 的 SHA-256 哈希 |
| `expires_at` | 过期时间 |
| `created_at` | 创建时间 |
| `revoked_at` | 撤销时间 |

### 6.4 privacy_consents 表

用于保存隐私协议同意历史。

| 字段 | 说明 |
| :--- | :--- |
| `id` | 记录 ID |
| `user_id` | 关联用户 ID |
| `version` | 隐私政策版本 |
| `consented_at` | 同意时间 |
| `source` | 来源，如 `register`、`login`、`anonymous`、`manual` |

## 7. 接口设计

### 7.1 统一响应格式

成功响应：

```json
{
  "success": true,
  "data": {}
}
```

失败响应：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "错误说明"
  }
}
```

### 7.2 接口清单

| 方法 | 路径 | 说明 | 是否需要 Token |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | 健康检查 | 否 |
| `GET` | `/api/privacy/policy` | 获取隐私政策 | 否 |
| `POST` | `/api/auth/register` | 用户注册 | 否 |
| `POST` | `/api/auth/login` | 用户登录 | 否 |
| `POST` | `/api/auth/anonymous` | 匿名进入 | 否 |
| `GET` | `/api/auth/me` | 获取当前用户 | 是 |
| `PATCH` | `/api/user/privacy` | 更新隐私设置 | 是 |
| `GET` | `/api/user/privacy` | 获取隐私设置 | 是 |
| `POST` | `/api/privacy/consent` | 记录隐私协议同意 | 是 |
| `POST` | `/api/auth/logout` | 退出登录 | 是 |
| `DELETE` | `/api/user/me` | 删除当前账号或匿名数据 | 是 |

### 7.3 Token 使用方式

登录、注册或匿名进入成功后，后端返回：

```json
{
  "token": "xxxx",
  "tokenType": "Bearer",
  "expiresAt": "2026-05-08T00:00:00Z"
}
```

后续受保护接口统一携带：

```http
Authorization: Bearer <token>
```

## 8. 权限规则

### 8.1 注册用户

注册用户默认可以保存历史记录：

```json
{
  "allowHistorySave": true,
  "allowAiMemory": false,
  "allowAnonymizedResearch": false,
  "dataRetentionDays": 180
}
```

### 8.2 匿名用户

匿名用户默认不保存长期历史：

```json
{
  "allowHistorySave": false,
  "allowAiMemory": false,
  "allowAnonymizedResearch": false,
  "dataRetentionDays": 7
}
```

匿名模式的限制：

- 不能开启长期历史保存。
- 数据保留天数不能超过 7 天。
- 后续模块不能默认把匿名评估结果写入长期历史库。
- 后续 AI 模块不能默认写入长期记忆。

## 9. 安全设计

### 9.1 密码安全

密码不会明文保存。后端使用：

- 算法：PBKDF2-HMAC-SHA256
- 盐值：每个密码独立随机盐
- 迭代次数：260000

数据库中保存格式：

```text
pbkdf2_sha256$260000$salt$digest
```

### 9.2 Token 安全

Token 只在登录、注册或匿名进入时返回给客户端一次。数据库中不保存 Token 明文，只保存：

```text
SHA256(token)
```

校验时流程为：

1. 从请求头读取 Bearer Token。
2. 对 Token 计算 SHA-256。
3. 用哈希值查询会话表。
4. 检查会话是否过期、是否撤销、用户是否有效。

### 9.3 隐私保护

- 匿名模式不要求用户提交身份信息。
- 匿名用户默认不写入长期历史。
- 用户可删除账号或清理匿名临时数据。
- 隐私协议同意版本会被记录，便于后续审计和展示。

## 10. 与其他模块的依赖关系

后续模块如果需要识别用户，都依赖本模块签发的 Token。

### 10.1 场景管理与 AI 情景生成模块

依赖内容：

- `user.id`
- `user.is_anonymous`

使用方式：

- 可允许匿名用户进入场景。
- 可根据用户是否匿名决定是否读取长期偏好或历史上下文。

### 10.2 微评估题库与评分模块

依赖内容：

- `user.id`
- `user.is_anonymous`

使用方式：

- 可使用 `user.id` 临时绑定一次答题过程。
- 不应在评分阶段默认写入长期历史。

### 10.3 结果可视化、历史记录、长期记忆库模块

依赖内容：

- `user.id`
- `user.is_anonymous`
- `user.allow_history_save`
- `user.data_retention_days`

必须遵守：

- 保存历史前检查 `allow_history_save`。
- 匿名用户不能默认保存长期历史。
- 如果 `allow_history_save` 为 `false`，只能返回本次结果，不入库。

### 10.4 AI 对话疏导模块

依赖内容：

- `user.id`
- `user.is_anonymous`
- `user.allow_ai_memory`
- `user.allow_anonymized_research`

必须遵守：

- 可以使用本次评估结果作为对话上下文。
- 写入 AI 长期记忆前必须检查 `allow_ai_memory`。
- 做统计分析前必须检查 `allow_anonymized_research` 或进行脱敏处理。

## 11. 前端对接说明

页面 2 登录页：

- 登录按钮调用 `POST /api/auth/login`。
- 匿名按钮调用 `POST /api/auth/anonymous`。
- 隐私政策弹窗调用 `GET /api/privacy/policy`。
- 登录或匿名进入成功后保存 `token`。

页面 10 个人中心：

- 页面加载时调用 `GET /api/auth/me`。
- 展示 `user.anonymous` 判断当前是否匿名模式。
- 隐私设置开关调用 `PATCH /api/user/privacy`。
- 退出登录调用 `POST /api/auth/logout`。
- 删除数据调用 `DELETE /api/user/me`。

前端保存 Token 的建议：

- 原型阶段可用 `localStorage`。
- 正式 App 可使用安全存储，例如移动端 Keychain、Keystore 或框架提供的 secure storage。

## 12. 运行与测试

启动后端：

```powershell
python backend/app.py --host 127.0.0.1 --port 8000
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

运行测试：

```powershell
python -m unittest discover -s backend/tests
```

测试覆盖内容：

- 注册用户流程。
- 登录流程。
- 重复用户名冲突。
- 匿名进入流程。
- 匿名用户权限限制。
- 退出登录后 Token 失效。

## 13. 当前边界与后续扩展

当前已实现：

- 用户注册、登录、匿名进入。
- 会话 Token 签发与撤销。
- 隐私政策与同意记录。
- 隐私设置读取和更新。
- 匿名权限限制。
- 账号删除和匿名数据删除。

当前未实现，属于其他模块范围：

- 场景内容生成。
- 剧情分支引擎。
- 微评估题库。
- 压力评分计算。
- 结果雷达图。
- 历史记录列表。
- AI 对话内容生成。

后续可扩展方向：

- 将 HTTP 层迁移到 FastAPI 或 Flask。
- 将 SQLite 替换为 MySQL。
- 增加管理员后台查看匿名统计。
- 增加 HTTPS、刷新 Token 和更细粒度权限控制。
- 与前端页面完成真实接口联调。
