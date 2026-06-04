# AI 图片生成网站

## 项目简介

AI 图片生成网站，用户可注册登录，购买积分或开通会员，通过输入文字描述即可生成 AI 图片。

**主要功能：**

- 用户注册与登录（JWT 认证）
- 积分充值（多档次积分包可选）
- 会员开通（月卡 / 季卡 / 年卡）
- AI 图片生成（支持低 / 中 / 高三档质量）
- 生成历史查看
- 模拟支付流程

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.10 + FastAPI |
| 数据库 ORM | SQLAlchemy 2.0（异步模式） |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 认证 | JWT（python-jose） |
| 密码加密 | bcrypt |
| HTTP 客户端 | httpx（调用外部 AI API） |
| 前端框架 | Vue 3（Composition API） |
| 构建工具 | Vite 5 |
| 状态管理 | Pinia |
| UI 组件库 | Element Plus |
| HTTP 客户端 | Axios |
| 反向代理 | Nginx |
| 进程管理 | systemd |

---

## 环境变量配置

项目启动前需配置环境变量。在后端目录下复制 `.env.example` 为 `.env` 并填写实际值：

```bash
cd backend
cp .env.example .env
```

`.env.example` 内容如下：

```ini
DATABASE_URL=sqlite+aiosqlite:///./aigen.db
SECRET_KEY=change-me-to-a-random-secret-key
AI_API_URL=https://api.example.com/v1/generate
AI_API_KEY=your-api-key-here
```

**环境变量说明：**

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DATABASE_URL` | 是 | `sqlite+aiosqlite:///./aigen.db` | 数据库连接字符串。开发使用 SQLite，生产部署时改为 MySQL 连接串，格式：`mysql+aiomysql://user:password@host:3306/dbname` |
| `SECRET_KEY` | 是 | `dev-secret-key-change-in-production` | JWT 签名密钥。生产环境务必更换为随机字符串 |
| `ALGORITHM` | 否 | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_DAYS` | 否 | `7` | JWT Token 过期天数 |
| `AI_API_URL` | 是 | `https://api.example.com/v1/generate` | 第三方 AI 图片生成 API 地址 |
| `AI_API_KEY` | 是 | 无 | 第三方 AI API 的访问密钥 |
| `AI_TIMEOUT` | 否 | `30` | 调用 AI API 的超时时间（秒） |

---

## 数据库初始化

数据库表的创建由后端启动时自动完成。在 `app/main.py` 中通过 `@app.on_event("startup")` 事件调用 `init_db()`，启动时自动检测并创建不存在的表，无需手动执行迁移脚本。

**使用 MySQL 时**，只需修改 `.env` 中的 `DATABASE_URL` 为 MySQL 连接串：

```ini
DATABASE_URL=mysql+aiomysql://root:password@127.0.0.1:3306/aigen
```

项目使用的数据模型包括三张表：
- `users` — 用户表（用户名、密码、积分、会员状态）
- `generate_histories` — 生成历史表（关联用户、提示词、生成结果、消耗积分）
- `orders` — 订单表（关联用户、订单类型、金额、支付状态）

---

## 开发环境运行

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端启动在 `http://127.0.0.1:8000`，API 交互文档可通过 `http://localhost:8000/docs` 访问。

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器启动在 `http://localhost:3000`，已通过 Vite 代理将 `/api` 请求转发到后端 `http://127.0.0.1:8000`。

### 访问地址

| 地址 | 说明 |
|------|------|
| `http://localhost:3000` | 前端页面 |
| `http://localhost:8000/docs` | 后端 Swagger API 文档 |

---

## 生产环境部署

详细部署步骤请参阅 [deploy/README_deploy.md](deploy/README_deploy.md)。

部署核心流程：

1. 克隆代码到服务器 `/opt/aigen`
2. 配置 `backend/.env` 环境变量
3. 创建 Python 虚拟环境并安装依赖
4. 构建前端：`cd frontend && npm install && npm run build`
5. 配置 systemd 服务（使用 `deploy/aigenerate.service`）
6. 配置 Nginx 反向代理（使用 `deploy/nginx.conf`）
7. 使用 `deploy/deploy.sh` 一键部署

---

## API 接口概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | `/api/auth/register` | 用户注册 | 否 |
| POST | `/api/auth/login` | 用户登录，返回 JWT Token | 否 |
| GET | `/api/points/balance` | 查询当前用户积分余额 | 是 |
| GET | `/api/points/packs` | 获取积分充值套餐列表 | 否 |
| GET | `/api/membership/plans` | 获取会员套餐列表 | 否 |
| POST | `/api/generate` | 提交图片生成请求 | 是 |
| POST | `/api/payment/orders` | 创建支付订单 | 是 |
| POST | `/api/payment/mock-pay-callback` | 模拟支付回调 | 是 |
| GET | `/api/history` | 查看生成历史记录 | 是 |

---

## 业务规则

### 图片生成积分消耗

| 质量 | 消耗积分 |
|------|----------|
| 低质量 (low) | 1 积分 |
| 中等质量 (medium) | 3 积分 |
| 高质量 (high) | 5 积分 |

### 积分充值套餐

| 套餐 | 价格 | 获得积分 |
|------|------|----------|
| 基础包 | ¥10 | 50 积分 |
| 进阶包 | ¥25 | 140 积分 |
| 高阶包 | ¥50 | 300 积分 |

### 会员套餐

| 套餐 | 价格 | 赠送积分 |
|------|------|----------|
| 月卡 | ¥39 / 月 | 260 积分 |
| 季卡 | ¥109 / 季 | 720 积分 |
| 年卡 | ¥399 / 年 | 2700 积分 |

开通会员后，用户在会员有效期内享有对应的权益。

---

## 注意事项

1. **数据库选择**：开发环境默认使用 SQLite，无需额外安装数据库。生产环境建议切换为 MySQL，只需修改 `DATABASE_URL` 环境变量。
2. **AI 图片生成**：本项目本身不包含 AI 模型，生成能力依赖外部 AI API 服务，通过 `AI_API_URL` 和 `AI_API_KEY` 环境变量配置。
3. **支付流程**：当前支付为模拟实现，通过 `/api/payment/mock-pay-callback` 模拟支付成功回调，适合开发演示环境。生产环境需对接真实支付网关。
4. **密钥安全**：生产环境务必修改 `SECRET_KEY` 为随机字符串，且不要将 `.env` 文件提交到版本控制系统。
5. **HTTPS**：生产部署时建议使用 Let's Encrypt（certbot）配置 SSL 证书，部署指南中已包含详细步骤。
