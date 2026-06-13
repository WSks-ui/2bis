# 2Bis AI Image Generator

2Bis 是一个全栈 AI 图片生成平台，当前目标是先稳定“体验积分 + 订阅额度”的账务闭环，再在此基础上扩展专业工作流和更多生成规格。

项目支持文生图、参考图生成、图片编辑、异步任务队列、生成历史、每日签到体验积分、体验包、订阅额度、专业工作流入口，以及多比例/多分辨率生成选项。

## 当前功能

- 用户注册、登录、JWT 鉴权。
- 每日签到发放体验积分，体验积分默认 10 天有效。
- 体验包和订阅套餐统一进入“订阅额度”池。
- 标准生成支持优先使用体验积分，专业工作流统一使用订阅额度。
- 生成任务异步入队，由 Redis + worker 执行，失败后按原扣费来源退款。
- 支持文生图、参考图/编辑图上传、生成历史、任务状态轮询。
- 前端支持先选比例、再选分辨率，后端通过 `GenerationOptions` 统一下发并校验生成选项。
- 本地开发使用模拟支付回调，便于验证账务闭环。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.10+、FastAPI、SQLAlchemy Async |
| 数据库 | SQLite 开发环境，PostgreSQL/MySQL 生产兼容 |
| 迁移 | Alembic |
| 队列 | Redis |
| 前端 | Vue 3、Vite、Pinia、Element Plus |
| 存储 | 本地静态目录或 S3 兼容对象存储 |
| 部署 | Docker Compose、Nginx、systemd |

## 目录结构

```text
2Bis/
├── backend/
│   ├── app/
│   │   ├── routers/          # API 路由
│   │   ├── services/         # AI 调用、额度、队列、存储等服务
│   │   ├── models.py         # SQLAlchemy 模型
│   │   ├── schemas.py        # Pydantic Schema
│   │   └── config.py         # 环境变量和业务配置
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 后端测试
│   ├── run.py                # API + worker 本地启动入口
│   └── worker.py             # 异步生成任务 worker
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── constants/
│   │   ├── stores/
│   │   └── views/
│   └── vite.config.js
├── deploy/
└── README.md
```

## 快速启动

### 1. 后端环境

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

编辑 `backend/.env`，至少配置：

```env
SECRET_KEY=change-me
ADMIN_USERNAMES=your-admin-username
AI_API_URL=https://www.aiartmirror.com/v1
AI_API_KEY=your-api-key-here
REDIS_URL=redis://localhost:6379/0
```

启动 Redis 后运行：

```bash
python run.py
```

`run.py` 当前会同时启动 FastAPI 服务和 worker。生产环境也可以拆分运行：

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
python worker.py
```

### 2. 前端环境

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，并通过 Vite proxy 转发：

- `/api` -> `http://127.0.0.1:8000`
- `/static` -> `http://127.0.0.1:8000`

### 3. 数据库迁移

开发环境 SQLite 会在启动时初始化/补齐表结构。生产或类生产环境建议执行：

```bash
cd backend
alembic upgrade head
```

## 计费模型

当前计费核心是“体验积分 + 订阅额度”。

### 体验积分

体验积分存储在 `users.free_points`。

- 来源：每日签到。
- 有效期：`FREE_POINTS_TTL_DAYS`，默认 10 天。
- 可用于标准工作流的 `low`、`medium` 质量。
- 不可用于 `high` 质量。
- 专业工作流不使用体验积分。

### 体验包

| 项 | 当前值 |
| --- | ---: |
| 价格 | ¥5 |
| 额度 | 30 |
| 有效期 | 7 天 |
| 限制 | 每个用户一次 |

体验包进入和订阅相同的额度池。

### 订阅套餐

| 套餐 | 月付 | 年付 | 月度额度 |
| --- | ---: | ---: | ---: |
| Light | ¥29 | ¥268 | 100 |
| Creator | ¥69 | ¥628 | 350 |
| Pro | ¥149 | ¥1368 | 800 |

### 质量消耗

| 质量 | 额度成本 |
| --- | ---: |
| low | 1 |
| medium | 2 |
| high | 3 |

扣费优先级：

- 标准工作流 `low` / `medium`：优先扣体验积分，体验积分不足时改扣订阅额度。
- 标准工作流 `high`：只扣订阅额度。
- 专业工作流：第一版只按额度扣费，不做单独支付产品。
- 异步任务入队失败或最终失败：按 `balance_source` 退回原来源。

## 专业工作流

当前已预留并接入专业工作流字段：

- `workflow_type`
- `workflow_cost`
- `workflow_preset`

前端从 `/api/points/plans` 获取 `workflow_presets` 和 `generation_options`。当前工作流包含：

| workflow_type | preset | 说明 |
| --- | --- | --- |
| `standard` | 空 | 标准生成，低/中质量优先体验积分 |
| `professional` | `pro-detail` | 专业工作流，统一消耗订阅额度 |

专业工作流的成本可通过环境变量调整：

| 变量 | 默认 |
| --- | ---: |
| `PROFESSIONAL_WORKFLOW_LOW_COST` | 1 |
| `PROFESSIONAL_WORKFLOW_MEDIUM_COST` | 2 |
| `PROFESSIONAL_WORKFLOW_HIGH_COST` | 3 |

后续测试应重点观察每类工作流的真实 API 成本、成功率、用户复用率，再调整额度成本。

## 图片比例与分辨率

尺寸、质量和上传图片类型由后端 `backend/app/services/generation_options.py` 统一维护并校验。前端从 `/api/points/plans` 的 `generation_options` 读取配置，`frontend/src/constants/imageSizes.js` 只作为后端不可用时的本地兜底。

当前硬限制：

- 最长边不超过 `3840`。
- 总像素不超过 `8,294,400`。
- 上传参考图/编辑图仅接受 PNG、JPG/JPEG、WebP，并会校验文件头。

当前 UI 是两级选择：

1. 选择比例。
2. 选择该比例下的具体分辨率。

当前比例：

- `21:9`
- `16:9`
- `3:2`
- `4:3`
- `1:1`
- `3:4`
- `2:3`
- `9:16`

当前分辨率选项：

| 比例 | 分辨率 |
| --- | --- |
| 21:9 | `3584x1536`, `2688x1152`, `1792x768` |
| 16:9 | `3840x2160`, `2560x1440`, `1920x1080`, `1344x768` |
| 3:2 | `3456x2304`, `2304x1536`, `1728x1152` |
| 4:3 | `3072x2304`, `2048x1536`, `1536x1152`, `1152x896` |
| 1:1 | `2048x2048`, `1536x1536`, `1024x1024` |
| 3:4 | `2304x3072`, `1792x2304`, `1536x2048`, `1152x1536`, `896x1152` |
| 2:3 | `2304x3456`, `1536x2304`, `1152x1728` |
| 9:16 | `2160x3840`, `1440x2560`, `1080x1920`, `720x1280` |

注意：即使用户绕过前端直接请求 `/api/generate` 或 `/api/edits`，后端也会在扣费前校验 `quality`、`size`、`workflow_type` 和上传文件类型。非法请求不会进入扣费或上游 AI 调用。

## 关键 API

| 方法 | 路径 | 说明 | 鉴权 |
| --- | --- | --- | --- |
| `POST` | `/api/auth/register` | 注册 | 否 |
| `POST` | `/api/auth/login` | 登录 | 否 |
| `POST` | `/api/auth/checkin` | 每日签到 | 是 |
| `GET` | `/api/auth/checkin/status` | 签到状态 | 是 |
| `GET` | `/api/points/balance` | 体验积分和订阅额度余额 | 是 |
| `GET` | `/api/points/plans` | 体验包、订阅套餐、工作流预设、生成选项 | 否 |
| `GET` | `/api/points/packs` | 兼容旧接口，返回空列表 | 否 |
| `GET` | `/api/membership/plans` | 兼容旧接口，返回空列表 | 否 |
| `POST` | `/api/payment/orders` | 创建体验包或订阅订单 | 是 |
| `POST` | `/api/payment/mock-pay-callback` | 本地模拟支付回调 | 是 |
| `POST` | `/api/generate` | 创建文生图任务 | 是 |
| `GET` | `/api/generate/tasks` | 查询当前用户任务列表 | 是 |
| `GET` | `/api/generate/tasks/{task_id}` | 查询单个任务 | 是 |
| `DELETE` | `/api/generate/tasks/{task_id}` | 删除任务 | 是 |
| `POST` | `/api/edits` | 创建图生图/编辑任务 | 是 |
| `GET` | `/api/history` | 生成历史 | 是 |
| `DELETE` | `/api/history/{id}` | 删除历史 | 是 |

## 生成任务流程

```text
前端提交生成请求
  -> 后端校验 prompt / quality / size / workflow_type / 上传文件
  -> QuotaManager 扣费并记录 balance_source
  -> 创建 generation_tasks
  -> Redis 入队
  -> worker 调用 AI API
  -> 保存图片到本地或 S3
  -> 写入 generate_histories
  -> 前端轮询展示结果
```

失败处理：

- Redis 入队失败：立即退款，任务标记 `REFUNDED`。
- AI 生成失败：按 `GENERATION_MAX_RETRIES` 重试。
- 最终失败：退款，任务标记 `REFUNDED`。
- worker 启动时会恢复卡在 `PROCESSING` 且超时的任务。

## 重要环境变量

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./aigen.db` | 数据库连接 |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT 签名密钥 |
| `ADMIN_USERNAMES` | 空 | 逗号分隔的管理员用户名，用于启用管理员控制台 |
| `API_KEY_ENCRYPTION_SECRET` | 空 | API Key 数据库加密密钥；生产环境应单独配置，避免 SECRET_KEY 轮换影响解密 |
| `API_KEY_CONFIG_CACHE_SECONDS` | `5` | 后台切换 API Key 后的运行时配置缓存秒数 |
| `AI_API_URL` | `https://www.aiartmirror.com/v1` | 图片 API 地址 |
| `AI_API_KEY` | 空 | 图片 API Key |
| `AI_TIMEOUT` | `2400` | AI 请求超时秒数 |
| `AI_RESPONSE_BODY_TIMEOUT` | `900` | 上游返回 200 后接收响应体的保护超时；当前上游返回大体积 base64，高质量大图可能需要较长接收时间 |
| `AI_IMAGE_RESPONSE_FORMAT` | 空 | 可选图片 API 返回格式；当前上游不支持 `response_format`，保持为空，只有更换支持 URL 返回的接口时才设为 `url` |
| `AI_RESPONSE_FORMAT_FALLBACK` | `false` | 是否在上游拒绝 `response_format` 后自动移除参数重试；默认关闭，避免静默回到大体积 base64 响应 |
| `AI_MAX_CONCURRENT` | `4` | AI 客户端并发限制 |
| `AI_MIN_REQUEST_INTERVAL_SECONDS` | `0.3` | AI 请求最小发送间隔，用于避开上游分钟级限流 |
| `AI_RATE_LIMIT_MAX_RETRIES` | `6` | 上游 429 限流后的最大重试次数 |
| `AI_RATE_LIMIT_RETRY_DELAY_SECONDS` | `1.0` | 未返回等待时间时的 429 基础退避秒数 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 地址 |
| `GENERATION_QUEUE_NAME` | `generation_tasks` | 任务队列名 |
| `GENERATION_WORKER_CONCURRENCY` | `4` | worker 并发 |
| `GENERATION_MAX_RETRIES` | `2` | 任务最大重试次数 |
| `GENERATION_TASK_TIMEOUT` | `3600` | 单任务超时秒数 |
| `GENERATION_PROCESSING_RECOVERY_SECONDS` | `3900` | 卡住任务恢复阈值 |
| `MAX_UPLOAD_SIZE` | `20971520` | 上传图片最大字节数 |
| `STORAGE_BACKEND` | `local` | `local` 或 `s3` |
| `IMAGE_DIR` | `static/images` | 本地图片目录 |
| `IMAGE_URL_PREFIX` | `/static/images` | 图片访问前缀 |
| `UPLOAD_DIR` | `static/uploads` | 上传源图目录 |
| `UVICORN_WORKERS` | `1` | Uvicorn worker 数 |
| `FREE_POINTS_TTL_DAYS` | `10` | 体验积分有效期 |
| `DEFAULT_WORKFLOW_TYPE` | `standard` | 默认工作流 |
| `PROFESSIONAL_WORKFLOW_LOW_COST` | `1` | 专业工作流 low 成本 |
| `PROFESSIONAL_WORKFLOW_MEDIUM_COST` | `2` | 专业工作流 medium 成本 |
| `PROFESSIONAL_WORKFLOW_HIGH_COST` | `3` | 专业工作流 high 成本 |

S3 存储相关变量：

- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET`
- `S3_REGION`
- `S3_PUBLIC_BASE_URL`

## 数据模型重点

账务相关字段：

- `users.free_points`
- `users.free_points_expire_at`
- `users.subscription_plan`
- `users.subscription_period`
- `users.monthly_quota_total`
- `users.monthly_quota_remaining`
- `users.monthly_quota_reset_at`
- `users.trial_activated`
- `users.trial_expire_at`
- `generation_tasks.points_cost`
- `generation_tasks.balance_source`
- `generation_tasks.workflow_type`
- `generation_tasks.workflow_cost`
- `generation_tasks.workflow_preset`
- `generation_tasks.source_image_mime_type`
- `generate_histories.points_cost`
- `generate_histories.balance_source`
- `generate_histories.workflow_type`
- `generate_histories.workflow_cost`
- `generate_histories.workflow_preset`
- `orders.plan_period`

兼容字段：

- `users.points`
- `users.is_member`
- `users.member_expire_at`

当前生成扣费主路径已迁移到 `QuotaManager`，兼容字段主要用于旧逻辑和前端展示兼容。

## 测试与构建

后端核心测试：

```bash
cd backend
python -m unittest tests.test_generation_options tests.test_ai_client tests.test_worker_recovery tests.test_quota_manager
```

前端构建：

```bash
cd frontend
npm run build
```

## 安全与提交注意事项

不要提交以下内容：

- `backend/.env`
- API Key、支付密钥、S3 密钥等任何真实凭据
- `backend/aigen.db`
- `backend/static/images/`
- `backend/static/uploads/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.test-deps/`

这些路径已在 `.gitignore` 中处理。提交前建议执行：

```bash
git status --short
git diff --stat
```

如需确认是否误提交敏感信息，可以重点检查：

```bash
git diff --cached
```

## 当前开发方向

短期优先级：

1. 稳定体验积分、订阅额度、退款、历史记录的账务闭环。
2. 保持 `workflow_type`、`workflow_cost`、`workflow_preset` 字段可追踪。
3. 专业工作流第一版继续按额度扣费，不拆独立支付。
4. 上线测试后按真实成本、成功率、用户复用率调整工作流成本和可选尺寸。
5. 如果 API 对尺寸白名单有更严格限制，优先收敛 `frontend/src/constants/imageSizes.js`。
