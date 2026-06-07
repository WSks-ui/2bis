# 2Bis — AI 图片生成平台

## 项目简介

2Bis 是一个全栈 AI 图片生成平台，支持文生图、参考图生成和图片编辑三种创作模式。用户可注册登录，通过每日签到获取免费积分、购买积分包或开通会员，输入文字描述即可生成 AI 图片。

**主要功能：**

- 用户注册与登录（JWT 认证）
- **每日签到** — 连续 7 天循环奖励免费积分（10 天有效期）
- 积分充值（多档次积分包可选，永久有效）
- 会员开通（月卡 / 季卡 / 年卡，赠送积分 + 折扣消耗）
- 三种创作模式 — 文生图 / 参考图生成 / 图片编辑
- AI 图片生成（低 / 中 / 高三档质量，支持多尺寸/比例）
- **异步任务队列** — Redis 驱动的并发 Worker，支持断线重试与故障恢复
- 生成任务实时轮询（排队中 → 生成中 → 完成/失败）
- **生成历史** — 大图预览、下载、删除（同步清理磁盘文件）
- **省钱对比计算器** — 可切换质量档位，动态对比非会员 vs 月卡 vs 年卡
- 模拟支付流程

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.10 + FastAPI |
| 数据库 ORM | SQLAlchemy 2.0（异步模式） |
| 数据库 | SQLite（开发）/ MySQL / PostgreSQL（生产） |
| 数据库迁移 | Alembic |
| 消息队列 | Redis（BRPOP/LPUSH 任务分发） |
| 认证 | JWT（python-jose） |
| 密码加密 | bcrypt |
| HTTP 客户端 | httpx（调用外部 AI API） |
| 前端框架 | Vue 3（Composition API） |
| 构建工具 | Vite 5 |
| 状态管理 | Pinia |
| UI 组件库 | Element Plus |
| HTTP 客户端 | Axios |
| 容器编排 | Docker Compose |
| 反向代理 | Nginx |
| 进程管理 | systemd |

---

## 项目结构

```
2Bis/
├── backend/
│   ├── app/
│   │   ├── routers/          # API 路由（auth, generate, edits, history, payment, points）
│   │   ├── services/         # 业务逻辑（task_queue, checkin, point_manager, image_storage...）
│   │   ├── models.py         # SQLAlchemy 数据模型
│   │   ├── schemas.py        # Pydantic 请求/响应模型
│   │   ├── database.py       # 数据库引擎与自动迁移
│   │   ├── config.py         # 环境变量配置
│   │   └── dependencies.py   # 依赖注入（JWT 鉴权）
│   ├── alembic/              # 数据库迁移脚本
│   ├── run.py                # FastAPI 启动入口
│   ├── worker.py             # 异步任务 Worker 进程
│   ├── .env.example          # 环境变量模板
│   ├── docker-compose.yml    # Redis + 后端容器编排
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/            # 页面组件（Home, History, Recharge, Login, Register）
│   │   ├── components/       # 通用组件（NavBar, PointsDisplay, TaskCard）
│   │   ├── stores/           # Pinia 状态管理（tasks, points, user）
│   │   └── api/              # Axios 实例
│   └── vite.config.js
├── deploy/                   # 生产部署文件
└── README.md
```

---

## 环境变量配置

项目启动前需配置环境变量。在后端目录下复制 `.env.example` 为 `.env` 并填写实际值：

```bash
cd backend
cp .env.example .env
```

**环境变量说明：**

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | 是 | `sqlite+aiosqlite:///./aigen.db` | 数据库连接字符串。开发使用 SQLite，生产部署时改为 MySQL/PostgreSQL 连接串 |
| `SECRET_KEY` | 是 | `dev-secret-key-change-in-production` | JWT 签名密钥。生产环境务必更换 |
| `ALGORITHM` | 否 | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_DAYS` | 否 | `7` | JWT Token 过期天数 |
| `AI_API_URL` | 是 | `https://api.example.com/v1` | 第三方 AI 图片生成 API 地址 |
| `AI_API_KEY` | 是 | — | 第三方 AI API 访问密钥 |
| `AI_TIMEOUT` | 否 | `120` | 调用 AI API 的超时时间（秒） |
| `AI_MAX_CONCURRENT` | 否 | `1000` | AI API 最大并发数 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接地址，用于任务队列 |
| `GENERATION_WORKER_CONCURRENCY` | 否 | `100` | Worker 并发处理数 |
| `GENERATION_MAX_RETRIES` | 否 | `2` | 生成任务最大重试次数 |
| `MAX_UPLOAD_SIZE` | 否 | `20971520` | 上传文件最大字节数（20MB） |
| `FREE_POINTS_TTL_DAYS` | 否 | `10` | 签到免费积分有效期（天） |

---

## 数据库初始化

### 自动迁移（SQLite 开发环境）

后端启动时自动执行列级别迁移，包括 `users` 表的 `free_points`、`consecutive_days` 等字段和 `generate_histories` 表的 `task_id` 字段。

### Alembic 迁移（生产环境）

```bash
cd backend
alembic upgrade head
```

**数据模型：**

| 表 | 说明 |
|----|------|
| `users` | 用户表（用户名、密码、积分、免费积分、签到状态、会员状态） |
| `daily_checkins` | 每日签到记录表（日期、天数、奖励） |
| `generate_histories` | 生成历史表（提示词、结果图片、消耗积分） |
| `generation_tasks` | 生成任务表（模式、质量、尺寸、状态、重试、锁定） |
| `orders` | 订单表（订单号、类型、金额、支付状态） |

---

## 开发环境运行

### 前置依赖

- Python 3.10+
- Node.js 18+
- Redis（用于任务队列，不装也可通过 fakeredis 降级运行）

### 启动 Redis

```bash
# Docker 方式
docker run -d -p 6379:6379 redis:7-alpine

# 或使用 docker-compose
cd backend
docker compose up -d redis
```

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端启动在 `http://127.0.0.1:8000`，Swagger API 文档：`http://localhost:8000/docs`

### Worker（异步任务处理）

```bash
cd backend
python worker.py
```

Worker 负责从 Redis 队列中拉取生成任务并调用 AI API，支持最多 `GENERATION_WORKER_CONCURRENCY` 个并发任务。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器启动在 `http://localhost:3000`，已通过 Vite 代理将 `/api` 和 `/static` 请求转发到后端。

### 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:3000` | 前端页面 |
| `http://localhost:8000/docs` | 后端 Swagger API 文档 |

---

## 业务规则

### 图片生成积分消耗

| 质量 | 非会员 | 会员 |
|------|--------|------|
| 低质量 (low) | 1 积分 | 1 积分 |
| 中等质量 (medium) | 3 积分 | 2 积分 |
| 高质量 / 4K (high) | 5 积分 | 3 积分 |

> 免费签到积分仅可用于低、中档质量生成，不可用于高档。

### 每日签到奖励

| 连续天数 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|----------|---|---|---|---|---|---|---|
| 免费积分 | +1 | +1 | +1 | +2 | +1 | +1 | +3 |

- 签到周期为 7 天，第 8 天重置回第 1 天
- 中途断签 → 重置回第 1 天
- 免费积分有效期 10 天，超时自动清零

### 积分充值套餐

| 套餐 | 价格 | 获得积分 | 单价 |
|------|------|----------|------|
| 小包 | ¥10 | 50 积分 | ¥0.200/积分 |
| 中包 | ¥25 | 140 积分 | ¥0.179/积分 |
| 大包 | ¥50 | 300 积分 | ¥0.167/积分 |

> 积分包购买后**永久有效**。

### 会员套餐

| 套餐 | 价格 | 赠送积分 | 日均成本 |
|------|------|----------|----------|
| 月卡 | ¥39 | 260 积分 | ¥1.30 |
| 季卡 | ¥109 | 720 积分 | ¥1.21 |
| 年卡 | ¥399 | 2700 积分 | ¥1.09 |

> 会员赠送积分随会员周期清零；超额积分需单独购买积分包补充。

---

## API 接口概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 否 |
| POST | `/api/auth/login` | 用户登录，返回 JWT Token | 否 |
| POST | `/api/auth/checkin` | 每日签到领免费积分 | 是 |
| GET | `/api/auth/checkin/status` | 查询签到状态 | 是 |
| GET | `/api/points/balance` | 查询积分与免费积分余额 | 是 |
| GET | `/api/points/packs` | 获取积分充值套餐列表 | 否 |
| GET | `/api/membership/plans` | 获取会员套餐列表 | 否 |
| POST | `/api/generate` | 提交文生图任务 | 是 |
| GET | `/api/generate/tasks` | 查询所有生成任务 | 是 |
| GET | `/api/generate/tasks/{id}` | 查询单个任务状态 | 是 |
| DELETE | `/api/generate/tasks/{id}` | 删除任务及生成图片 | 是 |
| POST | `/api/edits` | 提交图片编辑任务 | 是 |
| POST | `/api/payment/orders` | 创建支付订单 | 是 |
| POST | `/api/payment/mock-pay-callback` | 模拟支付回调 | 是 |
| GET | `/api/history` | 查看生成历史记录 | 是 |
| DELETE | `/api/history/{id}` | 删除历史记录及图片文件 | 是 |

---

## 任务队列架构

```
用户请求 → FastAPI → Redis Queue (LPUSH)
                          ↓
                    Worker (BRPOP)
                          ↓
                     AI API 调用
                          ↓
                    图片存储 (local/S3)
                          ↓
                    更新任务状态
```

- **FastAPI** 接收请求后创建 `generation_tasks` 记录并推入 Redis 队列
- **Worker** 独立进程异步消费，支持最多 100 并发
- 失败自动重试（最多 `GENERATION_MAX_RETRIES` 次）
- `locked_at` 机制防止任务被多个 Worker 抢占
- 超时恢复：处理中超过 `GENERATION_PROCESSING_RECOVERY_SECONDS` 的任务自动解锁重新入队

---

## 生产环境部署

详细部署步骤请参阅 [deploy/README_deploy.md](deploy/README_deploy.md)。

核心流程：

1. 克隆代码到服务器
2. 配置 `backend/.env` 环境变量（数据库、Redis、AI API 密钥等）
3. 启动 Redis：`docker compose up -d redis` 或系统安装
4. 创建 Python 虚拟环境并安装依赖
5. 执行数据库迁移：`alembic upgrade head`
6. 构建前端：`cd frontend && npm install && npm run build`
7. 配置 systemd 服务：
   - `deploy/aigenerate.service` — API 服务
   - `deploy/aigenerate-worker.service` — 异步 Worker
8. 配置 Nginx 反向代理
9. 一键部署：`bash deploy/deploy.sh`

---

## 注意事项

1. **数据库**：开发环境默认使用 SQLite，无需额外安装。生产环境建议切换为 MySQL/PostgreSQL。
2. **AI 图片生成**：本项目本身不包含 AI 模型，生成能力依赖外部 AI API 服务。
3. **支付流程**：当前为模拟实现，适合演示环境。生产环境需对接真实支付网关。
4. **密钥安全**：生产环境务必修改 `SECRET_KEY`，**永不提交 `.env` 文件**。
5. **Redis 依赖**：任务队列依赖 Redis，开发环境可通过 `pip install fakeredis` 降级运行。
6. **静态文件**：生成图片默认存储在 `backend/static/images/`，前端通过 `/static/` 代理访问。
