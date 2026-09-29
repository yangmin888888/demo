# Admin 管理后台

一个前后端分离的通用后台管理系统，包含 **JWT 鉴权**、**用户管理**（RBAC 两级权限）与**全量审计追踪**（自动记录所有数据增删改）。

| 层 | 技术栈 | 端口 |
| --- | --- | --- |
| 前端 | Vue 3 + Vite 6 + Element Plus + Pinia + Vue Router + Axios | `5173` |
| 后端 | FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PyJWT + bcrypt | `8000` |
| 数据库 | 开发期 SQLite（可切 MySQL） | — |

---

## 目录

- [快速开始](#快速开始)
- [默认账号](#默认账号)
- [项目结构](#项目结构)
- [配置项](#配置项)
- [API 接口](#api-接口)
- [数据库设计](#数据库设计)
- [核心机制](#核心机制)
- [前端实现要点](#前端实现要点)
- [已知问题与技术债](#已知问题与技术债)
- [生产部署](#生产部署)

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 说明 |
| --- | --- | --- |
| Python | >= 3.13 | `pyproject.toml` 中 `requires-python` 声明 |
| [uv](https://docs.astral.sh/uv/) | 最新版 | Python 依赖管理，替代 pip + venv |
| Node.js | >= 18 | Vite 6 要求 Node 18+ |
| npm | 随 Node | 前端依赖管理 |

### 1. 启动后端

```powershell
cd E:\demo\backend

# 首次运行：复制配置模板并按需修改
Copy-Item .env.example .env

# 一键启动（首次会自动执行 uv sync 创建 .venv 并装依赖）
powershell -ExecutionPolicy Bypass -File start.ps1
```

或手动执行：

```powershell
uv sync                                    # 创建 .venv 并安装依赖
uv run python main.py                      # 启动服务，热重载
```

服务启动后：

- API 根地址：<http://127.0.0.1:8000>
- Swagger UI：<http://127.0.0.1:8000/docs>
- ReDoc：<http://127.0.0.1:8000/redoc>
- OpenAPI 规范：<http://127.0.0.1:8000/openapi.json>

首次启动时 `lifespan` 会自动建表并写入种子管理员账号（见下）。

### 2. 启动前端

```powershell
cd E:\demo\frontend
powershell -ExecutionPolicy Bypass -File start.ps1
```

或手动执行：

```powershell
npm install
npm run dev
```

浏览器访问 <http://localhost:5173>。

> **必须先启动后端**。前端的 `/api` 请求由 Vite 代理转发到 `http://127.0.0.1:8000`（`vite.config.js:14-19`），后端未启动时所有接口都会失败。

### 启动时序

```
[1] 后端 start.ps1  → uv sync（首次）→ uvicorn 监听 127.0.0.1:8000
                       └─ lifespan: 建表 + 写入种子管理员
[2] 前端 start.ps1  → npm install（首次）→ vite 监听 5173
[3] 浏览器访问 http://localhost:5173
[4] 未登录 → 路由守卫重定向到 /login
[5] 提交登录 → POST /api/v1/auth/login → GET /api/v1/auth/me
              → 写入 localStorage → 跳转 /dashboard
[6] 普通用户   ：仅见「仪表盘」
    超级管理员 ：见「仪表盘 / 用户管理 / 审计日志」
```

### 停止服务

在各自的 PowerShell 窗口按 `Ctrl+C`。两个脚本都是前台阻塞运行的，关闭终端即停止。

---

## 默认账号

应用首次启动时自动创建（`app/db/init_db.py:11-17`）：

| 用户名 | 密码 | 邮箱 | 角色 |
| --- | --- | --- | --- |
| `admin` | `admin123` | `admin@example.com` | 超级管理员 |

创建逻辑是**幂等**的：先查 `username == "admin"`，已存在则跳过，不会覆盖或重置已有密码。

> ⚠️ **生产环境务必修改默认密码并替换 `SECRET_KEY`**。目前 `init_db.py:40` 会把明文密码写进启动日志。

---

## 项目结构

```
demo/
├── .gitignore
├── README.md
│
├── backend/
│   ├── main.py                  # 进程启动器：uvicorn.run("app.main:app", ...)
│   ├── app/
│   │   ├── main.py              # 应用定义：工厂 create_app() + CORS + lifespan + 路由挂载
│   │   ├── api/
│   │   │   ├── deps.py          # 鉴权依赖：get_current_user / get_current_superuser
│   │   │   └── v1/
│   │   │       ├── router.py     # 空聚合 APIRouter
│   │   │       ├── auth.py       # /auth      登录、当前用户
│   │   │       ├── users.py      # /users     用户 CRUD（仅超管）
│   │   │       └── audit.py      # /audit-logs 审计查询与导出
│   │   ├── core/
│   │   │   ├── config.py        # pydantic-settings 配置
│   │   │   ├── security.py      # bcrypt 哈希 + JWT 签发/校验
│   │   │   └── audit_context.py  # 操作人上下文
│   │   ├── db/
│   │   │   ├── base.py          # DeclarativeBase
│   │   │   ├── session.py       # engine / SessionLocal / get_db
│   │   │   └── init_db.py       # 建表 + 种子管理员
│   │   ├── models/              # SQLAlchemy ORM 模型
│   │   │   ├── user.py
│   │   │   └── audit.py
│   │   ├── schemas/             # Pydantic 入参/出参模型
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   └── audit.py
│   │   └── services/            # 业务逻辑层
│   │       ├── user_service.py
│   │       └── audit_service.py # 审计事件监听器（项目中最复杂的模块）
│   ├── .env.example             # 配置模板
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── start.ps1
│   └── test_main.http           # REST Client 手工测试请求集
│
└── frontend/
    ├── package.json
    ├── vite.config.js           # 别名 @ → src，端口 5173，/api 代理到 8000
    ├── index.html
    ├── start.ps1
    └── src/
        ├── main.js              # 应用入口：Element Plus / Pinia / Router 注册
        ├── App.vue
        ├── api/                 # 接口封装
        │   ├── auth.js
        │   ├── user.js
        │   └── audit.js
        ├── layout/AdminLayout.vue   # 侧边栏 + 顶栏布局
        ├── router/index.js     # 路由表 + 全局守卫
        ├── stores/user.js      # Pinia：登录态与用户信息
        ├── utils/request.js    # axios 实例 + 拦截器
        ├── styles/index.css     # 全局 reset
        └── views/
            ├── Login.vue
            ├── Dashboard.vue
            ├── user/UserList.vue
            └── audit/AuditLogs.vue
```

### 后端分层

```
api（路由 / HTTP 语义）
  └─ services（业务逻辑）
       └─ models（ORM）
            └─ db（引擎 / 会话）

schemas  负责入参校验与出参序列化
core     横切能力：配置 / 安全 / 审计上下文
```

### 两个 `main.py` 的区别

| 文件 | 职责 | 关键点 |
| --- | --- | --- |
| `backend/main.py` | 起进程 | `uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)`。用**字符串**导入路径而非 app 对象，这是 uvicorn 开启 `reload` 的必要条件 |
| `backend/app/main.py` | 造应用 | `create_app()` 工厂：挂载路由、配置 CORS、注册 `lifespan`、安装审计监听器；模块级 `app = create_app()` 供测试重建 |

---

## 配置项

后端配置通过 `pydantic-settings` 从 `.env` 与环境变量读取（`app/core/config.py`），环境变量名大小写不敏感。

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `APP_NAME` | str | `Admin 管理后台` | FastAPI 标题、根路径返回值 |
| `DEBUG` | bool | `true` | 调试开关（当前代码未实际使用） |
| `SECRET_KEY` | str | `change-me-in-production` | JWT 签名密钥，**生产必须替换** |
| `ALGORITHM` | str | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `1440` | Token 有效期（24 小时） |
| `DATABASE_URL` | str | `sqlite:///./admin.db` | 数据库连接串 |

切换到 MySQL（`.env`）：

```ini
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/admin?charset=utf8mb4
```

需额外安装驱动：`uv add pymysql`。

> `env_file=".env"` 以**进程工作目录**为基准查找，`start.ps1` 内的 `Set-Location` 保证能找到。`settings` 带 `@lru_cache`，**改完 `.env` 必须重启进程**。

---

## API 接口

所有业务接口挂在 `/api/v1` 前缀下。

### 接口总览

| # | 方法 | 路径 | 鉴权 | 请求体 | 响应 |
| --- | --- | --- | --- | --- | --- |
| 1 | GET | `/` | 无 | — | `{"app", "status"}` |
| 2 | POST | `/api/v1/auth/login` | 无 | `LoginRequest` | `Token` |
| 3 | GET | `/api/v1/auth/me` | 登录 | — | `UserOut` |
| 4 | GET | `/api/v1/users` | **超管** | — | `PageResult` |
| 5 | POST | `/api/v1/users` | **超管** | `UserCreate` | `UserOut` (201) |
| 6 | GET | `/api/v1/users/{id}` | **超管** | — | `UserOut` |
| 7 | PUT | `/api/v1/users/{id}` | **超管** | `UserUpdate` | `UserOut` |
| 8 | DELETE | `/api/v1/users/{id}` | **超管** | — | 无内容 (204) |
| 9 | GET | `/api/v1/audit-logs/tables` | 登录 | — | `string[]` |
| 10 | GET | `/api/v1/audit-logs` | 登录 | — | `AuditLogListOut` |
| 11 | GET | `/api/v1/audit-logs/export` | 登录 | — | CSV 流 |

「登录」= 任意已启用账号；「超管」= `is_superuser == true`，否则 403。

### 认证

#### `POST /api/v1/auth/login`

```json
{ "username": "admin", "password": "admin123" }
```

响应：

```json
{ "access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer" }
```

行为说明：

- 仅支持**用户名**登录，不支持邮箱。
- 用户不存在 **或** 密码错误，统一返回 `401 用户名或密码错误`，不区分两者（防用户名枚举）。
- 密码正确但账号被禁用 → `403 账号已被禁用`。
- 登录接口**不写审计记录**（未经过 `get_current_user` 依赖，无操作人上下文）。

#### `GET /api/v1/auth/me`

需 `Authorization: Bearer <token>`，返回当前登录用户信息。前端用它恢复登录态与判断菜单权限。

### 用户管理

以下 5 个接口全部要求超级管理员，普通用户一律 `403 需要管理员权限`。

#### `GET /api/v1/users`

查询参数：

| 参数 | 类型 | 默认 | 约束 | 说明 |
| --- | --- | --- | --- | --- |
| `page` | int | 1 | `>= 1` | 页码 |
| `size` | int | 10 | `1 ~ 100` | 每页条数 |
| `keyword` | str? | — | — | 对 `username` / `nickname` / `email` 三列做 `LIKE %keyword%` 模糊匹配 |

响应：

```json
{ "total": 1, "items": [ /* UserOut[] */ ] }
```

排序：`id` 倒序（最新在前）。`total` 是在**带过滤条件的子查询**上计数，保证与分页结果一致。

#### `POST /api/v1/users` → 201

```json
{
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "password": "pass123",
  "nickname": "张三",
  "is_active": true,
  "is_superuser": false
}
```

校验：`username` 3–50、`email` 合法邮箱格式、`password` 6–128、`nickname` ≤ 50。

冲突返回 `409`：用户名已存在 / 邮箱已被使用。

#### `PUT /api/v1/users/{id}`

部分更新语义（`model_dump(exclude_unset=True)`，只处理显式提交的字段），尽管 HTTP 方法是 `PUT`。

可改字段：`email`、`nickname`、`password`、`is_active`、`is_superuser`。**`username` 创建后不可改**。

两条保护规则：

- 目标不存在 → `404`；邮箱被他人占用 → `409`
- **不能降权自己**：`user_id == current_user.id` 时若试图把自己的 `is_superuser` 或 `is_active` 设为 `false` → `400 不能取消自身的管理员/启用状态`

#### `DELETE /api/v1/users/{id}` → 204

硬删除。**不能删除当前登录账号**（`400`）。删除用户后，其历史审计记录通过冗余存储的 `username` 字段保留。

### 审计日志

以下 3 个接口只要求「已登录」，**普通用户也能查询和导出全部审计日志**。如果需要收紧权限，把 `deps.get_current_user` 换成 `deps.get_current_superuser` 即可。

#### `GET /api/v1/audit-logs`

| 参数 | 类型 | 默认 | 约束 | 匹配方式 |
| --- | --- | --- | --- | --- |
| `page` | int | 1 | `>= 1` | — |
| `size` | int | 10 | `1 ~ 200` | — |
| `table_name` | str? | — | — | 精确 |
| `action` | str? | — | — | 精确（`insert`/`update`/`delete`） |
| `username` | str? | — | — | 模糊 `LIKE` |
| `record_id` | int? | — | — | 精确 |
| `start_time` | datetime? | — | — | `created_at >=`，闭区间 |
| `end_time` | datetime? | — | — | `created_at <=`，闭区间 |

响应 `{ "total": int, "items": AuditLogOut[] }`，按 `id` 倒序。

#### `GET /api/v1/audit-logs/tables`

返回可审计的表名列表，当前为 `["users"]`。不查库，纯常量。前端用它填充「业务表」下拉框。

#### `GET /api/v1/audit-logs/export`

接受与查询接口完全相同的过滤条件，返回 `text/csv` 流。**不分页**（全量加载）。

CSV 表头：`时间, 操作类型, 表, 记录ID, 操作人, 修改字段, 修改前, 修改后, 操作ID`

实现细节：内容前置 UTF-8 BOM（`\ufeff`）确保 Excel 正确识别中文；`Content-Disposition` 用 RFC 5987 的 `filename*=UTF-8''` 传递文件名；JSON 值序列化时换行替换为空格以免破坏 CSV 结构。

### 手工测试

`backend/test_main.http` 收录了主要接口的请求示例。若使用 VS Code，安装 [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) 扩展后可直接点击发送。

---

## 数据库设计

### `users` 用户表

| 字段 | 类型 | 约束 | 默认 | 说明 |
| --- | --- | --- | --- | --- |
| `id` | Integer | PK, autoincrement | — | |
| `username` | String(50) | unique, index, not null | — | 登录名 |
| `email` | String(120) | unique, index, not null | — | 邮箱 |
| `nickname` | String(50) | nullable | `""` | 昵称 |
| `hashed_password` | String(128) | not null | — | bcrypt 哈希（实际 60 字符） |
| `is_active` | Boolean | not null | `true` | 是否启用 |
| `is_superuser` | Boolean | not null | `false` | 是否管理员 |
| `created_at` | DateTime | not null | `server_default=now()` | |
| `updated_at` | DateTime | not null | `server_default=now()`, `onupdate=now()` | |

### `audit_logs` 审计表

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| `id` | Integer | PK | |
| `operation_id` | String(32) | index, not null | 操作唯一标识（`uuid4().hex`）。**同一次 update 的多个字段行共享此值** |
| `table_name` | String(64) | index, not null | 业务表名 |
| `record_id` | Integer | nullable | 记录主键，**无外键** |
| `action` | String(16) | index, not null | `insert` / `update` / `delete` |
| `user_id` | Integer | nullable, index | 操作人 ID，**无外键** |
| `username` | String(64) | index, default `system` | 操作人账号（冗余存储，用户被删后仍留痕） |
| `field_name` | String(64) | nullable | 变更字段名；`insert`/`delete` 固定为 `"*"` |
| `old_value` | JSON | nullable | 修改前值 |
| `new_value` | JSON | nullable | 修改后值 |
| `created_at` | DateTime | not null, index | |

复合索引 `ix_audit_table_record(table_name, record_id)` 支撑「按表 + 记录查审计轨迹」。

### 表结构管理

当前用 `Base.metadata.create_all(bind=engine)` 建表（`app/db/init_db.py:24`），**只创建缺失的表，不做迁移**。改字段类型、删列不会自动生效，也不使用 Alembic。

---

## 核心机制

### JWT 鉴权

`app/core/security.py`

- **密码哈希**：`bcrypt.hashpw(password, bcrypt.gensalt())`，自适应 cost=12。`verify_password` 用 `try/except ValueError` 兜底，库中若有非 bcrypt 格式的脏数据会返回 `False` 而非抛 500。
- **签发**：payload 仅 3 个声明 —— `sub`（字符串形式的用户 ID）、`exp`、`type="access"`。**无 refresh token 机制**。
- **校验**：`jwt.decode` 自动验证签名与过期；额外检查 `type == "access"`，为将来扩展 refresh token 预留区分位。所有 `PyJWTError` 统一吞掉返回 `None`。

鉴权链（`app/api/deps.py`）：

```
Authorization: Bearer <token>
   └─ get_current_user
        ├─ 无头 / 验签失败 / 无 sub  → 401 未登录或登录已过期
        ├─ 用户不存在                  → 401 用户不存在
        ├─ is_active == false          → 403 账号已被禁用
        └─ db.info["actor"] = (user.id, user.username)   ← 审计上下文
   └─ get_current_superuser
        └─ is_superuser == false       → 403 需要管理员权限
```

`HTTPBearer(auto_error=False)` 关闭了 FastAPI 的默认自动报错，让「无 token」和「token 无效」能返回统一的中文提示。

权限模型只有**登录用户**和**超级管理员**两级，没有角色表、没有 RBAC。

### 审计追踪

`app/services/audit_service.py` 是项目中最复杂的模块。审计**不依赖业务代码主动调用**，而是通过 SQLAlchemy ORM 事件自动捕获，因此任何走 ORM 的写操作都会被记录，无法遗漏。

安装（`app/main.py:16`，在**模块导入期**执行而非 lifespan）：

```python
install_audit_listeners()   # 为 Base.registry.mappers 中每个模型注册三个事件
```

捕获规则：

| 事件 | 记录条数 | `field_name` | `old_value` | `new_value` |
| --- | --- | --- | --- | --- |
| `before_insert` | 1 | `"*"` | `null` | 全部非空字段快照 |
| `before_update` | **每个变化的字段 1 条** | 字段名 | 旧值 | 新值 |
| `before_delete` | 1 | `"*"` | 全部非空字段快照 | `null` |

细节：

- `operation_id` 一次 update 内复用，可据此把多字段变更聚合成一次操作。
- `IGNORED_FIELDS = {"id", "created_at", "updated_at"}` 排除元数据噪音。
- `EXCLUDED_TABLES = {"audit_logs"}` 审计表自身不参与审计（否则会无限递归）。
- 写入用 `connection.execute(AuditLog.__table__.insert()...)` 走**同一条连接的原始 SQL**，不经过 ORM，因此不会再次触发事件。
- 序列化：datetime/date → ISO 8601；bytes → decode；Base 实例 → str；其余原样。

**操作人如何传递**（`app/core/audit_context.py`）：把 `(user_id, username)` 绑定到 `Session.info`，而不是用 `contextvars` —— 因为 FastAPI 的同步依赖和同步路由函数运行在线程池的不同线程，`ContextVar` 不跨线程传播。可行的前提是 `get_current_user` 与路由函数依赖的是**同一个** `get_db` 生成器，FastAPI 的依赖缓存保证只 yield 一次，因此拿到同一个 Session 实例。

**审计表只读**是约定而非数据库强制：模型注释声称「数据库层面禁止一切对该表的写操作」，但代码中并没有注册 `before_update` / `before_delete` 监听器去阻止写，只是**不提供**任何修改/删除接口。直接操作数据库仍可篡改审计记录。

> ⚠️ 改密码会写入一条 `field_name="hashed_password"` 的审计记录，**记录的是 bcrypt 哈希原文**。

### Session 管理

`app/db/session.py`

- `pool_pre_ping=True`：取连接前探活，防止数据库重启后的僵尸连接。切 MySQL 后依然生效。
- SQLite 专用 `connect_args={"check_same_thread": False}`。
- `autoflush=False`：避免只读查询隐式触发写操作（也避免意外触发审计事件）。
- `autocommit=False`：显式事务，必须手动 `commit()`。
- `get_db` 是 FastAPI 依赖，**每请求一个 Session，`finally` 保证关闭**。

---

## 前端实现要点

### 应用入口

`src/main.js` 注册顺序：Element Plus 全部图标组件 → Pinia → Router → Element Plus（中文 locale `zhCn`）。样式引入顺序为 `element-plus/dist/index.css` → `src/styles/index.css`，本地 reset 优先级更高。

### 路由与守卫

`src/router/index.js`

| 路径 | 组件 | meta | 访问控制 |
| --- | --- | --- | --- |
| `/login` | `Login.vue` | `public: true` | 公开，已登录则重定向 `/dashboard` |
| `/` | `AdminLayout.vue` | — | 重定向到 `/dashboard` |
| `/dashboard` | `Dashboard.vue` | `title: 仪表盘` | 任意登录用户 |
| `/users` | `UserList.vue` | `superOnly: true` | 仅超管 |
| `/audit-logs` | `AuditLogs.vue` | `superOnly: true` | 仅超管 |

守卫逻辑（`router/index.js:43-54`）：设置 `document.title` → 公开页放行 → 无 token 跳登录 → `superOnly` 页面非超管弹回 `/dashboard`。

所有组件都是**动态 import**（路由懒加载）。

### 请求封装

`src/utils/request.js`

- axios 实例：`baseURL: '/api/v1'`、`timeout: 15000`。
- 请求拦截器：从 `localStorage.getItem('token')` 读取，注入 `Authorization: Bearer <token>`。
- 响应拦截器：直接返回 `response.data`（业务代码无需 `.data`）；`401` 时清除 `token` / `userInfo` 并 `location.href = '/login'` 整页跳转；其余错误用 `ElMessage` 弹出后端 `detail`。
- Vite 代理把 `/api` 转发到后端，因此**开发环境无跨域问题**；后端 CORS 白名单仍配置了 `localhost:5173` 与 `127.0.0.1:5173`。

### 登录态

Pinia store（`src/stores/user.js`），localStorage 持久化两个 key：

| key | 内容 |
| --- | --- |
| `token` | JWT 字符串 |
| `userInfo` | `JSON.stringify(UserOut)` |

仪表盘直接读 store 里的缓存，不重新请求后端。

### 页面功能

| 页面 | 功能 |
| --- | --- |
| **Login** | 用户名密码登录，调用 `login` + `fetchMe`，成功后写 localStorage 并跳 `/dashboard` |
| **Dashboard** | 纯展示页，渲染当前用户信息卡片（用户名/昵称/邮箱/角色/创建时间），**不调用任何 API** |
| **UserList** | 用户 CRUD。关键字搜索（回车/清空触发）、分页（10/20/50）、新增/编辑弹窗、启停与角色开关、删除二次确认。**编辑时用户名禁用，密码留空则不提交**；**删除自己时按钮禁用** |
| **AuditLogs** | 6 维度组合筛选（业务表/操作类型/操作人/记录ID/时间范围）、分页（10/20/50/100）、CSV 导出（复用同一套查询参数，保证导出与列表一致） |

中文字典（表名、操作类型、字段名 → 中文）**硬编码在前端** `AuditLogs.vue:93-105`，未从后端获取。

`AuditLogs.vue` 用 `field_name === "*"` 哨兵值区分「整行(新增)」与「整行(删除)」，逐字段修改则通过 `FIELD_LABELS[表名][字段名]` 两级字典翻译。

### 样式

`src/styles/index.css` 仅 12 行，做两件事：全局 `margin/padding` 清零 + `box-sizing: border-box`；`html`/`body`/`#app` 三级 `height: 100%`（这是布局能铺满全屏的前提）。

**没有 CSS 变量、没有 Element Plus 主题定制**，颜色全部硬编码。实际配色偏 Ant Design 风格：侧边栏深蓝 `#001529`、登录页深蓝渐变 `#1f2d3d → #2c5282`、内容区浅灰 `#f5f7fa`，主色沿用 Element Plus 默认蓝 `#409EFF`。

---

## 已知问题与技术债

按影响程度排序。

### 需要修复

1. **CSV 导出的「修改字段」列翻译错误** —— `app/api/v1/audit.py:93` 误用了 `TABLE_LABELS`（表名映射 `{"users": "用户"}`）来翻译字段名，应为独立的 `FIELD_LABELS`。结果：导出的 CSV 中「修改字段」列恒为原始英文字段名（如 `nickname`），中文翻译只在页面上生效。
2. **审计日志权限过宽** —— 任意普通用户都能查询和导出全部审计日志（含其他用户的操作记录）。收紧方式：把 `audit.py` 中的 `deps.get_current_user` 换成 `deps.get_current_superuser`。
3. **导出接口无分页** —— `audit.py:80` 全量 `.all()` 后在内存中生成 CSV，数据量大时有 OOM 风险。建议加最大条数限制或改用流式游标。
4. **401 处理是整页跳转** —— `request.js:25` 用 `location.href` 而非 `router.push`，会丢失 SPA 状态并重新加载整个 bundle。同一处也只清了 localStorage，没清 Pinia state。
5. **改密码会记录密码哈希到审计表** —— 建议把 `hashed_password` 加入 `audit_service.IGNORED_FIELDS`，或实现脱敏（如 `***`）。
6. **`init_db.py:40` 把明文密码打进日志** —— 生产环境应删除或脱敏。

### 健壮性

7. **无 404 兜底路由** —— 访问未知路径白屏。
8. **FastAPI 422 校验错误被压成「请求失败」** —— 422 的 `detail` 是数组而非字符串，`request.js:28` 的三元判断走不进去，字段级校验信息全部丢失。应改用 `el-form` 的服务端错误回填或解析数组首条。
9. **只处理 401，不处理 403** —— 权限不足时用户看不到任何引导。
10. **页面只有 `try/finally` 没有 `catch`** —— 依赖全局拦截器提示，但会产生未捕获的 Promise rejection。
11. **`ElMessageBox.confirm` 取消产生的 rejection 未捕获** —— `AdminLayout.vue:64`、`UserList.vue:203` 会打控制台警告。
12. **`router.options.routes.find(...).children` 未用可选链** —— `AdminLayout.vue:58-59`，路由结构调整时会崩。
13. **登录态刷新后不校验 token 有效性** —— 直接读 localStorage，过期 token 会显示陈旧用户信息直到下一次 API 调用。
14. **登出不通知后端** —— 没有 token 失效机制，JWT 在过期前始终有效。

### 架构

15. **无数据库迁移** —— 只有 `create_all`，字段变更需手工处理，建议引入 Alembic。
16. **无自动化测试** —— `test_main.http` 只是手工请求集。
17. **时间字段无时区** —— `DateTime` 未加 `timezone=True`。SQLite 的 `CURRENT_TIMESTAMP` 是 UTC，MySQL 的 `func.now()` 是服务器本地时区，**切库时存在时区语义差异**。
18. **`keyword` 未转义 `%` 和 `_`** —— 用户输入的通配符会被 LIKE 直接解释。
19. **`start.ps1` 不检测 `package.json` 变更** —— `node_modules` 存在就跳过 `npm install`，改依赖后需手动重装。
20. **新增 ORM 模型不会被审计** —— `install_audit_listeners()` 在模块导入期遍历 `Base.registry.mappers`，新模型文件若未被任何路由导入，就不会注册审计事件。

---

## 生产部署

### 必须先做的事

- [ ] 修改默认管理员 `admin` 的密码
- [ ] 替换 `.env` 中的 `SECRET_KEY` 为随机长字符串
- [ ] 切换 `DATABASE_URL` 到 MySQL（`uv add pymysql`）
- [ ] `DEBUG=false`
- [ ] 收紧审计日志接口权限（见技术债 #2）
- [ ] 移除 `init_db.py` 中的明文密码日志（#6）

### 后端

```powershell
uv sync --no-dev
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

生产环境**不要**用 `main.py`，它硬编码了 `reload=True` 且只监听 `127.0.0.1`。

### 前端

```powershell
npm run build     # 产物在 dist/
```

用 Nginx 托管 `dist/`，并把 `/api` 反向代理到后端：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /var/www/demo/dist;
    index index.html;

    # 关键：前端使用 HTML5 History 模式，必须配置 fallback，
    # 否则直接访问 /users 这类路径会 404
    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

> **History 模式 fallback 是最容易漏的一步**。路由用 `createWebHistory()`，没有 fallback 的话用户刷新 `/audit-logs` 会直接 404。

### 尚未覆盖的部署项

项目当前**没有**：CORS 白名单的域名配置（硬编码为 `localhost:5173`，上线后需改 `app/main.py:41`）、HTTPS、限流、请求日志、结构化日志、健康检查探针、数据库连接池调优（当前用 SQLAlchemy 默认值）、多实例下的审计一致性。

---

## 常用命令速查

```powershell
# 后端
cd backend
uv sync                      # 安装依赖
uv add <包名>                 # 添加依赖
uv run python main.py        # 启动（热重载）
uv run python -m pytest      # 运行测试（当前无测试）

# 前端
cd frontend
npm install
npm run dev                  # 开发服务器
npm run build                # 生产构建
npm run preview              # 预览构建产物

# Git
git status
git add -A
git commit -m "message"
git push
```
