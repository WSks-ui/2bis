# Tasks

## Task 1: 后端基础框架搭建
- [x] 创建 backend 目录结构
  - [x] 创建 `requirements.txt` 含所有依赖：fastapi, uvicorn, sqlalchemy[asyncio], aiosqlite, pydantic, python-jose[cryptography], bcrypt, httpx, python-multipart
  - [x] 创建 `.env.example` 模板，包含 DATABASE_URL, SECRET_KEY, AI_API_URL, AI_API_KEY
  - [x] 创建 `app/__init__.py`
  - [x] 创建 `app/config.py` — 读取环境变量配置
  - [x] 创建 `app/database.py` — 异步SQLAlchemy引擎与Session工厂（支持SQLite和MySQL切换）
  - [x] 创建 `app/main.py` — FastAPI应用入口，注册所有路由，添加CORS中间件
  - [x] 创建 `run.py` — uvicorn启动脚本

## Task 2: 后端数据模型
- [x] 创建 `app/models.py` — SQLAlchemy ORM 模型
  - [x] User 表：id, username, hashed_password, points (Integer, 默认0), is_member (Boolean), member_expire_at (DateTime, nullable), created_at
  - [x] GenerateHistory 表：id, user_id (FK), prompt, image_url, quality, points_cost, created_at
  - [x] Order 表：id, user_id (FK), order_no (unique), order_type (points_pack / membership), product_id, amount (元), status (pending / paid), created_at, paid_at (nullable)

## Task 3: 后端认证系统
- [x] 创建 `app/utils/__init__.py`
- [x] 创建 `app/schemas.py` — Pydantic请求/响应模型（UserRegister, UserLogin, TokenResponse, UserInfo, GenerateRequest, HistoryItem 等）
- [x] 创建 `app/dependencies.py` — `get_current_user` 依赖注入，解析JWT获取当前用户
- [x] 创建 `app/routers/__init__.py`
- [x] 创建 `app/routers/auth.py` — POST /api/register, POST /api/login（JWT签发7天）

## Task 4: 后端积分与会员路由
- [x] 创建 `app/services/__init__.py`
- [x] 创建 `app/services/point_manager.py` — 积分扣减/增加/回滚（事务管理），查询积分；计算所需积分方法（根据会员状态和quality）
- [x] 创建 `app/routers/membership.py` — GET /api/membership/plans（返回会员套餐列表）
- [x] 创建 `app/routers/points.py` — GET /api/points/packs（返回积分包列表），GET /api/points/balance（返回当前用户积分和会员状态）

## Task 5: 后端AI生成路由
- [x] 创建 `app/services/ai_client.py` — 使用 httpx.AsyncClient 调用外部AI API，超时30秒
- [x] 创建 `app/routers/generate.py` — POST /api/generate（校验prompt非空 → 计算所需积分 → 检查余额 → 扣积分 → 调用AI → 成功则记录历史 / 失败则回滚）

## Task 6: 后端支付模拟与历史记录
- [x] 创建 `app/services/payment_simulator.py` — 生成模拟订单号，创建订单记录
- [x] 创建 `app/routers/payment.py` — POST /api/orders（创建订单），POST /api/mock-pay-callback（确认支付回调，更新订单状态、增加积分/激活会员）
- [x] 创建 `app/routers/history.py` — GET /api/history（返回当前用户生成记录列表）

## Task 7: 前端基础框架搭建
- [x] 创建 frontend 目录结构（使用 Vite + Vue 3 脚手架配置）
  - [x] `package.json` 含依赖：vue, vue-router, pinia, element-plus, @element-plus/icons-vue, axios, @vitejs/plugin-vue, vite
  - [x] `vite.config.js` — 配置代理 /api → 后端 8000 端口
  - [x] `index.html` — 入口HTML
  - [x] `src/main.js` — 创建Vue应用，注册Pinia/Router/ElementPlus
  - [x] `src/App.vue` — 根组件，包含 `<router-view />`

## Task 8: 前端路由与API层
- [x] 创建 `src/router/index.js` — 路由表：/login, /register, /, /recharge, /history
- [x] 创建 `src/api/index.js` — axios实例（baseURL /api），请求拦截器添加token，响应拦截器处理401

## Task 9: 前端状态管理
- [x] 创建 `src/stores/user.js` — Pinia Store：用户信息、token、登录/注册/登出方法
- [x] 创建 `src/stores/points.js` — Pinia Store：积分余额、会员状态、查询余额方法

## Task 10: 前端页面 — 登录与注册
- [x] 创建 `src/views/Login.vue` — 登录表单，调用登录API，存储token跳转主页
- [x] 创建 `src/views/Register.vue` — 注册表单，调用注册API，成功后跳转登录页

## Task 11: 前端页面 — 主页（图片生成）
- [x] 创建 `src/components/NavBar.vue` — 顶部导航栏（用户名、积分余额、会员状态、到期时间）
- [x] 创建 `src/components/PointsDisplay.vue` — 积分展示组件
- [x] 创建 `src/components/GenerateForm.vue` — prompt输入框、质量选择下拉、生成按钮、图片展示区域（可点击放大）
- [x] 创建 `src/views/Home.vue` — 组合 NavBar + GenerateForm，初始化时获取用户信息和积分

## Task 12: 前端页面 — 充值页与历史页
- [x] 创建 `src/views/Recharge.vue` — 展示积分包列表和会员套餐列表，点击购买创建订单 → 弹窗显示模拟支付信息 → 点击模拟支付按钮调用回调接口刷新余额
- [x] 创建 `src/views/History.vue` — 展示生成历史记录列表（图片缩略图、提示词、消耗积分、时间）

## Task 13: 部署脚本
- [x] 创建 `deploy/aigenerate.service` — systemd 服务文件
- [x] 创建 `deploy/nginx.conf` — Nginx 配置（前端静态文件 + /api/ 代理）
- [x] 创建 `deploy/deploy.sh` — 一键部署脚本
- [x] 创建 `deploy/README_deploy.md` — 部署说明（含 certbot SSL 配置）

## Task 14: 项目README
- [x] 创建 `README.md` — 项目简介、环境变量配置、开发运行、部署说明

# Task Dependencies
- Task 2 依赖 Task 1
- Task 3 依赖 Task 2
- Task 4 依赖 Task 2
- Task 5 依赖 Task 4
- Task 6 依赖 Task 2
- Task 7 无依赖（可与 Task 1 并行）
- Task 8 依赖 Task 7
- Task 9 依赖 Task 7
- Task 10 依赖 Task 8, Task 9
- Task 11 依赖 Task 8, Task 9
- Task 12 依赖 Task 8, Task 9
- Task 13 无依赖（可并行）
- Task 14 无依赖（可并行）
