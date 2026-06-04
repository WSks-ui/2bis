# AI图片生成网站 Spec

## Why
从零构建一个完整可运行的AI图片生成网站，让用户可以注册登录、购买积分/会员、利用积分消耗来调用外部AI生成图片，并查看历史记录。

## What Changes
- 新建完整后端项目（FastAPI + 异步SQLAlchemy + SQLite + JWT鉴权）
- 新建完整前端项目（Vue 3 + Vite + Pinia + Vue Router + Element Plus）
- 实现用户注册/登录（JWT，7天有效期）
- 实现积分管理（购买积分包、开通会员、会员积分赠送）
- 实现AI图片生成（调用外部API，扣积分前先校验，AI失败则回滚）
- 实现支付模拟（创建订单 → 模拟支付 → 回调确认 → 更新积分/会员）
- 实现生成历史记录查询
- 提供部署脚本（Nginx + uvicorn + systemd）
- 提供 README.md 和 .env.example

## Impact
- Affected specs: 无（全新项目）
- Affected code: 无（全新项目）

## ADDED Requirements

### Requirement: 用户认证系统
系统 SHALL 提供用户注册和登录功能，登录后返回 JWT access_token（有效期7天），除注册/登录外的所有API接口需要Bearer Token鉴权。

#### Scenario: 用户注册成功
- **WHEN** 用户提供唯一用户名和密码进行注册
- **THEN** 系统创建用户账户，初始积分余额为0，会员状态为普通用户

#### Scenario: 用户登录成功
- **WHEN** 用户提供正确的用户名和密码
- **THEN** 系统返回 JWT access_token，有效期7天

#### Scenario: 鉴权失败
- **WHEN** 请求携带无效或过期的 token
- **THEN** 系统返回 HTTP 401

---

### Requirement: 积分与会员系统
系统 SHALL 支持积分包购买（永久有效）和会员开通（月/季/年，积分按周期赠送，到期清零）。

#### 积分消耗规则
| 场景 | 低质量 | 中质量 | 高质量(4K) |
|------|--------|--------|------------|
| 非会员 | 1 积分 | 3 积分 | 5 积分 |
| 会员 | 1 积分 | 2 积分 | 3 积分 |

#### 会员赠送积分
| 类型 | 价格 | 赠送积分 |
|------|------|----------|
| 月卡 | 39元 | 260 积分 |
| 季卡 | 109元 | 720 积分 |
| 年卡 | 399元 | 2700 积分 |

#### 积分包
| 价格 | 积分 |
|------|------|
| 10元 | 50 积分 |
| 25元 | 140 积分 |
| 50元 | 300 积分 |

#### Scenario: 非会员购买积分包
- **WHEN** 用户完成支付购买积分包
- **THEN** 积分余额增加对应数量，积分永久有效

#### Scenario: 用户开通月卡会员
- **WHEN** 用户完成支付开通月卡
- **THEN** 用户获得会员身份（有效期30天），获得260积分（30天后清零），此后生成图片享受会员折扣

#### Scenario: 积分消耗失败（余额不足）
- **WHEN** 用户尝试生成图片但积分不足
- **THEN** 系统返回错误提示，不调用AI接口

---

### Requirement: AI图片生成
系统 SHALL 调用外部AI API生成图片，先生成单张图。先扣积分再调用AI，若AI调用失败则回滚积分。

#### Scenario: 生成成功
- **WHEN** 用户提交有效 prompt 且积分充足
- **THEN** 系统扣减积分 → 调用AI API → 返回图片URL → 记录生成历史

#### Scenario: AI调用失败回滚
- **WHEN** 积分扣减成功但AI API返回错误或超时
- **THEN** 系统回滚积分，返回错误信息给用户

#### Scenario: 积分不足
- **WHEN** 用户积分余额不足以支付所选质量等级的消耗
- **THEN** 系统返回积分不足错误，不扣积分，不调用AI

---

### Requirement: 支付模拟
系统 SHALL 提供模拟支付流程：创建订单 → 返回模拟支付信息 → 手动回调确认 → 更新积分或激活会员。

#### Scenario: 创建积分包订单
- **WHEN** 用户选择积分包并请求创建订单
- **THEN** 系统生成订单（含 `order_no`），返回模拟支付信息

#### Scenario: 支付回调成功
- **WHEN** 系统收到有效的支付回调（`POST /api/mock-pay-callback?order_no=xxx`）
- **THEN** 订单状态更新为已支付，积分增加或会员激活

---

### Requirement: 生成历史记录
系统 SHALL 提供接口查询当前用户最近的图片生成记录。

#### Scenario: 查询历史
- **WHEN** 已登录用户请求 `GET /api/history`
- **THEN** 返回该用户的生成记录列表，包含 prompt、图片URL、消耗积分、创建时间

---

### Requirement: 部署支持
系统 SHALL 提供 systemd 服务文件、Nginx 配置、部署脚本和使用说明。
