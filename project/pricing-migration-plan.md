# 2Bis 计费模型改造执行计划

## 1. 目标

将当前项目从“积分包 + 会员折扣 + 每日登录免费积分”模型，改造成“体验积分 + 新手体验包 + 订阅额度”模型，并保证以下目标同时成立：

1. 用户能清楚区分免费体验能力和正式付费能力。
2. 高质量生成必须和正式付费能力绑定。
3. 扣费、退款、支付回调、前端展示全部使用同一套计费语义。
4. 在项目尚未正式上线的前提下，优先选择最简单、最稳定、最易验证的实现路径。

## 2. 当前项目现状

当前代码实际采用的是旧计费模型，核心特征如下：

1. `User` 仍使用 `points`、`free_points`、`is_member`、`member_expire_at` 作为账户状态。
2. 生成扣费依赖 `PointManager`，会员与非会员通过不同 cost table 计算消耗。
3. 免费积分和普通积分在扣费、退款上并没有完整记录来源。
4. 支付订单仍是 `points_pack` 和 `membership` 两种类型。
5. 前端页面、状态 store、文档说明都围绕旧模型实现。

这意味着本次改造不是页面改文案，而是一次完整的计费域重构。

## 3. 新模型定义

### 3.1 体验积分

体验积分对应当前 `free_points`，仅用于免费体验。

规则：

1. 来源仅为每日签到奖励。
2. 默认有效期 10 天。
3. 仅支持低质量和中质量生成。
4. 不支持高质量生成。
5. 前端统一展示名称为“体验积分”。

### 3.2 新手体验包

新手体验包是低价的一次性试用产品，用于承接高意向新用户。

建议规则：

1. 售价 `5` 元。
2. 有效期 `7` 天。
3. 发放 `30` 订阅额度。
4. 每个用户仅允许购买一次。
5. 允许高质量生成。

### 3.3 订阅额度

订阅额度是正式付费能力，作为主收入模型。

统一扣费规则：

1. 低质量：1 额度。
2. 中质量：2 额度。
3. 高质量：3 额度。

建议套餐：

1. 轻量版：`29/月`，`268/年`，每月 `100` 额度。
2. 创作版：`69/月`，`628/年`，每月 `350` 额度。
3. 专业版：`149/月`，`1368/年`，每月 `800` 额度。

### 3.4 扣费优先级

这是整个改造中最重要的业务规则，必须全链路一致：

1. 低质量和中质量：优先消耗体验积分。
2. 当体验积分不足以完整支付本次消耗时，不做混合扣费，直接改扣订阅额度。
3. 高质量：只允许消耗体验包/订阅额度，不允许消耗体验积分。
4. 所有退款必须按实际扣费来源原路退回。

## 4. 关键业务规则

在进入开发前，以下规则必须先定死，否则实现容易反复返工。

### 4.1 订阅状态规则

1. 月付和年付都按“月额度”刷新。
2. 年付只是支付周期不同，不改变每月额度。
3. 第一版不做额度结转。
4. 续费同套餐时，订阅有效期顺延，但当前月剩余额度不叠加。
5. 升级套餐时，立即切换到新套餐，并将当前月额度重置为新套餐额度。
6. 降级套餐建议到下一个刷新周期生效，避免本月中途回退造成解释成本。

### 4.2 体验包和正式订阅关系

1. 体验包和正式订阅共用一套 `monthly_quota_remaining` 语义。
2. 用户购买正式订阅后，正式订阅状态覆盖体验包剩余额度语义。
3. 体验包到期后，如无正式订阅，则不可继续使用订阅额度。
4. 若已有正式订阅，体验包过期不影响正式订阅。

### 4.3 额度刷新时机

刷新不能只放在查余额接口里，必须同时出现在以下入口：

1. 查询余额前。
2. 生成扣费前。
3. 编辑扣费前。
4. 支付回调激活订阅时。

否则会出现“用户已到重置时间但未先查余额，直接生成时仍按旧额度扣费”的错误行为。

### 4.4 退款规则

退款必须覆盖所有失败路径：

1. 创建任务成功，但任务入队失败。
2. worker 最终重试失败。
3. 支付回调重复触发。
4. 异步处理过程中发生异常。

退款必须依赖 `balance_source`，不能再默认退回某一种余额。

## 5. 实施范围

## 5.1 后端

涉及文件：

1. [backend/app/models.py](/D:/Open_of/2Bis/backend/app/models.py)
2. [backend/app/schemas.py](/D:/Open_of/2Bis/backend/app/schemas.py)
3. [backend/app/routers/auth.py](/D:/Open_of/2Bis/backend/app/routers/auth.py)
4. [backend/app/routers/payment.py](/D:/Open_of/2Bis/backend/app/routers/payment.py)
5. [backend/app/routers/points.py](/D:/Open_of/2Bis/backend/app/routers/points.py)
6. [backend/app/routers/generate.py](/D:/Open_of/2Bis/backend/app/routers/generate.py)
7. [backend/app/routers/edits.py](/D:/Open_of/2Bis/backend/app/routers/edits.py)
8. [backend/app/services/checkin_service.py](/D:/Open_of/2Bis/backend/app/services/checkin_service.py)
9. [backend/app/services/point_manager.py](/D:/Open_of/2Bis/backend/app/services/point_manager.py)
10. [backend/worker.py](/D:/Open_of/2Bis/backend/worker.py)
11. [backend/app/database.py](/D:/Open_of/2Bis/backend/app/database.py)
12. [backend/app/routers/membership.py](/D:/Open_of/2Bis/backend/app/routers/membership.py)

新增文件：

1. `backend/app/services/quota_manager.py`
2. 新的 Alembic migration 文件

## 5.2 前端

涉及文件：

1. [frontend/src/stores/points.js](/D:/Open_of/2Bis/frontend/src/stores/points.js)
2. [frontend/src/stores/user.js](/D:/Open_of/2Bis/frontend/src/stores/user.js)
3. [frontend/src/stores/tasks.js](/D:/Open_of/2Bis/frontend/src/stores/tasks.js)
4. [frontend/src/router/index.js](/D:/Open_of/2Bis/frontend/src/router/index.js)
5. [frontend/src/views/Recharge.vue](/D:/Open_of/2Bis/frontend/src/views/Recharge.vue)
6. [frontend/src/views/Home.vue](/D:/Open_of/2Bis/frontend/src/views/Home.vue)
7. [frontend/src/views/History.vue](/D:/Open_of/2Bis/frontend/src/views/History.vue)
8. [frontend/src/components/NavBar.vue](/D:/Open_of/2Bis/frontend/src/components/NavBar.vue)
9. [frontend/src/components/GenerateForm.vue](/D:/Open_of/2Bis/frontend/src/components/GenerateForm.vue)
10. [frontend/src/components/TaskCard.vue](/D:/Open_of/2Bis/frontend/src/components/TaskCard.vue)

## 5.3 文档

涉及文件：

1. [README.md](/D:/Open_of/2Bis/README.md)
2. 本文档

## 6. 分阶段实施计划

### Phase 1: 规则冻结

目标：先把业务边界定死，再开始写代码。

需要确认：

1. 升级是否立即重置额度。
2. 降级是否下月生效。
3. 年付续费是否只顺延有效期，不追加当前月额度。
4. 体验包转正式订阅时，是否直接覆盖体验包剩余额度。
5. `/recharge` 是重命名为 `/plans` 还是临时兼容一版。

交付物：

1. 最终业务规则清单。
2. 本执行计划冻结版。

### Phase 2: 数据模型与迁移

目标：先把数据库结构调整到能承载新模型。

任务：

1. 在 `User` 上新增：
   - `subscription_plan`
   - `subscription_period`
   - `monthly_quota_total`
   - `monthly_quota_remaining`
   - `monthly_quota_reset_at`
   - `trial_activated`
   - `trial_expire_at`
   - `trial_high_quality_used`
2. 在 `Order` 上新增 `plan_period`。
3. 在 `GenerationTask` 和 `GenerateHistory` 上新增 `balance_source`。
4. 保留旧字段，不在第一版删除。
5. 新增 Alembic migration。
6. 同步更新 `backend/app/database.py` 中的启动补丁逻辑，避免 SQLite 本地开发失真。

验收标准：

1. 数据库可升级。
2. 老数据不会因缺列而启动失败。
3. 旧字段仍可读，但新业务链路不再依赖它们。

### Phase 3: 结算服务重构

目标：把扣费和退款逻辑统一收口。

任务：

1. 新建 `QuotaManager`，负责：
   - 额度刷新
   - 生成扣费
   - 退款
   - 体验包激活
   - 订阅激活
2. 保留 `PointManager` 仅做兼容期参考，不再作为主业务入口。
3. 所有扣费决策基于 `quality` 判断，而不是基于 cost 数值判断。
4. 所有退款都依赖 `balance_source`。

验收标准：

1. 低/中质量优先走体验积分。
2. 高质量始终不走体验积分。
3. 退款能正确退回体验积分或订阅额度。
4. 并发扣费不会把余额扣成负数。

### Phase 4: 支付与订单改造

目标：把支付链路切换到新商品模型。

任务：

1. `OrderCreate.order_type` 改为只接受 `trial | subscription`。
2. 新增 `plan_period`，订阅时必须指定 `monthly` 或 `yearly`。
3. 下单金额基于新套餐表计算。
4. mock callback 按订单类型调用 `QuotaManager.activate_trial` 或 `QuotaManager.activate_subscription`。
5. 重复回调保持幂等。
6. 处理旧接口：
   - `/points/packs` 下架或返回空结果
   - `/membership/plans` 替换或废弃

验收标准：

1. 体验包订单可下单、可支付、可激活。
2. 月付和年付订阅可下单、可支付、可激活。
3. 重复回调不会重复发放额度。

### Phase 5: 生成与退款链路改造

目标：打通“创建任务 -> 扣费 -> 入队 -> worker -> 成功或退款”的闭环。

任务：

1. 改 `generate.py` 与 `edits.py`，统一调用 `QuotaManager.deduct_for_generation(...)`。
2. 将本次扣费来源写入 `GenerationTask.balance_source`。
3. 入队失败时不再直接加普通积分，而是调用统一退款逻辑。
4. worker 最终失败时根据 `balance_source` 原路退款。
5. 历史记录保存 `points_cost` 与 `balance_source`。

验收标准：

1. 低/中/高质量任务都能按规则正确扣费。
2. 入队失败时余额能恢复。
3. worker 失败时余额能恢复。
4. 重试过程中不会重复扣费。

### Phase 6: 认证与余额接口改造

目标：让登录态和前端状态源切到新模型。

任务：

1. 调整 `auth.py` 中注册默认值。
2. 调整登录返回和用户信息结构。
3. 调整 `/points/balance` 响应，返回：
   - `free_points`
   - `free_points_expire_at`
   - `monthly_quota_remaining`
   - `monthly_quota_total`
   - `monthly_quota_reset_at`
   - `subscription_plan`
   - `subscription_period`
   - `trial_activated`
   - `trial_expire_at`
4. 查询余额时做过期体验积分清理和订阅额度刷新。

验收标准：

1. 登录后前端可拿到完整新余额结构。
2. 体验积分过期后自动清零。
3. 订阅到刷新时间后自动更新本月额度。

### Phase 7: 前端状态层改造

目标：让前端所有页面从同一套余额结构读取状态。

任务：

1. 改 `points.js`：
   - `freePoints`
   - `monthlyQuotaRemaining`
   - `monthlyQuotaTotal`
   - `quotaResetAt`
   - `subscriptionPlan`
   - `subscriptionPeriod`
   - `trialActivated`
   - `trialExpireAt`
2. 改 `user.js`，不要再只依赖 `isMember`。
3. 改 `tasks.js`，支持同步 `balance_source`。

验收标准：

1. 用户状态、余额状态、任务状态不再分裂。
2. 登录、支付、生成后余额显示一致。

### Phase 8: 前端页面与文案改造

目标：把界面语义从“充值/会员/积分包”切到“计划/体验积分/订阅额度”。

任务：

1. 将 [frontend/src/views/Recharge.vue](/D:/Open_of/2Bis/frontend/src/views/Recharge.vue) 改造成 plans 页面。
2. 路由从 `/recharge` 切到 `/plans`，旧路由可重定向。
3. `NavBar` 显示体验积分和订阅额度。
4. `GenerateForm` 与 `Home` 明确提示不同质量对应的消耗规则。
5. `History` 与 `TaskCard` 展示消耗来源。
6. 所有“会员折扣”“赠送积分”“积分包永久有效”旧文案全部清理。

验收标准：

1. 用户能看懂免费体验、体验包、订阅三者区别。
2. 余额不足提示能区分低/中质量和高质量场景。
3. 历史记录中能看到消耗来源。

### Phase 9: 文档与清理

目标：避免代码和说明脱节。

任务：

1. 更新 README 的计费说明、接口说明、数据模型说明。
2. 标记或移除废弃接口文档。
3. 检查代码中所有旧术语：
   - `membership`
   - `points_pack`
   - `is_member`
   - “充值”
   - “会员折扣”

验收标准：

1. README 与实际代码行为一致。
2. 无明显旧模型残留入口误导开发或测试。

## 7. 建议实现顺序

推荐按下面顺序落地，避免前后端同时大改导致难以定位问题：

1. 先完成数据模型和 migration。
2. 再完成 `QuotaManager` 和后端结算链路。
3. 再改支付与余额接口。
4. 然后改前端 store。
5. 最后改页面与文案。
6. 最后统一更新文档和清理旧接口。

## 8. 测试计划

### 8.1 后端单元测试

覆盖 `QuotaManager`：

1. 低质量优先扣体验积分。
2. 中质量优先扣体验积分。
3. 高质量禁止扣体验积分。
4. 体验积分不足时切换到订阅额度。
5. 扣费失败时余额不变。
6. 原路退款正确恢复。
7. 并发扣费不出现负数。

### 8.2 后端接口测试

覆盖支付链路：

1. 创建体验包订单。
2. 创建月付订阅订单。
3. 创建年付订阅订单。
4. 非法 `order_type`。
5. 缺失或非法 `plan_period`。
6. 重复回调幂等。

覆盖生成链路：

1. 创建任务扣费成功。
2. 入队失败退款成功。
3. worker 失败退款成功。
4. 重试过程中不重复扣费。

覆盖签到与余额链路：

1. 签到奖励发放。
2. 体验积分过期清零。
3. 月额度刷新。

### 8.3 前端手测

1. 登录后导航栏显示新余额结构。
2. plans 页面展示体验包、月付、年付方案。
3. 高质量按钮在无订阅额度时给出正确引导。
4. 历史页能看到扣费来源。
5. 支付成功后首页和导航栏余额同步更新。

## 9. 验收标准

本项目在完成改造后，至少应满足以下条件：

1. 系统中不存在新的 `points_pack` 或 `membership` 下单入口。
2. 高质量生成不能再通过体验积分完成。
3. 体验积分、体验包、正式订阅三套语义清晰且不冲突。
4. 扣费和退款在所有失败路径上都能保持一致。
5. 前端不会再把“订阅用户”简单等同于旧的 `is_member`。
6. 文档、接口、页面文案全部切换到新模型。

## 10. 风险提示

1. 这是领域模型重构，不是 UI 改版，优先保证账务链路正确。
2. 若不先统一 `QuotaManager`，后续退款、并发、重试会持续出错。
3. 若只改页面不改 store 和 auth，同一用户在不同页面会看到不同余额状态。
4. 若只在余额接口里做额度刷新，生成时会出现过期状态扣费错误。

## 11. 最终结论

这次改造的正确方向不是继续修补旧的“积分包 + 会员折扣”逻辑，而是彻底收敛成三层模型：

1. 免费体验：体验积分。
2. 低价完整试用：新手体验包。
3. 正式持续付费：订阅额度。

按这个方向实施，产品表达更简单，后端结算更稳定，前端展示也更容易统一。
