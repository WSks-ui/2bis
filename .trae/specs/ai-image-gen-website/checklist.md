# Verification Checklist

## 后端基础框架
- [x] `requirements.txt` 包含所有必需依赖
- [x] `.env.example` 包含 DATABASE_URL, SECRET_KEY, AI_API_URL, AI_API_KEY 模板
- [x] `config.py` 正确读取环境变量并提供默认值（含 load_dotenv）
- [x] `database.py` 使用异步SQLAlchemy，支持 SQLite（async）和 MySQL 切换
- [x] `main.py` 注册所有路由并配置 CORS
- [x] `run.py` 可正常启动 uvicorn

## 数据模型
- [x] User 模型字段完整（username, hashed_password, points, is_member, member_expire_at, created_at）
- [x] GenerateHistory 模型字段完整（user_id FK, prompt, image_url, quality, points_cost, created_at）
- [x] Order 模型字段完整（user_id FK, order_no unique, order_type, product_id, amount, status, created_at, paid_at）
- [x] 数据库表可正常创建（SQLite）

## 认证系统
- [x] POST /api/register 正确创建用户，密码经过 bcrypt 哈希
- [x] POST /api/login 返回 JWT access_token（7天有效期）
- [x] 用户名重复注册返回合适错误
- [x] 无效 token 请求受保护接口返回 401
- [x] `get_current_user` 依赖注入正确解析用户

## 积分与会员
- [x] GET /api/points/balance 返回当前用户积分和会员状态
- [x] GET /api/points/packs 返回积分包列表
- [x] GET /api/membership/plans 返回会员套餐列表
- [x] point_manager 正确计算所需积分（会员/非会员 × 质量等级）
- [x] 积分扣减在事务中执行
- [x] AI失败时积分正确回滚

## AI生成
- [x] POST /api/generate 校验 prompt 非空
- [x] POST /api/generate 积分不足时返回错误
- [x] POST /api/generate 成功时扣减积分、调用AI、保存历史
- [x] AI API 超时或错误时回滚积分
- [x] httpx.AsyncClient 超时设置为30秒

## 支付模拟
- [x] POST /api/orders 创建订单返回 order_no
- [x] POST /api/mock-pay-callback 成功后积分增加（积分包）或会员激活（会员套餐）
- [x] 订单状态从 pending 变为 paid
- [x] 重复回调同一订单不应重复增加积分

## 历史记录
- [x] GET /api/history 返回当前用户的生成记录
- [x] 记录包含 prompt, image_url, points_cost, created_at

## 前端框架
- [x] `package.json` 包含所有前端依赖
- [x] `vite.config.js` 配置代理和 Element Plus 自动导入（按需）
- [x] Vue 应用正确注册 Pinia, Router, ElementPlus
- [x] 路由表包含 /login, /register, /, /recharge, /history

## 前端API层
- [x] axios 实例 baseURL 为 /api
- [x] 请求拦截器自动添加 Authorization header
- [x] 响应拦截器处理 401 跳转登录页

## 前端状态管理
- [x] user store 管理登录状态、token、用户名
- [x] points store 管理积分余额和会员状态

## 前端页面
- [x] Login.vue 登录表单功能完整，含 loading 和错误提示
- [x] Register.vue 注册表单功能完整
- [x] NavBar.vue 显示用户名、积分、会员状态
- [x] GenerateForm.vue 可提交 prompt 和 quality 生成图片，展示结果
- [x] Home.vue 组合导航栏和生成表单
- [x] Recharge.vue 展示积分包和会员套餐，支持创建订单和模拟支付
- [x] History.vue 展示生成历史记录

## 部署脚本
- [x] systemd 服务文件配置正确
- [x] Nginx 配置正确（前端静态文件 + /api/ 代理）
- [x] deploy.sh 脚本逻辑完整
- [x] 部署说明含 certbot SSL 配置指引

## 项目文档
- [x] README.md 包含项目简介、环境配置、开发运行、部署说明
